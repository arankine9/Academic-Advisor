# New unified_program_service.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
import json
import os
from pathlib import Path
from fastapi import HTTPException

from backend.core.database import UserProgram, User
from backend.models.schemas import ProgramCreate, ProgramResponse

# Path to the program requirements files
PROGRAMS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "programs"

class UnifiedProgramService:
    """
    A unified service for all program-related operations.
    Completely replaces the major system with a program-based approach.
    """
    
    @staticmethod
    def get_available_programs() -> List[Dict[str, Any]]:
        """
        Gets all available program templates from the undergraduate/majors directory.
        """
        programs = []
        
        # Define the specific directory to search
        majors_dir = PROGRAMS_DIR / "undergraduate" / "majors"
        
        if not majors_dir.exists():
            return programs
        
        # Search for all JSON files in the majors directory
        for file_path in majors_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    program_data = json.load(f)
                
                    # Get filename without extension as the ID
                    program_id = file_path.stem
                    
                    # Set the ID with the full path
                    program_data["id"] = f"undergraduate/majors/{program_id}"
                    # Set category to "majors" since we're only looking in the majors directory
                    program_data["category"] = "majors"
                
                    programs.append(program_data)
            except Exception as e:
                print(f"Error loading program {file_path}: {e}")
        
        return programs
    
    @staticmethod
    def get_user_programs(db: Session, user_id: int) -> List[UserProgram]:
        """
        Gets all programs for a user.
        """
        return db.query(UserProgram).filter(UserProgram.user_id == user_id).all()
    
    @staticmethod
    def get_user_majors(db: Session, user_id: int) -> List[UserProgram]:
        """
        Gets all major programs for a user.
        """
        return db.query(UserProgram).filter(
            UserProgram.user_id == user_id,
            UserProgram.program_type == "major"
        ).all()
    
    @staticmethod
    def get_program_by_name(db: Session, user_id: int, program_name: str) -> Optional[UserProgram]:
        """
        Gets a specific program for a user by name.
        """
        return db.query(UserProgram).filter(
            UserProgram.user_id == user_id,
            UserProgram.program_name == program_name
        ).first()
    
    @staticmethod
    def create_program(db: Session, user_id: int, program: ProgramCreate) -> UserProgram:
        """
        Creates a new program for a user.
        """
        # Check if user exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
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
    
    @staticmethod
    def update_program(db: Session, user_id: int, program_name: str, updated_program: Dict[str, Any]) -> Optional[UserProgram]:
        """
        Updates a user's program.
        """
        program = UnifiedProgramService.get_program_by_name(db, user_id, program_name)
        if not program:
            return None
        
        # Update fields
        for key, value in updated_program.items():
            if hasattr(program, key):
                setattr(program, key, value)
        
        db.commit()
        db.refresh(program)
        return program
    
    @staticmethod
    def delete_program(db: Session, user_id: int, program_name: str) -> bool:
        """
        Deletes a user's program.
        """
        program = UnifiedProgramService.get_program_by_name(db, user_id, program_name)
        if not program:
            return False
        
        db.delete(program)
        db.commit()
        return True
    
    @staticmethod
    def load_program_template(program_id: str) -> Dict[str, Any]:
        """
        Loads program requirements from a JSON file.
        """
        file_path = PROGRAMS_DIR / f"{program_id}.json"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Program template {program_id} not found")
        
        with open(file_path, "r") as f:
            return json.load(f)
    
    @staticmethod
    def assign_program_to_user(db: Session, user_id: int, program_id: str) -> UserProgram:
        """
        Assigns a program template to a user.
        """
        # Load program requirements
        program_data = UnifiedProgramService.load_program_template(program_id)
        
        # Create program
        program = ProgramCreate(
            program_type=program_data["program_type"],
            program_name=program_data["program_name"],
            required_courses=program_data["required_courses"]
        )
        
        # Check if this program already exists for the user
        existing_program = UnifiedProgramService.get_program_by_name(db, user_id, program.program_name)
        if existing_program:
            # Update the existing program
            for key, value in program.dict().items():
                setattr(existing_program, key, value)
            db.commit()
            db.refresh(existing_program)
            return existing_program
        
        # Create new program for user
        return UnifiedProgramService.create_program(db, user_id, program)
    
    @staticmethod
    def format_user_progress(db: Session, user_id: int) -> str:
        """
        Formats the user's academic progress information for the RAG system.
        """
        # Get user with related data
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return "No user data found."
        
        # Get programs
        programs = UnifiedProgramService.get_user_programs(db, user_id)
        
        # Format the data for RAG
        result = []
        
        # Add programs information
        result.append(f"The user has the following academic programs:")
        for program in programs:
            program_type = program.program_type.capitalize()
            result.append(f"- {program_type}: {program.program_name}")
        
        # Add completed courses
        result.append("\nThey have completed these courses:")
        for course in user.courses:
            result.append(f"- {course.course_code}")
        
        # Add required courses for each program
        for program in programs:
            result.append(f"\nThe required courses for their {program.program_name} {program.program_type} include:")
            
            required_courses = program.required_courses
            if isinstance(required_courses, list):
                for course in required_courses:
                    if isinstance(course, str):
                        result.append(f"- {course}")
                    elif isinstance(course, dict):
                        if "course_code" in course:
                            result.append(f"- {course['course_code']}")
                        elif "requirement_name" in course and "options" in course:
                            result.append(f"- {course['requirement_name']} (Need {course.get('courses_needed', 1)} course(s)):")
                            
                            options = course["options"]
                            for option in options:
                                if isinstance(option, str):
                                    result.append(f"  * {option}")
                                elif isinstance(option, dict) and "course_code" in option:
                                    result.append(f"  * {option['course_code']}")
        
        result.append("\nIt is currently Spring 2025. Recommend which classes they should take next term to stay on track.")
        
        return "\n".join(result)

# Create a global instance of the service
program_service = UnifiedProgramService()