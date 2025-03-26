# New unified_course_service.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
import json
import os
import traceback
from fastapi import HTTPException
from langchain_pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings

from backend.core.database import Course, User
from backend.models.schemas import CourseBase, CourseCreate, CourseResponse, RecommendedCourseResponse

# Configure logging
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize vector database connections
INDEX_NAME = "duckweb-spring24"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

logger.debug(f"OPENAI_API_KEY is {'set' if OPENAI_API_KEY else 'NOT SET'}")
logger.debug(f"PINECONE_API_KEY is {'set' if PINECONE_API_KEY else 'NOT SET'}")
logger.debug(f"Using Pinecone index: {INDEX_NAME}")

try:
    logger.debug("Initializing OpenAI embeddings")
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-3-small")
    
    logger.debug("Initializing Pinecone vectorstore")
    vectorstore = Pinecone.from_existing_index(
        index_name=INDEX_NAME,
        embedding=embeddings,
        text_key="class_code",
    )
    logger.info("Vector database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing vector database: {e}")
    logger.error(traceback.format_exc())

class UnifiedCourseService:
    """
    A unified service for all course-related operations.
    Handles both SQL database and vector database interactions.
    """
    
    @staticmethod
    def get_course_by_code(db: Session, class_code: str) -> Optional[Course]:
        """Get a course by its code from the SQL database"""
        logger.debug(f"Getting course by code: '{class_code}'")
        
        try:
            course = db.query(Course).filter(Course.class_code == class_code).first()
            if course:
                logger.debug(f"Found course: {course.id} - {course.class_code}")
            else:
                logger.debug(f"No course found with code '{class_code}'")
            return course
        except Exception as e:
            logger.error(f"Error getting course by code: {e}")
            logger.error(traceback.format_exc())
            return None
    
    @staticmethod
    def create_course(db: Session, course: CourseCreate) -> Course:
        """Create a new course in the SQL database"""
        logger.debug(f"Creating course: {course.class_code}")
        
        try:
            # Debug course data
            course_dict = course.dict()
            logger.debug(f"Course data: {course_dict}")
            
            db_course = Course(
                class_code=course.class_code,
                course_name=course.course_name,
                credit_hours=course.credit_hours,
                term=course.term,
                description=course.description,
                prerequisites=course.prerequisites,
                instructor=course.instructor,
                days=course.days,
                time=course.time,
                classroom=course.classroom,
                available_seats=course.available_seats,
                total_seats=course.total_seats
            )
            
            logger.debug("Adding course to database session")
            db.add(db_course)
            
            logger.debug("Committing database transaction")
            db.commit()
            
            logger.debug("Refreshing course object")
            db.refresh(db_course)
            
            logger.info(f"Created course: {db_course.id} - {db_course.class_code}")
            return db_course
        except Exception as e:
            logger.error(f"Error creating course: {e}")
            logger.error(traceback.format_exc())
            # Roll back the transaction
            db.rollback()
            raise
    
    @staticmethod
    def get_or_create_course(db: Session, course: CourseCreate) -> Course:
        """Get a course by code or create it if it doesn't exist"""
        logger.debug(f"Get or create course: {course.class_code}")
        
        try:
            db_course = UnifiedCourseService.get_course_by_code(db, course.class_code)
            if db_course:
                logger.debug(f"Found existing course: {db_course.id} - {db_course.class_code}")
                
                # Check if we need to update any fields
                update_needed = False
                
                # Log the current course state
                logger.debug(f"Current course state: {db_course.__dict__}")
                
                # Update course fields if provided and not already set
                for field, value in course.dict(exclude_unset=True).items():
                    current_value = getattr(db_course, field)
                    if value is not None and current_value is None:
                        logger.debug(f"Updating field '{field}': {current_value} -> {value}")
                        setattr(db_course, field, value)
                        update_needed = True
                
                if update_needed:
                    logger.debug("Course updated, committing changes")
                    db.commit()
                    db.refresh(db_course)
                    logger.debug(f"Updated course state: {db_course.__dict__}")
                else:
                    logger.debug("No updates needed for existing course")
                
                return db_course
            
            logger.debug(f"Course not found, creating new one: {course.class_code}")
            return UnifiedCourseService.create_course(db, course)
        except Exception as e:
            logger.error(f"Error in get_or_create_course: {e}")
            logger.error(traceback.format_exc())
            raise
    
    @staticmethod
    def add_course_to_user(db: Session, user_id: int, course_id: int) -> Optional[Course]:
        """Add a course to a user's course list"""
        logger.debug(f"Adding course {course_id} to user {user_id}")
        
        try:
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User not found: {user_id}")
                return None
            
            # Get course
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                logger.warning(f"Course not found: {course_id}")
                return None
            
            logger.debug(f"Found user: {user.id} - {user.username}")
            logger.debug(f"Found course: {course.id} - {course.class_code}")
            
            # Check if user already has this course
            has_course = False
            for user_course in user.courses:
                if user_course.id == course_id:
                    has_course = True
                    break
            
            if has_course:
                logger.debug(f"User {user_id} already has course {course_id}")
                return course
            
            # Get current courses before adding
            current_courses = [c.class_code for c in user.courses]
            logger.debug(f"Current user courses before add: {current_courses}")
            
            # Add course to user
            logger.debug(f"Adding course {course.class_code} to user {user.username}")
            user.courses.append(course)
            
            # Commit and refresh
            logger.debug("Committing changes to database")
            db.commit()
            
            # Get updated courses
            updated_courses = [c.class_code for c in user.courses]
            logger.debug(f"User courses after add: {updated_courses}")
            
            logger.info(f"Successfully added course {course.class_code} to user {user.username}")
            return course
        except Exception as e:
            logger.error(f"Error adding course to user: {e}")
            logger.error(traceback.format_exc())
            # Roll back the transaction
            db.rollback()
            return None
    
    @staticmethod
    def remove_course_from_user(db: Session, user_id: int, course_id: int) -> Optional[Course]:
        """Remove a course from a user's course list"""
        logger.debug(f"Removing course {course_id} from user {user_id}")
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User not found: {user_id}")
                return None
                
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                logger.warning(f"Course not found: {course_id}")
                return None
            
            logger.debug(f"Found user: {user.id} - {user.username}")
            logger.debug(f"Found course: {course.id} - {course.class_code}")
            
            # Check if course is in user's courses
            has_course = False
            for user_course in user.courses:
                if user_course.id == course_id:
                    has_course = True
                    break
                    
            if not has_course:
                logger.warning(f"Course {course_id} not in user {user_id}'s course list")
                return None
            
            # Get current courses before removal
            current_courses = [c.class_code for c in user.courses]
            logger.debug(f"Current user courses before removal: {current_courses}")
            
            # Remove course from user
            logger.debug(f"Removing course {course.class_code} from user {user.username}")
            user.courses.remove(course)
            
            # Commit changes
            logger.debug("Committing changes to database")
            db.commit()
            
            # Get updated courses
            updated_courses = [c.class_code for c in user.courses]
            logger.debug(f"User courses after removal: {updated_courses}")
            
            logger.info(f"Successfully removed course {course.class_code} from user {user.username}")
            return course
        except Exception as e:
            logger.error(f"Error removing course from user: {e}")
            logger.error(traceback.format_exc())
            # Roll back the transaction
            db.rollback()
            return None
    
    @staticmethod
    def get_user_courses(db: Session, user_id: int) -> List[Course]:
        """Get all courses for a specific user"""
        logger.debug(f"Getting courses for user {user_id}")
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User not found: {user_id}")
                return []
                
            courses = user.courses
            course_count = len(courses)
            logger.debug(f"Found {course_count} courses for user {user_id}")
            
            if course_count > 0:
                class_codes = [course.class_code for course in courses]
                logger.debug(f"Courses: {class_codes}")
                
            return courses
        except Exception as e:
            logger.error(f"Error getting user courses: {e}")
            logger.error(traceback.format_exc())
            return []
    
    @staticmethod
    def parse_course_from_string(course_string: str) -> CourseCreate:
        """Parse a course from a string format like 'CS 101 - Introduction to Programming'"""
        logger.debug(f"Parsing course from string: '{course_string}'")
        
        try:
            parts = course_string.split(" - ", 1)
            
            if len(parts) == 2:
                class_code = parts[0].strip()
                course_name = parts[1].strip()
                logger.debug(f"Parsed class_code: '{class_code}', course_name: '{course_name}'")
            else:
                class_code = course_string.strip()
                course_name = ""
                logger.debug(f"Parsed class_code: '{class_code}', no course name provided")
            
            course_create = CourseCreate(
                class_code=class_code,
                course_name=course_name
            )
            
            return course_create
        except Exception as e:
            logger.error(f"Error parsing course from string: {e}")
            logger.error(traceback.format_exc())
            # Return a default course with the original string as code
            return CourseCreate(
                class_code=course_string,
                course_name=""
            )
    
    @staticmethod
    async def search_courses_in_vector_db(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for courses in the vector database using semantic search
        """
        logger.debug(f"Searching vector DB for courses related to: '{query}', limit: {limit}")
        
        try:
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": limit}
            )
            
            logger.debug(f"Executing vector search for: '{query}'")
            results = retriever.get_relevant_documents(query)
            logger.debug(f"Found {len(results)} results from vector search")
            
            formatted_courses = []
            
            for i, doc in enumerate(results):
                metadata = doc.metadata
                logger.debug(f"Processing result {i+1}: {metadata.get('class_code', 'Unknown')}")
                
                course_info = {
                    "class_code": metadata.get('class_code', 'Unknown'),
                    "course_name": metadata.get('course_name', ''),
                    "credit_hours": metadata.get('credit_hours'),
                    "description": metadata.get('description', ''),
                    "prerequisites": metadata.get('prerequisites', ''),
                    "instructor": metadata.get('instructor', ''),
                    "days": metadata.get('days', ''),
                    "time": metadata.get('time', ''),
                    "classroom": metadata.get('classroom', ''),
                    "available_seats": metadata.get('available_seats'),
                    "total_seats": metadata.get('total_seats')
                }
                
                formatted_courses.append(course_info)
            
            logger.info(f"Vector search complete, formatted {len(formatted_courses)} courses")
            return formatted_courses
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Vector search error: {str(e)}")

# Create a global instance of the service
logger.info("Creating global course_service instance")
course_service = UnifiedCourseService()