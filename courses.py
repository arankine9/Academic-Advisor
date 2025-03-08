from sqlalchemy.orm import Session
from database import Course, User
from typing import List, Optional
from pydantic import BaseModel
import json
import os

# Course model for API
class CourseBase(BaseModel):
    course_code: str
    course_name: str
    credit_hours: Optional[int] = None
    term: Optional[str] = None

# Course model for creation
class CourseCreate(CourseBase):
    pass

# Course model for response
class CourseResponse(CourseBase):
    id: int

    class Config:
        from_attributes = True

# Get course by code
def get_course_by_code(db: Session, course_code: str):
    return db.query(Course).filter(Course.course_code == course_code).first()

# Create course
def create_course(db: Session, course: CourseCreate):
    db_course = Course(
        course_code=course.course_code,
        course_name=course.course_name,
        credit_hours=course.credit_hours,
        term=course.term
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

# Get or create course
def get_or_create_course(db: Session, course: CourseCreate):
    db_course = get_course_by_code(db, course.course_code)
    if db_course:
        # Update course name and term if provided
        if course.course_name and not db_course.course_name:
            db_course.course_name = course.course_name
        if course.term and not db_course.term:
            db_course.term = course.term
        db.commit()
        return db_course
    return create_course(db, course)

# Add course to user
def add_course_to_user(db: Session, user_id: int, course_id: int):
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

# Remove course from user
def remove_course_from_user(db: Session, user_id: int, course_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    course = db.query(Course).filter(Course.id == course_id).first()
    
    if not user or not course:
        return None
    
    if course not in user.courses:
        return None
    
    user.courses.remove(course)
    db.commit()
    return course

# Get user courses
def get_user_courses(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    return user.courses

# Parse course from string
def parse_course_from_string(course_string: str) -> CourseCreate:
    # Example: "CS 210 - Introduction to Computer Science I"
    parts = course_string.split(" - ", 1)
    
    if len(parts) == 2:
        course_code = parts[0].strip()
        course_name = parts[1].strip()
    else:
        course_code = course_string.strip()
        course_name = ""
    
    return CourseCreate(
        course_code=course_code,
        course_name=course_name,
        credit_hours=None,
        term=None
    )

# Initialize courses from majors.json
def initialize_courses_from_json(db: Session):
    if not os.path.exists("majors.json"):
        return
    
    with open("majors.json", "r") as f:
        majors_data = json.load(f)
    
    for major_name, major_info in majors_data.items():
        for section_name, section_data in major_info.items():
            if isinstance(section_data, dict):
                # Handle courses
                if "courses" in section_data:
                    for course_string in section_data["courses"]:
                        parts = course_string.split(" - ", 1)
                        if len(parts) == 2:
                            course_code = parts[0].strip()
                            course_name = parts[1].strip()
                            
                            # Create course if it doesn't exist
                            course = CourseCreate(
                                course_code=course_code,
                                course_name=course_name,
                                credit_hours=None,
                                term=None
                            )
                            get_or_create_course(db, course) 