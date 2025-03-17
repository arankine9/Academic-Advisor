"""
Enhanced Query Engine for Academic Advisor
Implements intent classification, multi-step reasoning, and RAG-based query refinement.
"""

import os
import re
import logging
import json
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from langchain_pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from pinecone import Pinecone as PineconeClient
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

# Import our services
from backend.services.programs import format_courses_for_rag, get_required_and_completed_courses

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define Pinecone index name
INDEX_NAME = "duckweb-spring24"

# Initialize Pinecone client
pc = PineconeClient(api_key=PINECONE_API_KEY)

# Ensure index exists
if INDEX_NAME not in pc.list_indexes().names():
    raise ValueError(f"Pinecone index '{INDEX_NAME}' does not exist. Run `ingest_majors.py` first to create it.")

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-3-small")

# Initialize Pinecone vector store with proper text key
vectorstore = Pinecone.from_existing_index(
    index_name=INDEX_NAME,
    embedding=embeddings,
    text_key="class_code",  # Specify the text key to match our document structure
)

# Create a retriever with search parameters
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}  # Keep only the top 5 results
)

# Initialize LLM models
intent_classifier = ChatOpenAI(
    model="gpt-4o-mini",  # Faster model for intent classification
    openai_api_key=OPENAI_API_KEY,
    temperature=0.2
)

reasoning_model = ChatOpenAI(
    model="o1-mini",  # More powerful model for reasoning
    openai_api_key=OPENAI_API_KEY,
)

response_model = ChatOpenAI(
    model="gpt-4o",  # Efficient model for responses
    openai_api_key=OPENAI_API_KEY,
    temperature=0.7  # Higher temperature for more natural responses
)

# Enhanced Intent Classification Prompt
INTENT_CLASSIFICATION_PROMPT = """
You are an academic advising system assistant analyzing student queries to determine what they need help with.

Student query: {query}

Classify this query into ONE of these categories:
- COURSE: Any query related to course recommendations, prerequisites, scheduling, degree requirements, or specific course information.
- GENERAL: Only purely conversational exchanges with NO academic content whatsoever.

CRITICAL GUIDANCE:
- If a student mentions courses they've taken and is asking about what to take next, this is COURSE.
- If a student mentions their major and asks for recommendations, this is COURSE.
- If a query begins with a greeting but includes academic questions, this is COURSE, not GENERAL.
- Consider phrases like "I'm wondering what classes I should take" as COURSE.
- When a student mentions specific course codes (like CS 212, MATH 252) and asks about future courses, this is COURSE.
- If there's ANY mention of academic planning, course selection, prerequisites, or degree requirements, classify as COURSE.
- Only use GENERAL for pure greetings, thanks, or casual conversations with zero academic content.
- When in doubt between COURSE and GENERAL, choose COURSE.

Respond with exactly one word: either COURSE or GENERAL.
"""

# Reasoning Prompt
REASONING_PROMPT = """
You are an academic advisor who will be retrieving information and formulating recommendations for the given student.

You need to determine the best courses for this student based on:
- The user's specific query and academic history
- Their major/minor requirements
- Course prerequisites and availability
- How courses fit into their degree progress

{user_data}

Student query: {query}

Analyze what this student needs and generate 3-5 specific search queries that would find the most relevant courses.
Each query should target a different aspect of what the student needs.

SEARCH QUERIES:
"""

# Final Response Prompt
FINAL_RESPONSE_PROMPT = """
You are a friendly, helpful academic advisor. Based on the student's data and the recommended courses, provide a personalized response.

{user_data}

Student query: {query}

Recommended courses: 
{recommended_courses}

Create a brief, friendly response (1-3 sentences max) that:
1. Addresses their query directly
2. Mentions how the recommended courses help them
3. Includes 1-2 appropriate emojis (📚, ✨, 🎯, 🚀, ✅, 📋, etc.)

Do NOT list the courses in your response - they will be displayed separately. Focus on being encouraging and helpful.
"""


