from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List, Optional
from contextlib import asynccontextmanager
import os
import json

from database import get_db, create_tables
from auth import (
    authenticate_user, create_access_token, get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES, Token, UserCreate, User, create_user
)
from courses import (
    CourseCreate, CourseResponse, get_or_create_course,
    add_course_to_user, remove_course_from_user, get_user_courses,
    parse_course_from_string, initialize_courses_from_json
)
from query_engine import get_advice

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Define lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize courses from majors.json
    db = next(get_db())
    initialize_courses_from_json(db)
    yield
    # Shutdown: Clean up resources if needed
    pass

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Create database tables
create_tables()

# Login endpoint
@app.post("/token", response_model=Token)
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
@app.post("/register")
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
@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return {
        "username": current_user.username,
        "email": current_user.email,
        "major": current_user.major
    }

# Add course to user
@app.post("/courses/add")
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
@app.post("/courses/remove/{course_id}")
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
@app.get("/courses/me", response_model=List[CourseResponse])
async def get_my_courses(current_user: User = Depends(get_current_active_user),
                        db: Session = Depends(get_db)):
    try:
        courses = get_user_courses(db, current_user.id)
        return courses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Get recommendations
@app.get("/recommend/me")
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
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("pages/auth.html", {"request": request})

# Dashboard page
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("pages/dashboard.html", {"request": request})

# Class Management page
@app.get("/classes", response_class=HTMLResponse)
def classes(request: Request):
    return templates.TemplateResponse("pages/classes.html", {"request": request})

# Advising Chat page
@app.get("/advising", response_class=HTMLResponse)
def advising(request: Request):
    return templates.TemplateResponse("pages/advising.html", {"request": request})

# Define the recommendation endpoint (for backward compatibility)
@app.post("/recommend/")
def recommend(courses: list, major: str):
    return {"recommendations": get_advice(courses, major)}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)