# Copy from original query_engine.py with these import changes:
import os
from langchain_pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from pinecone import Pinecone as PineconeClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define Pinecone index name
index_name = "academic-advisor"

# Initialize Pinecone client
pc = PineconeClient(api_key=PINECONE_API_KEY)

# Ensure index exists
if index_name not in pc.list_indexes().names():
    raise ValueError(f"Pinecone index '{index_name}' does not exist. Run `ingest_majors.py` first to create it.")

# Initialize OpenAI embeddings
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Initialize Pinecone vector store with proper text key
vectorstore = Pinecone.from_existing_index(
    index_name=index_name,
    embedding=embeddings,
    text_key="text"  # Specify the text key to match our document structure
)

# Create a retriever with search parameters
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5}  # Retrieve top 5 most relevant documents
)

# Define an improved prompt template
template = """
You are an academic advisor helping a student plan their course schedule.

The student has completed the following courses:
{completed_courses}

They are majoring in {major}.

Based on the major requirements and the courses they've already taken, recommend what courses they should take next term. 
Consider prerequisites, course sequences, and graduation requirements.

Provide a clear explanation for your recommendations, including how they fit into the student's degree plan.
"""

prompt = PromptTemplate(input_variables=["completed_courses", "major"], template=template)

# Use ChatOpenAI with a more capable model
chat_llm = ChatOpenAI(
    model="gpt-4o",
    openai_api_key=OPENAI_API_KEY,
    temperature=0.2  # Lower temperature for more consistent advice
)

# Create the retrieval-based QA chain
chain = RetrievalQA.from_chain_type(
    llm=chat_llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={
        "prompt": PromptTemplate(
            template="""
            You are an academic advisor helping a student plan their course schedule.
            
            Use the following pieces of context to answer the question at the end.
            If you don't know the answer, just say that you don't know, don't try to make up an answer.
            
            {context}
            
            Question: {question}
            
            Helpful Answer:""",
            input_variables=["context", "question"],
        ),
    }
)

def get_advice(completed_courses, major):
    # Format the completed courses as a readable list
    if isinstance(completed_courses, list):
        formatted_courses = "\n".join([f"- {course}" for course in completed_courses])
    else:
        formatted_courses = completed_courses
    
    # Create the query
    formatted_prompt = prompt.format(completed_courses=formatted_courses, major=major)
    
    try:
        # Invoke the chain
        response = chain.invoke({"query": formatted_prompt})
        return response["result"]
    except Exception as e:
        print(f"Error in get_advice: {e}")
        return "I'm sorry, I encountered an error while generating recommendations. Please try again."

# Test the retrieval engine
if __name__ == "__main__":
    test_courses = ["CS 210 - Introduction to Computer Science I", "CS 211 - Introduction to Computer Science II"]
    test_major = "Computer Science"
    print(get_advice(test_courses, test_major))