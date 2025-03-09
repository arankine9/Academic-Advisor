import os
from pinecone import Pinecone
from dotenv import load_dotenv
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Check if the index exists, otherwise create it
index_name = "academic-advisor"
existing_indexes = pc.list_indexes().names()

if index_name not in existing_indexes:
    pc.create_index(
        name=index_name, 
        dimension=1536, 
        metric="cosine"
    )
    print(f"Created index '{index_name}'")
else:
    print(f"Index '{index_name}' already exists")