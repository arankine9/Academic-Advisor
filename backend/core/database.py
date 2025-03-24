# Copy from original database.py with these changes:
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Hardcode the correct connection string
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine with PostgreSQL-specific settings
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=3600,   # Recycle connections after 1 hour
    pool_size=5,         # Maximum number of connections to keep
    max_overflow=10      # Maximum number of connections to create beyond pool_size
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

# Define association table for many-to-many relationship between users and majors
user_majors = Table(
    "user_majors",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("major_id", Integer, ForeignKey("majors.id", ondelete="CASCADE"), primary_key=True),
    Column("added_date", DateTime, default=datetime.utcnow),
)

# Define User model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    major = Column(String, nullable=True)  # Keep for backward compatibility
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Define relationship with courses
    courses = relationship("Course", secondary=user_courses, back_populates="users")
    # Define relationship with programs
    programs = relationship("UserProgram", back_populates="user")
    # Define relationship with majors
    majors = relationship("Major", secondary=user_majors, back_populates="users")

# Define Course model
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String, index=True)
    course_name = Column(String)
    credit_hours = Column(Integer, nullable=True)
    term = Column(String, nullable=True)
    
    # Define relationship with users
    users = relationship("User", secondary=user_courses, back_populates="courses")

# Define Major model
class Major(Base):
    __tablename__ = "majors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    
    # Define relationship with users
    users = relationship("User", secondary=user_majors, back_populates="majors")

# Define UserProgram model
class UserProgram(Base):
    __tablename__ = "user_programs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    program_type = Column(String)  # 'major' or 'minor'
    program_name = Column(String)
    required_courses = Column(JSON)  # JSONB array of course codes
    
    # Define relationship with users
    user = relationship("User", back_populates="programs")
    
    __table_args__ = (
        # Composite unique constraint on user_id and program_name
        # to ensure a user can't have the same program twice
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