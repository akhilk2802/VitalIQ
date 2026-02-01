"""
Background Task Scheduler

Handles periodic sync of health data from connected providers.
Uses FastAPI's BackgroundTasks for simple scheduling.
For production, consider using Celery, APScheduler, or similar.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user_connection import UserConnection
from app.utils.enums import ConnectionStatus
from app.services.sync_service import SyncService
from app.config import settings


logger = logging.getLogger(__name__)


class SyncScheduler:
    """
    Scheduler for periodic data synchronization.
    
    In production, you would want to use a proper job scheduler like:
    - APScheduler
    - Celery with Redis/RabbitMQ
    - AWS Lambda scheduled events
    - Kubernetes CronJobs
    
    This implementation uses a simple asyncio background task.
    """
    
    def __init__(self, sync_interval_hours: int = 24):
        """
        Initialize the scheduler.
        
        Args:
            sync_interval_hours: Hours between sync runs (default: 24)
        """
        self.sync_interval = timedelta(hours=sync_interval_hours)
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Sync scheduler started with {self.sync_interval} interval")
    
    async def stop(self):
        """Stop the background scheduler."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Sync scheduler stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop."""
        while self.is_running:
            try:
                # Calculate time until next sync (e.g., 2 AM UTC)
                next_sync = self._get_next_sync_time()
                wait_seconds = (next_sync - datetime.utcnow()).total_seconds()
                
                if wait_seconds > 0:
                    logger.info(f"Next sync scheduled at {next_sync} ({wait_seconds:.0f}s from now)")
                    await asyncio.sleep(wait_seconds)
                
                if self.is_running:
                    await self._perform_sync_for_all_users()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                # Wait before retrying on error
                await asyncio.sleep(60)
    
    def _get_next_sync_time(self) -> datetime:
        """Calculate the next sync time (default: 2 AM UTC daily)."""
        now = datetime.utcnow()
        next_sync = now.replace(hour=2, minute=0, second=0, microsecond=0)
        
        # If it's already past 2 AM today, schedule for tomorrow
        if now >= next_sync:
            next_sync += timedelta(days=1)
        
        return next_sync
    
    async def _perform_sync_for_all_users(self):
        """Sync data for all users with connected providers."""
        logger.info("Starting scheduled sync for all users")
        
        async with AsyncSessionLocal() as db:
            try:
                # Get all users with active connections
                stmt = select(UserConnection.user_id).where(
                    UserConnection.status == ConnectionStatus.connected
                ).distinct()
                
                result = await db.execute(stmt)
                user_ids = [row[0] for row in result.fetchall()]
                
                logger.info(f"Found {len(user_ids)} users with active connections")
                
                for user_id in user_ids:
                    try:
                        sync_service = SyncService(db, user_id)
                        result = await sync_service.sync_all(days=7)  # Last 7 days for daily sync
                        
                        logger.info(
                            f"Synced user {user_id}: "
                            f"{result.get('total_records_synced', 0)} records"
                        )
                        
                    except Exception as e:
                        logger.error(f"Error syncing user {user_id}: {e}")
                        continue
                
                await db.commit()
                
            except Exception as e:
                logger.error(f"Error in scheduled sync: {e}")
                await db.rollback()
        
        logger.info("Scheduled sync completed")


# Global scheduler instance
scheduler = SyncScheduler()


async def trigger_manual_sync_for_user(user_id, days: int = 30):
    """
    Manually trigger a sync for a specific user.
    
    This can be called from an API endpoint or background task.
    """
    async with AsyncSessionLocal() as db:
        try:
            sync_service = SyncService(db, user_id)
            result = await sync_service.sync_all(days=days)
            await db.commit()
            return result
        except Exception as e:
            await db.rollback()
            raise e
