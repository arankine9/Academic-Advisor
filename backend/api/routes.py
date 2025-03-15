from fastapi import APIRouter, Depends, HTTPException, status, Form, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Optional

from backend.core.database import get_db, Course
from backend.core.auth import authenticate_user, create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES, create_user
from backend.models.schemas import Token, UserCreate, User, CourseResponse, ChatMessage
from backend.services.courses import get_or_create_course, add_course_to_user, remove_course_from_user, get_user_courses, parse_course_from_string
from backend.services.query_engine import get_advice

# Create API router
router = APIRouter()

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
    major: str = Form(...), 
    db: Session = Depends(get_db)
):
    # Check if username already exists
    user = db.query(User).filter(User.username == username).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Create new user
    user_create = UserCreate(username=username, email=email, password=password, major=major)
    user = create_user(db, user_create)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    # Return token
    return {"access_token": access_token, "token_type": "bearer"}

# User endpoints
@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


# JSON version for React frontend
@router.post("/courses")
async def add_course_json(
    course_data: dict = Body(...),
    current_user: User = Depends(get_current_active_user),
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
        course_create = parse_course_from_string(course_string)
        term = course_data.get("term")
        if term:
            course_create.term = term
            
        # Get or create course
        course = get_or_create_course(db, course_create)
        
        # Add course to user
        result = add_course_to_user(db, current_user.id, course.id)
        
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Remove course from user
        course = remove_course_from_user(db, current_user.id, course_id)
        
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Check if course exists and belongs to user
        user = db.query(User).filter(User.id == current_user.id).first()
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        courses = get_user_courses(db, current_user.id)
        return courses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Recommendation endpoints
@router.get("/recommend/me")
async def recommend_me(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Get user courses
        courses = get_user_courses(db, current_user.id)
        
        if not courses:
            return {"recommendations": "You haven't added any courses yet. Please add your completed courses to get recommendations."}
        
        # Format courses for recommendation
        course_strings = [f"{course.course_code} - {course.course_name}" for course in courses]
        
        # Get recommendations
        recommendations = get_advice(course_strings, current_user.major)
        
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.post("/advising")
async def advising_chat(
    message: ChatMessage,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        # Extract message from request
        message_text = message.message
        if not message_text:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        # Get user courses
        courses = get_user_courses(db, current_user.id)
        
        # Format courses for recommendation
        course_strings = [f"{course.course_code} - {course.course_name}" for course in courses]
        
        # Use the enhanced query engine with the user's message
        response = get_advice(course_strings, current_user.major, query=message_text)
        
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")