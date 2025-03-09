from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Optional

from backend.core.database import get_db
from backend.core.auth import authenticate_user, create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES, create_user
from backend.models.schemas import Token, UserCreate, User, CourseResponse
from backend.services.courses import get_or_create_course, add_course_to_user, remove_course_from_user, get_user_courses, parse_course_from_string
from backend.services.query_engine import get_advice

# Create router
router = APIRouter()

# Set up templates
templates = Jinja2Templates(directory="frontend/templates")

# Login endpoint
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

# Register endpoint
@router.post("/register")
async def register(username: str = Form(...), email: str = Form(...), 
                  password: str = Form(...), major: str = Form(...), 
                  db: Session = Depends(get_db)):
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

# Get current user
@router.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "major": current_user.major
    }

# Add course to user
@router.post("/courses/add")
async def add_course(course_string: str = Form(...), term: Optional[str] = Form(None),
                    current_user: User = Depends(get_current_active_user),
                    db: Session = Depends(get_db)):
    try:
        # Parse course from string
        course_create = parse_course_from_string(course_string)
        
        # Add term if provided
        if term:
            course_create.term = term
        
        # Get or create course
        course = get_or_create_course(db, course_create)
        
        # Add course to user
        result = add_course_to_user(db, current_user.id, course.id)
        
        if not result:
            raise HTTPException(status_code=400, detail="Failed to add course to user")
        
        return {"status": "success", "message": f"Course {course.course_code} added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Remove course from user
@router.post("/courses/remove/{course_id}")
async def remove_course(course_id: int, 
                       current_user: User = Depends(get_current_active_user),
                       db: Session = Depends(get_db)):
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

# Get user courses
@router.get("/courses/me", response_model=List[CourseResponse])
async def get_my_courses(current_user: User = Depends(get_current_active_user),
                        db: Session = Depends(get_db)):
    try:
        courses = get_user_courses(db, current_user.id)
        return courses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Get recommendations
@router.get("/recommend/me")
async def recommend_me(current_user: User = Depends(get_current_active_user),
                      db: Session = Depends(get_db)):
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

# Root endpoint (Login/Register page)
@router.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("pages/auth.html", {"request": request})

# Dashboard page
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {"request": request})

# Class Management page
@router.get("/classes", response_class=HTMLResponse)
def classes(request: Request):
    return templates.TemplateResponse("pages/classes.html", {"request": request})

# Advising Chat page
@router.get("/advising", response_class=HTMLResponse)
def advising(request: Request):
    return templates.TemplateResponse("pages/advising.html", {"request": request})

# Define the recommendation endpoint (for backward compatibility)
@router.post("/recommend/")
def recommend(courses: list, major: str):
    return {"recommendations": get_advice(courses, major)}