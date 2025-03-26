# New unified_course_service.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
import json
import os
from fastapi import HTTPException
from langchain_pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings

from backend.core.database import Course, User
from backend.models.schemas import CourseBase, CourseCreate, CourseResponse, RecommendedCourseResponse

# Initialize vector database connections
INDEX_NAME = "duckweb-spring24"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-3-small")
vectorstore = Pinecone.from_existing_index(
    index_name=INDEX_NAME,
    embedding=embeddings,
    text_key="course_code",
)

class UnifiedCourseService:
    """
    A unified service for all course-related operations.
    Handles both SQL database and vector database interactions.
    """
    
    @staticmethod
    def get_course_by_code(db: Session, course_code: str) -> Optional[Course]:
        """Get a course by its code from the SQL database"""
        return db.query(Course).filter(Course.course_code == course_code).first()
    
    @staticmethod
    def create_course(db: Session, course: CourseCreate) -> Course:
        """Create a new course in the SQL database"""
        db_course = Course(
            course_code=course.course_code,
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
        db.add(db_course)
        db.commit()
        db.refresh(db_course)
        return db_course
    
    @staticmethod
    def get_or_create_course(db: Session, course: CourseCreate) -> Course:
        """Get a course by code or create it if it doesn't exist"""
        db_course = UnifiedCourseService.get_course_by_code(db, course.course_code)
        if db_course:
            # Update course fields if provided and not already set
            for field, value in course.dict(exclude_unset=True).items():
                if value is not None and getattr(db_course, field) is None:
                    setattr(db_course, field, value)
            db.commit()
            return db_course
        return UnifiedCourseService.create_course(db, course)
    
    @staticmethod
    def add_course_to_user(db: Session, user_id: int, course_id: int) -> Optional[Course]:
        """Add a course to a user's course list"""
        user = db.query(User).filter(User.id == user_id).first()
        course = db.query(Course).filter(Course.id == course_id).first()
        
        if not user or not course:
            return None
        
        # Check if user already has this course
        if course in user.courses:
            return course
        
        user.courses.append(course)
        db.commit()
        return course
    
    @staticmethod
    def remove_course_from_user(db: Session, user_id: int, course_id: int) -> Optional[Course]:
        """Remove a course from a user's course list"""
        user = db.query(User).filter(User.id == user_id).first()
        course = db.query(Course).filter(Course.id == course_id).first()
        
        if not user or not course or course not in user.courses:
            return None
        
        user.courses.remove(course)
        db.commit()
        return course
    
    @staticmethod
    def get_user_courses(db: Session, user_id: int) -> List[Course]:
        """Get all courses for a specific user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        return user.courses
    
    @staticmethod
    def parse_course_from_string(course_string: str) -> CourseCreate:
        """Parse a course from a string format like 'CS 101 - Introduction to Programming'"""
        parts = course_string.split(" - ", 1)
        
        if len(parts) == 2:
            course_code = parts[0].strip()
            course_name = parts[1].strip()
        else:
            course_code = course_string.strip()
            course_name = ""
        
        return CourseCreate(
            course_code=course_code,
            course_name=course_name
        )
    
    @staticmethod
    async def search_courses_in_vector_db(query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for courses in the vector database using semantic search
        """
        try:
            retriever = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": limit}
            )
            
            results = retriever.get_relevant_documents(query)
            formatted_courses = []
            
            for doc in results:
                metadata = doc.metadata
                course_info = {
                    "course_code": metadata.get('course_code', 'Unknown'),
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
            
            return formatted_courses
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Vector search error: {str(e)}")
    
    @staticmethod
    def enrich_course_data(db: Session, courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich course data from vector DB with data from SQL DB when available
        """
        enriched_courses = []
        
        for course in courses:
            course_code = course.get("course_code")
            if course_code:
                # Check if we have this course in the SQL database
                db_course = UnifiedCourseService.get_course_by_code(db, course_code)
                if db_course:
                    # Merge the data, prioritizing vector DB for full descriptions
                    for field in ["course_name", "credit_hours", "term"]:
                        if getattr(db_course, field) and not course.get(field):
                            course[field] = getattr(db_course, field)
            
            enriched_courses.append(course)
        
        return enriched_courses

# Create a global instance of the service
course_service = UnifiedCourseService()