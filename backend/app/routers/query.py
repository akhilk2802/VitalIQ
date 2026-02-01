"""
Natural Language Query API

Allows users to ask questions about their health data in natural language.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.database import get_db
from app.models.user import User
from app.utils.security import get_current_user
from app.services.nl_query_service import NLQueryService

router = APIRouter()


class QueryRequest(BaseModel):
    """Natural language query request"""
    query: str = Field(..., min_length=3, max_length=500, description="Your question")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What was my average sleep last week?"
            }
        }


class QueryResponse(BaseModel):
    """Natural language query response"""
    query: str
    intent: str
    answer: str
    data: Optional[Dict[str, Any]] = None
    confidence: float
    follow_up_suggestions: List[str] = Field(default_factory=list)


@router.post("", response_model=QueryResponse)
async def natural_language_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ask a question about your health data in natural language.
    
    Examples:
    - "What was my average sleep last week?"
    - "How many times did I exercise this month?"
    - "Why was my glucose high yesterday?"
    - "What should I eat today?"
    - "How does this week compare to last week for sleep?"
    - "Show me my heart rate trends"
    - "Any anomalies in my recent data?"
    """
    service = NLQueryService(db, current_user.id)
    result = await service.query(request.query)
    
    return QueryResponse(
        query=result.query,
        intent=result.intent.value,
        answer=result.answer,
        data=result.data,
        confidence=result.confidence,
        follow_up_suggestions=result.follow_up_suggestions or []
    )


@router.get("/suggestions")
async def get_query_suggestions(
    current_user: User = Depends(get_current_user)
):
    """Get suggested queries the user can ask"""
    return {
        "categories": [
            {
                "name": "Data Retrieval",
                "examples": [
                    "What was my average sleep last week?",
                    "Show me my exercise data for this month",
                    "How many calories did I eat yesterday?",
                    "What's my average resting heart rate?"
                ]
            },
            {
                "name": "Insights",
                "examples": [
                    "Why was my glucose high yesterday?",
                    "What anomalies have been detected recently?",
                    "What correlations exist in my data?",
                    "Why is my HRV lower than usual?"
                ]
            },
            {
                "name": "Recommendations",
                "examples": [
                    "What should I eat today?",
                    "Should I work out today?",
                    "Any health tips for me?",
                    "How can I improve my sleep?"
                ]
            },
            {
                "name": "Comparisons",
                "examples": [
                    "How does this week compare to last week?",
                    "Am I sleeping better than last month?",
                    "Is my exercise improving?",
                    "Compare my nutrition this month vs last"
                ]
            },
            {
                "name": "Predictions",
                "examples": [
                    "How recovered am I today?",
                    "Will I have sugar cravings today?",
                    "What's my recovery score?",
                    "What should I expect today?"
                ]
            }
        ]
    }
