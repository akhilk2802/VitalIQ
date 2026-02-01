"""
Base Normalizer Class

Provides common functionality for all data normalizers that transform
external API data into VitalIQ's internal model format.
"""
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Optional, List, Dict, Any, TypeVar, Generic

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import Base
from app.models.raw_sync_data import RawSyncData
from app.utils.enums import SyncStatus, SyncDataType, DataSource


T = TypeVar('T', bound=Base)


class BaseNormalizer(ABC, Generic[T]):
    """
    Base class for data normalizers.
    
    Each normalizer is responsible for:
    1. Transforming raw API data into model instances
    2. Handling deduplication (via external_id)
    3. Updating raw_sync_data status after processing
    """
    
    # Override in subclasses
    MODEL_CLASS: type = None
    DATA_TYPE: SyncDataType = None
    TARGET_TABLE: str = None
    
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
    
    @abstractmethod
    def normalize_single(self, raw_data: Dict[str, Any], source: DataSource) -> T:
        """
        Transform a single raw data record into a model instance.
        
        Args:
            raw_data: Raw data from external API
            source: The data source provider
            
        Returns:
            Model instance (not yet added to session)
        """
        pass
    
    async def normalize_batch(
        self, 
        raw_records: List[RawSyncData]
    ) -> Dict[str, Any]:
        """
        Process a batch of raw sync records.
        
        Args:
            raw_records: List of RawSyncData records to process
            
        Returns:
            Dict with counts of processed, skipped, and failed records
        """
        results = {
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "created_ids": []
        }
        
        for raw_record in raw_records:
            try:
                # Check if already processed
                if raw_record.processing_status == SyncStatus.completed:
                    results["skipped"] += 1
                    continue
                
                # Mark as processing
                raw_record.processing_status = SyncStatus.processing
                
                # Check for duplicate by external_id
                existing = await self._find_existing(raw_record.external_id)
                if existing:
                    raw_record.processing_status = SyncStatus.skipped
                    raw_record.normalized_table = self.TARGET_TABLE
                    raw_record.normalized_id = existing.id
                    raw_record.processed_at = datetime.utcnow()
                    results["skipped"] += 1
                    continue
                
                # Normalize the data
                model_instance = self.normalize_single(
                    raw_record.raw_payload, 
                    raw_record.provider
                )
                
                # Add to session and flush to get ID
                self.db.add(model_instance)
                await self.db.flush()
                
                # Update raw record
                raw_record.processing_status = SyncStatus.completed
                raw_record.normalized_table = self.TARGET_TABLE
                raw_record.normalized_id = model_instance.id
                raw_record.processed_at = datetime.utcnow()
                
                results["processed"] += 1
                results["created_ids"].append(str(model_instance.id))
                
            except Exception as e:
                raw_record.processing_status = SyncStatus.failed
                raw_record.error_message = str(e)
                raw_record.processed_at = datetime.utcnow()
                results["failed"] += 1
        
        return results
    
    async def _find_existing(self, external_id: str) -> Optional[T]:
        """Find existing record by external_id to avoid duplicates."""
        if not self.MODEL_CLASS:
            return None
        
        stmt = select(self.MODEL_CLASS).where(
            self.MODEL_CLASS.user_id == self.user_id,
            self.MODEL_CLASS.external_id == external_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    @staticmethod
    def parse_datetime(dt_string: str) -> Optional[datetime]:
        """Parse ISO datetime string."""
        if not dt_string:
            return None
        try:
            # Handle various ISO formats
            dt_string = dt_string.replace("Z", "+00:00")
            return datetime.fromisoformat(dt_string)
        except ValueError:
            return None
    
    @staticmethod
    def parse_date(date_string: str) -> Optional[date]:
        """Parse ISO date string."""
        if not date_string:
            return None
        try:
            return date.fromisoformat(date_string)
        except ValueError:
            return None
    
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """Safely convert to float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """Safely convert to int."""
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