def classify_intent(query: str) -> str:
    """
    Classify if the query is course-related or general conversation using only LLM classification.
    
    Args:
        query: The student's query
        
    Returns:
        String indicating "COURSE" or "GENERAL"
    """
    try:
        prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
        response = intent_classifier.invoke(prompt)
        
        # Extract the response and normalize
        intent = response.content.strip().upper()
        
        # Default to COURSE if response is unclear
        if "COURSE" in intent:
            logger.info(f"Classified as COURSE: {query[:50]}...")
            return "COURSE"
        elif "GENERAL" in intent:
            logger.info(f"Classified as GENERAL: {query[:50]}...")
            return "GENERAL"
        else:
            logger.warning(f"Unclear classification result: '{intent}' - defaulting to COURSE")
            return "COURSE"
            
    except Exception as e:
        logger.error(f"Error in intent classification: {e}")
        # Default to COURSE in case of errors
        return "COURSE"

def generate_acknowledgment(query: str) -> str:
    """Generate a contextual acknowledgment message based on the query"""
    # Use the LLM to determine the exact type of request
    prompt = f"""
    The student asked: "{query}"
    
    What kind of information is the student looking for? Choose ONE of:
    1. COURSE_RECOMMENDATION: Seeking course suggestions
    2. PREREQUISITE_CHECK: Asking about prerequisites
    3. SCHEDULE_PLANNING: Concerned about scheduling
    4. DEGREE_PROGRESS: Asking about graduation requirements
    5. COURSE_DETAILS: Asking about specific course information
    
    Respond with only the category name.
    """
    
    try:
        response = intent_classifier.invoke(prompt)
        detailed_intent = response.content.strip().upper()
    except:
        detailed_intent = "COURSE_RECOMMENDATION"  # Default if classification fails
    
    # Generate acknowledgment based on intent
    if "PREREQUISITE" in detailed_intent:
        return "Checking prerequisites and course sequences for you... 📋"
    elif "SCHEDULE" in detailed_intent:
        return "Analyzing your schedule to find compatible courses... ⏰"
    elif "DEGREE" in detailed_intent or "PROGRESS" in detailed_intent:
        return "Reviewing your degree requirements and progress... 🎓"
    elif "DETAILS" in detailed_intent:
        return "Looking up those course details for you... 📚"
    else:
        return "On it! Searching for course recommendations that match your academic plan... 🔍"

def process_general_query(query: str) -> str:
    """
    Process general conversation queries with a friendly response.
    
    Args:
        query: The student's general query
        
    Returns:
        A friendly response
    """
    prompt = f"""
    You are a friendly academic advisor chatbot. The student has asked a general question (not specifically about courses).
    Respond in a friendly, helpful way. Keep your response concise and natural.
    
    If appropriate, suggest 1-2 course-related questions they could ask you, like "What classes should I take next term?"
    
    Student query: {query}
    """
    
    response = response_model.invoke(prompt)
    return response.content.strip()

def extract_search_queries(reasoning_output: str) -> List[str]:
    """
    Extract search queries from the reasoning model's output.
    
    Args:
        reasoning_output: The output from the reasoning model
        
    Returns:
        List of search queries
    """
    queries = []
    
    # Look for the SEARCH QUERIES section
    if "SEARCH QUERIES:" in reasoning_output:
        # Extract the section after SEARCH QUERIES:
        search_section = reasoning_output.split("SEARCH QUERIES:")[1].split("REASONING:")[0].strip()
        
        # Parse each line that might be a query
        lines = search_section.split("\n")
        for line in lines:
            line = line.strip()
            # Match both numbered (1. query) and bullet point (* query) formats
            if line and (
                (line[0].isdigit() and line[1:3] in [". ", ") "]) or
                line.startswith("* ") or line.startswith("- ")
            ):
                # Extract the query part
                if line[0].isdigit():
                    query = line[line.index(" ")+1:].strip()
                else:
                    query = line[2:].strip()
                
                if query and not query.startswith("[") and len(query) > 5:
                    queries.append(query)
    
    # If no queries found with the structured format, try to extract any lines that look like queries
    if not queries:
        lines = reasoning_output.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("Query:") or line.startswith("Search for:"):
                query = line.split(":", 1)[1].strip()
                if len(query) > 5:  # Ensure it's not too short
                    queries.append(query)
    
    # Fallback: if still no queries, use parts of the reasoning text
    if not queries and len(reasoning_output) > 30:
        # Just use the first paragraph as a query
        first_para = reasoning_output[:200].replace("\n", " ")
        queries.append(first_para)
    
    return queries[:5]  # Limit to 5 queries

