#!/usr/bin/env python3
import os
import sys
import traceback
import json
from sqlalchemy import create_engine, text, inspect, Column, String, Text, Integer, DateTime
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Insert project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Updated imports for program-based approach
from backend.core.database import get_db, create_tables, Base, User, UserProgram, Course
from backend.services.unified_course_service import course_service
from backend.services.unified_program_service import program_service

# Load environment variables
load_dotenv()

# Get the database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Using database URL: {DATABASE_URL}")

def init_db():
    """Initialize the database with the new program-based approach."""
    print("Initializing database...")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Test connection
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"Successfully connected to database: {DATABASE_URL}")
        except Exception as e:
            print(f"Error connecting to database: {e}")
            print("\nTraceback:")
            traceback.print_exc()
            print("\nPossible solutions:")
            print("1. Make sure PostgreSQL is running")
            print("2. Check your DATABASE_URL in .env file")
            print("3. Make sure the database exists")
            sys.exit(1)
        
        # Create tables
        try:
            create_tables()
            
            # Verify tables were created - Updated for program-based approach
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            expected_tables = ['users', 'courses', 'user_courses', 'user_programs']
            
            for table in expected_tables:
                if table in table_names:
                    print(f"✅ Table '{table}' created successfully")
                else:
                    print(f"❌ Table '{table}' not found!")
            
            # Check for missing columns and add them
            ensure_all_columns_exist(engine)
            
            # Rename 'course_code' column to 'class_code'
            rename_column_course_code_to_class_code(engine)
            
            # Check if legacy tables exist (for migration purposes)
            legacy_tables = ['majors', 'user_majors']
            legacy_exists = False
            
            for table in legacy_tables:
                if table in table_names:
                    legacy_exists = True
                    print(f"⚠️ Legacy table '{table}' exists - will migrate data")
                
            print("Database tables created or verified.")
            
            # Migrate data if legacy tables exist
            if legacy_exists:
                migrate_legacy_data(engine)
        except Exception as e:
            print(f"Error creating/verifying tables: {e}")
            traceback.print_exc()
            sys.exit(1)
        
        # Initialize data
        try:
            db = next(get_db())
            
            # Initialize courses from program files
            initialize_courses_from_programs(db)
            print("Initialized courses from program files.")
            
            # Initialize program templates
            initialize_program_templates(db)
            print("Initialized program templates.")
            
            db.close()
        except Exception as e:
            print(f"Error initializing data: {e}")
            traceback.print_exc()
            sys.exit(1)
        
        print("Database initialization complete.")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

def ensure_all_columns_exist(engine):
    """Check for and add any missing columns in existing tables based on SQLAlchemy models."""
    print("Checking for missing columns in database tables...")
    
    inspector = inspect(engine)
    connection = engine.connect()
    transaction = connection.begin()
    
    try:
        # Check Course table columns
        print("Verifying columns for 'courses' table...")
        existing_columns = {column['name'] for column in inspector.get_columns('courses')}
        model_columns = {column.name: column for column in Course.__table__.columns}
        
        missing_columns = set(model_columns.keys()) - existing_columns
        
        for column_name in missing_columns:
            column = model_columns[column_name]
            column_type = column.type.compile(engine.dialect)
            nullable = "NULL" if column.nullable else "NOT NULL"
            
            # Build the ALTER TABLE query
            query = f"ALTER TABLE courses ADD COLUMN {column_name} {column_type} {nullable}"
            print(f"Adding missing column: {column_name} ({column_type}) to courses table")
            connection.execute(text(query))
            print(f"✅ Added column '{column_name}' to 'courses' table")
        
        # Check User table columns
        print("Verifying columns for 'users' table...")
        existing_columns = {column['name'] for column in inspector.get_columns('users')}
        model_columns = {column.name: column for column in User.__table__.columns}
        
        missing_columns = set(model_columns.keys()) - existing_columns
        
        for column_name in missing_columns:
            column = model_columns[column_name]
            column_type = column.type.compile(engine.dialect)
            nullable = "NULL" if column.nullable else "NOT NULL"
            
            # Build the ALTER TABLE query
            query = f"ALTER TABLE users ADD COLUMN {column_name} {column_type} {nullable}"
            print(f"Adding missing column: {column_name} ({column_type}) to users table")
            connection.execute(text(query))
            print(f"✅ Added column '{column_name}' to 'users' table")
        
        # Check UserProgram table columns
        print("Verifying columns for 'user_programs' table...")
        existing_columns = {column['name'] for column in inspector.get_columns('user_programs')}
        model_columns = {column.name: column for column in UserProgram.__table__.columns}
        
        missing_columns = set(model_columns.keys()) - existing_columns
        
        for column_name in missing_columns:
            column = model_columns[column_name]
            column_type = column.type.compile(engine.dialect)
            nullable = "NULL" if column.nullable else "NOT NULL"
            
            # Build the ALTER TABLE query
            query = f"ALTER TABLE user_programs ADD COLUMN {column_name} {column_type} {nullable}"
            print(f"Adding missing column: {column_name} ({column_type}) to user_programs table")
            connection.execute(text(query))
            print(f"✅ Added column '{column_name}' to 'user_programs' table")
        
        # Commit the transaction
        transaction.commit()
        print("Column verification complete. All necessary columns have been added.")
        
    except Exception as e:
        transaction.rollback()
        print(f"Error checking/adding columns: {e}")
        traceback.print_exc()
    finally:
        connection.close()

