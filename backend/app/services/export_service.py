"""
Export Service

Handles exporting health data to CSV and PDF formats.
"""

import csv
import io
from typing import List, Dict, Optional, Any
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.sleep_entry import SleepEntry
from app.models.food_entry import FoodEntry
from app.models.exercise_entry import ExerciseEntry
from app.models.vital_signs import VitalSigns
from app.models.body_metrics import BodyMetrics
from app.models.chronic_metrics import ChronicMetrics
from app.models.anomaly import Anomaly


@dataclass
class ExportConfig:
    """Export configuration"""
    start_date: date
    end_date: date
    include_sleep: bool = True
    include_nutrition: bool = True
    include_exercise: bool = True
    include_vitals: bool = True
    include_body: bool = True
    include_chronic: bool = True
    include_anomalies: bool = True


class ExportService:
    """Service for exporting health data"""
    
    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.db = db
        self.user_id = user_id
    
    async def export_csv(
        self,
        config: ExportConfig,
        combined: bool = False
    ) -> Dict[str, str]:
        """
        Export data to CSV format.
        
        Args:
            config: Export configuration
            combined: If True, return single combined CSV; else separate files
        
        Returns:
            Dictionary mapping data type to CSV string
        """
        exports = {}
        
        if config.include_sleep:
            exports["sleep"] = await self._export_sleep_csv(config)
        
        if config.include_nutrition:
            exports["nutrition"] = await self._export_nutrition_csv(config)
        
        if config.include_exercise:
            exports["exercise"] = await self._export_exercise_csv(config)
        
        if config.include_vitals:
            exports["vitals"] = await self._export_vitals_csv(config)
        
        if config.include_body:
            exports["body"] = await self._export_body_csv(config)
        
        if config.include_chronic:
            exports["chronic"] = await self._export_chronic_csv(config)
        
        if config.include_anomalies:
            exports["anomalies"] = await self._export_anomalies_csv(config)
        
        if combined:
            return {"combined": self._combine_csvs(exports)}
        
        return exports
    
    async def _export_sleep_csv(self, config: ExportConfig) -> str:
        """Export sleep data to CSV"""
        result = await self.db.execute(
            select(SleepEntry)
            .where(and_(
                SleepEntry.user_id == self.user_id,
                SleepEntry.date >= config.start_date,
                SleepEntry.date <= config.end_date
            ))
            .order_by(SleepEntry.date)
        )
        entries = result.scalars().all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Date", "Duration (hours)", "Quality Score", 
            "Deep Sleep (min)", "REM Sleep (min)", "Awakenings",
            "Bedtime", "Wake Time", "Source"
        ])
        
        for e in entries:
            writer.writerow([
                e.date.isoformat(),
                e.duration_hours,
                e.quality_score,
                e.deep_sleep_minutes,
                e.rem_sleep_minutes,
                e.awakenings,
                e.bedtime.isoformat() if e.bedtime else "",
                e.wake_time.isoformat() if e.wake_time else "",
                e.source or "manual"
            ])
        
        return output.getvalue()
    
    async def _export_nutrition_csv(self, config: ExportConfig) -> str:
        """Export nutrition data to CSV"""
        result = await self.db.execute(
            select(FoodEntry)
            .where(and_(
                FoodEntry.user_id == self.user_id,
                FoodEntry.date >= config.start_date,
                FoodEntry.date <= config.end_date
            ))
            .order_by(FoodEntry.date)
        )
        entries = result.scalars().all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Date", "Meal Type", "Food Name", "Calories",
            "Protein (g)", "Carbs (g)", "Fats (g)", "Sugar (g)", "Fiber (g)",
            "Source"
        ])
        
        for e in entries:
            writer.writerow([
                e.date.isoformat(),
                e.meal_type.value if e.meal_type else "",
                e.food_name,
                e.calories,
                e.protein_g,
                e.carbs_g,
                e.fats_g,
                e.sugar_g,
                e.fiber_g,
                e.source or "manual"
            ])
        
        return output.getvalue()
    
    async def _export_exercise_csv(self, config: ExportConfig) -> str:
        """Export exercise data to CSV"""
        result = await self.db.execute(
            select(ExerciseEntry)
            .where(and_(
                ExerciseEntry.user_id == self.user_id,
                ExerciseEntry.date >= config.start_date,
                ExerciseEntry.date <= config.end_date
            ))
            .order_by(ExerciseEntry.date)
        )
        entries = result.scalars().all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Date", "Exercise Type", "Exercise Name", "Duration (min)",
            "Intensity", "Calories Burned", "Avg HR", "Max HR", "Source"
        ])
        
        for e in entries:
            writer.writerow([
                e.date.isoformat(),
                e.exercise_type.value if e.exercise_type else "",
                e.exercise_name,
                e.duration_minutes,
                e.intensity.value if e.intensity else "",
                e.calories_burned,
                e.heart_rate_avg,
                e.heart_rate_max,
                e.source or "manual"
            ])
        
        return output.getvalue()
    
    async def _export_vitals_csv(self, config: ExportConfig) -> str:
        """Export vitals data to CSV"""
        result = await self.db.execute(
            select(VitalSigns)
            .where(and_(
                VitalSigns.user_id == self.user_id,
                VitalSigns.date >= config.start_date,
                VitalSigns.date <= config.end_date
            ))
            .order_by(VitalSigns.date)
        )
        entries = result.scalars().all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Date", "Time of Day", "Resting HR", "HRV (ms)",
            "BP Systolic", "BP Diastolic", "SpO2 (%)", "Source"
        ])
        
        for e in entries:
            writer.writerow([
                e.date.isoformat(),
                e.time_of_day.value if e.time_of_day else "",
                e.resting_heart_rate,
                e.hrv_ms,
                e.blood_pressure_systolic,
                e.blood_pressure_diastolic,
                e.spo2,
                e.source or "manual"
            ])
        
        return output.getvalue()
    
    async def _export_body_csv(self, config: ExportConfig) -> str:
        """Export body metrics to CSV"""
        result = await self.db.execute(
            select(BodyMetrics)
            .where(and_(
                BodyMetrics.user_id == self.user_id,
                BodyMetrics.date >= config.start_date,
                BodyMetrics.date <= config.end_date
            ))
            .order_by(BodyMetrics.date)
        )
        entries = result.scalars().all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Date", "Weight (kg)", "Body Fat (%)", "BMI", "Source"
        ])
        
        for e in entries:
            writer.writerow([
                e.date.isoformat(),
                e.weight_kg,
                e.body_fat_pct,
                e.bmi,
                e.source or "manual"
            ])
        
        return output.getvalue()
    
    async def _export_chronic_csv(self, config: ExportConfig) -> str:
        """Export chronic metrics to CSV"""
        result = await self.db.execute(
            select(ChronicMetrics)
            .where(and_(
                ChronicMetrics.user_id == self.user_id,
                ChronicMetrics.date >= config.start_date,
                ChronicMetrics.date <= config.end_date
            ))
            .order_by(ChronicMetrics.date)
        )
        entries = result.scalars().all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Date", "Time of Day", "Condition", "Blood Glucose (mg/dL)",
            "Cholesterol Total", "LDL", "HDL", "Triglycerides", "Source"
        ])
        
        for e in entries:
            writer.writerow([
                e.date.isoformat(),
                e.time_of_day.value if e.time_of_day else "",
                e.condition_type.value if e.condition_type else "",
                e.blood_glucose_mgdl,
                e.cholesterol_total,
                e.cholesterol_ldl,
                e.cholesterol_hdl,
                e.triglycerides,
                e.source or "manual"
            ])
        
        return output.getvalue()
    
    async def _export_anomalies_csv(self, config: ExportConfig) -> str:
        """Export anomalies to CSV"""
        result = await self.db.execute(
            select(Anomaly)
            .where(and_(
                Anomaly.user_id == self.user_id,
                Anomaly.date >= config.start_date,
                Anomaly.date <= config.end_date
            ))
            .order_by(Anomaly.date.desc())
        )
        anomalies = result.scalars().all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Date", "Metric", "Value", "Baseline", "Severity",
            "Detector", "Score", "Explanation"
        ])
        
        for a in anomalies:
            writer.writerow([
                a.date.isoformat(),
                a.metric_name,
                a.metric_value,
                a.baseline_value,
                a.severity.value if a.severity else "",
                a.detector_type.value if a.detector_type else "",
                a.anomaly_score,
                a.explanation or ""
            ])
        
        return output.getvalue()
    
    def _combine_csvs(self, exports: Dict[str, str]) -> str:
        """Combine multiple CSVs into one with section headers"""
        combined = io.StringIO()
        
        for data_type, csv_content in exports.items():
            if csv_content.strip():
                combined.write(f"\n=== {data_type.upper()} ===\n")
                combined.write(csv_content)
                combined.write("\n")
        
        return combined.getvalue()
    
    async def generate_summary_data(self, config: ExportConfig) -> Dict[str, Any]:
        """Generate summary data for PDF report"""
        summary = {
            "period": {
                "start": config.start_date.isoformat(),
                "end": config.end_date.isoformat(),
                "days": (config.end_date - config.start_date).days + 1
            },
            "sections": {}
        }
        
        # Sleep summary
        if config.include_sleep:
            sleep_result = await self.db.execute(
                select(SleepEntry)
                .where(and_(
                    SleepEntry.user_id == self.user_id,
                    SleepEntry.date >= config.start_date,
                    SleepEntry.date <= config.end_date
                ))
            )
            sleep_entries = sleep_result.scalars().all()
            
            if sleep_entries:
                durations = [e.duration_hours for e in sleep_entries if e.duration_hours]
                qualities = [e.quality_score for e in sleep_entries if e.quality_score]
                
                summary["sections"]["sleep"] = {
                    "total_nights": len(sleep_entries),
                    "avg_duration": round(sum(durations) / len(durations), 2) if durations else 0,
                    "avg_quality": round(sum(qualities) / len(qualities), 1) if qualities else 0,
                    "best_night": max(qualities) if qualities else 0,
                    "worst_night": min(qualities) if qualities else 0
                }
        
        # Exercise summary
        if config.include_exercise:
            exercise_result = await self.db.execute(
                select(ExerciseEntry)
                .where(and_(
                    ExerciseEntry.user_id == self.user_id,
                    ExerciseEntry.date >= config.start_date,
                    ExerciseEntry.date <= config.end_date
                ))
            )
            exercise_entries = exercise_result.scalars().all()
            
            if exercise_entries:
                total_minutes = sum(e.duration_minutes or 0 for e in exercise_entries)
                total_calories = sum(e.calories_burned or 0 for e in exercise_entries)
                active_days = len(set(e.date for e in exercise_entries))
                
                summary["sections"]["exercise"] = {
                    "total_workouts": len(exercise_entries),
                    "active_days": active_days,
                    "total_minutes": total_minutes,
                    "total_calories": total_calories,
                    "avg_workout_duration": round(total_minutes / len(exercise_entries), 1)
                }
        
        # Nutrition summary
        if config.include_nutrition:
            food_result = await self.db.execute(
                select(FoodEntry)
                .where(and_(
                    FoodEntry.user_id == self.user_id,
                    FoodEntry.date >= config.start_date,
                    FoodEntry.date <= config.end_date
                ))
            )
            food_entries = food_result.scalars().all()
            
            if food_entries:
                days = (config.end_date - config.start_date).days + 1
                total_calories = sum(e.calories or 0 for e in food_entries)
                total_protein = sum(e.protein_g or 0 for e in food_entries)
                
                summary["sections"]["nutrition"] = {
                    "total_meals": len(food_entries),
                    "avg_daily_calories": round(total_calories / days, 0),
                    "avg_daily_protein": round(total_protein / days, 1)
                }
        
        # Anomaly summary
        if config.include_anomalies:
            anomaly_result = await self.db.execute(
                select(Anomaly)
                .where(and_(
                    Anomaly.user_id == self.user_id,
                    Anomaly.date >= config.start_date,
                    Anomaly.date <= config.end_date
                ))
            )
            anomalies = anomaly_result.scalars().all()
            
            if anomalies:
                from collections import Counter
                severity_counts = Counter(a.severity.value for a in anomalies if a.severity)
                metric_counts = Counter(a.metric_name for a in anomalies)
                
                summary["sections"]["anomalies"] = {
                    "total": len(anomalies),
                    "by_severity": dict(severity_counts),
                    "most_common_metric": metric_counts.most_common(1)[0][0] if metric_counts else None
                }
        
        return summary
