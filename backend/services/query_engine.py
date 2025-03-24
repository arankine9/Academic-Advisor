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
# Add back the majors import that was missing in paste 2
from backend.services.majors import get_user_majors

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

# Reasoning Prompt - Updated to include major requirements
REASONING_PROMPT = """
You are an academic advisor who will be retrieving information and formulating recommendations for the given student.

You need to determine the best courses for this student based on:
- The user's specific query and academic history
- Their major/minor requirements and degree progress
- Course prerequisites and availability
- How courses fit into their academic plan

{user_data}

Student query: {query}

Analyze what this student needs and generate 3-5 specific search queries that would find the most relevant courses.
Each query should target a different aspect of what the student needs, including major requirements if applicable.

SEARCH QUERIES:
"""

# Final Response Prompt - Updated to reference major requirements
FINAL_RESPONSE_PROMPT = """
You are a friendly, helpful academic advisor. Based on the student's data and the recommended courses, provide a personalized response.

{user_data}

Student query: {query}

Recommended courses: 
{recommended_courses}

Create a brief, friendly response (1-3 sentences max) that:
1. Addresses their query directly
2. Mentions how the recommended courses help them progress in their major when applicable
3. Includes 1-2 appropriate emojis (📚, ✨, 🎯, 🚀, ✅, 📋, etc.)

Do NOT list the courses in your response - they will be displayed separately. Focus on being encouraging and helpful.
"""

