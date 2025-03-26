# New unified_program_service.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Union
import json
import os
import traceback
from pathlib import Path
from fastapi import HTTPException

from backend.core.database import UserProgram, User
from backend.models.schemas import ProgramCreate, ProgramResponse

# Configure logging
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Path to the program requirements files
PROGRAMS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "programs"
logger.info(f"Programs directory path: {PROGRAMS_DIR}")

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
        logger.debug("Getting available programs")
        programs = []
        
        # Define the specific directory to search
        majors_dir = PROGRAMS_DIR / "undergraduate" / "majors"
        logger.debug(f"Looking for majors in directory: {majors_dir}")
        
        if not majors_dir.exists():
            logger.warning(f"Majors directory does not exist: {majors_dir}")
            return programs
        
        # Search for all JSON files in the majors directory
        logger.debug("Searching for JSON files in majors directory")
        json_files = list(majors_dir.glob("*.json"))
        logger.debug(f"Found {len(json_files)} JSON files")
        
        for file_path in json_files:
            try:
                logger.debug(f"Loading program from file: {file_path}")
                with open(file_path, "r") as f:
                    program_data = json.load(f)
                
                    # Get filename without extension as the ID
                    program_id = file_path.stem
                    logger.debug(f"Program ID from filename: {program_id}")
                    
                    # Set the ID with the full path
                    program_data["id"] = f"undergraduate/majors/{program_id}"
                    # Set category to "majors" since we're only looking in the majors directory
                    program_data["category"] = "majors"
                    
                    logger.debug(f"Loaded program '{program_data.get('program_name', 'Unknown')}'")
                    programs.append(program_data)
            except Exception as e:
                logger.error(f"Error loading program {file_path}: {e}")
                logger.error(traceback.format_exc())
        
        logger.info(f"Loaded {len(programs)} available programs")
        program_names = [p.get('program_name', 'Unknown') for p in programs]
        logger.debug(f"Available programs: {program_names}")
        return programs
    
    @staticmethod
    def get_user_programs(db: Session, user_id: int) -> List[UserProgram]:
        """
        Gets all programs for a user.
        """
        logger.debug(f"Getting all programs for user {user_id}")
        
        try:
            programs = db.query(UserProgram).filter(UserProgram.user_id == user_id).all()
            logger.debug(f"Found {len(programs)} programs for user {user_id}")
            
            if len(programs) > 0:
                program_names = [p.program_name for p in programs]
                logger.debug(f"Programs: {program_names}")
                
            return programs
        except Exception as e:
            logger.error(f"Error getting user programs: {e}")
            logger.error(traceback.format_exc())
            return []
    
    @staticmethod
    def get_user_majors(db: Session, user_id: int) -> List[UserProgram]:
        """
        Gets all major programs for a user.
        """
        logger.debug(f"Getting major programs for user {user_id}")
        
        try:
            programs = db.query(UserProgram).filter(
                UserProgram.user_id == user_id,
                UserProgram.program_type == "major"
            ).all()
            
            logger.debug(f"Found {len(programs)} major programs for user {user_id}")
            
            if len(programs) > 0:
                program_names = [p.program_name for p in programs]
                logger.debug(f"Major programs: {program_names}")
                
            return programs
        except Exception as e:
            logger.error(f"Error getting user majors: {e}")
            logger.error(traceback.format_exc())
            return []
    
    @staticmethod
    def get_program_by_name(db: Session, user_id: int, program_name: str) -> Optional[UserProgram]:
        """
        Gets a specific program for a user by name.
        """
        logger.debug(f"Getting program '{program_name}' for user {user_id}")
        
        try:
            program = db.query(UserProgram).filter(
                UserProgram.user_id == user_id,
                UserProgram.program_name == program_name
            ).first()
            
            if program:
                logger.debug(f"Found program: {program.id} - {program.program_name}")
            else:
                logger.debug(f"Program '{program_name}' not found for user {user_id}")
                
            return program
        except Exception as e:
            logger.error(f"Error getting program by name: {e}")
            logger.error(traceback.format_exc())
            return None
    
    @staticmethod
    def create_program(db: Session, user_id: int, program: ProgramCreate) -> UserProgram:
        """
        Creates a new program for a user.
        """
        logger.debug(f"Creating program '{program.program_name}' for user {user_id}")
        
        try:
            # Check if user exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                raise HTTPException(status_code=404, detail="User not found")
            
            # Create program
            logger.debug(f"Creating new UserProgram: {program.program_name} ({program.program_type})")
            db_program = UserProgram(
                user_id=user_id,
                program_type=program.program_type,
                program_name=program.program_name,
                required_courses=program.required_courses
            )
            
            # Add to session and commit
            logger.debug("Adding program to database session")
            db.add(db_program)
            
            logger.debug("Committing to database")
            db.commit()
            
            logger.debug("Refreshing program object")
            db.refresh(db_program)
            
            logger.info(f"Created program: {db_program.id} - {db_program.program_name} for user {user_id}")
            return db_program
        except Exception as e:
            logger.error(f"Error creating program: {e}")
            logger.error(traceback.format_exc())
            # Roll back the transaction
            db.rollback()
            raise
    
    @staticmethod
    def update_program(db: Session, user_id: int, program_name: str, updated_program: Dict[str, Any]) -> Optional[UserProgram]:
        """
        Updates a user's program.
        """
        logger.debug(f"Updating program '{program_name}' for user {user_id}")
        logger.debug(f"Update data: {updated_program}")
        
        try:
            program = UnifiedProgramService.get_program_by_name(db, user_id, program_name)
            if not program:
                logger.warning(f"Program '{program_name}' not found for user {user_id}")
                return None
            
            # Log current state
            logger.debug(f"Current program state: {program.__dict__}")
            
            # Update fields
            for key, value in updated_program.items():
                if hasattr(program, key):
                    logger.debug(f"Updating field '{key}': {getattr(program, key)} -> {value}")
                    setattr(program, key, value)
                else:
                    logger.warning(f"Field '{key}' not found in UserProgram model")
            
            logger.debug("Committing changes to database")
            db.commit()
            
            logger.debug("Refreshing program object")
            db.refresh(program)
            
            logger.debug(f"Updated program state: {program.__dict__}")
            logger.info(f"Updated program: {program.id} - {program.program_name} for user {user_id}")
            
            return program
        except Exception as e:
            logger.error(f"Error updating program: {e}")
            logger.error(traceback.format_exc())
            # Roll back the transaction
            db.rollback()
            return None
    
    @staticmethod
    def delete_program(db: Session, user_id: int, program_name: str) -> bool:
        """
        Deletes a user's program.
        """
        logger.debug(f"Deleting program '{program_name}' for user {user_id}")
        
        try:
            program = UnifiedProgramService.get_program_by_name(db, user_id, program_name)
            if not program:
                logger.warning(f"Program '{program_name}' not found for user {user_id}")
                return False
            
            logger.debug(f"Found program to delete: {program.id} - {program.program_name}")
            
            # Delete program
            logger.debug("Deleting program from database")
            db.delete(program)
            
            logger.debug("Committing changes to database")
            db.commit()
            
            logger.info(f"Deleted program '{program_name}' for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting program: {e}")
            logger.error(traceback.format_exc())
            # Roll back the transaction
            db.rollback()
            return False
    
    @staticmethod
    def load_program_template(program_id: str) -> Dict[str, Any]:
        """
        Loads program requirements from a JSON file.
        """
        logger.debug(f"Loading program template '{program_id}'")
        
        file_path = PROGRAMS_DIR / f"{program_id}.json"
        logger.debug(f"Looking for program file at: {file_path}")
        
        if not file_path.exists():
            logger.warning(f"Program template file not found: {file_path}")
            raise HTTPException(status_code=404, detail=f"Program template {program_id} not found")
        
        try:
            logger.debug(f"Reading program template from file: {file_path}")
            with open(file_path, "r") as f:
                template = json.load(f)
                
            logger.debug(f"Loaded program template: {template.get('program_name', 'Unknown')}")
            return template
        except Exception as e:
            logger.error(f"Error loading program template: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Error loading program template: {str(e)}")
    
    @staticmethod
    def assign_program_to_user(db: Session, user_id: int, program_id: str) -> UserProgram:
        """
        Assigns a program template to a user.
        """
        logger.debug(f"Assigning program '{program_id}' to user {user_id}")
        
        try:
            # Load program requirements
            logger.debug(f"Loading program template: {program_id}")
            program_data = UnifiedProgramService.load_program_template(program_id)
            
            logger.debug(f"Creating ProgramCreate object")
            # Create program
            program = ProgramCreate(
                program_type=program_data["program_type"],
                program_name=program_data["program_name"],
                required_courses=program_data["required_courses"]
            )
            
            logger.debug(f"Program to assign: {program.program_name} ({program.program_type})")
            
            # Check if this program already exists for the user
            existing_program = UnifiedProgramService.get_program_by_name(db, user_id, program.program_name)
            if existing_program:
                logger.debug(f"Program '{program.program_name}' already exists for user {user_id}, updating")
                
                # Update the existing program
                for key, value in program.dict().items():
                    logger.debug(f"Updating field '{key}': {getattr(existing_program, key)} -> {value}")
                    setattr(existing_program, key, value)
                    
                logger.debug("Committing changes to database")
                db.commit()
                
                logger.debug("Refreshing program object")
                db.refresh(existing_program)
                
                logger.info(f"Updated existing program: {existing_program.id} - {existing_program.program_name}")
                return existing_program
            
            # Create new program for user
            logger.debug(f"Creating new program for user {user_id}")
            new_program = UnifiedProgramService.create_program(db, user_id, program)
            logger.info(f"Created new program: {new_program.id} - {new_program.program_name}")
            return new_program
        except Exception as e:
            logger.error(f"Error assigning program to user: {e}")
            logger.error(traceback.format_exc())
            raise
    
    @staticmethod
    def format_user_progress(db: Session, user_id: int) -> str:
        """
        Formats the user's academic progress information for the RAG system.
        """
        logger.debug(f"Formatting academic progress for user {user_id}")
        
        try:
            # Get user with related data
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found")
                return "No user data found."
            
            logger.debug(f"Found user: {user.username} (ID: {user.id})")
            
            # Get programs
            programs = UnifiedProgramService.get_user_programs(db, user_id)
            logger.debug(f"Found {len(programs)} programs for user")
            
            # Format the data for RAG
            result = []
            
            # Add programs information
            result.append(f"The user has the following academic programs:")
            for program in programs:
                program_type = program.program_type.capitalize()
                result.append(f"- {program_type}: {program.program_name}")
            
            # Add completed courses
            logger.debug(f"Adding completed courses ({len(user.courses)})")
            result.append("\nThey have completed these courses:")
            for course in user.courses:
                result.append(f"- {course.class_code}")
            
            # Add required courses for each program
            for program in programs:
                logger.debug(f"Adding requirements for {program.program_name}")
                result.append(f"\nThe required courses for their {program.program_name} {program.program_type} include:")
                
                required_courses = program.required_courses
                if not required_courses:
                    logger.warning(f"No required courses found for program {program.program_name}")
                    result.append("- No specific requirements found")
                    continue
                    
                logger.debug(f"Processing required courses: {type(required_courses)}")
                
                if isinstance(required_courses, list):
                    logger.debug(f"Found {len(required_courses)} required courses")
                    for course in required_courses:
                        if isinstance(course, str):
                            logger.debug(f"String course requirement: {course}")
                            result.append(f"- {course}")
                        elif isinstance(course, dict):
                            if "class_code" in course:
                                logger.debug(f"Dict course requirement with class_code: {course['class_code']}")
                                result.append(f"- {course['class_code']}")
                            elif "requirement_name" in course and "options" in course:
                                req_name = course['requirement_name']
                                courses_needed = course.get('courses_needed', 1)
                                logger.debug(f"Course group requirement: {req_name} (need {courses_needed})")
                                result.append(f"- {req_name} (Need {courses_needed} course(s)):")
                                
                                options = course["options"]
                                logger.debug(f"Processing {len(options)} options for requirement {req_name}")
                                for option in options:
                                    if isinstance(option, str):
                                        logger.debug(f"Option (string): {option}")
                                        result.append(f"  * {option}")
                                    elif isinstance(option, dict) and "class_code" in option:
                                        logger.debug(f"Option (dict): {option['class_code']}")
                                        result.append(f"  * {option['class_code']}")
                                    else:
                                        logger.warning(f"Unknown option format: {option}")
                            else:
                                logger.warning(f"Unknown course requirement format: {course}")
                        else:
                            logger.warning(f"Unknown course type in required_courses: {type(course)}")
                else:
                    logger.warning(f"required_courses is not a list: {type(required_courses)}")
                    result.append("- Requirements format not recognized")
        
            result.append("\nIt is currently Spring 2025. Recommend which classes they should take next term to stay on track.")
        
            formatted_result = "\n".join(result)
            logger.debug(f"Formatted user progress: {len(formatted_result)} chars, {len(result)} lines")
            return formatted_result
            
        except Exception as e:
            logger.error(f"Error formatting user progress: {e}")
            logger.error(traceback.format_exc())
            return "Error retrieving student progress information."

# Create a global instance of the service
logger.info("Creating global program_service instance")
program_service = UnifiedProgramService()