# New recommendation_service.py
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import os
from langchain_openai import ChatOpenAI

from backend.services.unified_course_service import course_service
from backend.services.unified_program_service import program_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize LLM models with consistent naming
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

intent_model = ChatOpenAI(
    model="gpt-4o-mini",
    openai_api_key=OPENAI_API_KEY,
    temperature=0.2
)

recommendation_model = ChatOpenAI(
    model="o1-mini",
    openai_api_key=OPENAI_API_KEY,
    temperature=0.2
)

response_model = ChatOpenAI(
    model="gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    temperature=0.7
)

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
- [course_code_1]: [reason] | [priority]
- [course_code_2]: [reason] | [priority]
- [course_code_3]: [reason] | [priority]
- [course_code_4]: [reason] | [priority] (optional)
- [course_code_5]: [reason] | [priority] (optional)
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
        try:
            prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)
            response = intent_model.invoke(prompt)
            
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
    
    @staticmethod
    def generate_acknowledgment(query: str) -> str:
        """
        Generate a contextual acknowledgment message based on the query.
        """
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
            response = intent_model.invoke(prompt)
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
        elif "PROGRAM" in detailed_intent:
            return "Checking your program requirements and progress... 📝"
        else:
            return "On it! Searching for course recommendations that match your academic plan... 🔍"
    
    @staticmethod
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
        
        If appropriate, suggest that they can ask about their program requirements or what courses to take next.
        
        Student query: {query}
        """
        
        response = response_model.invoke(prompt)
        return response.content.strip()
    
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
        # Set default query if none provided
        if not query:
            query = "What courses should I take next term?"
        
        try:
            # Get user's academic progress information
            user_progress = program_service.format_user_progress(db, user_id)
            
            # Search for available courses
            available_courses = await course_service.search_courses_in_vector_db(query, limit=10)
            
            # Format available courses for the recommendation prompt
            formatted_courses = []
            for i, course in enumerate(available_courses):
                course_info = f"""
                Course {i+1}: {course.get('course_code', 'Unknown')}
                Name: {course.get('course_name', '')}
                Description: {course.get('description', '')[:100]}...
                Prerequisites: {course.get('prerequisites', '')}
                Credit Hours: {course.get('credit_hours', '')}
                """
                formatted_courses.append(course_info)
            
            courses_text = "\n\n".join(formatted_courses)
            
            # Generate course recommendations
            recommendation_prompt = COURSE_RECOMMENDATION_PROMPT.format(
                query=query,
                user_progress=user_progress,
                available_courses=courses_text
            )
            
            recommendation_response = recommendation_model.invoke(recommendation_prompt)
            recommendation_text = recommendation_response.content
            
            # Parse recommended courses
            recommended_courses = []
            recommendation_section = ""
            
            if "RECOMMENDED COURSES:" in recommendation_text:
                recommendation_section = recommendation_text.split("RECOMMENDED COURSES:")[1].strip()
                
                for line in recommendation_section.split('\n'):
                    line = line.strip()
                    if line.startswith('-') or line.startswith('*'):
                        parts = line[1:].strip().split(':', 1)
                        if len(parts) == 2:
                            course_code = parts[0].strip()
                            details = parts[1].strip()
                            
                            # Split reason and priority
                            if '|' in details:
                                reason, priority = details.split('|', 1)
                                reason = reason.strip()
                                priority = priority.strip()
                            else:
                                reason = details
                                priority = "Medium"
                            
                            # Find the matching course in our enriched courses
                            for course in available_courses:
                                if course.get('course_code') and course_code in course.get('course_code'):
                                    course_copy = course.copy()
                                    course_copy['recommendation'] = {
                                        'is_recommended': True,
                                        'reason': reason,
                                        'priority': priority
                                    }
                                    recommended_courses.append(course_copy)
                                    break
            
            # If we couldn't extract recommendations, use the first 3 courses
            if not recommended_courses and available_courses:
                for i, course in enumerate(available_courses[:3]):
                    course_copy = course.copy()
                    course_copy['recommendation'] = {
                        'is_recommended': True,
                        'reason': "Suggested option for your next semester.",
                        'priority': "Medium"
                    }
                    recommended_courses.append(course_copy)
            
            # Generate friendly response
            response_prompt = FINAL_RESPONSE_PROMPT.format(
                query=query,
                recommended_courses=recommendation_section
            )
            
            message_response = response_model.invoke(response_prompt)
            message = message_response.content.strip()
            
            # Return structured response
            return {
                "type": "course_recommendations",
                "message": message,
                "course_data": recommended_courses
            }
            
        except Exception as e:
            logger.error(f"Error in get_course_recommendations: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
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
        # Set default query if none provided
        if not query:
            query = "What courses should I take next term?"
            return await RecommendationService.get_course_recommendations(db, user_id, query)
        
        # Classify the intent
        intent = RecommendationService.classify_intent(query)
        
        # Process based on intent
        if intent == "COURSE":
            return await RecommendationService.get_course_recommendations(db, user_id, query)
        else:
            # For general conversation, return plain text
            return {
                "type": "general_response",
                "message": RecommendationService.process_general_query(query)
            }

# Create a global instance of the service
recommendation_service = RecommendationService()