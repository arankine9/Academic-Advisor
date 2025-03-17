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

def debug_print_document(doc, prefix="DEBUG DOCUMENT"):
    """Helper function to print document content and metadata"""
    try:
        metadata_str = ", ".join([f"{k}:{v}" for k, v in doc.metadata.items()])
        logger.info(f"{prefix} - METADATA: {metadata_str}")
        logger.info(f"{prefix} - PAGE_CONTENT: {doc.page_content[:100]}")
    except Exception as e:
        logger.info(f"{prefix} - ERROR printing document: {str(e)}")

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
    """
    try:
        docs = retriever.get_relevant_documents(search_query)
        logger.info(f"Retrieved {len(docs)} documents for query: {search_query[:50]}...")
        
        # Log metadata structure for debugging
        if docs:
            logger.info(f"First document metadata keys: {list(docs[0].metadata.keys())}")
        
        # Format each document to include all available fields
        for doc in docs:
            # All fields are available directly in doc.metadata
            formatted_content = f"""
            Course: {doc.metadata.get('class_code', 'Unknown')}
            Credits: {doc.metadata.get('credits', '')}
            Description: {doc.metadata.get('description', '')}
            Prerequisites: {doc.metadata.get('prerequisites', '')}
            Instructor: {doc.metadata.get('instructor', '')}
            Schedule: {doc.metadata.get('days', '')} at {doc.metadata.get('time', '')}
            Location: {doc.metadata.get('classroom', '')}
            Seats Available: {doc.metadata.get('available_seats', '')}
            Total Seats: {doc.metadata.get('total_seats', '')}
            """
            doc.page_content = formatted_content.strip()
            
            # Ensure document has a valid class_code in its metadata
            if 'class_code' not in doc.metadata or not doc.metadata['class_code']:
                # Try to extract from page_content if missing
                course_line = doc.page_content.strip().split('\n')[0]
                if 'Course:' in course_line:
                    extracted_code = course_line.split('Course:')[1].strip()
                    if extracted_code != 'Unknown':
                        doc.metadata['class_code'] = extracted_code
                
                # If still no class_code, create an artificial one
                if 'class_code' not in doc.metadata or not doc.metadata['class_code']:
                    # Try to use some other field as the identifier
                    for key in ['id', 'course_code', 'title']:
                        if key in doc.metadata and doc.metadata[key]:
                            doc.metadata['class_code'] = str(doc.metadata[key])
                            break
                    
                    # Last resort - create a synthetic ID
                    if 'class_code' not in doc.metadata or not doc.metadata['class_code']:
                        doc.metadata['class_code'] = f"SYN-{hash(doc.page_content) % 10000}"
        
        return docs
    except Exception as e:
        logger.error(f"Error in RAG query execution: {e}")
        return []

def optimized_course_search(db: Session, user_id: int, query: str) -> List[Document]:
    """
    Perform optimized course search to find relevant courses.
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
            query_text = future_to_query[future]
            try:
                docs = future.result()
                logger.info(f"Query '{query_text[:30]}...' returned {len(docs)} documents")
                all_results.extend(docs)
            except Exception as e:
                logger.error(f"Error executing search query: {e}")
    
    # Much more lenient deduplication logic
    unique_results = []
    seen_identifiers = set()
    
    # Debug info
    logger.info(f"Starting deduplication for {len(all_results)} documents")
    if all_results:
        sample_doc = all_results[0]
        logger.info(f"Sample document metadata keys: {list(sample_doc.metadata.keys())}")
    
    for doc in all_results:
        # Try multiple different fields as potential identifiers
        # First priority: class_code, then other identifiers
        identifier = None
        
        # Try every possible identifier field
        for field in ['class_code', 'course_code', 'id', 'title', 'name']:
            if field in doc.metadata and doc.metadata[field]:
                identifier = str(doc.metadata[field])
                break
        
        # If no identifier found yet, use first line of page_content
        if not identifier:
            content_lines = doc.page_content.strip().split('\n')
            if content_lines:
                identifier = content_lines[0][:50]  # Use first 50 chars of first line
        
        # As a last resort, use a hash of the content
        if not identifier:
            identifier = f"doc_{hash(doc.page_content[:100])}"
        
        # Only deduplicate if we've seen this exact identifier before
        if identifier not in seen_identifiers:
            seen_identifiers.add(identifier)
            unique_results.append(doc)
            logger.info(f"Added unique document with identifier: {identifier[:30]}...")
    
    logger.info(f"Found {len(unique_results)} unique courses after deduplication")
    return unique_results

