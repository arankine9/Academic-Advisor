from fastapi import APIRouter, Depends, HTTPException, status, Form, Body, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Optional, Dict, Any
import logging
import asyncio
from fastapi.concurrency import run_in_threadpool

from backend.core.database import get_db, Course, SessionLocal
from backend.core.auth import authenticate_user, create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES, create_user
from backend.core.database import User as UserModel
from backend.models.schemas import Token, UserCreate, CourseResponse, ChatMessage, User as UserSchema, ProgramResponse
from backend.services.unified_course_service import course_service
from backend.services.recommendation_service import recommendation_service
from backend.services.unified_program_service import program_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# In-memory response cache
_processing_responses = {}

# Authentication endpoints
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=Token)
async def register(
    username: str = Form(...),
    email: str = Form(...), 
    password: str = Form(...),
    program_id: str = Form(...),  # Changed from major to program_id
    db: Session = Depends(get_db)
):
    # Check if username already exists
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create new user without setting legacy major field
    user_create = UserCreate(username=username, email=email, password=password)
    user = create_user(db, user_create)
    
    # Assign program to user
    try:
        program_service.assign_program_to_user(db, user.id, program_id)
    except HTTPException as e:
        logger.error(f"Error assigning program {program_id} to new user {username}: {e.detail}")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Return token
    return {"access_token": access_token, "token_type": "bearer"}

# User endpoints
@router.get("/users/me", response_model=UserSchema)
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    return current_user

# JSON version for React frontend
@router.post("/courses")
async def add_course_json(
    course_data: dict = Body(...),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Create course string from JSON data
        department = course_data.get("department", "").strip().upper()
        course_number = course_data.get("course_number", "").strip()
        course_string = f"{department} {course_number}"
        
        # Add course name if provided
        course_name = course_data.get("name", "").strip()
        if course_name:
            course_string = f"{course_string} - {course_name}"
            
        # Parse course and add term if provided
        course_create = course_service.parse_course_from_string(course_string)
        term = course_data.get("term")
        if term:
            course_create.term = term
            
        # Get or create course
        course = course_service.get_or_create_course(db, course_create)
        
        # Add course to user
        result = course_service.add_course_to_user(db, current_user.id, course.id)
        
        if not result:
            raise HTTPException(status_code=400, detail="Failed to add course to user")
            
        # Format response for frontend
        return {
            "id": course.id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "term": course.term,
            "credit_hours": course.credit_hours
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.delete("/courses/{course_id}")
async def remove_course(
    course_id: int, 
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Remove course from user
        course = course_service.remove_course_from_user(db, current_user.id, course_id)
        
        if not course:
            raise HTTPException(status_code=404, detail="Course not found or not associated with user")
        
        return {"status": "success", "message": f"Course {course.course_code} removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.put("/courses/{course_id}")
async def update_course(
    course_id: int,
    course_data: dict = Body(...),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Check if course exists and belongs to user
        user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
        course = db.query(Course).filter(Course.id == course_id).first()
        
        if not course or not user or course not in user.courses:
            raise HTTPException(status_code=404, detail="Course not found or not associated with user")
            
        # Update course
        department = course_data.get("department", "").strip().upper()
        course_number = course_data.get("course_number", "").strip()
        course.course_code = f"{department} {course_number}"
        
        if "name" in course_data:
            course.course_name = course_data["name"]
            
        if "term" in course_data:
            course.term = course_data["term"]
            
        db.commit()
        db.refresh(course)
        
        return {
            "id": course.id,
            "course_code": course.course_code,
            "course_name": course.course_name,
            "term": course.term,
            "credit_hours": course.credit_hours
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/courses/me", response_model=List[CourseResponse])
async def get_my_courses(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        courses = course_service.get_user_courses(db, current_user.id)
        return courses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Recommendation endpoints
@router.get("/recommend/me")
async def recommend_me(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Get recommendations using the unified service
        recommendations = await recommendation_service.process_query(db, current_user.id)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.post("/advising")
async def advising_chat(
    message: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Extract message from request
        message_text = message.message
        if not message_text:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Classify the intent of the query
        intent = recommendation_service.classify_intent(message_text)
        logger.info(f"Intent classification result: {intent}")
        
        if intent == "COURSE":
            # For course-related queries, send acknowledgment first
            acknowledgment = recommendation_service.generate_acknowledgment(message_text)
            
            # Process query in background
            background_tasks.add_task(
                process_advising_query_background,
                db, current_user.id, message_text
            )
            
            # Return acknowledgment with processing flag
            return {"response": acknowledgment, "processing": True}
        else:
            # For general conversation, process immediately
            response = recommendation_service.process_general_query(message_text)
            return {"response": response}
            
    except Exception as e:
        logger.error(f"Error in advising_chat: {e}")
        return {"response": "I'm sorry, I encountered an error. Please try again later or try rephrasing your question."}

async def process_advising_query_background(db: Session, user_id: int, query: str):
    """Process an advising query in the background and store the result"""
    try:
        # Create a new session since we're in a background task
        db_session = SessionLocal()
        
        # Run the CPU-intensive process in a thread pool
        result = await run_in_threadpool(
            lambda: recommendation_service.process_query(db_session, user_id, query)
        )
        
        # Store the result in the cache
        _processing_responses[user_id] = result
        
    except Exception as e:
        logger.error(f"Background processing error: {e}")
        _processing_responses[user_id] = {
            "type": "error",
            "message": "I encountered an error while processing your request. Please try again."
        }
    finally:
        db_session.close()

@router.get("/advising/pending")
async def check_pending_response(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Check if there's a pending response for the user"""
    response = _processing_responses.get(current_user.id)
    
    if response:
        # Remove from cache after retrieving
        del _processing_responses[current_user.id]
        return {"response": response, "pending": False}
    
    return {"pending": True}

# Program endpoints (replacing major endpoints)
@router.get("/programs/available", response_model=List[Dict[str, Any]])
async def get_available_program_options():
    """
    Get a list of all available program options.
    """
    try:
        programs = program_service.get_available_programs()
        return programs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/programs/me", response_model=List[ProgramResponse])
async def get_my_programs(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all programs for the current user.
    """
    try:
        programs = program_service.get_user_programs(db, current_user.id)
        return programs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.post("/programs", response_model=ProgramResponse)
async def add_program(
    program_data: dict = Body(...),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Add a program to the current user.
    """
    try:
        # If program_id is provided, use the program template
        if "program_id" in program_data:
            program_id = program_data.get("program_id")
            program = program_service.assign_program_to_user(db, current_user.id, program_id)
            return program
        
        # Otherwise, create a custom program
        program_type = program_data.get("program_type")
        program_name = program_data.get("program_name")
        required_courses = program_data.get("required_courses", [])
        
        if not program_type or not program_name:
            raise HTTPException(status_code=400, detail="Program type and name are required")
        
        # Create program
        program_create = {
            "program_type": program_type,
            "program_name": program_name,
            "required_courses": required_courses
        }
        
        program = program_service.create_program(db, current_user.id, program_create)
        
        return program
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.delete("/programs/{program_name}", response_model=dict)
async def remove_program(
    program_name: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a program from the current user.
    """
    try:
        success = program_service.delete_program(db, current_user.id, program_name)
        
        if not success:
            raise HTTPException(status_code=404, detail="Program not found or not associated with user")
        
        return {"status": "success", "message": f"Program {program_name} removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/programs/progress", response_model=dict)
async def get_progress(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get formatted progress information for the current user.
    """
    try:
        progress = program_service.format_user_progress(db, current_user.id)
        return {"progress": progress}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")