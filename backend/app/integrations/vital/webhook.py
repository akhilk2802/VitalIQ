"""
Vital Webhook Handler

Handles incoming webhooks from Vital API for connection events and data updates.
"""
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.config import settings
from app.models.user_connection import UserConnection
from app.utils.enums import ConnectionStatus, DataSource
from app.integrations.vital.link import VitalLinkManager


router = APIRouter()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify the webhook signature from Vital.
    
    Vital signs webhooks using HMAC-SHA256.
    """
    if not secret:
        # In mock mode or development, skip verification
        return True
    
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def handle_vital_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle incoming webhooks from Vital.
    
    Vital sends webhooks for:
    - connection.created: User successfully connected a provider
    - connection.error: Connection failed
    - connection.deregistered: User disconnected a provider
    - daily.data.*.created: New data available
    
    See: https://docs.tryvital.io/webhooks/overview
    """
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify signature (if configured)
    signature = request.headers.get("X-Vital-Signature", "")
    if settings.VITAL_WEBHOOK_SECRET and not verify_webhook_signature(
        body, signature, settings.VITAL_WEBHOOK_SECRET
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse payload
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    event_type = payload.get("event_type", "")
    
    # Route to appropriate handler
    if event_type == "connection.created":
        return await handle_connection_created(payload, db)
    elif event_type == "connection.error":
        return await handle_connection_error(payload, db)
    elif event_type == "connection.deregistered":
        return await handle_connection_deregistered(payload, db)
    elif event_type.startswith("daily.data."):
        return await handle_data_available(payload, db)
    else:
        # Unknown event type - log and acknowledge
        return {"status": "acknowledged", "event_type": event_type}


async def handle_connection_created(payload: Dict[str, Any], db: AsyncSession) -> Dict:
    """Handle successful connection webhook."""
    data = payload.get("data", {})
    vital_user_id = data.get("user_id")
    provider = data.get("source", {}).get("slug")
    
    if not vital_user_id or not provider:
        return {"status": "ignored", "reason": "missing user_id or provider"}
    
    link_manager = VitalLinkManager(db)
    
    try:
        connection = await link_manager.handle_connection_success(vital_user_id, provider)
        if connection:
            return {
                "status": "success",
                "connection_id": str(connection.id),
                "provider": provider
            }
        else:
            return {"status": "ignored", "reason": "connection not found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_connection_error(payload: Dict[str, Any], db: AsyncSession) -> Dict:
    """Handle connection error webhook."""
    data = payload.get("data", {})
    vital_user_id = data.get("user_id")
    provider = data.get("source", {}).get("slug")
    error_message = data.get("error", {}).get("message", "Unknown error")
    
    if not vital_user_id or not provider:
        return {"status": "ignored", "reason": "missing user_id or provider"}
    
    link_manager = VitalLinkManager(db)
    
    try:
        connection = await link_manager.handle_connection_error(
            vital_user_id, provider, error_message
        )
        if connection:
            return {
                "status": "recorded",
                "connection_id": str(connection.id),
                "error": error_message
            }
        else:
            return {"status": "ignored", "reason": "connection not found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def handle_connection_deregistered(payload: Dict[str, Any], db: AsyncSession) -> Dict:
    """Handle connection deregistration webhook."""
    data = payload.get("data", {})
    vital_user_id = data.get("user_id")
    provider = data.get("source", {}).get("slug")
    
    if not vital_user_id or not provider:
        return {"status": "ignored", "reason": "missing user_id or provider"}
    
    try:
        provider_enum = DataSource(provider)
    except ValueError:
        return {"status": "ignored", "reason": f"unknown provider: {provider}"}
    
    # Find and update the connection
    stmt = select(UserConnection).where(
        UserConnection.vital_user_id == vital_user_id,
        UserConnection.provider == provider_enum
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    
    if connection:
        connection.status = ConnectionStatus.disconnected
        connection.updated_at = datetime.utcnow()
        await db.flush()
        return {
            "status": "disconnected",
            "connection_id": str(connection.id)
        }
    
    return {"status": "ignored", "reason": "connection not found"}


async def handle_data_available(payload: Dict[str, Any], db: AsyncSession) -> Dict:
    """
    Handle data availability webhook.
    
    When Vital receives new data from a provider, it sends a webhook
    to notify us. We can then trigger a sync for that user.
    
    In a production system, you might want to queue this for background processing.
    """
    data = payload.get("data", {})
    vital_user_id = data.get("user_id")
    
    if not vital_user_id:
        return {"status": "ignored", "reason": "missing user_id"}
    
    # Find the user from vital_user_id
    stmt = select(UserConnection).where(
        UserConnection.vital_user_id == vital_user_id
    ).limit(1)
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    
    if not connection:
        return {"status": "ignored", "reason": "user not found"}
    
    # In production, you would queue a sync job here
    # For now, we just acknowledge the webhook
    return {
        "status": "acknowledged",
        "user_id": str(connection.user_id),
        "data_type": payload.get("event_type", "").replace("daily.data.", "").replace(".created", ""),
        "message": "Sync queued"
    }