def rename_column_course_code_to_class_code(engine):
    """Rename 'course_code' column to 'class_code' in the courses table."""
    print("Checking for column renaming from 'course_code' to 'class_code'...")
    
    inspector = inspect(engine)
    connection = engine.connect()
    transaction = connection.begin()
    
    try:
        # Check if the 'course_code' column exists in the 'courses' table
        course_columns = {column['name'] for column in inspector.get_columns('courses')}
        
        if 'course_code' in course_columns:
            # Rename 'course_code' to 'class_code'
            query = "ALTER TABLE courses RENAME COLUMN course_code TO class_code"
            print(f"Renaming column: 'course_code' to 'class_code' in courses table")
            connection.execute(text(query))
            print(f"✅ Renamed column 'course_code' to 'class_code' in 'courses' table")
        else:
            print(f"Column 'course_code' not found in 'courses' table, no renaming needed")
        
        # Commit the transaction
        transaction.commit()
        print("Column renaming complete.")
        
    except Exception as e:
        transaction.rollback()
        print(f"Error renaming columns: {e}")
        traceback.print_exc()
    finally:
        connection.close()

def migrate_legacy_data(engine):
    """Migrate data from legacy major system to new program system."""
    print("Migrating legacy major data to program-based system...")
    
    # Create a session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if user_majors table exists and has data
        major_data_exists = False
        try:
            result = db.execute(text("SELECT COUNT(*) FROM user_majors"))
            count = result.scalar()
            if count > 0:
                major_data_exists = True
                print(f"Found {count} user-major associations to migrate")
        except Exception:
            print("Could not check user_majors table, may not exist")
        
        # Check if users.major column has data
        user_major_exists = False
        try:
            result = db.execute(text("SELECT COUNT(*) FROM users WHERE major IS NOT NULL AND major != ''"))
            count = result.scalar()
            if count > 0:
                user_major_exists = True
                print(f"Found {count} users with major field to migrate")
        except Exception:
            print("Could not check users.major column, may not exist")
        
        # Migrate data from user_majors table
        if major_data_exists:
            try:
                # Get all user-major associations
                query = text("""
                    SELECT um.user_id, m.name 
                    FROM user_majors um 
                    JOIN majors m ON um.major_id = m.id
                """)
                results = db.execute(query).fetchall()
                
                for user_id, major_name in results:
                    # Check if a program already exists for this user
                    program_exists = db.execute(
                        text("SELECT COUNT(*) FROM user_programs WHERE user_id = :user_id AND program_name = :program_name"),
                        {"user_id": user_id, "program_name": major_name}
                    ).scalar() > 0
                    
                    if not program_exists:
                        # Create a new user program
                        new_program = UserProgram(
                            user_id=user_id,
                            program_type="major",
                            program_name=major_name,
                            required_courses=[]  # Will be populated later
                        )
                        db.add(new_program)
                print(f"Migrated {len(results)} user-major associations to user_programs")
            except Exception as e:
                print(f"Error migrating from user_majors: {e}")
                traceback.print_exc()
        
        # Migrate data from users.major column
        if user_major_exists:
            try:
                # Get all users with a major
                query = text("SELECT id, major FROM users WHERE major IS NOT NULL AND major != ''")
                results = db.execute(query).fetchall()
                
                for user_id, major_name in results:
                    # Check if a program already exists for this user
                    program_exists = db.execute(
                        text("SELECT COUNT(*) FROM user_programs WHERE user_id = :user_id AND program_name = :program_name"),
                        {"user_id": user_id, "program_name": major_name}
                    ).scalar() > 0
                    
                    if not program_exists:
                        # Create a new user program
                        new_program = UserProgram(
                            user_id=user_id,
                            program_type="major",
                            program_name=major_name,
                            required_courses=[]  # Will be populated later
                        )
                        db.add(new_program)
                print(f"Migrated {len(results)} user major fields to user_programs")
            except Exception as e:
                print(f"Error migrating from users.major: {e}")
                traceback.print_exc()
        
        # Commit the changes
        db.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
        traceback.print_exc()
    finally:
        db.close()

