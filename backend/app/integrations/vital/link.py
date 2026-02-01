"""
Vital Link Flow Management

Handles the OAuth flow for connecting external data sources via Vital.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user_connection import UserConnection
from app.utils.enums import DataSource, ConnectionStatus
from app.integrations.vital.client import VitalClient


class VitalLinkManager:
    """
    Manages the connection flow between users and external data sources.
    
    Flow:
    1. User requests to connect a provider
    2. We create/get a Vital user for them
    3. We generate a link token/URL
    4. User completes OAuth on provider
    5. Vital sends webhook when connected
    6. We update UserConnection status
    """
    
    def __init__(self, db: AsyncSession, vital_client: Optional[VitalClient] = None):
        self.db = db
        self.vital_client = vital_client or VitalClient(mock_mode=True)
    
    async def initiate_connection(
        self, 
        user_id: uuid.UUID, 
        provider: DataSource,
        redirect_url: Optional[str] = None
    ) -> dict:
        """
        Start the connection flow for a user and provider.
        
        Returns:
            dict with link_url and connection_id
        """
        # Check if connection already exists
        existing = await self._get_existing_connection(user_id, provider)
        if existing and existing.status == ConnectionStatus.connected:
            raise ValueError(f"Already connected to {provider.value}")
        
        # Get or create Vital user
        vital_user_id = await self._ensure_vital_user(user_id)
        
        # Create pending connection record
        if existing:
            connection = existing
            connection.status = ConnectionStatus.pending
            connection.error_message = None
        else:
            connection = UserConnection(
                user_id=user_id,
                provider=provider,
                vital_user_id=vital_user_id,
                status=ConnectionStatus.pending
            )
            self.db.add(connection)
        
        await self.db.flush()
        
        # Get link URL from Vital
        link_response = await self.vital_client.create_link_token(
            vital_user_id=vital_user_id,
            provider=provider,
            redirect_url=redirect_url
        )
        
        return {
            "connection_id": str(connection.id),
            "link_url": link_response.link_url,
            "link_token": link_response.link_token,
            "expires_at": link_response.expires_at.isoformat(),
            "provider": provider.value
        }
    
    async def handle_connection_success(
        self, 
        vital_user_id: str, 
        provider: str
    ) -> Optional[UserConnection]:
        """
        Handle successful connection webhook from Vital.
        
        Called when Vital sends a webhook indicating the user
        has successfully authenticated with the provider.
        """
        # Find the connection by vital_user_id and provider
        provider_enum = DataSource(provider)
        
        stmt = select(UserConnection).where(
            UserConnection.vital_user_id == vital_user_id,
            UserConnection.provider == provider_enum
        )
        result = await self.db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if connection:
            connection.status = ConnectionStatus.connected
            connection.error_message = None
            connection.updated_at = datetime.utcnow()
            await self.db.flush()
        
        return connection
    
    async def handle_connection_error(
        self, 
        vital_user_id: str, 
        provider: str,
        error_message: str
    ) -> Optional[UserConnection]:
        """Handle connection error webhook from Vital."""
        provider_enum = DataSource(provider)
        
        stmt = select(UserConnection).where(
            UserConnection.vital_user_id == vital_user_id,
            UserConnection.provider == provider_enum
        )
        result = await self.db.execute(stmt)
        connection = result.scalar_one_or_none()
        
        if connection:
            connection.status = ConnectionStatus.error
            connection.error_message = error_message
            connection.updated_at = datetime.utcnow()
            await self.db.flush()
        
        return connection
    
    async def disconnect(self, user_id: uuid.UUID, provider: DataSource) -> bool:
        """
        Disconnect a user from a provider.
        
        This marks the connection as disconnected. The actual disconnection
        from Vital would happen via their API in production.
        """
        connection = await self._get_existing_connection(user_id, provider)
        if not connection:
            return False
        
        connection.status = ConnectionStatus.disconnected
        connection.updated_at = datetime.utcnow()
        await self.db.flush()
        
        return True
    
    async def get_user_connections(self, user_id: uuid.UUID) -> list[UserConnection]:
        """Get all connections for a user."""
        stmt = select(UserConnection).where(
            UserConnection.user_id == user_id
        ).order_by(UserConnection.created_at.desc())
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def _get_existing_connection(
        self, 
        user_id: uuid.UUID, 
        provider: DataSource
    ) -> Optional[UserConnection]:
        """Get existing connection if any."""
        stmt = select(UserConnection).where(
            UserConnection.user_id == user_id,
            UserConnection.provider == provider
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _ensure_vital_user(self, user_id: uuid.UUID) -> str:
        """
        Get or create a Vital user ID for our user.
        
        Checks if user already has a Vital user ID from an existing connection,
        otherwise creates a new Vital user.
        """
        # Check if user already has a vital_user_id from any connection
        stmt = select(UserConnection.vital_user_id).where(
            UserConnection.user_id == user_id,
            UserConnection.vital_user_id.isnot(None)
        ).limit(1)
        
        result = await self.db.execute(stmt)
        existing_vital_id = result.scalar_one_or_none()
        
        if existing_vital_id:
            return existing_vital_id
        
        # Create new Vital user
        vital_user = await self.vital_client.create_user(str(user_id))
        return vital_user.user_id