def execute_rag_query(search_query: str) -> List[Document]:
    """
    Execute a RAG query to retrieve relevant documents.
    
    Args:
        search_query: The search query for the retriever
        
    Returns:
        List of retrieved documents including all fields
    """
    try:
        docs = retriever.get_relevant_documents(search_query)
        logger.info(f"Retrieved {len(docs)} documents for query: {search_query[:50]}...")
        
        # Format each document to include all available fields
        for doc in docs:
            # All fields are available directly in doc.metadata
            formatted_content = f"""
            Course: {doc.metadata.get('class_code', '')}
            Credits: {doc.metadata.get('credits', '')}
            Description: {doc.metadata.get('description', '')}
            Prerequisites: {doc.metadata.get('prerequisites', '')}
            Instructor: {doc.metadata.get('instructor', '')}
            Schedule: {doc.metadata.get('days', '')} at {doc.metadata.get('time', '')}
            Location: {doc.metadata.get('classroom', '')}
            Seats Available: {doc.metadata.get('available_seats', '')}
            Total Seats: {doc.metadata.get('total_seats', '')}
            CRN: {doc.metadata.get('crn', '')}
            """
            doc.page_content = formatted_content.strip()
        return docs
    except Exception as e:
        logger.error(f"Error in RAG query execution: {e}")
        return []

def optimized_course_search(db: Session, user_id: int, query: str) -> List[Document]:
    """
    Perform optimized course search to find relevant courses.
    
    Args:
        db: Database session
        user_id: User ID
        query: The student's query
    
    Returns:
        List of relevant course documents
    """
    # Format user data for RAG
    user_data = format_courses_for_rag(db, user_id)
    
    # Generate search queries
    reasoning_prompt = REASONING_PROMPT.format(
        query=query,
        user_data=user_data
    )
    
    reasoning_response = reasoning_model.invoke(reasoning_prompt)
    reasoning_output = reasoning_response.content
    
    # Extract search queries
    search_queries = extract_search_queries(reasoning_output)
    logger.info(f"Generated {len(search_queries)} search queries for '{query[:50]}...'")
    
    if not search_queries:
        # Fallback: use the original query
        search_queries = [query]
    
    # Execute all search queries in parallel
    all_results = []
    with ThreadPoolExecutor(max_workers=min(len(search_queries), 5)) as executor:
        future_to_query = {executor.submit(execute_rag_query, q): q for q in search_queries}
        for future in concurrent.futures.as_completed(future_to_query):
            try:
                docs = future.result()
                all_results.extend(docs)
            except Exception as e:
                logger.error(f"Error executing search query: {e}")
    
    # Deduplicate results
    unique_results = []
    seen_codes = set()
    
    for doc in all_results:
        code = doc.metadata.get('class_code')
        if code and code not in seen_codes:
            seen_codes.add(code)
            unique_results.append(doc)
    
    logger.info(f"Found {len(unique_results)} unique courses after deduplication")
    return unique_results

def check_schedule_conflict(days1: str, time1: str, days2: str, time2: str) -> bool:
    """
    Check if two schedules conflict.
    
    Args:
        days1: Days for first schedule (e.g., "MWF")
        time1: Time for first schedule (e.g., "10:00-11:50")
        days2: Days for second schedule
        time2: Time for second schedule
    
    Returns:
        True if there's a conflict, False otherwise
    """
    # Simple check for now - more sophisticated logic can be added
    if not days1 or not time1 or not days2 or not time2:
        return False  # If any schedule is unspecified, assume no conflict
    
    # Check if any days overlap
    for day in days1:
        if day in days2:
            # Now check if times overlap
            try:
                # Parse times (assuming format like "10:00-11:50")
                t1_start, t1_end = time1.split('-')
                t2_start, t2_end = time2.split('-')
                
                # Convert to 24-hour format for comparison
                # This is a simplified version - in a real app we would use proper time parsing
                t1_start_hour = int(t1_start.split(':')[0])
                t1_end_hour = int(t1_end.split(':')[0])
                t2_start_hour = int(t2_start.split(':')[0])
                t2_end_hour = int(t2_end.split(':')[0])
                
                # Check for overlap
                if (t1_start_hour <= t2_end_hour and t1_end_hour >= t2_start_hour):
                    return True
            except:
                # If time parsing fails, be conservative and assume conflict
                return True
                
    return False

