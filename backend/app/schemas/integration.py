"""
Integration Schemas

Pydantic schemas for integration-related API requests and responses.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.utils.enums import DataSource, ConnectionStatus, SyncStatus, SyncDataType


# ============================================================================
# Provider Schemas
# ============================================================================

class ProviderInfo(BaseModel):
    """Information about a supported data provider"""
    id: DataSource
    name: str
    description: str
    supported_data_types: List[SyncDataType]
    requires_mobile: bool = False  # True for Apple Health


class ProvidersResponse(BaseModel):
    """List of available providers"""
    providers: List[ProviderInfo]


# ============================================================================
# Connection Schemas
# ============================================================================

class ConnectionResponse(BaseModel):
    """User connection to an external data source"""
    id: UUID
    provider: DataSource
    status: ConnectionStatus
    last_sync_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConnectionsListResponse(BaseModel):
    """List of user's connections"""
    connections: List[ConnectionResponse]
    total: int


class ConnectRequest(BaseModel):
    """Request to initiate connection to a provider"""
    redirect_url: Optional[str] = Field(
        None, 
        description="URL to redirect after OAuth completion"
    )


class ConnectResponse(BaseModel):
    """Response with link URL for OAuth flow"""
    connection_id: str
    link_url: str
    link_token: str
    expires_at: str
    provider: str


class DisconnectResponse(BaseModel):
    """Response after disconnecting a provider"""
    success: bool
    message: str


# ============================================================================
# Sync Schemas
# ============================================================================

class SyncRequest(BaseModel):
    """Request to trigger manual sync"""
    providers: Optional[List[DataSource]] = Field(
        None, 
        description="Specific providers to sync. If None, syncs all connected providers."
    )
    days: int = Field(
        30, 
        ge=1, 
        le=365, 
        description="Number of days of historical data to sync"
    )


class SyncDataTypeResult(BaseModel):
    """Result for a single data type sync"""
    data_type: SyncDataType
    records_fetched: int
    records_normalized: int
    records_skipped: int
    records_failed: int


class SyncProviderResult(BaseModel):
    """Result for a single provider sync"""
    provider: DataSource
    status: str  # "success", "partial", "failed"
    data_types: List[SyncDataTypeResult]
    error: Optional[str] = None


class SyncResponse(BaseModel):
    """Response from sync operation"""
    sync_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str  # "in_progress", "completed", "failed"
    providers: List[SyncProviderResult]
    total_records_synced: int


class SyncStatusResponse(BaseModel):
    """Status of ongoing or recent sync"""
    last_sync_at: Optional[datetime] = None
    sync_in_progress: bool = False
    providers: List[ConnectionResponse]


# ============================================================================
# Raw Data Schemas
# ============================================================================

class RawSyncDataResponse(BaseModel):
    """Raw sync data record"""
    id: UUID
    provider: DataSource
    data_type: SyncDataType
    external_id: str
    processing_status: SyncStatus
    received_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    normalized_table: Optional[str] = None
    normalized_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class RawDataListResponse(BaseModel):
    """List of raw sync data records"""
    records: List[RawSyncDataResponse]
    total: int
    pending: int
    completed: int
    failed: int