# Add the major formatting function from paste 1
def format_major_info(majors):
    """
    Format user majors for inclusion in the RAG context.
    
    Args:
        majors: List of Major objects
        
    Returns:
        Formatted string with major information
    """
    if not majors:
        return "Majors: None declared"
    
    major_names = [major.name for major in majors]
    if len(major_names) == 1:
        return f"Major: {major_names[0]}"
    else:
        return f"Majors: {', '.join(major_names[:-1])} and {major_names[-1]}"

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
    6. MAJOR_REQUIREMENTS: Asking about major-specific courses or requirements
    
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
    elif "MAJOR" in detailed_intent:
        return "Checking your major requirements and progress... 📝"
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
    Includes major information in the search context.
    """
    # Get user course data for RAG
    course_data = format_courses_for_rag(db, user_id)
    
    # Get and format user major information
    majors = get_user_majors(db, user_id)
    major_info = format_major_info(majors)
    
    # Combine course and major information for the user context
    user_data = f"{major_info}\n\n{course_data}"
    logger.info(f"User context includes: {major_info}")
    
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
    Use the reasoning model to recommend 3-5 courses based on user data including major information.
    """
    try:
        # Log the number of courses we're starting with
        logger.info(f"Starting with {len(courses)} courses to evaluate")
        
        # Get user course data
        course_data = ""
        try:
            course_data = format_courses_for_rag(db, user_id)
            logger.info("Successfully retrieved user course data")
        except Exception as e:
            logger.error(f"Error getting user course data: {e}")
            # Continue anyway - we'll just have less context
        
        # Get user major data
        major_info = ""
        try:
            majors = get_user_majors(db, user_id)
            major_info = format_major_info(majors)
            logger.info(f"Successfully retrieved user major data: {major_info}")
        except Exception as e:
            logger.error(f"Error getting user major data: {e}")
            major_info = "Majors: Unknown"
        
        # Combine course and major information for the user context
        user_data = f"{major_info}\n\n{course_data}"
        
        # Format course data for the reasoning model - simplified version
        formatted_courses = []
        for i, course in enumerate(courses):
            course_info = f"""
Course {i+1}: {course.get('course_code', 'Unknown')}
Name: {course.get('course_name', '')}
Description: {course.get('description', '')[:100]}...
Prerequisites: {course.get('prerequisites', '')}
            """
            formatted_courses.append(course_info)
        
        courses_text = "\n\n".join(formatted_courses)
        
        # Create simpler prompt for the reasoning model
        reasoning_prompt = f"""
You are an academic advisor helping a student choose courses. Based on the student's query, academic history, and major requirements, recommend 3-5 courses from the list below.

STUDENT QUERY: {query}

STUDENT ACADEMIC INFORMATION:
{user_data}

AVAILABLE COURSES:
{courses_text}

Please respond with ONLY the course codes of your recommended courses in this exact format:
RECOMMENDED COURSES:
- [course_code_1]
- [course_code_2]
- [course_code_3]
- [course_code_4] (optional)
- [course_code_5] (optional)

Just list the course codes, nothing else. For example: "CS 101", "MATH 210", etc.
"""
        
        # Get reasoning model's evaluation
        logger.info("Sending query to reasoning model")
        reasoning_response = reasoning_model.invoke(reasoning_prompt)
        reasoning_text = reasoning_response.content
        logger.info(f"Received reasoning model response of length: {len(reasoning_text)}")
        
        # Extract recommended course codes using a more forgiving approach
        recommended_codes = []
        
        # Try to find a "RECOMMENDED COURSES:" section
        if "RECOMMENDED COURSES:" in reasoning_text:
            recommendation_section = reasoning_text.split("RECOMMENDED COURSES:")[1].strip()
            
            # Extract course codes from bullet points or numbered lists
            for line in recommendation_section.split('\n'):
                line = line.strip()
                if line.startswith('-') or line.startswith('*') or (line and line[0].isdigit() and '. ' in line):
                    # Extract the code from the line
                    if line.startswith('-') or line.startswith('*'):
                        code = line[1:].strip()
                    else:
                        code = line.split('. ', 1)[1].strip()
                    
                    # Clean up the code
                    if '[' in code and ']' in code:
                        code = code.split('[')[1].split(']')[0]
                    
                    recommended_codes.append(code)
        else:
            # Fallback: just look for anything that looks like a course code
            # This regex looks for patterns like "CS 101", "MATH 210", etc.
            import re
            course_code_pattern = r'[A-Z]{2,4}\s*\d{3,4}'
            recommended_codes = re.findall(course_code_pattern, reasoning_text)[:5]  # Take up to 5
        
        logger.info(f"Extracted {len(recommended_codes)} recommended course codes: {recommended_codes}")
        
        # If we got no recommendations, just take the first 3 courses
        if not recommended_codes and courses:
            logger.info("No recommendations found, using first 3 courses")
            recommended_codes = [course.get('course_code', f"Course-{i}") for i, course in enumerate(courses[:3])]
        
        # Map recommended codes back to full course objects
        result_courses = []
        for code in recommended_codes:
            # Find matching course
            for course in courses:
                course_code = course.get('course_code', '')
                # Case-insensitive partial matching for robustness
                if code.lower() in course_code.lower() or course_code.lower() in code.lower():
                    # Create a copy with recommendation data
                    course_copy = course.copy()
                    
                    # Add recommendation reason based on user's major if available
                    major_names = [major.name for major in majors] if majors else []
                    if major_names:
                        major_text = major_names[0] if len(major_names) == 1 else "your majors"
                        course_copy['recommendation'] = {
                            'is_recommended': True,
                            'reason': f"Recommended for your progress in {major_text}.",
                            'priority': "High"
                        }
                    else:
                        course_copy['recommendation'] = {
                            'is_recommended': True,
                            'reason': "Recommended based on your academic history and goals.",
                            'priority': "High"
                        }
                    
                    result_courses.append(course_copy)
                    break
        
        # Ensure we have at least some recommendations
        if not result_courses and courses:
            logger.info("Couldn't match recommendations to courses, using first 3")
            for i, course in enumerate(courses[:3]):
                course_copy = course.copy()
                course_copy['recommendation'] = {
                    'is_recommended': True,
                    'reason': "Suggested option for your next semester.",
                    'priority': "Medium"
                }
                result_courses.append(course_copy)
        
        logger.info(f"Returning {len(result_courses)} recommended courses")
        return result_courses
        
    except Exception as e:
        logger.error(f"Error in reasoning-based recommendations: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # As a last resort, return simple recommendations
        if courses:
            logger.info("Using fallback recommendation logic")
            return [
                {**courses[i], 'recommendation': {
                    'is_recommended': True,
                    'reason': "Suggested course option.",
                    'priority': "Medium"
                }} 
                for i in range(min(3, len(courses)))
            ]
        return []

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
    Includes major information in the reasoning context.
    
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
        
        # Get user's majors for personalized response
        majors = get_user_majors(db, user_id)
        major_names = [major.name for major in majors] if majors else []
        
        # Step 4: Generate friendly response based on reasoning results
        response_prompt = f"""
The student asked: "{query}"

Student major(s): {', '.join(major_names) if major_names else 'None declared'}

Based on their academic history and requirements, I've evaluated potential courses. 
I found {len(recommended_courses)} recommended courses that would be beneficial for them.

Write a friendly, brief response (2-3 sentences) that:
1. Addresses their query directly
2. Mentions how you evaluated courses based on their academic history and requirements
3. References their major(s) if they have any declared
4. Includes an encouraging tone and 1-2 appropriate emojis
5. Is personalized to their situation

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
    Main function that orchestrates the entire query processing pipeline.
    Now includes user major information in the context.
    
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