def verify_course_recommendations(db: Session, user_id: int, courses: List[dict]) -> List[dict]:
    """
    Verify course recommendations against various constraints.
    
    Args:
        db: Database session
        user_id: User ID
        courses: List of course data dictionaries
        
    Returns:
        List of verified courses with additional verification status
    """
    # Get user data
    user_info = get_required_and_completed_courses(db, user_id)
    completed_courses = [course['course_code'] for course in user_info.get('completed_courses', [])]
    
    # Track scheduled times to check conflicts
    scheduled_times = {}
    verified_courses = []
    
    for course in courses:
        # Set default verification status
        course['verification_status'] = "VALID"
        
        # Check if already completed
        if course['course_code'] in completed_courses:
            course['verification_status'] = f"INVALID: Already completed {course['course_code']}"
            continue
        
        # Check seat availability
        available_seats = course.get('availability', {}).get('available_seats', 0)
        try:
            available_seats = int(available_seats)
        except:
            available_seats = 0
            
        if available_seats <= 0:
            course['verification_status'] = "INVALID: No available seats"
            continue
            
        # Schedule conflict check
        days = course.get('schedule', {}).get('days', '')
        time = course.get('schedule', {}).get('time', '')
        
        if days and time:
            has_conflict = False
            for existing_course, existing_time in scheduled_times.items():
                if check_schedule_conflict(days, time, existing_time[0], existing_time[1]):
                    course['verification_status'] = f"INVALID: Schedule conflict with {existing_course}"
                    has_conflict = True
                    break
                    
            if has_conflict:
                continue
                
            # Add to scheduled times
            scheduled_times[course['course_code']] = (days, time)
        
        # Course passed all basic checks
        verified_courses.append(course)
    
    # If we have many verified courses, use LLM for prerequisite checking
    if len(verified_courses) > 1:
        prerequisite_check_data = []
        for course in verified_courses:
            prerequisite_check_data.append({
                'code': course['course_code'],
                'prerequisites': course.get('prerequisites', '')
            })
        
        # Prepare user data for prerequisite check
        prerequisite_prompt = f"""
        Check if this student has completed prerequisites for these courses:
        {json.dumps(prerequisite_check_data, indent=2)}
        
        Student's completed courses: {', '.join(completed_courses)}
        
        For each course, respond ONLY with one of:
        1. "PREREQUISITE_MET" if all prerequisites are met
        2. "PREREQUISITE_MISSING: [specific missing prerequisite]" if any are missing
        
        Format: COURSE_CODE: RESULT
        """
        
        try:
            prerequisite_response = reasoning_model.invoke(prerequisite_prompt)
            prerequisite_results = parse_prerequisite_results(prerequisite_response.content)
            
            # Apply prerequisite check results
            for course in verified_courses:
                course_code = course['course_code']
                if course_code in prerequisite_results:
                    result = prerequisite_results[course_code]
                    if not result.startswith("PREREQUISITE_MET"):
                        course['verification_status'] = f"INVALID: {result}"
        except Exception as e:
            logger.error(f"Error in prerequisite checking: {e}")
    
    return courses

def parse_prerequisite_results(content: str) -> Dict[str, str]:
    """
    Parse prerequisite check results from LLM output.
    
    Args:
        content: LLM response content
        
    Returns:
        Dictionary mapping course codes to prerequisite check results
    """
    results = {}
    
    # Parse each line
    for line in content.strip().split('\n'):
        # Look for "COURSE_CODE: RESULT" pattern
        if ':' in line:
            parts = line.split(':', 1)
            course_code = parts[0].strip()
            result = parts[1].strip()
            
            results[course_code] = result
    
    return results

def format_course_data(courses: List[Document]) -> List[dict]:
    """
    Format course documents into structured data for the frontend.
    
    Args:
        courses: List of course documents
        
    Returns:
        List of course data dictionaries
    """
    course_data = []
    
    for doc in courses:
        metadata = doc.metadata
        
        # Extract course details from metadata
        course_info = {
            "course_code": metadata.get('class_code', ''),
            "course_name": metadata.get('class_name', ''),
            "credits": metadata.get('credits', ''),
            "description": metadata.get('description', ''),
            "prerequisites": metadata.get('prerequisites', ''),
            "instructor": metadata.get('instructor', ''),
            "schedule": {
                "days": metadata.get('days', ''),
                "time": metadata.get('time', '')
            },
            "location": metadata.get('classroom', ''),
            "availability": {
                "available_seats": metadata.get('available_seats', ''),
                "total_seats": metadata.get('total_seats', '')
            },
            "crn": metadata.get('crn', '')
        }
        
        course_data.append(course_info)
    
    return course_data

