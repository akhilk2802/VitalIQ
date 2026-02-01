"""Add correlations table

Revision ID: 002
Revises: 001
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types for correlations
    correlation_type = postgresql.ENUM(
        'pearson', 'spearman', 'cross_correlation', 
        'granger_causality', 'mutual_information',
        name='correlationtype', 
        create_type=False
    )
    correlation_type.create(op.get_bind(), checkfirst=True)
    
    correlation_strength = postgresql.ENUM(
        'strong_positive', 'moderate_positive', 'weak_positive',
        'negligible', 'weak_negative', 'moderate_negative', 'strong_negative',
        name='correlationstrength',
        create_type=False
    )
    correlation_strength.create(op.get_bind(), checkfirst=True)
    
    causal_direction = postgresql.ENUM(
        'a_causes_b', 'b_causes_a', 'bidirectional', 'none',
        name='causaldirection',
        create_type=False
    )
    causal_direction.create(op.get_bind(), checkfirst=True)

    # Create correlations table
    op.create_table(
        'correlations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        
        # Metrics being correlated
        sa.Column('metric_a', sa.String(100), nullable=False),
        sa.Column('metric_b', sa.String(100), nullable=False),
        
        # Correlation details
        sa.Column('correlation_type', correlation_type, nullable=False),
        sa.Column('correlation_value', sa.Float(), nullable=False),
        sa.Column('strength', correlation_strength, nullable=False),
        
        # Statistical significance
        sa.Column('p_value', sa.Float(), nullable=True),
        sa.Column('is_significant', sa.Boolean(), nullable=False, server_default='false'),
        
        # Time lag
        sa.Column('lag_days', sa.Integer(), nullable=False, server_default='0'),
        
        # Granger causality specific
        sa.Column('granger_f_stat', sa.Float(), nullable=True),
        sa.Column('causal_direction', causal_direction, nullable=True),
        
        # Granularity
        sa.Column('granularity', sa.String(20), nullable=False, server_default='daily'),
        
        # Analysis period
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False),
        
        # AI-generated insight
        sa.Column('insight', sa.String(1000), nullable=True),
        sa.Column('recommendation', sa.String(500), nullable=True),
        
        # Population comparison
        sa.Column('population_avg', sa.Float(), nullable=True),
        sa.Column('percentile_rank', sa.Float(), nullable=True),
        
        # Metadata
        sa.Column('is_actionable', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for common queries
    op.create_index('ix_correlations_user_metrics', 'correlations', 
                    ['user_id', 'metric_a', 'metric_b'])
    op.create_index('ix_correlations_actionable', 'correlations', 
                    ['user_id', 'is_actionable'])


def downgrade() -> None:
    op.drop_index('ix_correlations_actionable')
    op.drop_index('ix_correlations_user_metrics')
    op.drop_table('correlations')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS causaldirection')
    op.execute('DROP TYPE IF EXISTS correlationstrength')
    op.execute('DROP TYPE IF EXISTS correlationtype')
