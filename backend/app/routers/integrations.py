"""
Integrations Router

API endpoints for managing external data source connections and sync operations.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.user_connection import UserConnection
from app.models.raw_sync_data import RawSyncData
from app.utils.security import get_current_user
from app.utils.enums import DataSource, ConnectionStatus, SyncDataType, SyncStatus
from app.schemas.integration import (
    ProviderInfo, ProvidersResponse,
    ConnectionResponse, ConnectionsListResponse,
    ConnectRequest, ConnectResponse, DisconnectResponse,
    SyncRequest, SyncResponse, SyncStatusResponse,
    RawSyncDataResponse, RawDataListResponse
)
from app.integrations.vital.link import VitalLinkManager
from app.integrations.vital.client import VitalClient
from app.services.sync_service import SyncService
from app.config import settings
from app.integrations.vital.webhook import router as webhook_router


router = APIRouter()

# Include webhook routes
router.include_router(webhook_router, tags=["Webhooks"])


# ============================================================================
# Provider Information
# ============================================================================

@router.get("/providers", response_model=ProvidersResponse)
async def list_providers():
    """
    List all available data source providers.
    
    Returns information about each provider including supported data types
    and whether it requires a mobile app (e.g., Apple Health).
    """
    providers = [
        ProviderInfo(
            id=DataSource.google_fit,
            name="Google Fit",
            description="Activity, sleep, heart rate, and workout data from Google Fit",
            supported_data_types=[
                SyncDataType.sleep, SyncDataType.activity, 
                SyncDataType.workout, SyncDataType.vitals
            ]
        ),
        ProviderInfo(
            id=DataSource.fitbit,
            name="Fitbit",
            description="Comprehensive health data including sleep, activity, heart rate, and weight",
            supported_data_types=[
                SyncDataType.sleep, SyncDataType.activity, 
                SyncDataType.workout, SyncDataType.vitals, SyncDataType.body
            ]
        ),
        ProviderInfo(
            id=DataSource.garmin,
            name="Garmin",
            description="Activity, workout, sleep, and body composition from Garmin devices",
            supported_data_types=[
                SyncDataType.sleep, SyncDataType.activity, 
                SyncDataType.workout, SyncDataType.vitals, SyncDataType.body
            ]
        ),
        ProviderInfo(
            id=DataSource.oura,
            name="Oura Ring",
            description="Advanced sleep tracking, readiness scores, and HRV data",
            supported_data_types=[
                SyncDataType.sleep, SyncDataType.activity, SyncDataType.vitals
            ]
        ),
        ProviderInfo(
            id=DataSource.myfitnesspal,
            name="MyFitnessPal",
            description="Nutrition and meal tracking data",
            supported_data_types=[SyncDataType.nutrition]
        ),
        ProviderInfo(
            id=DataSource.whoop,
            name="WHOOP",
            description="Recovery, strain, and sleep data from WHOOP band",
            supported_data_types=[
                SyncDataType.sleep, SyncDataType.activity, SyncDataType.vitals
            ]
        ),
        ProviderInfo(
            id=DataSource.withings,
            name="Withings",
            description="Weight, body composition, blood pressure, and sleep data",
            supported_data_types=[
                SyncDataType.sleep, SyncDataType.body, SyncDataType.vitals
            ]
        ),
        ProviderInfo(
            id=DataSource.strava,
            name="Strava",
            description="Workout and activity data for runners and cyclists",
            supported_data_types=[SyncDataType.workout, SyncDataType.activity]
        ),
        ProviderInfo(
            id=DataSource.apple_health,
            name="Apple Health",
            description="Comprehensive health data from Apple Health (requires iOS app)",
            supported_data_types=[
                SyncDataType.sleep, SyncDataType.activity, 
                SyncDataType.workout, SyncDataType.vitals, 
                SyncDataType.body, SyncDataType.nutrition
            ],
            requires_mobile=True
        ),
    ]
    
    return ProvidersResponse(providers=providers)


# ============================================================================
# Connection Management
# ============================================================================

@router.get("/connections", response_model=ConnectionsListResponse)
async def list_connections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all data source connections for the current user.
    """
    link_manager = VitalLinkManager(db)
    connections = await link_manager.get_user_connections(current_user.id)
    
    return ConnectionsListResponse(
        connections=[ConnectionResponse.model_validate(c) for c in connections],
        total=len(connections)
    )