def generate_friendly_response(query: str, valid_courses: List[dict]) -> str:
    """
    Generate a friendly, concise response with emojis
    
    Args:
        query: The student's query
        valid_courses: List of validated course data
        
    Returns:
        A friendly, concise response message
    """
    # Extract course codes for the prompt
    course_codes = [course['course_code'] for course in valid_courses]
    
    if not course_codes:
        # No valid courses found
        prompt = f"""
        The student asked: "{query}"
        
        Unfortunately, I couldn't find any suitable courses that meet all requirements (prerequisites, availability, scheduling).
        
        Write a friendly, brief response (1-3 sentences) that:
        1. Acknowledges their request
        2. Explains that no perfect matches were found
        3. Suggests they might want to check with their academic advisor or consider schedule flexibility
        4. Includes an appropriate emoji
        
        RESPONSE:
        """
    else:
        # Valid courses found
        prompt = f"""
        The student asked: "{query}"
        
        I found these courses for them: {', '.join(course_codes)}
        
        Write a friendly, brief response (1-3 sentences) that:
        1. Addresses their query directly
        2. Mentions you've found some great options for them
        3. Includes 1-2 appropriate emojis (📚, ✨, 🎯, 🚀, ✅)
        4. Is encouraging and positive
        5. Does NOT list the individual courses (they'll be shown separately)
        
        RESPONSE:
        """
    
    response = response_model.invoke(prompt)
    return response.content.strip()

def process_course_query(db: Session, user_id: int, query: str) -> dict:
    """
    Process course-related queries using optimized search and verification.
    
    Args:
        db: Database session
        user_id: User ID
        query: The student's query
        
    Returns:
        A dictionary with structured course data and a conversational message
    """
    try:
        # Step 1: Perform optimized search
        search_results = optimized_course_search(db, user_id, query)
        
        if not search_results:
            # No results found
            return {
                "type": "course_recommendations",
                "message": "I couldn't find any courses matching your criteria. Can you try rephrasing your request or providing more details? 📚",
                "course_data": []
            }
        
        # Step 2: Format course data
        course_data = format_course_data(search_results)
        
        # Step 3: Verify courses against constraints
        verified_courses = verify_course_recommendations(db, user_id, course_data)
        
        # Filter out valid courses
        valid_courses = [course for course in verified_courses if course['verification_status'] == "VALID"]
        
        # Step 4: Generate friendly response
        message = generate_friendly_response(query, valid_courses)
        
        # Return structured response
        return {
            "type": "course_recommendations",
            "message": message,
            "course_data": verified_courses  # Include all courses with their verification status
        }
    except Exception as e:
        logger.error(f"Error in process_course_query: {e}")
        return {
            "type": "course_recommendations",
            "message": "I encountered an issue while finding courses for you. Please try again or rephrase your request. 🙇",
            "course_data": []
        }

def get_advice(db, user_id: int, query=None):
    """
    Main function that orchestrates the entire query processing pipeline.
    
    Args:
        db: Database session
        user_id: The user's ID
        query: The student's query (optional)
        
    Returns:
        A formatted response or structured data
    """
    try:
        # If no query is provided, use a default recommendation prompt
        if not query:
            default_query = "What courses should I take next term?"
            return process_course_query(db, user_id, default_query)
        
        # Classify the intent using LLM
        intent = classify_intent(query)
        logger.info(f"LLM classified intent: {intent} for query: {query[:50]}...")
        
        # Process based on intent
        if intent == "COURSE":
            return process_course_query(db, user_id, query)
        else:
            # For general conversation, return plain text
            return process_general_query(query)
            
    except Exception as e:
        logger.error(f"Error in get_advice: {e}")
        return "I'm sorry, I encountered an error while generating recommendations. Please try again later or try rephrasing your question."