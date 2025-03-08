import pinecone
import os
from dotenv import load_dotenv

load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

pinecone.init(api_key=PINECONE_API_KEY, environment="us-west1-gcp")
index = pinecone.Index("academic-advisor")

# Check if the index exists, otherwise create it
if "academic-advisor" not in pinecone.list_indexes():
    pinecone.create_index("academic-advisor", dimension=1536, metric="cosine")