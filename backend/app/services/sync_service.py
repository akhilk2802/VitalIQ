"""
Sync Service

Orchestrates data synchronization from external sources through the staging pipeline.
"""
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.user_connection import UserConnection
from app.models.raw_sync_data import RawSyncData
from app.utils.enums import DataSource, ConnectionStatus, SyncStatus, SyncDataType
from app.integrations.vital.client import VitalClient
from app.integrations.normalizers.sleep import SleepNormalizer
from app.integrations.normalizers.activity import ActivityNormalizer
from app.integrations.normalizers.nutrition import NutritionNormalizer
from app.integrations.normalizers.body import BodyNormalizer
from app.integrations.normalizers.vitals import VitalsNormalizer
from app.config import settings


class SyncService:
    """
    Orchestrates the sync pipeline:
    1. Fetch data from Vital API
    2. Store raw data in staging table
    3. Normalize and insert into main tables
    """
    
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
        self.vital_client = VitalClient(mock_mode=settings.VITAL_MOCK_MODE)
        
        # Initialize normalizers
        self.normalizers = {
            SyncDataType.sleep: SleepNormalizer(db, user_id),
            SyncDataType.workout: ActivityNormalizer(db, user_id),
            SyncDataType.activity: ActivityNormalizer(db, user_id),
            SyncDataType.nutrition: NutritionNormalizer(db, user_id),
            SyncDataType.body: BodyNormalizer(db, user_id),
            SyncDataType.vitals: VitalsNormalizer(db, user_id),
        }
    
    async def sync_all(
        self, 
        days: int = 30,
        providers: Optional[List[DataSource]] = None
    ) -> Dict[str, Any]:
        """
        Sync data from all connected providers.
        
        Args:
            days: Number of days of historical data to sync
            providers: Specific providers to sync, or None for all connected
            
        Returns:
            Sync results summary
        """
        sync_id = str(uuid.uuid4())
        started_at = datetime.utcnow()
        
        # Get connected providers
        connections = await self._get_connections(providers)
        if not connections:
            return {
                "sync_id": sync_id,
                "started_at": started_at,
                "completed_at": datetime.utcnow(),
                "status": "no_connections",
                "providers": [],
                "total_records_synced": 0
            }
        
        provider_results = []
        total_synced = 0
        
        for connection in connections:
            result = await self._sync_provider(connection, days)
            provider_results.append(result)
            total_synced += sum(
                dt.get("records_normalized", 0) 
                for dt in result.get("data_types", [])
            )
            
            # Update last_sync_at
            connection.last_sync_at = datetime.utcnow()
        
        await self.db.flush()
        
        # Determine overall status
        statuses = [r.get("status") for r in provider_results]
        if all(s == "success" for s in statuses):
            overall_status = "completed"
        elif all(s == "failed" for s in statuses):
            overall_status = "failed"
        else:
            overall_status = "partial"
        
        return {
            "sync_id": sync_id,
            "started_at": started_at,
            "completed_at": datetime.utcnow(),
            "status": overall_status,
            "providers": provider_results,
            "total_records_synced": total_synced
        }
    
    async def _sync_provider(
        self, 
        connection: UserConnection, 
        days: int
    ) -> Dict[str, Any]:
        """Sync data from a single provider."""
        provider = connection.provider
        vital_user_id = connection.vital_user_id
        
        if not vital_user_id:
            return {
                "provider": provider.value,
                "status": "failed",
                "error": "No Vital user ID",
                "data_types": []
            }
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        data_type_results = []
        
        try:
            # Fetch and process each data type
            data_type_results.extend(await self._sync_sleep(
                vital_user_id, provider, connection.id, start_date, end_date
            ))
            
            data_type_results.extend(await self._sync_workouts(
                vital_user_id, provider, connection.id, start_date, end_date
            ))
            
            data_type_results.extend(await self._sync_body(
                vital_user_id, provider, connection.id, start_date, end_date
            ))
            
            data_type_results.extend(await self._sync_vitals(
                vital_user_id, provider, connection.id, start_date, end_date
            ))
            
            # Nutrition only from MyFitnessPal
            if provider == DataSource.myfitnesspal:
                data_type_results.extend(await self._sync_nutrition(
                    vital_user_id, provider, connection.id, start_date, end_date
                ))
            
            status = "success"
            if any(r.get("records_failed", 0) > 0 for r in data_type_results):
                status = "partial"
                
        except Exception as e:
            return {
                "provider": provider.value,
                "status": "failed",
                "error": str(e),
                "data_types": data_type_results
            }
        
        return {
            "provider": provider.value,
            "status": status,
            "data_types": data_type_results
        }
    
    async def _sync_sleep(
        self, 
        vital_user_id: str, 
        provider: DataSource,
        connection_id: uuid.UUID,
        start_date: date, 
        end_date: date
    ) -> List[Dict]:
        """Sync sleep data."""
        try:
            raw_data = await self.vital_client.get_sleep(
                vital_user_id, start_date, end_date
            )
            return await self._process_raw_data(
                raw_data, provider, connection_id, SyncDataType.sleep
            )
        except Exception as e:
            return [{
                "data_type": SyncDataType.sleep.value,
                "records_fetched": 0,
                "records_normalized": 0,
                "records_skipped": 0,
                "records_failed": 1,
                "error": str(e)
            }]
    
    async def _sync_workouts(
        self, 
        vital_user_id: str, 
        provider: DataSource,
        connection_id: uuid.UUID,
        start_date: date, 
        end_date: date
    ) -> List[Dict]:
        """Sync workout data."""
        try:
            raw_data = await self.vital_client.get_workouts(
                vital_user_id, start_date, end_date
            )
            return await self._process_raw_data(
                raw_data, provider, connection_id, SyncDataType.workout
            )
        except Exception as e:
            return [{
                "data_type": SyncDataType.workout.value,
                "records_fetched": 0,
                "records_normalized": 0,
                "records_skipped": 0,
                "records_failed": 1,
                "error": str(e)
            }]
    
    async def _sync_body(
        self, 
        vital_user_id: str, 
        provider: DataSource,
        connection_id: uuid.UUID,
        start_date: date, 
        end_date: date
    ) -> List[Dict]:
        """Sync body metrics data."""
        try:
            raw_data = await self.vital_client.get_body(
                vital_user_id, start_date, end_date
            )
            return await self._process_raw_data(
                raw_data, provider, connection_id, SyncDataType.body
            )
        except Exception as e:
            return [{
                "data_type": SyncDataType.body.value,
                "records_fetched": 0,
                "records_normalized": 0,
                "records_skipped": 0,
                "records_failed": 1,
                "error": str(e)
            }]
    
    async def _sync_vitals(
        self, 
        vital_user_id: str, 
        provider: DataSource,
        connection_id: uuid.UUID,
        start_date: date, 
        end_date: date
    ) -> List[Dict]:
        """Sync vital signs data."""
        try:
            # Get time series data
            vitals_data = await self.vital_client.get_vitals(
                vital_user_id, start_date, end_date
            )
            
            # Aggregate by date
            aggregated = []
            current = start_date
            while current <= end_date:
                date_str = current.isoformat()
                
                # Filter data for this date
                hr_day = [d for d in vitals_data.get("heartrate", []) 
                         if d.get("timestamp", "").startswith(date_str)]
                hrv_day = [d for d in vitals_data.get("hrv", []) 
                          if d.get("timestamp", "").startswith(date_str)]
                spo2_day = [d for d in vitals_data.get("blood_oxygen", []) 
                           if d.get("timestamp", "").startswith(date_str)]
                
                if hr_day or hrv_day or spo2_day:
                    agg = VitalsNormalizer.aggregate_time_series(
                        hr_day, hrv_day, spo2_day, date_str
                    )
                    aggregated.append(agg)
                
                current += timedelta(days=1)
            
            return await self._process_raw_data(
                aggregated, provider, connection_id, SyncDataType.vitals
            )
        except Exception as e:
            return [{
                "data_type": SyncDataType.vitals.value,
                "records_fetched": 0,
                "records_normalized": 0,
                "records_skipped": 0,
                "records_failed": 1,
                "error": str(e)
            }]
    
    async def _sync_nutrition(
        self, 
        vital_user_id: str, 
        provider: DataSource,
        connection_id: uuid.UUID,
        start_date: date, 
        end_date: date
    ) -> List[Dict]:
        """Sync nutrition/meal data."""
        try:
            raw_data = await self.vital_client.get_meal(
                vital_user_id, start_date, end_date
            )
            return await self._process_raw_data(
                raw_data, provider, connection_id, SyncDataType.nutrition
            )
        except Exception as e:
            return [{
                "data_type": SyncDataType.nutrition.value,
                "records_fetched": 0,
                "records_normalized": 0,
                "records_skipped": 0,
                "records_failed": 1,
                "error": str(e)
            }]
    
    async def _process_raw_data(
        self,
        raw_data: List[Dict],
        provider: DataSource,
        connection_id: uuid.UUID,
        data_type: SyncDataType
    ) -> List[Dict]:
        """
        Store raw data in staging and normalize.
        
        Returns list of result dicts (one per data type processed).
        """
        if not raw_data:
            return [{
                "data_type": data_type.value,
                "records_fetched": 0,
                "records_normalized": 0,
                "records_skipped": 0,
                "records_failed": 0
            }]
        
        # Store in staging table
        raw_records = []
        for item in raw_data:
            external_id = item.get("id", str(uuid.uuid4()))
            
            # Check if already exists
            existing = await self._find_existing_raw(provider, external_id)
            if existing:
                continue
            
            raw_record = RawSyncData(
                user_id=self.user_id,
                connection_id=connection_id,
                provider=provider,
                data_type=data_type,
                external_id=external_id,
                raw_payload=item,
                processing_status=SyncStatus.pending
            )
            self.db.add(raw_record)
            raw_records.append(raw_record)
        
        await self.db.flush()
        
        # Normalize
        normalizer = self.normalizers.get(data_type)
        if normalizer and raw_records:
            norm_result = await normalizer.normalize_batch(raw_records)
        else:
            norm_result = {"processed": 0, "skipped": 0, "failed": 0}
        
        return [{
            "data_type": data_type.value,
            "records_fetched": len(raw_data),
            "records_normalized": norm_result.get("processed", 0),
            "records_skipped": norm_result.get("skipped", 0) + (len(raw_data) - len(raw_records)),
            "records_failed": norm_result.get("failed", 0)
        }]
    
    async def _find_existing_raw(
        self, 
        provider: DataSource, 
        external_id: str
    ) -> Optional[RawSyncData]:
        """Check if raw data already exists."""
        stmt = select(RawSyncData).where(
            RawSyncData.user_id == self.user_id,
            RawSyncData.provider == provider,
            RawSyncData.external_id == external_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _get_connections(
        self, 
        providers: Optional[List[DataSource]] = None
    ) -> List[UserConnection]:
        """Get connected providers for user."""
        stmt = select(UserConnection).where(
            UserConnection.user_id == self.user_id,
            UserConnection.status == ConnectionStatus.connected
        )
        
        if providers:
            stmt = stmt.where(UserConnection.provider.in_(providers))
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status for user."""
        # Get connections
        stmt = select(UserConnection).where(
            UserConnection.user_id == self.user_id
        )
        result = await self.db.execute(stmt)
        connections = list(result.scalars().all())
        
        # Get pending raw data count
        pending_stmt = select(func.count()).select_from(RawSyncData).where(
            RawSyncData.user_id == self.user_id,
            RawSyncData.processing_status == SyncStatus.pending
        )
        pending_result = await self.db.execute(pending_stmt)
        pending_count = pending_result.scalar() or 0
        
        # Find last sync time
        last_sync = None
        for conn in connections:
            if conn.last_sync_at and (not last_sync or conn.last_sync_at > last_sync):
                last_sync = conn.last_sync_at
        
        return {
            "last_sync_at": last_sync,
            "sync_in_progress": pending_count > 0,
            "pending_records": pending_count,
            "connections": connections
        }
