import json
import os
from typing import List, Optional, Dict
from sqlalchemy.orm import Session

from backend.core.database import Major, User
from backend.models.schemas import MajorCreate
from backend.services.programs import assign_program_to_user, get_available_programs

# Helper function to get available majors list from JSON file
def get_available_majors() -> List[str]:
    try:
        json_path = os.path.join("data", "majors_list.json")
        if not os.path.exists(json_path):
            # Fallback list if file doesn't exist
            return [
                "Computer Science", 
                "Business Administration", 
                "Mathematics", 
                "Physics", 
                "Chemistry"
            ]
        
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading majors list: {e}")
        return ["Computer Science"]  # Default fallback

# Load mapping between major names and program IDs
def get_major_program_mapping() -> Dict[str, str]:
    try:
        json_path = os.path.join("data", "major_program_mapping.json")
        if not os.path.exists(json_path):
            # Fallback empty mapping if file doesn't exist
            return {}
        
        with open(json_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading major-program mapping: {e}")
        return {}  # Default fallback

# Get or create a major by name
def get_or_create_major(db: Session, major_name: str) -> Major:
    # Check if major already exists
    major = db.query(Major).filter(Major.name == major_name).first()
    
    if not major:
        # Create new major
        major = Major(name=major_name)
        db.add(major)
        db.commit()
        db.refresh(major)
    
    return major

# Add major to user
def add_major_to_user(db: Session, user_id: int, major_name: str) -> Optional[Major]:
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    # Get or create major
    major = get_or_create_major(db, major_name)
    
    # Check if user already has this major
    if major in user.majors:
        return major
    
    # Add major to user
    user.majors.append(major)
    
    # If this is the first major and the legacy major field is empty, set it
    if not user.major and len(user.majors) == 1:
        user.major = major_name
        
    db.commit()
    db.refresh(user)
    
    # Attempt to assign the corresponding program to the user
    mapping = get_major_program_mapping()
    if major_name in mapping:
        program_id = mapping[major_name]
        try:
            # Assign the program to the user
            assign_program_to_user(db, user_id, program_id)
            print(f"Successfully assigned program {program_id} to user {user_id} for major {major_name}")
        except Exception as e:
            print(f"Error assigning program {program_id} for major {major_name}: {e}")
    else:
        print(f"Warning: No program mapping found for major {major_name}")
    
    return major

# Remove major from user
def remove_major_from_user(db: Session, user_id: int, major_id: int) -> Optional[Major]:
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    # Get major
    major = db.query(Major).filter(Major.id == major_id).first()
    if not major or major not in user.majors:
        return None
    
    # Remove major from user
    user.majors.remove(major)
    
    # If this was the last major and matches the legacy major field, clear it
    if len(user.majors) == 0 and user.major == major.name:
        user.major = None
    # If the removed major matches the legacy major field, update it to one of the remaining majors if any
    elif user.major == major.name and len(user.majors) > 0:
        user.major = user.majors[0].name
        
    db.commit()
    
    return major

# Get user majors
def get_user_majors(db: Session, user_id: int) -> List[Major]:
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    return user.majors

# Initialize mapping file from available programs
def initialize_major_program_mapping():
    """
    Creates or updates the major_program_mapping.json file based on available programs.
    This is intended to run during application startup to ensure the mapping stays current.
    """
    # Get existing mapping or create new empty dict
    mapping = get_major_program_mapping()
    
    # Get all available programs
    available_programs = get_available_programs()
    
    # Update mapping based on available programs
    for program in available_programs:
        program_id = program.get("id")
        program_name = program.get("program_name")
        program_type = program.get("program_type")
        
        # Only process major programs
        if program_type != "major":
            continue
            
        # Extract major name from program name (e.g. "Accounting Major" -> "Accounting")
        if " Major" in program_name:
            major_name = program_name.replace(" Major", "")
            mapping[major_name] = program_id
    
    # Save the updated mapping
    try:
        json_path = os.path.join("data", "major_program_mapping.json")
        with open(json_path, "w") as f:
            json.dump(mapping, f, indent=2)
        print(f"Updated major-program mapping with {len(mapping)} entries")
    except Exception as e:
        print(f"Error saving major-program mapping: {e}")

# Initialize majors from the majors list
def initialize_majors_from_list(db: Session):
    # First, initialize the major-program mapping
    initialize_major_program_mapping()
    
    # Delete all existing majors that aren't associated with any users
    # This is safer than deleting all majors, as it preserves any user associations
    existing_majors = db.query(Major).all()
    for major in existing_majors:
        if len(major.users) == 0:
            db.delete(major)
    
    # Get the current list of majors from JSON
    majors_list = get_available_majors()
    
    # Find majors in DB that aren't in the JSON list
    majors_to_remove = db.query(Major).filter(~Major.name.in_(majors_list)).all()
    
    # For majors with users, just log a warning
    for major in majors_to_remove:
        if len(major.users) > 0:
            print(f"Warning: Major '{major.name}' is associated with users but no longer in majors_list.json")
        else:
            # Delete the major if it's not in the list and has no users
            db.delete(major)
    
    # Add all majors from the list (get_or_create_major will handle duplicates)
    for major_name in majors_list:
        get_or_create_major(db, major_name)
    
    # Commit all changes
    db.commit() 