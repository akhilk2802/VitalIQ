"""
Chat API Router for RAG-powered health conversations.

Provides:
- Session management endpoints
- Message sending (sync and streaming)
- Quick insights
"""

from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.chat_service import ChatService
from app.utils.security import get_current_user
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionWithMessages,
    ChatMessageCreate,
    ChatMessageResponse,
    QuickInsightRequest,
    QuickInsightResponse
)


router = APIRouter(prefix="/chat", tags=["chat"])


# ==================== Session Endpoints ====================

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    session_data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new chat session.
    
    A session groups related messages together for conversation context.
    """
    chat_service = ChatService(db)
    session = await chat_service.create_session(
        user_id=current_user.id,
        title=session_data.title
    )
    await db.commit()
    
    return ChatSessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def get_chat_sessions(
    active_only: bool = True,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all chat sessions for the current user.
    
    Sessions are ordered by most recent activity.
    """
    chat_service = ChatService(db)
    sessions = await chat_service.get_sessions(
        user_id=current_user.id,
        active_only=active_only,
        limit=limit
    )
    
    return [
        ChatSessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            is_active=s.is_active,
            created_at=s.created_at,
            updated_at=s.updated_at,
            message_count=len(s.messages) if hasattr(s, 'messages') else None
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific chat session with its messages.
    """
    chat_service = ChatService(db)
    
    session = await chat_service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    messages = await chat_service.get_messages(session_id)
    
    return ChatSessionWithMessages(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        is_active=session.is_active,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(messages),
        messages=[
            ChatMessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role.value,
                content=m.content,
                context_used=m.context_used,
                tokens_used=m.tokens_used,
                created_at=m.created_at
            )
            for m in messages
        ]
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete (archive) a chat session.
    
    The session is marked as inactive but not permanently deleted.
    """
    chat_service = ChatService(db)
    
    success = await chat_service.delete_session(session_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    await db.commit()


# ==================== Message Endpoints ====================

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(
    session_id: UUID,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get messages for a chat session.
    """
    chat_service = ChatService(db)
    
    # Verify session belongs to user
    session = await chat_service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    messages = await chat_service.get_messages(session_id, limit=limit)
    
    return [
        ChatMessageResponse(
            id=m.id,
            session_id=m.session_id,
            role=m.role.value,
            content=m.content,
            context_used=m.context_used,
            tokens_used=m.tokens_used,
            created_at=m.created_at
        )
        for m in messages
    ]


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: UUID,
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message and get an AI response.
    
    This is the synchronous endpoint that returns the complete response.
    For streaming responses, use the WebSocket endpoint.
    """
    chat_service = ChatService(db)
    
    # Verify session belongs to user
    session = await chat_service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    if not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat session is no longer active"
        )
    
    # Generate response
    response_text = await chat_service.generate_response_sync(
        user_id=current_user.id,
        session_id=session_id,
        user_message=message.content
    )
    
    await db.commit()
    
    # Get the saved messages (user message + assistant response)
    messages = await chat_service.get_messages(session_id, limit=2)
    
    # Return the assistant's response
    assistant_msg = messages[-1] if messages else None
    if not assistant_msg:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save response"
        )
    
    return ChatMessageResponse(
        id=assistant_msg.id,
        session_id=assistant_msg.session_id,
        role=assistant_msg.role.value,
        content=assistant_msg.content,
        context_used=assistant_msg.context_used,
        tokens_used=assistant_msg.tokens_used,
        created_at=assistant_msg.created_at
    )


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: UUID,
    message: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Send a message and get a streaming AI response.
    
    Returns Server-Sent Events (SSE) with response chunks.
    """
    chat_service = ChatService(db)
    
    # Verify session belongs to user
    session = await chat_service.get_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    if not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat session is no longer active"
        )
    
    async def generate():
        """Generator for SSE streaming."""
        try:
            async for chunk in chat_service.generate_response(
                user_id=current_user.id,
                session_id=session_id,
                user_message=message.content
            ):
                yield f"data: {chunk}\n\n"
            
            await db.commit()
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# ==================== Quick Insights ====================

@router.post("/quick-insight", response_model=QuickInsightResponse)
async def get_quick_insight(
    request: QuickInsightRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a quick health insight without creating a persistent session.
    
    Types:
    - summary: Quick summary of health patterns
    - tips: Actionable health tip
    - anomalies: Recent unusual readings
    """
    valid_types = {"summary", "tips", "anomalies"}
    if request.insight_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid insight type. Must be one of: {valid_types}"
        )
    
    chat_service = ChatService(db)
    
    insight = await chat_service.generate_quick_insight(
        user_id=current_user.id,
        insight_type=request.insight_type
    )
    
    await db.commit()
    
    return QuickInsightResponse(
        insight=insight,
        insight_type=request.insight_type,
        generated_at=datetime.utcnow()
    )
