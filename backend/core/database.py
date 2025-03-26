# Updated database.py
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine with optimized settings
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Define association table for many-to-many relationship between users and courses
user_courses = Table(
    "user_courses",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("course_id", Integer, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("completed_date", DateTime, default=datetime.utcnow),
)

# Define User model - REMOVED legacy major field and majors relationship
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Define relationships
    courses = relationship("Course", secondary=user_courses, back_populates="users")
    programs = relationship("UserProgram", back_populates="user")

# Define enhanced Course model with all fields that might be used
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    class_code = Column(String, index=True)
    course_name = Column(String)
    credit_hours = Column(Integer, nullable=True)
    term = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    prerequisites = Column(String, nullable=True)
    instructor = Column(String, nullable=True)
    days = Column(String, nullable=True)
    time = Column(String, nullable=True)
    classroom = Column(String, nullable=True)
    available_seats = Column(Integer, nullable=True)
    total_seats = Column(Integer, nullable=True)
    
    # Define relationship with users
    users = relationship("User", secondary=user_courses, back_populates="courses")

# Define UserProgram model - This will replace the Major model completely
class UserProgram(Base):
    __tablename__ = "user_programs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    program_type = Column(String)  # 'major' or 'minor'
    program_name = Column(String, index=True)
    required_courses = Column(JSON)  # JSON array of course codes
    
    # Define relationship with user
    user = relationship("User", back_populates="programs")
    
    __table_args__ = (
        # Composite unique constraint on user_id and program_name
        {'sqlite_autoincrement': True},
    )

# Function to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables in the database
def create_tables():
    Base.metadata.create_all(bind=engine)