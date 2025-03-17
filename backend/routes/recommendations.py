from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.auth import get_current_user
from backend.models.schemas import UserResponse
from backend.services.query_engine import get_advice

router = APIRouter(
    prefix="/recommendations",
    tags=["recommendations"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=dict)
def get_course_recommendations(
    query: Optional[str] = Query(None, description="The user's query for course recommendations"),
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get course recommendations based on the user's completed courses and degree requirements.
    
    If no query is provided, a default query will be used: "What courses should I take next term?"
    """
    try:
        # Use the RAG system to get recommendations
        recommendation = get_advice(db, current_user.id, query)
        return {"recommendation": recommendation}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting recommendations: {str(e)}",
        ) 