def initialize_courses_from_programs(db):
    """Extract and initialize courses from program templates."""
    print("Initializing courses from program templates...")
    
    # Get all program files
    programs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'programs'))
    for root, dirs, files in os.walk(programs_dir):
        for file in files:
            if file.endswith('.json'):
                try:
                    filepath = os.path.join(root, file)
                    
                    # Read the JSON file directly instead of using the service
                    with open(filepath, 'r') as f:
                        program_data = json.load(f)
                    
                    # Extract course codes from required_courses
                    if 'required_courses' in program_data:
                        extract_and_create_courses(db, program_data['required_courses'])
                except Exception as e:
                    print(f"Error processing program file {file}: {e}")
    
    print("Course initialization from programs complete")

def extract_and_create_courses(db, required_courses):
    """Extract course codes from required courses and create them in the database."""
    if not required_courses:
        return
    
    for item in required_courses:
        if isinstance(item, str):
            # Direct course code
            course_data = course_service.parse_course_from_string(item)
            course_service.get_or_create_course(db, course_data)
        elif isinstance(item, dict):
            # Could be a requirement with options
            if 'options' in item:
                for option in item['options']:
                    if isinstance(option, str):
                        course_data = course_service.parse_course_from_string(option)
                        course_service.get_or_create_course(db, course_data)
                    elif isinstance(option, dict) and 'class_code' in option:
                        course_data = course_service.parse_course_from_string(option['class_code'])
                        course_service.get_or_create_course(db, course_data)
            # Could be a direct course reference
            elif 'class_code' in item:
                course_data = course_service.parse_course_from_string(item['class_code'])
                course_service.get_or_create_course(db, course_data)

def initialize_program_templates(db):
    """Initialize program templates from JSON files."""
    print("Verifying program templates...")
    
    # Count program files directly rather than using the service
    programs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'programs'))
    count = 0
    program_categories = []
    
    # Check main directory and subdirectories
    for root, dirs, files in os.walk(programs_dir):
        json_files = [f for f in files if f.endswith('.json')]
        count += len(json_files)
        
        # Track categories (subdirectories)
        relative_path = os.path.relpath(root, programs_dir)
        if relative_path != '.' and json_files:
            program_categories.append(f"{relative_path} ({len(json_files)} programs)")
    
    if count > 0:
        print(f"Found {count} program templates in categories: {', '.join(program_categories)}")
        
        # Print examples of programs found
        print("Examples of programs found:")
        examples = []
        for root, dirs, files in os.walk(programs_dir):
            json_files = [f for f in files if f.endswith('.json')]
            if json_files:
                category = os.path.relpath(root, programs_dir)
                for file in json_files[:2]:  # Show max 2 examples per category
                    examples.append(f"{category}/{file}")
                    if len(examples) >= 5:  # Cap at 5 total examples
                        break
            if len(examples) >= 5:
                break
                
        for example in examples:
            print(f"  - {example}")
    else:
        print("Warning: No program templates found. Make sure data/programs directory contains valid program files.")

if __name__ == "__main__":
    init_db()