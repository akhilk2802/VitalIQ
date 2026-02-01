"""Add integration tables for external data sources

Revision ID: 003
Revises: 002
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types for integrations
    data_source = postgresql.ENUM(
        'manual', 'google_fit', 'fitbit', 'garmin', 'oura', 
        'myfitnesspal', 'apple_health', 'whoop', 'withings', 'polar', 'strava',
        name='datasource', 
        create_type=False
    )
    data_source.create(op.get_bind(), checkfirst=True)
    
    connection_status = postgresql.ENUM(
        'pending', 'connected', 'disconnected', 'error',
        name='connectionstatus',
        create_type=False
    )
    connection_status.create(op.get_bind(), checkfirst=True)
    
    sync_status = postgresql.ENUM(
        'pending', 'processing', 'completed', 'failed', 'skipped',
        name='syncstatus',
        create_type=False
    )
    sync_status.create(op.get_bind(), checkfirst=True)
    
    sync_data_type = postgresql.ENUM(
        'sleep', 'activity', 'nutrition', 'body', 'vitals', 'workout',
        name='syncdatatype',
        create_type=False
    )
    sync_data_type.create(op.get_bind(), checkfirst=True)

    # Create user_connections table
    op.create_table(
        'user_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('provider', data_source, nullable=False),
        sa.Column('vital_user_id', sa.String(255), nullable=True),
        sa.Column('status', connection_status, nullable=False, server_default='pending'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('sync_cursor', sa.String(500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create unique constraint for user + provider
    op.create_index('ix_user_connections_user_provider', 'user_connections', 
                    ['user_id', 'provider'], unique=True)

    # Create raw_sync_data table
    op.create_table(
        'raw_sync_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('user_connections.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('provider', data_source, nullable=False),
        sa.Column('data_type', sync_data_type, nullable=False),
        sa.Column('external_id', sa.String(500), nullable=False, index=True),
        sa.Column('raw_payload', postgresql.JSONB(), nullable=False),
        sa.Column('received_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('processing_status', sync_status, nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('normalized_table', sa.String(100), nullable=True),
        sa.Column('normalized_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    
    # Create indexes for common queries
    op.create_index('ix_raw_sync_data_status', 'raw_sync_data', 
                    ['processing_status', 'received_at'])
    op.create_index('ix_raw_sync_data_external', 'raw_sync_data', 
                    ['provider', 'external_id'], unique=True)

    # Add source tracking columns to existing tables
    # Food entries
    op.add_column('food_entries', sa.Column('source', sa.String(50), nullable=True, server_default='manual'))
    op.add_column('food_entries', sa.Column('external_id', sa.String(500), nullable=True))
    op.add_column('food_entries', sa.Column('synced_at', sa.DateTime(), nullable=True))
    
    # Sleep entries
    op.add_column('sleep_entries', sa.Column('source', sa.String(50), nullable=True, server_default='manual'))
    op.add_column('sleep_entries', sa.Column('external_id', sa.String(500), nullable=True))
    op.add_column('sleep_entries', sa.Column('synced_at', sa.DateTime(), nullable=True))
    
    # Exercise entries
    op.add_column('exercise_entries', sa.Column('source', sa.String(50), nullable=True, server_default='manual'))
    op.add_column('exercise_entries', sa.Column('external_id', sa.String(500), nullable=True))
    op.add_column('exercise_entries', sa.Column('synced_at', sa.DateTime(), nullable=True))
    
    # Vital signs
    op.add_column('vital_signs', sa.Column('source', sa.String(50), nullable=True, server_default='manual'))
    op.add_column('vital_signs', sa.Column('external_id', sa.String(500), nullable=True))
    op.add_column('vital_signs', sa.Column('synced_at', sa.DateTime(), nullable=True))
    
    # Body metrics
    op.add_column('body_metrics', sa.Column('source', sa.String(50), nullable=True, server_default='manual'))
    op.add_column('body_metrics', sa.Column('external_id', sa.String(500), nullable=True))
    op.add_column('body_metrics', sa.Column('synced_at', sa.DateTime(), nullable=True))
    
    # Chronic metrics
    op.add_column('chronic_metrics', sa.Column('source', sa.String(50), nullable=True, server_default='manual'))
    op.add_column('chronic_metrics', sa.Column('external_id', sa.String(500), nullable=True))
    op.add_column('chronic_metrics', sa.Column('synced_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove source tracking columns from existing tables
    op.drop_column('chronic_metrics', 'synced_at')
    op.drop_column('chronic_metrics', 'external_id')
    op.drop_column('chronic_metrics', 'source')
    
    op.drop_column('body_metrics', 'synced_at')
    op.drop_column('body_metrics', 'external_id')
    op.drop_column('body_metrics', 'source')
    
    op.drop_column('vital_signs', 'synced_at')
    op.drop_column('vital_signs', 'external_id')
    op.drop_column('vital_signs', 'source')
    
    op.drop_column('exercise_entries', 'synced_at')
    op.drop_column('exercise_entries', 'external_id')
    op.drop_column('exercise_entries', 'source')
    
    op.drop_column('sleep_entries', 'synced_at')
    op.drop_column('sleep_entries', 'external_id')
    op.drop_column('sleep_entries', 'source')
    
    op.drop_column('food_entries', 'synced_at')
    op.drop_column('food_entries', 'external_id')
    op.drop_column('food_entries', 'source')
    
    # Drop indexes and tables
    op.drop_index('ix_raw_sync_data_external')
    op.drop_index('ix_raw_sync_data_status')
    op.drop_table('raw_sync_data')
    
    op.drop_index('ix_user_connections_user_provider')
    op.drop_table('user_connections')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS syncdatatype')
    op.execute('DROP TYPE IF EXISTS syncstatus')
    op.execute('DROP TYPE IF EXISTS connectionstatus')
    op.execute('DROP TYPE IF EXISTS datasource')
