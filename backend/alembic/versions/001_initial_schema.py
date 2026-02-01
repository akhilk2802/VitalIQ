"""Initial schema with all health metric tables

Revision ID: 001
Revises: 
Create Date: 2026-02-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    meal_type = postgresql.ENUM('breakfast', 'lunch', 'dinner', 'snack', name='mealtype', create_type=False)
    exercise_type = postgresql.ENUM('cardio', 'strength', 'flexibility', 'sports', 'other', name='exercisetype', create_type=False)
    exercise_intensity = postgresql.ENUM('low', 'moderate', 'high', 'very_high', name='exerciseintensity', create_type=False)
    time_of_day = postgresql.ENUM('morning', 'afternoon', 'evening', 'night', name='timeofday', create_type=False)
    chronic_time_of_day = postgresql.ENUM('fasting', 'pre_meal', 'post_meal', 'bedtime', 'other', name='chronictimeofday', create_type=False)
    condition_type = postgresql.ENUM('diabetes', 'hypertension', 'heart', 'other', name='conditiontype', create_type=False)
    detector_type = postgresql.ENUM('zscore', 'isolation_forest', 'ensemble', name='detectortype', create_type=False)
    severity = postgresql.ENUM('low', 'medium', 'high', name='severity', create_type=False)
    
    # Create enums
    meal_type.create(op.get_bind(), checkfirst=True)
    exercise_type.create(op.get_bind(), checkfirst=True)
    exercise_intensity.create(op.get_bind(), checkfirst=True)
    time_of_day.create(op.get_bind(), checkfirst=True)
    chronic_time_of_day.create(op.get_bind(), checkfirst=True)
    condition_type.create(op.get_bind(), checkfirst=True)
    detector_type.create(op.get_bind(), checkfirst=True)
    severity.create(op.get_bind(), checkfirst=True)

    # Users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Food entries table
    op.create_table(
        'food_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('meal_type', meal_type, nullable=False),
        sa.Column('food_name', sa.String(255), nullable=False),
        sa.Column('calories', sa.Float(), nullable=False),
        sa.Column('protein_g', sa.Float(), nullable=False, server_default='0'),
        sa.Column('carbs_g', sa.Float(), nullable=False, server_default='0'),
        sa.Column('fats_g', sa.Float(), nullable=False, server_default='0'),
        sa.Column('sugar_g', sa.Float(), nullable=False, server_default='0'),
        sa.Column('fiber_g', sa.Float(), nullable=True),
        sa.Column('sodium_mg', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Sleep entries table
    op.create_table(
        'sleep_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('bedtime', sa.DateTime(), nullable=False),
        sa.Column('wake_time', sa.DateTime(), nullable=False),
        sa.Column('duration_hours', sa.Float(), nullable=False),
        sa.Column('quality_score', sa.Integer(), nullable=False),
        sa.Column('deep_sleep_minutes', sa.Integer(), nullable=True),
        sa.Column('rem_sleep_minutes', sa.Integer(), nullable=True),
        sa.Column('awakenings', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Exercise entries table
    op.create_table(
        'exercise_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('exercise_type', exercise_type, nullable=False),
        sa.Column('exercise_name', sa.String(255), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('intensity', exercise_intensity, nullable=False),
        sa.Column('calories_burned', sa.Integer(), nullable=True),
        sa.Column('heart_rate_avg', sa.Integer(), nullable=True),
        sa.Column('heart_rate_max', sa.Integer(), nullable=True),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('sets', sa.Integer(), nullable=True),
        sa.Column('reps', sa.Integer(), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Vital signs table
    op.create_table(
        'vital_signs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('time_of_day', time_of_day, nullable=False),
        sa.Column('resting_heart_rate', sa.Integer(), nullable=True),
        sa.Column('hrv_ms', sa.Integer(), nullable=True),
        sa.Column('blood_pressure_systolic', sa.Integer(), nullable=True),
        sa.Column('blood_pressure_diastolic', sa.Integer(), nullable=True),
        sa.Column('respiratory_rate', sa.Integer(), nullable=True),
        sa.Column('body_temperature', sa.Float(), nullable=True),
        sa.Column('spo2', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Body metrics table
    op.create_table(
        'body_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('body_fat_pct', sa.Float(), nullable=True),
        sa.Column('muscle_mass_kg', sa.Float(), nullable=True),
        sa.Column('bmi', sa.Float(), nullable=True),
        sa.Column('waist_cm', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Chronic metrics table
    op.create_table(
        'chronic_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('time_of_day', chronic_time_of_day, nullable=False),
        sa.Column('condition_type', condition_type, nullable=False),
        sa.Column('blood_glucose_mgdl', sa.Float(), nullable=True),
        sa.Column('insulin_units', sa.Float(), nullable=True),
        sa.Column('hba1c_pct', sa.Float(), nullable=True),
        sa.Column('cholesterol_total', sa.Float(), nullable=True),
        sa.Column('cholesterol_ldl', sa.Float(), nullable=True),
        sa.Column('cholesterol_hdl', sa.Float(), nullable=True),
        sa.Column('triglycerides', sa.Float(), nullable=True),
        sa.Column('medication_taken', sa.String(500), nullable=True),
        sa.Column('symptoms', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Anomalies table
    op.create_table(
        'anomalies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('source_table', sa.String(100), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('baseline_value', sa.Float(), nullable=False),
        sa.Column('detector_type', detector_type, nullable=False),
        sa.Column('severity', severity, nullable=False),
        sa.Column('anomaly_score', sa.Float(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('anomalies')
    op.drop_table('chronic_metrics')
    op.drop_table('body_metrics')
    op.drop_table('vital_signs')
    op.drop_table('exercise_entries')
    op.drop_table('sleep_entries')
    op.drop_table('food_entries')
    op.drop_table('users')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS severity')
    op.execute('DROP TYPE IF EXISTS detectortype')
    op.execute('DROP TYPE IF EXISTS conditiontype')
    op.execute('DROP TYPE IF EXISTS chronictimeofday')
    op.execute('DROP TYPE IF EXISTS timeofday')
    op.execute('DROP TYPE IF EXISTS exerciseintensity')
    op.execute('DROP TYPE IF EXISTS exercisetype')
    op.execute('DROP TYPE IF EXISTS mealtype')
