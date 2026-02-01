import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import uuid

from app.models.food_entry import FoodEntry
from app.models.sleep_entry import SleepEntry
from app.models.exercise_entry import ExerciseEntry
from app.models.vital_signs import VitalSigns
from app.models.body_metrics import BodyMetrics
from app.models.chronic_metrics import ChronicMetrics
from app.utils.enums import ExerciseIntensity


class FeatureEngineer:
    """Transform health data tables into a unified daily feature matrix for ML"""
    
    INTENSITY_MAP = {
        ExerciseIntensity.low: 1,
        ExerciseIntensity.moderate: 2,
        ExerciseIntensity.high: 3,
        ExerciseIntensity.very_high: 4,
    }
    
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
    
    async def build_daily_feature_matrix(
        self, 
        days: int = 60,
        end_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Build a feature matrix with one row per day containing all health metrics.
        
        Returns DataFrame with columns:
        - date
        - total_calories, total_protein_g, total_carbs_g, total_fats_g, total_sugar_g
        - sleep_hours, sleep_quality, awakenings
        - exercise_minutes, exercise_calories, exercise_intensity_avg
        - resting_hr, hrv, bp_systolic, bp_diastolic
        - weight_kg, body_fat_pct
        - blood_glucose_fasting, blood_glucose_post_meal
        """
        if end_date is None:
            end_date = date.today()
        
        start_date = end_date - timedelta(days=days)
        
        # Generate date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        df = pd.DataFrame({'date': date_range.date})
        
        # Fetch and merge all data
        nutrition_df = await self._get_nutrition_features(start_date, end_date)
        sleep_df = await self._get_sleep_features(start_date, end_date)
        exercise_df = await self._get_exercise_features(start_date, end_date)
        vitals_df = await self._get_vitals_features(start_date, end_date)
        body_df = await self._get_body_features(start_date, end_date)
        chronic_df = await self._get_chronic_features(start_date, end_date)
        
        # Merge all features
        df = df.merge(nutrition_df, on='date', how='left')
        df = df.merge(sleep_df, on='date', how='left')
        df = df.merge(exercise_df, on='date', how='left')
        df = df.merge(vitals_df, on='date', how='left')
        df = df.merge(body_df, on='date', how='left')
        df = df.merge(chronic_df, on='date', how='left')
        
        # Forward fill body metrics (measured less frequently)
        body_cols = ['weight_kg', 'body_fat_pct', 'bmi']
        df[body_cols] = df[body_cols].ffill()
        
        # Add derived features
        df = self._add_derived_features(df)
        
        return df
    
    async def _get_nutrition_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Aggregate daily nutrition"""
        query = select(FoodEntry).where(
            and_(
                FoodEntry.user_id == self.user_id,
                FoodEntry.date >= start_date,
                FoodEntry.date <= end_date
            )
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        if not entries:
            return pd.DataFrame(columns=['date', 'total_calories', 'total_protein_g', 
                                        'total_carbs_g', 'total_fats_g', 'total_sugar_g'])
        
        data = []
        for entry in entries:
            data.append({
                'date': entry.date,
                'calories': entry.calories,
                'protein_g': entry.protein_g,
                'carbs_g': entry.carbs_g,
                'fats_g': entry.fats_g,
                'sugar_g': entry.sugar_g,
            })
        
        df = pd.DataFrame(data)
        daily = df.groupby('date').agg({
            'calories': 'sum',
            'protein_g': 'sum',
            'carbs_g': 'sum',
            'fats_g': 'sum',
            'sugar_g': 'sum',
        }).reset_index()
        
        daily.columns = ['date', 'total_calories', 'total_protein_g', 
                        'total_carbs_g', 'total_fats_g', 'total_sugar_g']
        return daily
    
    async def _get_sleep_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get sleep features"""
        query = select(SleepEntry).where(
            and_(
                SleepEntry.user_id == self.user_id,
                SleepEntry.date >= start_date,
                SleepEntry.date <= end_date
            )
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        if not entries:
            return pd.DataFrame(columns=['date', 'sleep_hours', 'sleep_quality', 'awakenings'])
        
        data = [{
            'date': e.date,
            'sleep_hours': e.duration_hours,
            'sleep_quality': e.quality_score,
            'awakenings': e.awakenings or 0,
        } for e in entries]
        
        return pd.DataFrame(data)
    
    async def _get_exercise_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Aggregate daily exercise"""
        query = select(ExerciseEntry).where(
            and_(
                ExerciseEntry.user_id == self.user_id,
                ExerciseEntry.date >= start_date,
                ExerciseEntry.date <= end_date
            )
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        if not entries:
            return pd.DataFrame(columns=['date', 'exercise_minutes', 'exercise_calories', 
                                        'exercise_intensity_avg'])
        
        data = []
        for entry in entries:
            data.append({
                'date': entry.date,
                'duration': entry.duration_minutes,
                'calories': entry.calories_burned or 0,
                'intensity': self.INTENSITY_MAP.get(entry.intensity, 2),
            })
        
        df = pd.DataFrame(data)
        daily = df.groupby('date').agg({
            'duration': 'sum',
            'calories': 'sum',
            'intensity': 'mean',
        }).reset_index()
        
        daily.columns = ['date', 'exercise_minutes', 'exercise_calories', 'exercise_intensity_avg']
        return daily
    
    async def _get_vitals_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get vital signs (morning readings)"""
        query = select(VitalSigns).where(
            and_(
                VitalSigns.user_id == self.user_id,
                VitalSigns.date >= start_date,
                VitalSigns.date <= end_date
            )
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        if not entries:
            return pd.DataFrame(columns=['date', 'resting_hr', 'hrv', 'bp_systolic', 'bp_diastolic'])
        
        data = []
        for entry in entries:
            data.append({
                'date': entry.date,
                'resting_hr': entry.resting_heart_rate,
                'hrv': entry.hrv_ms,
                'bp_systolic': entry.blood_pressure_systolic,
                'bp_diastolic': entry.blood_pressure_diastolic,
            })
        
        df = pd.DataFrame(data)
        # Take first reading of the day (morning)
        daily = df.groupby('date').first().reset_index()
        return daily
    
    async def _get_body_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get body metrics"""
        query = select(BodyMetrics).where(
            and_(
                BodyMetrics.user_id == self.user_id,
                BodyMetrics.date >= start_date,
                BodyMetrics.date <= end_date
            )
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        if not entries:
            return pd.DataFrame(columns=['date', 'weight_kg', 'body_fat_pct', 'bmi'])
        
        data = [{
            'date': e.date,
            'weight_kg': e.weight_kg,
            'body_fat_pct': e.body_fat_pct,
            'bmi': e.bmi,
        } for e in entries]
        
        return pd.DataFrame(data)
    
    async def _get_chronic_features(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Get chronic health metrics (focus on glucose)"""
        from app.utils.enums import ChronicTimeOfDay, ConditionType
        
        query = select(ChronicMetrics).where(
            and_(
                ChronicMetrics.user_id == self.user_id,
                ChronicMetrics.date >= start_date,
                ChronicMetrics.date <= end_date,
                ChronicMetrics.condition_type == ConditionType.diabetes
            )
        )
        result = await self.db.execute(query)
        entries = result.scalars().all()
        
        if not entries:
            return pd.DataFrame(columns=['date', 'blood_glucose_fasting', 'blood_glucose_post_meal'])
        
        data = []
        for entry in entries:
            row = {'date': entry.date}
            if entry.time_of_day == ChronicTimeOfDay.fasting:
                row['blood_glucose_fasting'] = entry.blood_glucose_mgdl
            elif entry.time_of_day == ChronicTimeOfDay.post_meal:
                row['blood_glucose_post_meal'] = entry.blood_glucose_mgdl
            data.append(row)
        
        df = pd.DataFrame(data)
        # Aggregate by date
        daily = df.groupby('date').agg({
            col: 'first' for col in df.columns if col != 'date'
        }).reset_index()
        
        return daily
    
    def _add_derived_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add derived/computed features"""
        
        # Calorie ratio features
        if 'total_calories' in df.columns and 'total_protein_g' in df.columns:
            df['protein_ratio'] = (df['total_protein_g'] * 4) / df['total_calories'].replace(0, np.nan)
        
        # 7-day rolling averages for trend detection
        rolling_cols = ['sleep_hours', 'total_calories', 'resting_hr', 'exercise_minutes']
        for col in rolling_cols:
            if col in df.columns:
                df[f'{col}_7d_avg'] = df[col].rolling(window=7, min_periods=1).mean()
                df[f'{col}_deviation'] = df[col] - df[f'{col}_7d_avg']
        
        # Weight change over 7 days
        if 'weight_kg' in df.columns:
            df['weight_change_7d'] = df['weight_kg'].diff(periods=7)
        
        # Blood pressure combined metric
        if 'bp_systolic' in df.columns and 'bp_diastolic' in df.columns:
            df['bp_mean'] = (df['bp_systolic'] + 2 * df['bp_diastolic']) / 3
        
        return df
    
    async def get_user_baselines(self, days: int = 30) -> Dict[str, float]:
        """Calculate user's baseline values for each metric"""
        df = await self.build_daily_feature_matrix(days=days)
        
        baselines = {}
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            if col != 'date':
                values = df[col].dropna()
                if len(values) > 0:
                    baselines[col] = {
                        'mean': float(values.mean()),
                        'std': float(values.std()) if len(values) > 1 else 0,
                        'min': float(values.min()),
                        'max': float(values.max()),
                    }
        
        return baselines
