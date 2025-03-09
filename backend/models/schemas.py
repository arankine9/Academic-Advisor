from pydantic import BaseModel
from typing import Optional, List

# User schemas
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    major: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserAuth(UserBase):
    pass

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Course schemas
class CourseBase(BaseModel):
    course_code: str
    course_name: str
    credit_hours: Optional[int] = None
    term: Optional[str] = None

class CourseCreate(CourseBase):
    pass

class CourseResponse(CourseBase):
    id: int

    class Config:
        from_attributes = True