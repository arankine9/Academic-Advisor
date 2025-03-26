# New recommendation_service.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import os
import traceback
from langchain_openai import ChatOpenAI

from backend.services.unified_course_service import course_service
from backend.services.unified_program_service import program_service

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize LLM models with consistent naming
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
logger.debug(f"OPENAI_API_KEY is {'set' if OPENAI_API_KEY else 'NOT SET'}")

newline = '\n'

try:
    logger.debug("Initializing intent_model (gpt-4o-mini)")
    intent_model = ChatOpenAI(
        model="gpt-4o-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.2
    )
    
    logger.debug("Initializing recommendation_model (o1-mini)")
    recommendation_model = ChatOpenAI(
        model="o1-mini",
        openai_api_key=OPENAI_API_KEY,
        temperature=1.0
    )
    
    logger.debug("Initializing response_model (gpt-4o)")
    response_model = ChatOpenAI(
        model="gpt-4o",
        openai_api_key=OPENAI_API_KEY,
        temperature=0.7
    )
    
    logger.info("All OpenAI models initialized successfully")
except Exception as e:
    logger.error(f"Error initializing OpenAI models: {e}")
    logger.error(traceback.format_exc())

# Intent classification prompt
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

# Course recommendation prompt
COURSE_RECOMMENDATION_PROMPT = """
You are an AI academic advisor helping a student choose courses based on their academic history, program requirements, and query.

STUDENT QUERY: {query}

STUDENT ACADEMIC INFORMATION:
{user_progress}

AVAILABLE COURSES:
{available_courses}

Please select the 3-5 most appropriate courses for this student based on:
1. Their program requirements
2. Courses they've already completed
3. Prerequisites they've satisfied
4. The specific nature of their query

For each course you recommend, provide:
1. The course code
2. A brief explanation of why you're recommending it (1-2 sentences)
3. Priority level (High, Medium, Low)

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:
RECOMMENDED COURSES:
- [class_code_1]: [reason] | [priority]
- [class_code_2]: [reason] | [priority]
- [class_code_3]: [reason] | [priority]
- [class_code_4]: [reason] | [priority] (optional)
- [class_code_5]: [reason] | [priority] (optional)
"""

# Final response format
FINAL_RESPONSE_PROMPT = """
You are a friendly, helpful academic advisor. Based on the student's data and the recommended courses, provide a personalized response.

Student query: {query}

Recommended courses: 
{recommended_courses}

Create a brief, friendly response (2-3 sentences max) that:
1. Addresses their query directly
2. Mentions how the recommended courses help them progress in their programs when applicable
3. Includes 1-2 appropriate emojis (📚, ✨, 🎯, 🚀, ✅, 📋, etc.)

Do NOT list the courses in your response - they will be displayed separately. Focus on being encouraging and helpful.
"""