def reasoning_based_recommendations(db: Session, user_id: int, query: str, courses: List[dict]) -> List[dict]:
    """
    Use the reasoning model to evaluate and filter courses based on user data and course characteristics.
    
    Args:
        db: Database session
        user_id: User ID
        query: The student's original query
        courses: List of potential course data dictionaries
        
    Returns:
        List of filtered and ranked courses with reasoning notes
    """
    try:
        # First, filter out courses with 0 seats available (only hard rule we keep)
        available_courses = []
        for course in courses:
            # Add debug logging to see what's coming in
            logger.info(f"Checking course: {course.get('course_code', 'Unknown')}")
            logger.info(f"Course structure: {course.keys()}")
            if 'availability' in course:
                logger.info(f"Availability structure: {course['availability']}")
            
            # Try to get available seats (handle both nested and direct access)
            available_seats = ''
            if 'availability' in course and isinstance(course['availability'], dict):
                available_seats = course['availability'].get('available_seats', '')
                logger.info(f"Found nested available_seats: {available_seats}")
            elif 'available_seats' in course:
                available_seats = course.get('available_seats', '')
                logger.info(f"Found direct available_seats: {available_seats}")
            
            # More lenient filtering: only filter out if we're SURE seats = 0
            try:
                if available_seats and int(available_seats) == 0:
                    logger.info(f"Filtering out course with 0 seats: {course.get('course_code', 'Unknown')}")
                    continue
                # Keep course in all other cases
                available_courses.append(course)
                logger.info(f"Keeping course: {course.get('course_code', 'Unknown')}")
            except (ValueError, TypeError):
                # If not parseable as integer, keep the course (benefit of doubt)
                available_courses.append(course)
                logger.info(f"Keeping course (non-integer seats): {course.get('course_code', 'Unknown')}")
        
        # If no courses with available seats, return empty list
        if not available_courses:
            logger.info("No courses with available seats found")
            return []
            
        # Get user data for RAG format
        user_data = format_courses_for_rag(db, user_id)

        # Extract course data safely
        try:
            # Get user progress data
            user_progress = get_required_and_completed_courses(db, user_id)
            
            # Extract completed courses
            completed_courses = []
            if user_progress and 'completed_courses' in user_progress:
                completed_courses = [course.get('course_code', '') for course in user_progress['completed_courses']]
            
            # Extract required courses from all programs
            required_courses = []
            if user_progress and 'programs' in user_progress:
                for program_name, program_data in user_progress['programs'].items():
                    if 'required_courses' in program_data:
                        for course in program_data['required_courses']:
                            if isinstance(course, str):
                                required_courses.append(course)
                            elif isinstance(course, dict) and 'course_code' in course:
                                required_courses.append(course['course_code'])
                            elif isinstance(course, dict) and 'options' in course:
                                # Handle course options (OR relationship)
                                for option in course['options']:
                                    if isinstance(option, str):
                                        required_courses.append(option)
                                    elif isinstance(option, dict) and 'course_code' in option:
                                        required_courses.append(option['course_code'])
            
            logger.info(f"Extracted {len(completed_courses)} completed courses and {len(required_courses)} required courses")
        except Exception as e:
            logger.error(f"Error extracting course data: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            completed_courses = []
            required_courses = []
        
        # Prepare for reasoning model
        logger.info(f"Preparing to evaluate {len(available_courses)} courses with reasoning model")
        
        # Format course data for the reasoning model
        formatted_courses = []
        for i, course in enumerate(available_courses):
            formatted_course = f"""
Course {i+1}: {course.get('course_code', '')}
Name: {course.get('course_name', '')}
Credits: {course.get('credits', '')}
Description: {course.get('description', '')}
Prerequisites: {course.get('prerequisites', '')}
Schedule: {course.get('schedule', {}).get('days', '')} at {course.get('schedule', {}).get('time', '')}
Instructor: {course.get('instructor', '')}
Location: {course.get('location', '')}
Available Seats: {course.get('availability', {}).get('available_seats', '')}
            """
            formatted_courses.append(formatted_course)
        
        courses_text = "\n\n".join(formatted_courses)
        
        # Create prompt for the reasoning model
        reasoning_prompt = f"""
You are an expert academic advisor evaluating course options for a student. You need to:
1. Consider the student's academic history and requirements
2. Evaluate each course option for fit, prerequisites, and schedule conflicts
3. Select the BEST options that would serve this student

STUDENT DATA:
{user_data}

COMPLETED COURSES:
{', '.join(completed_courses) if completed_courses else 'None provided'}

REQUIRED COURSES FOR DEGREE:
{', '.join(required_courses) if required_courses else 'None provided'}

STUDENT QUERY:
{query}

AVAILABLE COURSE OPTIONS:
{courses_text}

For each course, determine:
1. If the student meets prerequisites (based on their completed courses)
2. If there are schedule conflicts with other recommended courses
3. How well it aligns with their query and academic goals
4. Its overall priority ranking (High, Medium, Low)

Then provide your final recommendations in this exact format:

RECOMMENDATIONS:
[course_code_1]: RECOMMEND - [brief reason] - [priority]
[course_code_2]: RECOMMEND - [brief reason] - [priority]
[course_code_3]: REJECT - [brief reason]
...etc for all courses

Final format must be "RECOMMEND" or "REJECT" followed by reason and priority.
"""
        
        # Get reasoning model's evaluation
        reasoning_response = reasoning_model.invoke(reasoning_prompt)
        reasoning_text = reasoning_response.content
        
        # Log response information
        logger.info(f"Received reasoning model response of length: {len(reasoning_text)}")
        
        # Process recommendations
        recommendation_results = []
        
        # Extract recommendations section
        recommendations_section = reasoning_text
        if "RECOMMENDATIONS:" in reasoning_text:
            recommendations_section = reasoning_text.split("RECOMMENDATIONS:")[1].strip()
        
        # Map from course codes to original course dictionaries
        code_to_course = {course.get('course_code', ''): course for course in available_courses}
        
        # Process each line in the recommendations
        for line in recommendations_section.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            try:
                # Extract course code and recommendation
                parts = line.split(':', 1)
                if len(parts) < 2:
                    continue
                    
                course_code = parts[0].strip()
                recommendation = parts[1].strip()
                
                # Find the original course data
                course = code_to_course.get(course_code)
                if not course:
                    # Try partial matching if exact match fails
                    for code, c in code_to_course.items():
                        if course_code in code:
                            course = c
                            break
                
                if not course:
                    continue
                    
                # Extract decision and reason
                is_recommended = "RECOMMEND" in recommendation.upper()
                
                # Try to extract priority
                priority = "Medium"  # Default
                if "HIGH" in recommendation.upper():
                    priority = "High"
                elif "MEDIUM" in recommendation.upper():
                    priority = "Medium" 
                elif "LOW" in recommendation.upper():
                    priority = "Low"
                
                # Extract reason
                reason = recommendation
                if "-" in recommendation:
                    parts = recommendation.split("-")
                    if len(parts) >= 2:
                        reason = parts[1].strip()
                
                # Add evaluated course to results
                course_copy = course.copy()
                course_copy['recommendation'] = {
                    'is_recommended': is_recommended,
                    'reason': reason,
                    'priority': priority
                }
                
                recommendation_results.append(course_copy)
            except Exception as e:
                logger.error(f"Error processing recommendation line: {e}")
                continue
        
        # Sort by priority (High > Medium > Low)
        priority_order = {"High": 0, "Medium": 1, "Low": 2}
        recommendation_results.sort(
            key=lambda x: (
                not x.get('recommendation', {}).get('is_recommended', False),  # Recommended first
                priority_order.get(x.get('recommendation', {}).get('priority', "Medium"), 1)  # Then by priority
            )
        )
        
        logger.info(f"Evaluated {len(recommendation_results)} courses with reasoning model")
        return recommendation_results
        
    except Exception as e:
        logger.error(f"Error in reasoning-based evaluation: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []  # Return empty list on error


def format_course_data(courses: List[Document]) -> List[dict]:
    """
    Format course documents into structured data for the frontend.
    """
    course_data = []
    
    for doc in courses:
        metadata = doc.metadata
        
        # Extract course details from metadata using class_code
        course_info = {
            "course_code": metadata.get('class_code', 'Unknown'),
            "course_name": metadata.get('course_name', 'Unknown'),  # Could be improved with a course name field
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
            "crn": ""  # Keep empty as we're not using CRN
        }
        
        course_data.append(course_info)
    
    return course_data

def process_course_query_with_reasoning(db: Session, user_id: int, query: str) -> dict:
    """
    Process course-related queries using reasoning model for filtering and ranking.
    
    Args:
        db: Database session
        user_id: User ID
        query: The student's query
        
    Returns:
        A dictionary with structured course data and a conversational message
    """
    try:
        logger.info(f"Starting course query processing with reasoning for query: {query[:100]}")
        
        # Step 1: Perform optimized search
        search_results = optimized_course_search(db, user_id, query)
        
        logger.info(f"Search returned {len(search_results)} results")
        
        if not search_results:
            # No results found
            logger.info("No search results found")
            return {
                "type": "course_recommendations",
                "message": "I couldn't find any courses matching your criteria. Can you try rephrasing your request or providing more details? 📚",
                "course_data": []
            }
        
        # Step 2: Format course data
        course_data = format_course_data(search_results)
        logger.info(f"Formatted {len(course_data)} courses")
        
        # Step 3: Use reasoning model to evaluate and filter courses
        evaluated_courses = reasoning_based_recommendations(db, user_id, query, course_data)
        logger.info(f"Evaluated {len(evaluated_courses)} courses with reasoning model")
        
        # Filter recommended courses
        recommended_courses = [course for course in evaluated_courses 
                              if course.get('recommendation', {}).get('is_recommended', False)]
        
        # Step 4: Generate friendly response based on reasoning results
        response_prompt = f"""
The student asked: "{query}"

Based on their academic history and requirements, I've evaluated potential courses. 
I found {len(recommended_courses)} recommended courses that would be beneficial for them.

Write a friendly, brief response (2-3 sentences) that:
1. Addresses their query directly
2. Mentions how you evaluated courses based on their academic history and requirements
3. Includes an encouraging tone and 1-2 appropriate emojis
4. Is personalized to their situation

DO NOT list the courses - they'll be shown separately.
"""
        
        message_response = response_model.invoke(response_prompt)
        message = message_response.content.strip()
        
        # Return structured response with all evaluated courses
        return {
            "type": "course_recommendations",
            "message": message,
            "course_data": evaluated_courses  # Include all courses with reasoning notes
        }
        
    except Exception as e:
        logger.error(f"Error in process_course_query_with_reasoning: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "type": "course_recommendations",
            "message": "I encountered an issue while finding courses for you. Please try again or rephrase your request. 🙇",
            "course_data": []
        }

def get_advice(db, user_id: int, query=None):
    """
    Main function that orchestrates the entire query processing pipeline using reasoning model.
    
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
            return process_course_query_with_reasoning(db, user_id, default_query)
        
        # Classify the intent using LLM
        intent = classify_intent(query)
        logger.info(f"LLM classified intent: {intent} for query: {query[:50]}...")
        
        # Process based on intent
        if intent == "COURSE":
            return process_course_query_with_reasoning(db, user_id, query)
        else:
            # For general conversation, return plain text
            return process_general_query(query)
            
    except Exception as e:
        logger.error(f"Error in get_advice: {e}")
        return "I'm sorry, I encountered an error while generating recommendations. Please try again later or try rephrasing your question."