from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# Course schemas
class CourseBase(BaseModel):
    course_code: str
    course_name: Optional[str] = None
    credit_hours: Optional[int] = None
    term: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseResponse(CourseBase):
    id: int
    
    class Config:
        from_attributes = True

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    major: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserAuth(UserBase):
    password: str

# Major schema
class MajorBase(BaseModel):
    name: str

class MajorCreate(MajorBase):
    pass

class MajorResponse(MajorBase):
    id: int
    
    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    courses: List[CourseResponse] = []
    majors: List[MajorResponse] = []
    
    class Config:
        from_attributes = True

# Create an alias for UserResponse as User for backward compatibility
User = UserResponse

# User Program schemas
class UserProgramBase(BaseModel):
    program_type: str  # 'major' or 'minor'
    program_name: str
    required_courses: List[Union[str, Dict[str, Any]]]  # List of course codes or course objects

class UserProgramCreate(UserProgramBase):
    pass

class UserProgramResponse(UserProgramBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class ChatMessage(BaseModel):
    message: str