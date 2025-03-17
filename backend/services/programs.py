from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import json
import os
from pathlib import Path

from backend.core.database import UserProgram, User
from backend.models.schemas import UserProgramCreate, UserProgramResponse

"""
This file handles the user's academic programs (majors and minors).
It manages the programs a user is enrolled in and their required courses.

Functions:
- create_user_program: Creates a new program for a user
- get_user_programs: Gets all programs for a user
- get_program_by_name: Gets a specific program for a user
- update_user_program: Updates a user's program
- delete_user_program: Deletes a user's program
- get_remaining_courses: Compares completed courses with required courses
- load_program_requirements: Loads program requirements from JSON files
- get_available_programs: Lists all available programs
- assign_program_to_user: Assigns a program to a user from available templates
"""

# Path to the program requirements files
PROGRAMS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "programs"

def load_program_requirements(program_id: str) -> Dict[str, Any]:
    """
    Loads program requirements from a JSON file.
    
    Args:
        program_id: ID of the program (filename without .json)
    
    Returns:
        Dict with program requirements or None if not found
    """
    file_path = PROGRAMS_DIR / f"{program_id}.json"
    
    if not file_path.exists():
        return None
    
    with open(file_path, "r") as f:
        return json.load(f)

def get_available_programs() -> List[Dict[str, Any]]:
    """
    Gets all available program templates.
    
    Returns:
        List of program templates
    """
    programs = []
    
    if not PROGRAMS_DIR.exists():
        return programs
    
    for file_path in PROGRAMS_DIR.glob("*.json"):
        try:
            with open(file_path, "r") as f:
                program_data = json.load(f)
                program_data["id"] = file_path.stem  # Add the filename (without extension) as ID
                programs.append(program_data)
        except Exception as e:
            print(f"Error loading program {file_path}: {e}")
    
    return programs

def assign_program_to_user(db: Session, user_id: int, program_id: str) -> Dict[str, Any]:
    """
    Assigns a program template to a user.
    
    Args:
        db: Database session
        user_id: ID of the user
        program_id: ID of the program template
    
    Returns:
        Created program or None if not found
    """
    # Load program requirements
    program_data = load_program_requirements(program_id)
    if not program_data:
        return None
    
    # Create program
    program = UserProgramCreate(
        program_type=program_data["program_type"],
        program_name=program_data["program_name"],
        required_courses=program_data["required_courses"]
    )
    
    # Assign to user
    return create_user_program(db, user_id, program)

def create_user_program(db: Session, user_id: int, program: UserProgramCreate):
    """
    Creates a new program for a user.
    
    Args:
        db: Database session
        user_id: ID of the user
        program: Program information
    
    Returns:
        Created program
    """
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    # Create program
    db_program = UserProgram(
        user_id=user_id,
        program_type=program.program_type,
        program_name=program.program_name,
        required_courses=program.required_courses
    )
    
    db.add(db_program)
    db.commit()
    db.refresh(db_program)
    return db_program

def get_user_programs(db: Session, user_id: int):
    """
    Gets all programs for a user.
    
    Args:
        db: Database session
        user_id: ID of the user
    
    Returns:
        List of user programs
    """
    return db.query(UserProgram).filter(UserProgram.user_id == user_id).all()

def get_program_by_name(db: Session, user_id: int, program_name: str):
    """
    Gets a specific program for a user by name.
    
    Args:
        db: Database session
        user_id: ID of the user
        program_name: Name of the program
    
    Returns:
        Program or None
    """
    return db.query(UserProgram).filter(
        UserProgram.user_id == user_id,
        UserProgram.program_name == program_name
    ).first()

def update_user_program(db: Session, user_id: int, program_name: str, updated_program: Dict[str, Any]):
    """
    Updates a user's program.
    
    Args:
        db: Database session
        user_id: ID of the user
        program_name: Name of the program to update
        updated_program: Updated program information
    
    Returns:
        Updated program or None
    """
    program = get_program_by_name(db, user_id, program_name)
    if not program:
        return None
    
    # Update fields
    for key, value in updated_program.items():
        if hasattr(program, key):
            setattr(program, key, value)
    
    db.commit()
    db.refresh(program)
    return program

def delete_user_program(db: Session, user_id: int, program_name: str):
    """
    Deletes a user's program.
    
    Args:
        db: Database session
        user_id: ID of the user
        program_name: Name of the program to delete
    
    Returns:
        True if successful, False otherwise
    """
    program = get_program_by_name(db, user_id, program_name)
    if not program:
        return False
    
    db.delete(program)
    db.commit()
    return True

def get_required_and_completed_courses(db: Session, user_id: int):
    """
    Gets both required and completed courses for a user for all their programs.
    
    Args:
        db: Database session
        user_id: ID of the user
    
    Returns:
        Dict with required and completed courses
    """
    # Get user with completed courses
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    # Get completed courses - simplify to just course codes
    completed_courses = []
    for course in user.courses:
        completed_courses.append({
            "course_code": course.course_code
        })
    
    # Get programs and required courses
    programs = get_user_programs(db, user_id)
    required_by_program = {}
    
    for program in programs:
        required_by_program[program.program_name] = {
            "program_type": program.program_type,
            "required_courses": program.required_courses
        }
    
    return {
        "completed_courses": completed_courses,
        "programs": required_by_program
    }

def format_courses_for_rag(db: Session, user_id: int) -> str:
    """
    Formats the user's courses and programs information for the RAG system.
    
    Args:
        db: Database session
        user_id: ID of the user
    
    Returns:
        Formatted string for RAG
    """
    data = get_required_and_completed_courses(db, user_id)
    if not data:
        return "No user data found."
    
    # Get user info
    user = db.query(User).filter(User.id == user_id).first()
    
    # Format the data for RAG
    result = []
    result.append(f"The user has the following academic programs:")
    
    for program_name, program_data in data["programs"].items():
        program_type = program_data["program_type"].capitalize()
        result.append(f"- {program_type}: {program_name}")
    
    result.append("\nThey have completed these courses:")
    for course in data["completed_courses"]:
        # For completed courses, just use the course code
        result.append(f"- {course['course_code']}")
    
    for program_name, program_data in data["programs"].items():
        program_type = program_data["program_type"].capitalize()
        result.append(f"\nThe required courses for their {program_name} {program_data['program_type']} include:")
        
        required_courses = program_data["required_courses"]
        if isinstance(required_courses, list):
            for course in required_courses:
                if isinstance(course, str):
                    # Just the course code
                    result.append(f"- {course}")
                elif isinstance(course, dict):
                    if "course_code" in course:
                        # Just the course code
                        result.append(f"- {course['course_code']}")
                    elif "requirement_name" in course and "options" in course:
                        # Course options (OR relationship)
                        result.append(f"- {course['requirement_name']} (Need {course.get('courses_needed', 1)} course(s)):")
                        
                        options = course["options"]
                        for option in options:
                            if isinstance(option, str):
                                # Just the course code
                                result.append(f"  * {option}")
                            elif isinstance(option, dict) and "course_code" in option:
                                # Just the course code from dict
                                result.append(f"  * {option['course_code']}")
    
    result.append("\nIt is currently Spring 2025. Recommend which classes they should take next term to stay on track.")
    
    return "\n".join(result) 