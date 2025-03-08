import os
import sys
import traceback
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from database import create_tables
from courses import initialize_courses_from_json
from database import get_db

# Load environment variables
load_dotenv()

# Hardcode the correct connection string
DATABASE_URL = "postgresql://alexanderrankine@localhost/academic_advisor"
print(f"Using database URL: {DATABASE_URL}")

def init_db():
    """Initialize the database."""
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
            print("Created database tables.")
        except Exception as e:
            print(f"Error creating tables: {e}")
            traceback.print_exc()
            sys.exit(1)
        
        # Initialize courses from majors.json
        try:
            db = next(get_db())
            initialize_courses_from_json(db)
            print("Initialized courses from majors.json.")
        except Exception as e:
            print(f"Error initializing courses: {e}")
            traceback.print_exc()
            sys.exit(1)
        
        print("Database initialization complete.")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    init_db() 