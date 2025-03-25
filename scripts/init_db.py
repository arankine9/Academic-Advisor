import os
import sys
import traceback
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# IMPORTANT: Updated imports
from backend.core.database import get_db, create_tables, Base, UserProgram
from backend.services.unified_course_service import initialize_courses_from_json
from backend.services.unified_program_service import initialize_majors_from_list

# Load environment variables
load_dotenv()

# Hardcode the correct connection string
DATABASE_URL = os.getenv("DATABASE_URL")
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
            
            # Verify tables were created
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            expected_tables = ['users', 'courses', 'user_courses', 'user_programs', 'majors', 'user_majors']
            
            for table in expected_tables:
                if table in table_names:
                    print(f"✅ Table '{table}' created successfully")
                else:
                    print(f"❌ Table '{table}' not found!")
            
            print("Created database tables.")
        except Exception as e:
            print(f"Error creating tables: {e}")
            traceback.print_exc()
            sys.exit(1)
        
        # Initialize data
        try:
            db = next(get_db())
            
            # Initialize courses from majors.json
            initialize_courses_from_json(db)
            print("Initialized courses from majors.json.")
            
            # Synchronize majors with majors_list.json
            initialize_majors_from_list(db)
            print("Synchronized majors with majors_list.json.")
        except Exception as e:
            print(f"Error initializing data: {e}")
            traceback.print_exc()
            sys.exit(1)
        
        print("Database initialization complete.")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    init_db()