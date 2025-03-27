from fastapi import APIRouter, Depends, HTTPException, status, Form, Body, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Optional, Dict, Any
import logging
import asyncio
import traceback
from fastapi.concurrency import run_in_threadpool

from backend.core.database import get_db, Course, SessionLocal
from backend.core.auth import authenticate_user, create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES, create_user
from backend.core.database import User as UserModel
from backend.models.schemas import Token, UserCreate, CourseResponse, ChatMessage, User as UserSchema, ProgramResponse
from backend.services.unified_course_service import course_service
from backend.services.recommendation_service import recommendation_service
from backend.services.unified_program_service import program_service

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter()

# In-memory response cache
_processing_responses = {}

# User endpoints
@router.get("/users/me", response_model=UserSchema)
async def read_users_me(current_user: UserModel = Depends(get_current_active_user)):
    logger.debug(f"User profile requested: {current_user.username} (ID: {current_user.id})")
    return current_user

# Course endpoints
@router.post("/courses")
async def add_course_json(
    course_data: dict = Body(...),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    logger.debug(f"Add course request for user {current_user.username} with data: {course_data}")
    
    try:
        # Create course string from JSON data
        department = course_data.get("department", "").strip().upper()
        course_number = course_data.get("course_number", "").strip()
        course_string = f"{department} {course_number}"
        
        logger.debug(f"Generated course string: '{course_string}'")
        
        # Add course name if provided
        course_name = course_data.get("name", "").strip()
        if course_name:
            course_string = f"{course_string} - {course_name}"
            logger.debug(f"Added course name to string: '{course_string}'")
            
        # Parse course and add term if provided
        logger.debug(f"Parsing course from string: '{course_string}'")
        course_create = course_service.parse_course_from_string(course_string)
        logger.debug(f"Parsed course: {course_create}")
        
        term = course_data.get("term")
        if term:
            course_create.term = term
            logger.debug(f"Added term '{term}' to course")
            
        # Get or create course
        logger.debug(f"Attempting to get or create course in database")
        course = course_service.get_or_create_course(db, course_create)
        logger.info(f"Course retrieved/created with ID {course.id}: {course.class_code}")
        
        # Add course to user
        logger.debug(f"Adding course {course.id} to user {current_user.id}")
        result = course_service.add_course_to_user(db, current_user.id, course.id)
        
        if not result:
            logger.error(f"Failed to add course {course.id} to user {current_user.id}")
            raise HTTPException(status_code=400, detail="Failed to add course to user")
            
        logger.info(f"Successfully added course {course.class_code} to user {current_user.username}")
        
        # Format response for frontend
        response = {
            "id": course.id,
            "class_code": course.class_code,
            "course_name": course.course_name,
            "term": course.term,
            "credit_hours": course.credit_hours
        }
        logger.debug(f"Returning response: {response}")
        return response
    except Exception as e:
        logger.error(f"Error in add_course_json: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.delete("/courses/{course_id}")
async def remove_course(
    course_id: int, 
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    logger.debug(f"Remove course request for user {current_user.username}, course_id: {course_id}")
    
    try:
        # Get course before removal for logging
        course_before = db.query(Course).filter(Course.id == course_id).first()
        if course_before:
            logger.debug(f"Found course to remove: {course_before.class_code}")
        else:
            logger.warning(f"Course with ID {course_id} not found in database")
        
        # Check if course is in user's courses
        user_has_course = False
        for course in current_user.courses:
            if course.id == course_id:
                user_has_course = True
                break
        
        logger.debug(f"User has course in their list: {user_has_course}")
        
        # Remove course from user
        logger.debug(f"Attempting to remove course {course_id} from user {current_user.id}")
        course = course_service.remove_course_from_user(db, current_user.id, course_id)
        
        if not course:
            logger.warning(f"Course {course_id} not found or not associated with user {current_user.id}")
            raise HTTPException(status_code=404, detail="Course not found or not associated with user")
        
        logger.info(f"Successfully removed course {course.class_code} from user {current_user.username}")
        return {"status": "success", "message": f"Course {course.class_code} removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in remove_course: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.put("/courses/{course_id}")
async def update_course(
    course_id: int,
    course_data: dict = Body(...),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    logger.debug(f"Update course request for user {current_user.username}, course_id: {course_id}, data: {course_data}")
    
    try:
        # Check if course exists and belongs to user
        logger.debug(f"Checking if course {course_id} belongs to user {current_user.id}")
        user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
        course = db.query(Course).filter(Course.id == course_id).first()
        
        if not course:
            logger.warning(f"Course {course_id} not found in database")
            raise HTTPException(status_code=404, detail="Course not found")
            
        course_in_user_list = False
        if user and course:
            course_in_user_list = course in user.courses
            logger.debug(f"Course in user's list: {course_in_user_list}")
        
        if not course or not user or not course_in_user_list:
            logger.warning(f"Course {course_id} not found or not associated with user {current_user.id}")
            raise HTTPException(status_code=404, detail="Course not found or not associated with user")
            
        # Update course
        logger.debug(f"Updating course {course_id}")
        department = course_data.get("department", "").strip().upper()
        course_number = course_data.get("course_number", "").strip()
        new_class_code = f"{department} {course_number}"
        
        logger.debug(f"Updating class_code from '{course.class_code}' to '{new_class_code}'")
        course.class_code = new_class_code
        
        if "name" in course_data:
            logger.debug(f"Updating course_name from '{course.course_name}' to '{course_data['name']}'")
            course.course_name = course_data["name"]
            
        if "term" in course_data:
            logger.debug(f"Updating term from '{course.term}' to '{course_data['term']}'")
            course.term = course_data["term"]
            
        db.commit()
        db.refresh(course)
        
        logger.info(f"Successfully updated course {course.id}: {course.class_code}")
        
        response = {
            "id": course.id,
            "class_code": course.class_code,
            "course_name": course.course_name,
            "term": course.term,
            "credit_hours": course.credit_hours
        }
        logger.debug(f"Returning response: {response}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_course: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/courses/me", response_model=List[CourseResponse])
async def get_my_courses(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    logger.debug(f"Get courses request for user {current_user.username} (ID: {current_user.id})")
    
    try:
        courses = course_service.get_user_courses(db, current_user.id)
        logger.debug(f"Retrieved {len(courses)} courses for user {current_user.id}")
        class_codes = [course.class_code for course in courses]
        logger.debug(f"Course codes: {class_codes}")
        return courses
    except Exception as e:
        logger.error(f"Error in get_my_courses: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Advising chat endpoints
@router.post("/advising")
async def advising_chat(
    message: ChatMessage,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    logger.debug(f"Advising chat request from user {current_user.username}: '{message.message}'")
    
    try:
        # Extract message from request
        message_text = message.message
        if not message_text:
            logger.warning("Empty message received in advising chat")
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Classify the intent of the query
        logger.debug(f"Classifying intent for message: '{message_text}'")
        intent = recommendation_service.classify_intent(message_text)
        logger.info(f"Intent classification result for user {current_user.id}: {intent}")
        
        if intent == "COURSE":
            logger.debug("Processing as COURSE intent with background task")
            # For course-related queries, send acknowledgment first
            acknowledgment = recommendation_service.generate_acknowledgment(message_text)
            logger.debug(f"Generated acknowledgment: '{acknowledgment}'")
            
            # Process query in background
            logger.debug(f"Starting background task for user {current_user.id}")
            background_tasks.add_task(
                process_advising_query_background,
                db, current_user.id, message_text
            )
            
            # Return acknowledgment with processing flag
            return {"response": acknowledgment, "processing": True}
        else:
            logger.debug("Processing as GENERAL intent immediately")
            # For general conversation, process immediately
            response = recommendation_service.process_general_query(message_text)
            logger.debug(f"Generated general response: '{response[:100]}...'")
            return {"response": response}
            
    except Exception as e:
        logger.error(f"Error in advising_chat: {e}")
        logger.error(traceback.format_exc())
        return {"response": "I'm sorry, I encountered an error. Please try again later or try rephrasing your question."}

async def process_advising_query_background(db: Session, user_id: int, query: str):
    logger.debug(f"Background processing started for user {user_id}, query: '{query}'")
    
    try:
        # Create a new session since we're in a background task
        logger.debug("Creating new database session for background task")
        db_session = SessionLocal()
        
        # Check if it's an async function and handle accordingly
        logger.debug("Checking if recommendation_service.process_query is async")
        is_async = asyncio.iscoroutinefunction(recommendation_service.process_query)
        logger.debug(f"process_query is async: {is_async}")
        
        if is_async:
            # For async function, we need to await it properly
            logger.debug("Processing query with async call")
            result = await recommendation_service.process_query(db_session, user_id, query)
        else:
            # For sync function, use threadpool
            logger.debug("Processing query with threadpool")
            result = await run_in_threadpool(
                lambda: recommendation_service.process_query(db_session, user_id, query)
            )
        
        # Store the result in the cache
        logger.debug(f"Storing result in cache for user {user_id}")
        _processing_responses[user_id] = result
        logger.info(f"Background processing completed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Background processing error for user {user_id}: {e}")
        logger.error(traceback.format_exc())
        _processing_responses[user_id] = {
            "type": "error",
            "message": "I encountered an error while processing your request. Please try again."
        }
    finally:
        logger.debug("Closing background task database session")
        db_session.close()

@router.get("/advising/pending")
async def check_pending_response(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Check if there's a pending response for the user"""
    logger.debug(f"Checking pending response for user {current_user.id}")
    
    response = _processing_responses.get(current_user.id)
    
    if response:
        logger.debug(f"Found pending response for user {current_user.id}")
        # Dump a limited portion of the response to avoid giant logs
        if isinstance(response, dict) and 'message' in response:
            message_preview = response['message'][:100] + '...' if len(response['message']) > 100 else response['message']
            logger.debug(f"Response message: {message_preview}")
        
        # Remove from cache after retrieving
        logger.debug(f"Removing response from cache for user {current_user.id}")
        del _processing_responses[current_user.id]
        return {"response": response, "pending": False}
    
    logger.debug(f"No pending response found for user {current_user.id}")
    return {"pending": True}

# Program endpoints (consolidated from both route files)
@router.get("/programs/available", response_model=List[Dict[str, Any]])
async def get_available_programs():
    """
    Get a list of all available programs.
    """
    logger.debug("Getting available programs")
    
    try:
        programs = program_service.get_available_programs()
        logger.debug(f"Retrieved {len(programs)} available programs")
        program_names = [p.get('program_name', 'Unknown') for p in programs]
        logger.debug(f"Available programs: {program_names}")
        return programs
    except Exception as e:
        logger.error(f"Error getting available programs: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/programs/me", response_model=List[ProgramResponse])
async def get_my_programs(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all programs for the current user.
    """
    logger.debug(f"Getting programs for user {current_user.username} (ID: {current_user.id})")
    
    try:
        programs = program_service.get_user_programs(db, current_user.id)
        logger.debug(f"Retrieved {len(programs)} programs for user {current_user.id}")
        program_names = [p.program_name for p in programs]
        logger.debug(f"User programs: {program_names}")
        return programs
    except Exception as e:
        logger.error(f"Error getting user programs: {str(e)}")
        logger.error(traceback.format_exc())
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
    logger.debug(f"Add program request for user {current_user.username} with data: {program_data}")
    
    try:
        program_id = program_data.get("program_id")
        logger.debug(f"Program ID from request: {program_id}")
        
        if not program_id:
            logger.warning("No program_id provided in request")
            raise HTTPException(status_code=400, detail="Program ID is required")
            
        program = program_service.assign_program_to_user(db, current_user.id, program_id)
        logger.info(f"Successfully assigned program '{program.program_name}' to user {current_user.username}")
        return program
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding program: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.delete("/programs/{program_name}", response_model=dict)
async def remove_program(
    program_name: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Remove a program from the current user by name.
    """
    logger.debug(f"Remove program request for user {current_user.username}, program: '{program_name}'")
    
    try:
        # Check if program exists for user before deletion
        existing_program = program_service.get_program_by_name(db, current_user.id, program_name)
        if existing_program:
            logger.debug(f"Found program '{program_name}' (ID: {existing_program.id}) to remove")
        else:
            logger.warning(f"Program '{program_name}' not found for user {current_user.id}")
        
        success = program_service.delete_program(db, current_user.id, program_name)
        
        if not success:
            logger.warning(f"Failed to delete program '{program_name}' for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Program not found or not associated with user")
        
        logger.info(f"Successfully removed program '{program_name}' from user {current_user.username}")
        return {"status": "success", "message": f"Program {program_name} removed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing program: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.get("/programs/{program_name}", response_model=ProgramResponse)
async def get_program(
    program_name: str,
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific program by name for the current user.
    """
    logger.debug(f"Get program request for user {current_user.username}, program: '{program_name}'")
    
    program = program_service.get_program_by_name(db, current_user.id, program_name)
    if not program:
        logger.warning(f"Program '{program_name}' not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program {program_name} not found",
        )
    
    logger.debug(f"Found program '{program_name}' (ID: {program.id}) for user {current_user.id}")
    return program

@router.put("/programs/{program_name}", response_model=ProgramResponse)
async def update_program(
    program_name: str,
    program_update: dict = Body(...),
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update a program by name for the current user.
    """
    logger.debug(f"Update program request for user {current_user.username}, program: '{program_name}', data: {program_update}")
    
    result = program_service.update_program(db, current_user.id, program_name, program_update)
    if not result:
        logger.warning(f"Program '{program_name}' not found for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program {program_name} not found",
        )
    
    logger.info(f"Successfully updated program '{program_name}' for user {current_user.username}")
    return result

@router.get("/programs/progress", response_model=dict)
async def get_program_progress(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get the user's progress information.
    """
    logger.debug(f"Get program progress for user {current_user.username} (ID: {current_user.id})")
    
    try:
        progress = program_service.format_user_progress(db, current_user.id)
        # Fix: Use one of these alternatives instead
        newline = '\n'
        logger.debug(f"Retrieved progress data for user {current_user.id} ({len(progress.split(newline))} lines)")
        return {"progress": progress}
    except Exception as e:
        logger.error(f"Error getting program progress: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")