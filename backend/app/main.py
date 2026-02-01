from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import json
from uuid import UUID

from app.config import settings
from app.database import init_db, AsyncSessionLocal
from app.routers import auth, nutrition, sleep, exercise, vitals, body, chronic, anomalies, dashboard, mock, correlations, integrations, briefing, query, export, chat
from app.services.scheduler import scheduler
from app.services.chat_service import ChatService
from app.utils.security import decode_token


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    await init_db()
    
    # Start background scheduler for periodic syncs (optional - disabled by default)
    # Uncomment to enable daily automatic syncs
    # if not settings.DEBUG:
    #     await scheduler.start()
    #     logger.info("Background sync scheduler started")
    
    yield
    
    # Shutdown
    if scheduler.is_running:
        await scheduler.stop()
        logger.info("Background sync scheduler stopped")


app = FastAPI(
    title=settings.APP_NAME,
    description="Personal Health & Wellness Aggregator - Unifying health data with AI-powered insights",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(nutrition.router, prefix=f"{settings.API_V1_PREFIX}/nutrition", tags=["Nutrition"])
app.include_router(sleep.router, prefix=f"{settings.API_V1_PREFIX}/sleep", tags=["Sleep"])
app.include_router(exercise.router, prefix=f"{settings.API_V1_PREFIX}/exercise", tags=["Exercise"])
app.include_router(vitals.router, prefix=f"{settings.API_V1_PREFIX}/vitals", tags=["Vitals"])
app.include_router(body.router, prefix=f"{settings.API_V1_PREFIX}/body", tags=["Body Metrics"])
app.include_router(chronic.router, prefix=f"{settings.API_V1_PREFIX}/chronic", tags=["Chronic Health"])
app.include_router(anomalies.router, prefix=f"{settings.API_V1_PREFIX}/anomalies", tags=["Anomalies"])
app.include_router(correlations.router, prefix=f"{settings.API_V1_PREFIX}/correlations", tags=["Correlations"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_PREFIX}/dashboard", tags=["Dashboard"])
app.include_router(mock.router, prefix=f"{settings.API_V1_PREFIX}/mock", tags=["Mock Data"])
app.include_router(integrations.router, prefix=f"{settings.API_V1_PREFIX}/integrations", tags=["Integrations"])
app.include_router(briefing.router, prefix=f"{settings.API_V1_PREFIX}/briefing", tags=["Morning Briefing"])
app.include_router(query.router, prefix=f"{settings.API_V1_PREFIX}/query", tags=["Natural Language Query"])
app.include_router(export.router, prefix=f"{settings.API_V1_PREFIX}/export", tags=["Data Export"])
app.include_router(chat.router, prefix=f"{settings.API_V1_PREFIX}", tags=["Chat"])


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# ==================== WebSocket Chat Endpoint ====================

@app.websocket("/ws/chat/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: UUID,
    token: str = Query(...)
):
    """
    WebSocket endpoint for streaming chat responses.
    
    Connection requires JWT token as query parameter.
    
    Client sends:
        {"message": "Why is my sleep worse?"}
    
    Server sends:
        {"type": "chunk", "content": "Based on..."}
        {"type": "chunk", "content": " your data..."}
        {"type": "done", "message_id": "uuid"}
    
    On error:
        {"type": "error", "message": "Error description"}
    """
    # Authenticate
    try:
        payload = decode_token(token)
        if not payload:
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        user_id = UUID(payload.get("sub"))
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    await websocket.accept()
    
    async with AsyncSessionLocal() as db:
        chat_service = ChatService(db)
        
        # Verify session belongs to user
        session = await chat_service.get_session(session_id, user_id)
        if not session:
            await websocket.send_json({
                "type": "error",
                "message": "Session not found"
            })
            await websocket.close(code=4004, reason="Session not found")
            return
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_json()
                user_message = data.get("message", "")
                
                if not user_message:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty message"
                    })
                    continue
                
                # Stream response
                try:
                    async for chunk in chat_service.generate_response(
                        user_id=user_id,
                        session_id=session_id,
                        user_message=user_message
                    ):
                        await websocket.send_json({
                            "type": "chunk",
                            "content": chunk
                        })
                    
                    # Commit the transaction
                    await db.commit()
                    
                    # Send completion message
                    messages = await chat_service.get_messages(session_id, limit=1)
                    last_msg = messages[-1] if messages else None
                    
                    await websocket.send_json({
                        "type": "done",
                        "message_id": str(last_msg.id) if last_msg else None
                    })
                    
                except Exception as e:
                    logger.error(f"Error generating response: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
        
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await websocket.close(code=4000, reason=str(e))
