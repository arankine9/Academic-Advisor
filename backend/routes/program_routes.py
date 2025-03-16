from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.schemas import UserProgramCreate, UserProgramResponse, UserResponse
from backend.services import programs

router = APIRouter(
    prefix="/programs",
    tags=["programs"],
    responses={404: {"description": "Not found"}},
)

@router.get("/templates", response_model=List[dict])
def get_available_programs():
    """
    Get all available program templates.
    """
    return programs.get_available_programs()

@router.post("/templates/{program_id}/assign", response_model=UserProgramResponse)
def assign_program_template(
    program_id: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Assign a program template to the current user.
    """
    result = programs.assign_program_to_user(db, current_user.id, program_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program template {program_id} not found",
        )
    return result

@router.post("/", response_model=UserProgramResponse)
def create_program(
    program: UserProgramCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new program (major or minor) for the current user.
    """
    result = programs.create_user_program(db, current_user.id, program)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create program",
        )
    return result

@router.get("/", response_model=List[UserProgramResponse])
def get_programs(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all programs for the current user.
    """
    return programs.get_user_programs(db, current_user.id)

@router.get("/{program_name}", response_model=UserProgramResponse)
def get_program(
    program_name: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific program by name for the current user.
    """
    program = programs.get_program_by_name(db, current_user.id, program_name)
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program {program_name} not found",
        )
    return program

@router.delete("/{program_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(
    program_name: str,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a program by name for the current user.
    """
    result = programs.delete_user_program(db, current_user.id, program_name)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program {program_name} not found",
        )
    return {"detail": "Program deleted successfully"}

@router.put("/{program_name}", response_model=UserProgramResponse)
def update_program(
    program_name: str,
    program_update: UserProgramCreate,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a program by name for the current user.
    """
    # Convert Pydantic model to dict
    program_data = program_update.dict()
    
    result = programs.update_user_program(db, current_user.id, program_name, program_data)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program {program_name} not found",
        )
    return result

@router.get("/progress", response_model=dict)
def get_user_progress(
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the user's progress information for RAG system input.
    This returns both completed courses and required courses.
    """
    progress_data = programs.get_required_and_completed_courses(db, current_user.id)
    if not progress_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User progress data not found",
        )
    return progress_data 