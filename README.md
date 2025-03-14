# Academic Advisor RAG Application

This application uses Retrieval-Augmented Generation (RAG) to provide personalized course recommendations for students based on their major and completed courses.

## Features

- User authentication system
- Course management (add/remove completed courses)
- Personalized course recommendations
- PostgreSQL database for persistent storage
- RAG-based recommendations using Pinecone and OpenAI
- React-based modern frontend

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL
- Pinecone account
- OpenAI API key
- Node.js and npm (installed automatically if missing)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip3 install -r requirements.txt
```

4. Set up environment variables:
   - Create a `.env` file in the root directory
   - Add the following variables:
```
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
DATABASE_URL=postgresql://username:password@localhost/academic_advisor
SECRET_KEY=your_secret_key_for_jwt_tokens
DEVELOPMENT_MODE=true  # Set to true during development, false in production
```

5. Initialize the database:
```bash
python3 init_db.py
```

6. Ingest major data into Pinecone:
```bash
python3 ingest_majors.py
```

### Running the Application

Start the FastAPI server:
```bash
python3 main.py
```

The application will handle both frontend and backend setup automatically:
- In development mode (`DEVELOPMENT_MODE=true`), it will set up React and start the development server
- In production mode (`DEVELOPMENT_MODE=false`), it will build the React app and serve it directly

The application will be available at:
- Development: http://localhost:5173 (React dev server) with API at http://localhost:8000
- Production: http://localhost:8000 (Both frontend and API)

## Development

### Backend Development
The backend is built with FastAPI and follows a modular structure:
- `backend/api/routes.py`: API routes and endpoints
- `backend/core/`: Core functionality (auth, database)
- `backend/services/`: Business logic and services
- `backend/models/`: Database models and schemas

### Frontend Development
The frontend is built with React and follows a modern component structure:
- `/frontend/src/components/`: Reusable UI components
- `/frontend/src/pages/`: Page components
- `/frontend/src/services/`: API service modules
- `/frontend/src/context/`: React context providers

To run the frontend separately during development:
```bash
cd frontend
npm run dev
```

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
- **React**: Frontend framework
- **Axios**: HTTP client for API requests
- **React Router**: Frontend routing

## Database Schema

- **users**: Stores user information (id, email, username, hashed_password, major)
- **courses**: Stores course information (id, course_code, course_name, credit_hours, term)
- **user_courses**: Junction table for the many-to-many relationship between users and courses