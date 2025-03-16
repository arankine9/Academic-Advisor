

import os
import json
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Create Pinecone instance
pc = Pinecone(api_key=PINECONE_API_KEY)

# Define index name and check if it exists
index_name = "academic-advisor"
existing_indexes = pc.list_indexes().names()
if index_name in existing_indexes:
    # Delete existing index to recreate it with proper structure
    pc.delete_index(index_name)
    print(f"Deleted existing index '{index_name}' to recreate it with proper structure.")

# Create a new index
pc.create_index(
    name=index_name, 
    dimension=1536, 
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1")  # Update region and cloud if needed
)
print(f"Created new index '{index_name}'")

# Connect to the Pinecone index
index = pc.Index(index_name)

# IMPORTANT: Updated file path
json_path = os.path.join("data", "majors.json")

# Load the major requirements from JSON
with open(json_path, "r") as f:
    majors_data = json.load(f)

# Initialize the embedding model
embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# Process and store courses into Pinecone with proper document structure
document_id = 0
for major_name, major_info in majors_data.items():
    # Process each section of the major
    for section_name, section_data in major_info.items():
        if isinstance(section_data, dict):
            # Handle nested sections
            if "courses" in section_data:
                courses = section_data["courses"]
                for course in courses:
                    # Create document text with context
                    text = f"Course: {course}. This is part of the {section_name} section for {major_name} major. "
                    if "requirements" in section_data:
                        text += f"Requirements: {section_data['requirements']}. "
                    if "credits" in section_data:
                        text += f"Credits: {section_data['credits']}. "
                    
                    # Generate embedding
                    vector = embeddings.embed_query(text)
                    
                    # Store in Pinecone with proper metadata
                    index.upsert(
                        vectors=[
                            {
                                "id": f"doc_{document_id}",
                                "values": vector,
                                "metadata": {
                                    "text": text,
                                    "major": major_name,
                                    "section": section_name,
                                    "course": course
                                }
                            }
                        ]
                    )
                    document_id += 1
            
            # Handle course sequences if present
            if "course_sequences" in section_data:
                for sequence in section_data["course_sequences"]:
                    sequence_text = ", ".join(sequence)
                    text = f"Course Sequence: {sequence_text}. This is part of the {section_name} section for {major_name} major. "
                    if "requirements" in section_data:
                        text += f"Requirements: {section_data['requirements']}. "
                    if "credits" in section_data:
                        text += f"Credits: {section_data['credits']}. "
                    
                    vector = embeddings.embed_query(text)
                    index.upsert(
                        vectors=[
                            {
                                "id": f"doc_{document_id}",
                                "values": vector,
                                "metadata": {
                                    "text": text,
                                    "major": major_name,
                                    "section": section_name,
                                    "sequence": sequence_text
                                }
                            }
                        ]
                    )
                    document_id += 1
            
            # Handle options if present
            if "options" in section_data:
                for option in section_data["options"]:
                    option_text = ", ".join(option)
                    text = f"Course Option: {option_text}. This is part of the {section_name} section for {major_name} major. "
                    if "requirements" in section_data:
                        text += f"Requirements: {section_data['requirements']}. "
                    if "credits" in section_data:
                        text += f"Credits: {section_data['credits']}. "
                    
                    vector = embeddings.embed_query(text)
                    index.upsert(
                        vectors=[
                            {
                                "id": f"doc_{document_id}",
                                "values": vector,
                                "metadata": {
                                    "text": text,
                                    "major": major_name,
                                    "section": section_name,
                                    "option": option_text
                                }
                            }
                        ]
                    )
                    document_id += 1

print(f"Successfully ingested {document_id} documents into Pinecone index '{index_name}'")