@router.post("/connect/{provider}", response_model=ConnectResponse)
async def connect_provider(
    provider: DataSource,
    request: ConnectRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate connection to an external data provider.
    
    Returns a link URL that the user should be redirected to for OAuth authentication.
    After successful authentication, Vital will send a webhook to complete the connection.
    """
    if provider == DataSource.apple_health:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apple Health requires a mobile app. This feature is coming soon."
        )
    
    if provider == DataSource.manual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot connect to 'manual' - this is for manually entered data only."
        )
    
    vital_client = VitalClient(mock_mode=settings.VITAL_MOCK_MODE)
    link_manager = VitalLinkManager(db, vital_client)
    
    try:
        redirect_url = request.redirect_url if request else None
        result = await link_manager.initiate_connection(
            user_id=current_user.id,
            provider=provider,
            redirect_url=redirect_url
        )
        return ConnectResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/connections/{connection_id}", response_model=DisconnectResponse)
async def disconnect_provider(
    connection_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect from a data source provider.
    """
    # Find the connection
    stmt = select(UserConnection).where(
        UserConnection.id == connection_id,
        UserConnection.user_id == current_user.id
    )
    result = await db.execute(stmt)
    connection = result.scalar_one_or_none()
    
    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )
    
    link_manager = VitalLinkManager(db)
    success = await link_manager.disconnect(current_user.id, connection.provider)
    
    return DisconnectResponse(
        success=success,
        message=f"Disconnected from {connection.provider.value}" if success else "Failed to disconnect"
    )


# ============================================================================
# Sync Operations
# ============================================================================

@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    request: SyncRequest = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger manual sync of health data from connected providers.
    
    This fetches data from all (or specified) connected providers,
    stores it in the staging table, and normalizes it into the main tables.
    """
    sync_service = SyncService(db, current_user.id)
    
    providers = request.providers if request else None
    days = request.days if request else 30
    
    result = await sync_service.sync_all(days=days, providers=providers)
    
    # Convert to response format
    provider_results = []
    for pr in result.get("providers", []):
        data_types = []
        for dt in pr.get("data_types", []):
            data_types.append({
                "data_type": dt.get("data_type"),
                "records_fetched": dt.get("records_fetched", 0),
                "records_normalized": dt.get("records_normalized", 0),
                "records_skipped": dt.get("records_skipped", 0),
                "records_failed": dt.get("records_failed", 0)
            })
        
        provider_results.append({
            "provider": pr.get("provider"),
            "status": pr.get("status"),
            "data_types": data_types,
            "error": pr.get("error")
        })
    
    return SyncResponse(
        sync_id=result.get("sync_id"),
        started_at=result.get("started_at"),
        completed_at=result.get("completed_at"),
        status=result.get("status"),
        providers=provider_results,
        total_records_synced=result.get("total_records_synced", 0)
    )


@router.get("/sync/status", response_model=SyncStatusResponse)
async def get_sync_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current sync status for the user.
    
    Returns information about connected providers and whether a sync is in progress.
    """
    sync_service = SyncService(db, current_user.id)
    status_data = await sync_service.get_sync_status()
    
    return SyncStatusResponse(
        last_sync_at=status_data.get("last_sync_at"),
        sync_in_progress=status_data.get("sync_in_progress", False),
        providers=[ConnectionResponse.model_validate(c) for c in status_data.get("connections", [])]
    )


# ============================================================================
# Raw Data Access (for debugging/admin)
# ============================================================================

@router.get("/raw-data", response_model=RawDataListResponse)
async def list_raw_data(
    data_type: Optional[SyncDataType] = None,
    status_filter: Optional[SyncStatus] = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List raw sync data records (for debugging and monitoring).
    """
    stmt = select(RawSyncData).where(
        RawSyncData.user_id == current_user.id
    )
    
    if data_type:
        stmt = stmt.where(RawSyncData.data_type == data_type)
    if status_filter:
        stmt = stmt.where(RawSyncData.processing_status == status_filter)
    
    stmt = stmt.order_by(RawSyncData.received_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(stmt)
    records = list(result.scalars().all())
    
    # Get counts
    from sqlalchemy import func
    
    total_stmt = select(func.count()).select_from(RawSyncData).where(
        RawSyncData.user_id == current_user.id
    )
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0
    
    pending_stmt = select(func.count()).select_from(RawSyncData).where(
        RawSyncData.user_id == current_user.id,
        RawSyncData.processing_status == SyncStatus.pending
    )
    pending_result = await db.execute(pending_stmt)
    pending = pending_result.scalar() or 0
    
    completed_stmt = select(func.count()).select_from(RawSyncData).where(
        RawSyncData.user_id == current_user.id,
        RawSyncData.processing_status == SyncStatus.completed
    )
    completed_result = await db.execute(completed_stmt)
    completed = completed_result.scalar() or 0
    
    failed_stmt = select(func.count()).select_from(RawSyncData).where(
        RawSyncData.user_id == current_user.id,
        RawSyncData.processing_status == SyncStatus.failed
    )
    failed_result = await db.execute(failed_stmt)
    failed = failed_result.scalar() or 0
    
    return RawDataListResponse(
        records=[RawSyncDataResponse.model_validate(r) for r in records],
        total=total,
        pending=pending,
        completed=completed,
        failed=failed
    )
