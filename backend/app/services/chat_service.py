"""
Chat Service for RAG-powered health conversations.

Provides:
- Session management
- RAG-augmented response generation
- Streaming support
"""

import uuid
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from openai import AsyncOpenAI

from app.models.chat import ChatSession, ChatMessage
from app.models.user import User
from app.rag.health_knowledge_rag import HealthKnowledgeRAG
from app.rag.user_history_rag import UserHistoryRAG
from app.rag.prompt_builder import RAGPromptBuilder
from app.ml.feature_engineering import FeatureEngineer
from app.utils.enums import MessageRole
from app.config import settings


class ChatService:
    """Service for RAG-powered health conversations."""
    
    MODEL = "gpt-4-turbo-preview"
    MAX_TOKENS = 300  # Keep responses concise
    TEMPERATURE = 0.7
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.health_rag = HealthKnowledgeRAG(db)
        self.user_history_rag = UserHistoryRAG(db)
        self.prompt_builder = RAGPromptBuilder()
    
    # ==================== Session Management ====================
    
    async def create_session(
        self, 
        user_id: uuid.UUID, 
        title: Optional[str] = None
    ) -> ChatSession:
        """
        Create a new chat session.
        
        Args:
            user_id: User ID
            title: Optional session title
            
        Returns:
            Created ChatSession
        """
        session = ChatSession(
            user_id=user_id,
            title=title,
            is_active=True
        )
        
        self.db.add(session)
        await self.db.flush()
        
        return session
    
    async def get_sessions(
        self, 
        user_id: uuid.UUID,
        active_only: bool = True,
        limit: int = 50
    ) -> List[ChatSession]:
        """Get chat sessions for a user."""
        query = select(ChatSession).where(ChatSession.user_id == user_id)
        
        if active_only:
            query = query.where(ChatSession.is_active == True)
        
        query = query.order_by(ChatSession.updated_at.desc()).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_session(
        self, 
        session_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[ChatSession]:
        """Get a specific session."""
        result = await self.db.execute(
            select(ChatSession).where(
                and_(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_messages(
        self, 
        session_id: uuid.UUID,
        limit: int = 100,
        before_id: Optional[uuid.UUID] = None
    ) -> tuple[List[ChatMessage], bool]:
        """
        Get messages for a session with cursor-based pagination.
        
        Args:
            session_id: Session ID
            limit: Max messages to return
            before_id: Get messages before this message ID (for infinite scroll)
            
        Returns:
            Tuple of (messages in chronological order, has_more flag)
        """
        query = select(ChatMessage).where(ChatMessage.session_id == session_id)
        
        if before_id:
            # Get the message to use as cursor
            cursor_result = await self.db.execute(
                select(ChatMessage).where(ChatMessage.id == before_id)
            )
            cursor_msg = cursor_result.scalar_one_or_none()
            
            if cursor_msg:
                # Get messages older than cursor
                query = query.where(ChatMessage.created_at < cursor_msg.created_at)
        
        # Order by created_at DESC to get most recent first, then reverse
        query = query.order_by(ChatMessage.created_at.desc()).limit(limit + 1)
        
        result = await self.db.execute(query)
        messages = list(result.scalars().all())
        
        # Check if there are more messages
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]
        
        # Reverse to chronological order
        messages.reverse()
        
        return messages, has_more
    
    async def get_messages_simple(
        self, 
        session_id: uuid.UUID,
        limit: int = 100
    ) -> List[ChatMessage]:
        """Get messages for a session (simple, no pagination)."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        return result.scalars().all()
    
    async def update_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        title: Optional[str] = None
    ) -> Optional[ChatSession]:
        """Update a session's properties."""
        session = await self.get_session(session_id, user_id)
        if session:
            if title is not None:
                session.title = title
            session.updated_at = datetime.utcnow()
            await self.db.flush()
            return session
        return None

    async def delete_session(
        self, 
        session_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> bool:
        """Mark a session as inactive."""
        session = await self.get_session(session_id, user_id)
        if session:
            session.is_active = False
            await self.db.flush()
            return True
        return False
    
    # ==================== Response Generation ====================
    
    async def generate_response(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        user_message: str
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming RAG-augmented response.
        
        Args:
            user_id: User ID
            session_id: Chat session ID
            user_message: User's message
            
        Yields:
            Response chunks as they're generated
        """
        if not self.client:
            yield "I'm sorry, but the AI service is not configured. Please check your API settings."
            return
        
        # Save user message
        user_msg = await self._save_message(
            session_id=session_id,
            role=MessageRole.user,
            content=user_message
        )
        
        # Gather RAG context
        context = await self._gather_context(user_id, user_message)
        
        # Get conversation history
        messages = await self.get_messages_simple(session_id, limit=20)
        # Exclude the message we just added
        history = [m for m in messages if m.id != user_msg.id]
        
        # Build prompt
        prompt_messages = self.prompt_builder.build_chat_prompt(
            user_message=user_message,
            health_context=context.get("health_knowledge"),
            user_history_context=context.get("user_history"),
            recent_metrics=context.get("recent_metrics"),
            conversation_history=history[-10:] if history else None  # Last 10 messages
        )
        
        # Generate streaming response
        full_response = ""
        tokens_used = 0
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=prompt_messages,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
                
                if chunk.usage:
                    tokens_used = chunk.usage.total_tokens
        
        except Exception as e:
            error_msg = f"I encountered an error generating a response: {str(e)}"
            yield error_msg
            full_response = error_msg
        
        # Save assistant response
        await self._save_message(
            session_id=session_id,
            role=MessageRole.assistant,
            content=full_response,
            context_used=context,
            tokens_used=tokens_used
        )
        
        # Update session
        await self._update_session(session_id, user_message)
        
        # Index messages for future retrieval
        await self._index_messages(user_id, user_msg.id, user_message, "user")
    
    async def generate_response_sync(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        user_message: str
    ) -> str:
        """
        Generate a non-streaming response (for REST API).
        
        Args:
            user_id: User ID
            session_id: Chat session ID
            user_message: User's message
            
        Returns:
            Complete response string
        """
        if not self.client:
            return "I'm sorry, but the AI service is not configured. Please check your API settings."
        
        # Save user message
        user_msg = await self._save_message(
            session_id=session_id,
            role=MessageRole.user,
            content=user_message
        )
        
        # Gather RAG context
        context = await self._gather_context(user_id, user_message)
        
        # Get conversation history
        messages = await self.get_messages_simple(session_id, limit=20)
        history = [m for m in messages if m.id != user_msg.id]
        
        # Build prompt
        prompt_messages = self.prompt_builder.build_chat_prompt(
            user_message=user_message,
            health_context=context.get("health_knowledge"),
            user_history_context=context.get("user_history"),
            recent_metrics=context.get("recent_metrics"),
            conversation_history=history[-10:] if history else None
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=prompt_messages,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE
            )
            
            assistant_response = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
        except Exception as e:
            assistant_response = f"I encountered an error generating a response: {str(e)}"
            tokens_used = 0
        
        # Save assistant response
        await self._save_message(
            session_id=session_id,
            role=MessageRole.assistant,
            content=assistant_response,
            context_used=context,
            tokens_used=tokens_used
        )
        
        # Update session
        await self._update_session(session_id, user_message)
        
        # Index messages for future retrieval
        await self._index_messages(user_id, user_msg.id, user_message, "user")
        
        return assistant_response
    
    # ==================== Context Gathering ====================
    
    async def _gather_context(
        self, 
        user_id: uuid.UUID, 
        user_message: str
    ) -> Dict[str, Any]:
        """
        Gather all RAG context for a message.
        
        Args:
            user_id: User ID
            user_message: User's message
            
        Returns:
            Dict with health_knowledge, user_history, recent_metrics
        """
        context = {}
        
        # Get recent metrics
        try:
            feature_eng = FeatureEngineer(self.db, user_id)
            df = await feature_eng.build_daily_feature_matrix(days=7)
            
            if not df.empty:
                # Get latest values
                latest = df.iloc[-1].to_dict()
                # Remove non-metric columns
                metrics = {k: v for k, v in latest.items() 
                          if k not in ['date'] and v is not None and str(v) != 'nan'}
                context["recent_metrics"] = metrics
                recent_metric_names = list(metrics.keys())
            else:
                recent_metric_names = []
        except Exception as e:
            print(f"Error getting recent metrics: {e}")
            await self.db.rollback()  # Rollback to clear aborted transaction state
            recent_metric_names = []
        
        # Retrieve health knowledge
        try:
            knowledge_chunks = await self.health_rag.retrieve_for_chat(
                user_message=user_message,
                recent_metrics=recent_metric_names,
                k=4
            )
            
            if knowledge_chunks:
                context["health_knowledge"] = self.health_rag.format_chunks_for_prompt(
                    knowledge_chunks, 
                    max_tokens=1500
                )
                # Store chunk sources for context_used
                context["health_sources"] = [
                    {"title": c.title, "source_type": c.source_type, "similarity": c.similarity}
                    for c in knowledge_chunks
                ]
        except Exception as e:
            print(f"Error retrieving health knowledge: {e}")
            await self.db.rollback()  # Rollback to clear aborted transaction state
        
        # Retrieve user history
        try:
            history_chunks = await self.user_history_rag.retrieve_relevant_history(
                user_id=user_id,
                query=user_message,
                k=3
            )
            
            if history_chunks:
                context["user_history"] = self.user_history_rag.format_history_for_prompt(
                    history_chunks,
                    max_tokens=1000
                )
                # Store for context_used
                context["history_refs"] = [
                    {"entity_type": c.entity_type, "similarity": c.similarity}
                    for c in history_chunks
                ]
        except Exception as e:
            print(f"Error retrieving user history: {e}")
            await self.db.rollback()  # Rollback to clear aborted transaction state
        
        return context
    
    # ==================== Helper Methods ====================
    
    async def _save_message(
        self,
        session_id: uuid.UUID,
        role: MessageRole,
        content: str,
        context_used: Optional[Dict[str, Any]] = None,
        tokens_used: Optional[int] = None
    ) -> ChatMessage:
        """Save a chat message."""
        # Simplify context for storage (remove actual content)
        stored_context = None
        if context_used:
            stored_context = {
                "health_sources": context_used.get("health_sources"),
                "history_refs": context_used.get("history_refs"),
                "had_recent_metrics": "recent_metrics" in context_used,
            }
        
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            context_used=stored_context,
            tokens_used=tokens_used
        )
        
        self.db.add(message)
        await self.db.flush()
        
        return message
    
    async def _update_session(
        self, 
        session_id: uuid.UUID, 
        user_message: str
    ):
        """Update session with auto-generated title if needed."""
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if session:
            # Update timestamp
            session.updated_at = datetime.utcnow()
            
            # Auto-generate title from first message if not set
            if not session.title:
                # Take first 50 chars of first message as title
                title = user_message[:50]
                if len(user_message) > 50:
                    title += "..."
                session.title = title
            
            await self.db.flush()
    
    async def _index_messages(
        self,
        user_id: uuid.UUID,
        message_id: uuid.UUID,
        content: str,
        role: str
    ):
        """Index messages for conversation memory."""
        try:
            await self.user_history_rag.index_chat_message(
                user_id=user_id,
                message_id=message_id,
                content=content,
                role=role
            )
        except Exception as e:
            # Don't fail chat if indexing fails
            print(f"Failed to index chat message: {e}")
    
    # ==================== Quick Actions ====================
    
    async def generate_quick_insight(
        self,
        user_id: uuid.UUID,
        insight_type: str = "summary"
    ) -> str:
        """
        Generate a quick health insight without creating a session.
        
        Args:
            user_id: User ID
            insight_type: Type of insight (summary, tips, anomalies)
            
        Returns:
            Generated insight text
        """
        prompts = {
            "summary": "Give me a quick summary of my health patterns from the past week.",
            "tips": "What's one actionable health tip based on my recent data?",
            "anomalies": "Were there any unusual readings in my recent health data?",
        }
        
        prompt = prompts.get(insight_type, prompts["summary"])
        
        # Create temporary session
        session = await self.create_session(user_id, title=f"Quick {insight_type}")
        
        # Generate response
        response = await self.generate_response_sync(
            user_id=user_id,
            session_id=session.id,
            user_message=prompt
        )
        
        # Mark session as inactive (it was just for this quick insight)
        session.is_active = False
        await self.db.flush()
        
        return response