class RecommendationService:
    """
    Unified service for all course recommendation functionality.
    Handles intent classification, course searching, and generating recommendations.
    """
    
    @staticmethod
    def classify_intent(query: str) -> str:
        """
        Classify if the query is course-related or general conversation.
        
        Args:
            query: The student's query
            
        Returns:
            String indicating "COURSE" or "GENERAL"
        """
        logger.debug(f"Classifying intent for query: '{query}'")
        
        try:
            prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
            logger.debug("Calling intent_model with formatted prompt")
            
            response = intent_model.invoke(prompt)
            logger.debug(f"Raw intent model response: {response}")
            
            # Extract the response and normalize
            intent = response.content.strip().upper()
            logger.debug(f"Extracted intent: '{intent}'")
            
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
            logger.error(traceback.format_exc())
            # Default to COURSE in case of errors
            return "COURSE"
    
    @staticmethod
    def generate_acknowledgment(query: str) -> str:
        """
        Generate a contextual acknowledgment message based on the query.
        """
        logger.debug(f"Generating acknowledgment for query: '{query}'")
        
        prompt = f"""
        The student asked: "{query}"
        
        What kind of information is the student looking for? Choose ONE of:
        1. COURSE_RECOMMENDATION: Seeking course suggestions
        2. PREREQUISITE_CHECK: Asking about prerequisites
        3. SCHEDULE_PLANNING: Concerned about scheduling
        4. DEGREE_PROGRESS: Asking about graduation requirements
        5. COURSE_DETAILS: Asking about specific course information
        6. PROGRAM_REQUIREMENTS: Asking about program-specific courses or requirements
        
        Respond with only the category name.
        """
        
        try:
            logger.debug("Calling intent_model for detailed intent classification")
            response = intent_model.invoke(prompt)
            detailed_intent = response.content.strip().upper()
            logger.debug(f"Detailed intent classification: '{detailed_intent}'")
        except Exception as e:
            logger.error(f"Error in detailed intent classification: {e}")
            logger.error(traceback.format_exc())
            detailed_intent = "COURSE_RECOMMENDATION"  # Default if classification fails
            logger.debug(f"Using default intent: {detailed_intent}")
        
        # Generate acknowledgment based on intent
        acknowledgment = ""
        if "PREREQUISITE" in detailed_intent:
            acknowledgment = "Checking prerequisites and course sequences for you... 📋"
        elif "SCHEDULE" in detailed_intent:
            acknowledgment = "Analyzing your schedule to find compatible courses... ⏰"
        elif "DEGREE" in detailed_intent or "PROGRESS" in detailed_intent:
            acknowledgment = "Reviewing your degree requirements and progress... 🎓"
        elif "DETAILS" in detailed_intent:
            acknowledgment = "Looking up those course details for you... 📚"
        elif "PROGRAM" in detailed_intent:
            acknowledgment = "Checking your program requirements and progress... 📝"
        else:
            acknowledgment = "On it! Searching for course recommendations that match your academic plan... 🔍"
        
        logger.debug(f"Generated acknowledgment: '{acknowledgment}'")
        return acknowledgment
    
    @staticmethod
    def process_general_query(query: str) -> str:
        """
        Process general conversation queries with a friendly response.
        
        Args:
            query: The student's general query
            
        Returns:
            A friendly response
        """
        logger.debug(f"Processing general query: '{query}'")
        
        prompt = f"""
        You are a friendly academic advisor chatbot. The student has asked a general question (not specifically about courses).
        Respond in a friendly, helpful way. Keep your response concise and natural.
        
        If appropriate, suggest that they can ask about their program requirements or what courses to take next.
        
        Student query: {query}
        """
        
        try:
            logger.debug("Calling response_model for general query")
            response = response_model.invoke(prompt)
            logger.debug(f"Raw response model output: {response}")
            
            result = response.content.strip()
            logger.debug(f"Processed general response: '{result[:100]}...'")
            return result
        except Exception as e:
            logger.error(f"Error processing general query: {e}")
            logger.error(traceback.format_exc())
            return "I'm sorry, I'm having trouble understanding your question. Could you try asking in a different way?"
    
    @staticmethod
    async def get_course_recommendations(db: Session, user_id: int, query: str = None) -> Dict[str, Any]:
        """
        Get course recommendations for a user based on their query and academic history.
        
        Args:
            db: Database session
            user_id: User ID
            query: Optional query string, defaults to "What courses should I take next term?"
            
        Returns:
            Dictionary with recommendation message and course data
        """
        logger.debug(f"Getting course recommendations for user {user_id}, query: '{query}'")
        
        # Set default query if none provided
        if not query:
            query = "What courses should I take next term?"
            logger.debug(f"Using default query: '{query}'")
        
        try:
            # Get user's academic progress information
            logger.debug(f"Getting academic progress for user {user_id}")
            user_progress = program_service.format_user_progress(db, user_id)
            logger.debug(f"Retrieved user progress: {len(user_progress.split(newline))} lines")
            logger.debug(f"Progress preview: {user_progress[:200]}...")
            
            # Search for available courses
            logger.debug(f"Searching for courses related to query: '{query}'")
            available_courses = await course_service.search_courses_in_vector_db(query, limit=10)
            logger.debug(f"Found {len(available_courses)} available courses")
            class_codes = [c.get('class_code', 'Unknown') for c in available_courses]
            logger.debug(f"Available course codes: {class_codes}")
            
            # Format available courses for the recommendation prompt
            logger.debug("Formatting courses for recommendation prompt")
            formatted_courses = []
            for i, course in enumerate(available_courses):
                course_info = f"""
                Course {i+1}: {course.get('class_code', 'Unknown')}
                Name: {course.get('course_name', '')}
                Description: {course.get('description', '')[:100]}...
                Prerequisites: {course.get('prerequisites', '')}
                Credit Hours: {course.get('credit_hours', '')}
                """
                formatted_courses.append(course_info)
            
            courses_text = "\n\n".join(formatted_courses)
            logger.debug(f"Formatted {len(formatted_courses)} courses for prompt")
            
            # Generate course recommendations
            recommendation_prompt = COURSE_RECOMMENDATION_PROMPT.format(
                query=query,
                user_progress=user_progress,
                available_courses=courses_text
            )
            
            logger.debug("Calling recommendation_model for course recommendations")
            recommendation_response = recommendation_model.invoke(recommendation_prompt)
            recommendation_text = recommendation_response.content
            logger.debug(f"Recommendation response length: {len(recommendation_text)} chars")
            logger.debug(f"Raw recommendation text preview: {recommendation_text[:200]}...")
            
            # Parse recommended courses
            logger.debug("Parsing recommended courses from response")
            recommended_courses = []
            recommendation_section = ""
            
            if "RECOMMENDED COURSES:" in recommendation_text:
                recommendation_section = recommendation_text.split("RECOMMENDED COURSES:")[1].strip()
                logger.debug(f"Found recommendation section: {len(recommendation_section)} chars")
                
                for line in recommendation_section.split(newline):
                    line = line.strip()
                    if line.startswith('-') or line.startswith('*'):
                        logger.debug(f"Parsing recommendation line: '{line}'")
                        parts = line[1:].strip().split(':', 1)
                        if len(parts) == 2:
                            class_code = parts[0].strip()
                            details = parts[1].strip()
                            logger.debug(f"Extracted class_code: '{class_code}', details: '{details}'")
                            
                            # Split reason and priority
                            if '|' in details:
                                reason, priority = details.split('|', 1)
                                reason = reason.strip()
                                priority = priority.strip()
                                logger.debug(f"Extracted reason: '{reason}', priority: '{priority}'")
                            else:
                                reason = details
                                priority = "Medium"
                                logger.debug(f"No priority found, using default. Reason: '{reason}'")
                            
                            # Find the matching course in our enriched courses
                            found_match = False
                            for course in available_courses:
                                if course.get('class_code') and class_code in course.get('class_code'):
                                    logger.debug(f"Found matching course for '{class_code}'")
                                    course_copy = course.copy()
                                    course_copy['recommendation'] = {
                                        'is_recommended': True,
                                        'reason': reason,
                                        'priority': priority
                                    }
                                    recommended_courses.append(course_copy)
                                    found_match = True
                                    break
                            
                            if not found_match:
                                logger.warning(f"No matching course found for '{class_code}'")
            else:
                logger.warning("No 'RECOMMENDED COURSES:' section found in response")
            
            logger.debug(f"Parsed {len(recommended_courses)} recommended courses")
            
            # If we couldn't extract recommendations, use the first 3 courses
            if not recommended_courses and available_courses:
                logger.warning("No recommended courses parsed, using first 3 available courses")
                for i, course in enumerate(available_courses[:3]):
                    course_copy = course.copy()
                    course_copy['recommendation'] = {
                        'is_recommended': True,
                        'reason': "Suggested option for your next semester.",
                        'priority': "Medium"
                    }
                    recommended_courses.append(course_copy)
                logger.debug(f"Added {len(recommended_courses)} fallback course recommendations")
            
            # Generate friendly response
            logger.debug("Generating final response message")
            response_prompt = FINAL_RESPONSE_PROMPT.format(
                query=query,
                recommended_courses=recommendation_section
            )
            
            message_response = response_model.invoke(response_prompt)
            message = message_response.content.strip()
            logger.debug(f"Generated final message: '{message}'")
            
            # Return structured response
            result = {
                "type": "course_recommendations",
                "message": message,
                "course_data": recommended_courses
            }
            
            logger.info(f"Successfully generated recommendations for user {user_id} with {len(recommended_courses)} courses")
            return result
            
        except Exception as e:
            logger.error(f"Error in get_course_recommendations: {e}")
            logger.error(traceback.format_exc())
            
            # Return error response
            return {
                "type": "course_recommendations",
                "message": "I encountered an issue while finding courses for you. Please try again or rephrase your request. 🙇",
                "course_data": []
            }
    
    @staticmethod
    async def process_query(db: Session, user_id: int, query: str = None) -> Dict[str, Any]:
        """
        Main function to process a user query.
        
        Args:
            db: Database session
            user_id: User ID
            query: The query string
            
        Returns:
            Response data based on the query
        """
        logger.debug(f"Processing query for user {user_id}: '{query}'")
        
        # Set default query if none provided
        if not query:
            logger.debug("No query provided, using default")
            query = "What courses should I take next term?"
            logger.debug(f"Using default query: '{query}'")
            return await RecommendationService.get_course_recommendations(db, user_id, query)
        
        # Classify the intent
        logger.debug(f"Classifying intent for query: '{query}'")
        intent = RecommendationService.classify_intent(query)
        logger.info(f"Query intent for user {user_id}: {intent}")
        
        # Process based on intent
        if intent == "COURSE":
            logger.debug(f"Processing as COURSE intent for user {user_id}")
            return await RecommendationService.get_course_recommendations(db, user_id, query)
        else:
            logger.debug(f"Processing as GENERAL intent for user {user_id}")
            # For general conversation, return plain text
            general_response = RecommendationService.process_general_query(query)
            return {
                "type": "general_response",
                "message": general_response
            }

# Create a global instance of the service
logger.info("Creating global recommendation_service instance")
recommendation_service = RecommendationService()