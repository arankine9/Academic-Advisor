# Academic Advisor RAG Application

This application uses Retrieval-Augmented Generation (RAG) to provide personalized course recommendations for students based on their major and completed courses.

## Features

- User authentication system
- Course management (add/remove completed courses)
- Personalized course recommendations
- PostgreSQL database for persistent storage
- RAG-based recommendations using Pinecone and OpenAI

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL
- Pinecone account
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add the following variables:
```
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
DATABASE_URL=postgresql://username:password@localhost/academic_advisor
SECRET_KEY=your_secret_key_for_jwt_tokens
```

5. Initialize the database:
```bash
python init_db.py
```

6. Ingest major data into Pinecone:
```bash
python ingest_majors.py
```

### Running the Application

Start the FastAPI server:
```bash
python main.py
```

The application will be available at http://localhost:8000

## Usage

1. Register a new account with your email, username, password, and major
2. Login with your credentials
3. Add your completed courses
4. Get personalized course recommendations

## Architecture

- **FastAPI**: Web framework for the API
- **SQLAlchemy**: ORM for database interactions
- **PostgreSQL**: Database for user and course data
- **Pinecone**: Vector database for RAG
- **OpenAI**: LLM for generating recommendations
- **JWT**: Authentication mechanism

## Database Schema

- **users**: Stores user information (id, email, username, hashed_password, major)
- **courses**: Stores course information (id, course_code, course_name, credit_hours, term)
- **user_courses**: Junction table for the many-to-many relationship between users and courses 