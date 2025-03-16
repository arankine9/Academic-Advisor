"""
Enhanced Query Engine for Academic Advisor
Implements intent classification, multi-step reasoning, and RAG-based query refinement.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from langchain_pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import Document
from pinecone import Pinecone as PineconeClient
from dotenv import load_dotenv

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
#INDEX_NAME = "academic-advisor"
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
    #metadata_key="metadata"
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

# Intent Classification Prompt
INTENT_CLASSIFICATION_PROMPT = """
You are an academic advising system assistant. Determine if the student's query is:
1. Course-related: About what courses to take, prerequisites, degree requirements, etc.
2. General conversation: Greetings, personal questions, or topics not directly related to course selection.

Student query: {query}

Respond with exactly "COURSE" if the query is course-related, or "GENERAL" for general conversation.
"""

# Reasoning Prompt
REASONING_PROMPT = """
You are an academic advisor helping a student plan their academic journey. Think step by step to answer their question effectively.

{user_data}

Student query: {query}

Your task:
1. Analyze what specific information you need to properly answer this query
2. Determine what specific searches would retrieve the most relevant information
3. Formulate up to 3 specific, focused search queries that would help answer the student's question

For each search query, explain why you're searching for this information and how it relates to the student's question.

Format your reasoning as:
ANALYSIS: [Your analysis of the student's needs]

SEARCH QUERIES:
1. [First specific search query]
2. [Second specific search query, if needed]
3. [Third specific search query, if needed]

REASONING: [Brief explanation of your search strategy]
"""

# Final Response Prompt
FINAL_RESPONSE_PROMPT = """
You are a friendly, helpful academic advisor. Based on the student's data and retrieved information, provide a personalized response.

{user_data}

Student query: {query}

Retrieved information:
{retrieved_info}

Respond directly to the student in a warm, supportive tone. Focus on giving clear advice and actionable recommendations. 
Do not mention the search process or "retrieved information" - 
just provide the advice naturally as if you already knew this information.
mention things like:
- Course descriptions and prerequisites
- Current availability and scheduling
- How courses fit into degree requirements

Include specific course recommendations when appropriate, explaining how they fit into the student's academic path.
Provide practical advice that considers both academic requirements and logistical factors like class timing and seat availability.
Focus on helping the student make progress on their degree requirements by taking courses that:
1. They haven't yet completed
2. They have prerequisites for
3. Are required for their major/minor
4. Are offered in the current/upcoming term

The current term is Winter 2025.
"""

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
        response = intent_classifier.invoke(prompt)
        
        # Extract the response and normalize
        intent = response.content.strip().upper()
        
        # Handle edge cases
        if "COURSE" in intent:
            return "COURSE"
        else:
            return "GENERAL"
    except Exception as e:
        logger.error(f"Error in intent classification: {e}")
        # Default to COURSE in case of errors
        return "COURSE"

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
        
        # Parse numbered queries
        lines = search_section.split("\n")
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() and line[1:3] in [". ", ") "]):
                query = line[line.index(" ")+1:].strip()
                if query:
                    queries.append(query)
    
    # If no queries found with the structured format, try to extract any lines that look like queries
    if not queries:
        lines = reasoning_output.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("Query:") or line.startswith("Search for:"):
                query = line.split(":", 1)[1].strip()
                queries.append(query)
    
    # Fallback: if still no queries, use parts of the reasoning text
    if not queries and len(reasoning_output) > 30:
        # Just use the first paragraph as a query
        first_para = reasoning_output[:200].replace("\n", " ")
        queries.append(first_para)
    
    return queries[:3]  # Limit to 3 queries

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
        # Add debug logging
        logger.info(f"Retrieved document metadata example: {docs[0].metadata if docs else 'No documents found'}")
        
        # Format each document to include all available fields
        for doc in docs:
            # All fields are available directly in doc.metadata
            formatted_content = f"""
            Course: {doc.metadata.get('class_code')}
            Credits: {doc.metadata.get('credits')}
            Description: {doc.metadata.get('description')}
            Prerequisites: {doc.metadata.get('prerequisites')}
            Instructor: {doc.metadata.get('instructor')}
            Schedule: {doc.metadata.get('days')} at {doc.metadata.get('time')}
            Location: {doc.metadata.get('classroom')}
            Seats Available: {doc.metadata.get('available_seats')}/{doc.metadata.get('total_seats')}
            CRN: {doc.metadata.get('crn')}
            """
            doc.page_content = formatted_content.strip()
        return docs
    except Exception as e:
        logger.error(f"Error in RAG query execution: {e}")
        return []

def process_course_query(query: str, user_data: str) -> str:
    """
    Process course-related queries using multi-step reasoning and RAG.
    
    Args:
        query: The student's query
        user_data: Formatted string with user's academic information
        
    Returns:
        A formatted response with course recommendations
    """
    # Step 1: Generate reasoning about how to approach the query
    reasoning_prompt = REASONING_PROMPT.format(
        query=query,
        user_data=user_data
    )
    
    reasoning_response = reasoning_model.invoke(reasoning_prompt)
    reasoning_output = reasoning_response.content.strip()
    logger.info(f"Reasoning output: {reasoning_output[:100]}...")
    
    # Step 2: Extract search queries from reasoning
    search_queries = extract_search_queries(reasoning_output)
    
    if not search_queries:
        # Fallback: use the original query
        search_queries = [query]
    
    logger.info(f"Search queries: {search_queries}")
    
    # Step 3: Execute RAG queries and collect results
    all_results = []
    for search_query in search_queries:
        retrieved_docs = execute_rag_query(search_query)
        all_results.extend(retrieved_docs)
    
    # Deduplicate results
    seen_content = set()
    unique_results = []
    for doc in all_results:
        if doc.page_content not in seen_content:
            seen_content.add(doc.page_content)
            unique_results.append(doc)
    
    # Format retrieved information
    retrieved_info = "\n\n".join([doc.page_content for doc in unique_results[:5]])
    
    # If no information was retrieved, provide a graceful fallback
    if not retrieved_info:
        retrieved_info = "No specific course information found. Provide general guidance based on the student's major and completed courses."
    
    # Step 4: Generate final response
    response_prompt = FINAL_RESPONSE_PROMPT.format(
        query=query,
        user_data=user_data,
        retrieved_info=retrieved_info
    )
    
    final_response = response_model.invoke(response_prompt)
    return final_response.content.strip()

def get_advice(db, user_id: int, query=None):
    """
    Main function that orchestrates the entire query processing pipeline.
    
    Args:
        db: Database session
        user_id: The user's ID
        query: The student's query (optional)
        
    Returns:
        A formatted response
    """
    try:
        # Format user data for RAG
        user_data = format_courses_for_rag(db, user_id)
        
        # If no query is provided, use a default recommendation prompt
        if not query:
            default_query = "What courses should I take next term?"
            return process_course_query(default_query, user_data)
        
        # Classify the intent of the query
        intent = classify_intent(query)
        logger.info(f"Classified intent: {intent}")
        
        # Process based on intent
        if intent == "COURSE":
            return process_course_query(query, user_data)
        else:
            return process_general_query(query)
            
    except Exception as e:
        logger.error(f"Error in get_advice: {e}")
        return "I'm sorry, I encountered an error while generating recommendations. Please try again later or try rephrasing your question."

# Test the retrieval engine (only runs when script is executed directly)
if __name__ == "__main__":
    # This is just for testing without a database connection
    # In a real application, you'd pass a database session
    from sqlalchemy.orm import Session
    from backend.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Replace with a real user ID for testing
        test_user_id = 1
        test_query = "What math courses should I take next?"
        print(get_advice(db, test_user_id, test_query))
    finally:
        db.close()