# Updated schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# Course schemas - Consistent naming and fields
class CourseBase(BaseModel):
    course_code: str
    course_name: Optional[str] = None
    credit_hours: Optional[int] = None
    term: Optional[str] = None
    description: Optional[str] = None
    prerequisites: Optional[str] = None
    instructor: Optional[str] = None
    days: Optional[str] = None
    time: Optional[str] = None
    classroom: Optional[str] = None
    available_seats: Optional[int] = None
    total_seats: Optional[int] = None

class CourseCreate(CourseBase):
    pass

class CourseResponse(CourseBase):
    id: int
    
    class Config:
        from_attributes = True

# Recommendation-specific schemas
class RecommendationDetails(BaseModel):
    is_recommended: bool
    reason: str
    priority: str  # High, Medium, Low

class RecommendedCourseResponse(CourseResponse):
    recommendation: Optional[RecommendationDetails] = None

class CourseRecommendationResponse(BaseModel):
    type: str = "course_recommendations"
    message: str
    course_data: List[RecommendedCourseResponse]

# User schemas - REMOVED major field
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str
    academic_level: str

class UserAuth(UserBase):
    password: str

# Program schemas
class ProgramBase(BaseModel):
    program_type: str  # 'major' or 'minor'
    program_name: str
    required_courses: List[Union[str, Dict[str, Any]]]

class ProgramCreate(ProgramBase):
    pass

class ProgramResponse(ProgramBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    courses: List[CourseResponse] = []
    programs: List[ProgramResponse] = []
    
    class Config:
        from_attributes = True

# Create an alias for UserResponse for backward compatibility
User = UserResponse

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ChatMessage(BaseModel):
    message: str