import random
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
import numpy as np

from app.utils.enums import (
    MealType, ExerciseType, ExerciseIntensity, 
    TimeOfDay, ChronicTimeOfDay, ConditionType, DataSource
)


class MockDataGenerator:
    """Generate realistic mock health data with intentional anomalies"""
    
    def __init__(self, user_id: uuid.UUID, days: int = 60):
        self.user_id = user_id
        self.days = days
        self.start_date = date.today() - timedelta(days=days)
        
        # User baselines (randomized per user)
        self.base_weight = random.uniform(60, 90)
        self.base_rhr = random.randint(55, 75)
        self.base_hrv = random.randint(35, 55)
        self.base_sleep_hours = random.uniform(6.5, 8)
        self.base_calories = random.randint(1800, 2400)
        self.base_glucose = random.uniform(85, 105)  # fasting glucose
        
        # Anomaly injection settings
        self.anomaly_days = self._select_anomaly_days()
    
    def _select_anomaly_days(self) -> List[int]:
        """Select random days for anomaly injection"""
        num_anomalies = max(3, self.days // 15)  # ~1 anomaly per 2 weeks
        return random.sample(range(self.days), num_anomalies)
    
    def _is_anomaly_day(self, day_offset: int) -> bool:
        return day_offset in self.anomaly_days
    
    def _get_date(self, day_offset: int) -> date:
        return self.start_date + timedelta(days=day_offset)
    
    def generate_food_entries(self, source: DataSource = DataSource.manual) -> List[dict]:
        """Generate food/nutrition entries"""
        entries = []
        
        foods = {
            MealType.breakfast: [
                ("Oatmeal with berries", 350, 12, 55, 8, 15, 6),
                ("Eggs and toast", 400, 20, 30, 18, 3, 2),
                ("Greek yogurt parfait", 300, 15, 40, 8, 20, 3),
                ("Avocado toast", 380, 10, 35, 22, 2, 8),
                ("Protein smoothie", 320, 25, 45, 5, 25, 4),
            ],
            MealType.lunch: [
                ("Grilled chicken salad", 450, 40, 20, 22, 5, 6),
                ("Turkey sandwich", 520, 35, 45, 18, 8, 4),
                ("Quinoa bowl", 480, 18, 65, 15, 4, 8),
                ("Salmon with rice", 550, 38, 50, 18, 2, 2),
                ("Vegetable stir-fry", 400, 15, 55, 12, 8, 6),
            ],
            MealType.dinner: [
                ("Steak with vegetables", 600, 45, 25, 35, 4, 5),
                ("Pasta with marinara", 650, 20, 85, 18, 12, 6),
                ("Grilled fish with salad", 450, 40, 15, 22, 3, 4),
                ("Chicken curry with rice", 580, 35, 60, 20, 6, 4),
                ("Vegetarian burrito bowl", 520, 18, 70, 16, 5, 12),
            ],
            MealType.snack: [
                ("Apple with peanut butter", 250, 7, 30, 12, 18, 4),
                ("Protein bar", 220, 20, 25, 8, 10, 3),
                ("Mixed nuts", 200, 6, 8, 18, 2, 2),
                ("Cheese and crackers", 180, 8, 15, 10, 2, 1),
                ("Banana", 105, 1, 27, 0, 14, 3),
            ],
        }
        
        for day in range(self.days):
            current_date = self._get_date(day)
            is_anomaly = self._is_anomaly_day(day)
            
            # Generate meals for the day
            for meal_type in [MealType.breakfast, MealType.lunch, MealType.dinner]:
                if random.random() < 0.95:  # 95% chance of having each meal
                    food = random.choice(foods[meal_type])
                    multiplier = 1.0
                    
                    if is_anomaly and meal_type == MealType.dinner:
                        # Anomaly: very high calorie dinner
                        multiplier = random.uniform(1.8, 2.5)
                    
                    entries.append({
                        "user_id": self.user_id,
                        "date": current_date,
                        "meal_type": meal_type,
                        "food_name": food[0],
                        "calories": food[1] * multiplier,
                        "protein_g": food[2] * multiplier,
                        "carbs_g": food[3] * multiplier,
                        "fats_g": food[4] * multiplier,
                        "sugar_g": food[5] * multiplier,
                        "fiber_g": food[6] * multiplier,
                        "source": source.value,
                        "external_id": f"food_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                    })
            
            # Random snacks
            if random.random() < 0.7:
                snack = random.choice(foods[MealType.snack])
                entries.append({
                    "user_id": self.user_id,
                    "date": current_date,
                    "meal_type": MealType.snack,
                    "food_name": snack[0],
                    "calories": snack[1],
                    "protein_g": snack[2],
                    "carbs_g": snack[3],
                    "fats_g": snack[4],
                    "sugar_g": snack[5],
                    "fiber_g": snack[6],
                    "source": source.value,
                    "external_id": f"food_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                })
        
        return entries
    
    def generate_sleep_entries(self, source: DataSource = DataSource.manual) -> List[dict]:
        """Generate sleep entries"""
        entries = []
        
        for day in range(self.days):
            current_date = self._get_date(day)
            is_anomaly = self._is_anomaly_day(day)
            
            # Base sleep with daily variation
            if is_anomaly:
                # Anomaly: very poor sleep
                duration = random.uniform(3.5, 4.5)
                quality = random.randint(20, 35)
            else:
                duration = self.base_sleep_hours + random.gauss(0, 0.5)
                duration = max(5, min(10, duration))
                quality = int(50 + (duration - 5) * 10 + random.gauss(0, 10))
                quality = max(30, min(100, quality))
            
            # Calculate bedtime and wake time
            bedtime_hour = random.randint(21, 23)
            bedtime = datetime.combine(current_date - timedelta(days=1), 
                                      datetime.min.time().replace(hour=bedtime_hour, minute=random.randint(0, 59)))
            wake_time = bedtime + timedelta(hours=duration)
            
            entries.append({
                "user_id": self.user_id,
                "date": current_date,
                "bedtime": bedtime,
                "wake_time": wake_time,
                "duration_hours": round(duration, 2),
                "quality_score": quality,
                "deep_sleep_minutes": int(duration * 60 * random.uniform(0.15, 0.25)),
                "rem_sleep_minutes": int(duration * 60 * random.uniform(0.20, 0.30)),
                "awakenings": random.randint(0, 3) if not is_anomaly else random.randint(5, 10),
                "source": source.value,
                "external_id": f"sleep_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
            })
        
        return entries
    
    def generate_exercise_entries(self, source: DataSource = DataSource.manual) -> List[dict]:
        """Generate exercise entries"""
        entries = []
        
        exercises = {
            ExerciseType.cardio: [
                ("Running", 30, 45, 300, 450),
                ("Cycling", 45, 60, 350, 500),
                ("Swimming", 30, 45, 250, 400),
                ("Walking", 30, 60, 150, 250),
            ],
            ExerciseType.strength: [
                ("Weight Training", 45, 60, 200, 300),
                ("Bodyweight Exercises", 30, 45, 150, 250),
                ("CrossFit", 45, 60, 350, 500),
            ],
            ExerciseType.flexibility: [
                ("Yoga", 30, 60, 100, 200),
                ("Stretching", 15, 30, 50, 100),
                ("Pilates", 45, 60, 150, 250),
            ],
        }
        
        for day in range(self.days):
            current_date = self._get_date(day)
            
            # ~70% chance of exercising on any given day
            if random.random() < 0.7:
                exercise_type = random.choice(list(exercises.keys()))
                exercise = random.choice(exercises[exercise_type])
                
                duration = random.randint(exercise[1], exercise[2])
                calories = random.randint(exercise[3], exercise[4])
                intensity = random.choice([ExerciseIntensity.moderate, ExerciseIntensity.high])
                
                entries.append({
                    "user_id": self.user_id,
                    "date": current_date,
                    "exercise_type": exercise_type,
                    "exercise_name": exercise[0],
                    "duration_minutes": duration,
                    "intensity": intensity,
                    "calories_burned": calories,
                    "heart_rate_avg": random.randint(120, 160),
                    "heart_rate_max": random.randint(160, 185),
                    "source": source.value,
                    "external_id": f"exercise_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                })
        
        return entries
    
    def generate_vital_signs(self, source: DataSource = DataSource.manual) -> List[dict]:
        """Generate vital signs entries"""
        entries = []
        
        for day in range(self.days):
            current_date = self._get_date(day)
            is_anomaly = self._is_anomaly_day(day)
            
            # Morning vitals
            if is_anomaly:
                # Anomaly: elevated heart rate
                rhr = self.base_rhr + random.randint(15, 25)
                hrv = self.base_hrv - random.randint(10, 20)
                bp_sys = random.randint(135, 150)
            else:
                rhr = self.base_rhr + random.randint(-5, 5)
                hrv = self.base_hrv + random.randint(-8, 8)
                bp_sys = random.randint(110, 125)
            
            entries.append({
                "user_id": self.user_id,
                "date": current_date,
                "time_of_day": TimeOfDay.morning,
                "resting_heart_rate": max(45, rhr),
                "hrv_ms": max(15, hrv),
                "blood_pressure_systolic": bp_sys,
                "blood_pressure_diastolic": random.randint(65, 85),
                "spo2": random.randint(96, 100),
                "source": source.value,
                "external_id": f"vitals_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
            })
        
        return entries
    
    def generate_body_metrics(self, source: DataSource = DataSource.manual) -> List[dict]:
        """Generate body metrics entries (weekly)"""
        entries = []
        
        current_weight = self.base_weight
        
        for day in range(0, self.days, 7):  # Weekly measurements
            current_date = self._get_date(day)
            
            # Slight weight fluctuation
            current_weight += random.gauss(0, 0.3)
            current_weight = max(self.base_weight - 5, min(self.base_weight + 5, current_weight))
            
            entries.append({
                "user_id": self.user_id,
                "date": current_date,
                "weight_kg": round(current_weight, 1),
                "body_fat_pct": round(random.uniform(15, 25), 1),
                "bmi": round(current_weight / (1.75 ** 2), 1),  # Assuming 175cm height
                "source": source.value,
                "external_id": f"body_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
            })
        
        return entries
    
    def generate_chronic_metrics(self, condition: ConditionType = ConditionType.diabetes, source: DataSource = DataSource.manual) -> List[dict]:
        """Generate chronic health metrics"""
        entries = []
        
        for day in range(self.days):
            current_date = self._get_date(day)
            is_anomaly = self._is_anomaly_day(day)
            
            if condition == ConditionType.diabetes:
                # Fasting glucose
                if is_anomaly:
                    glucose = self.base_glucose + random.uniform(40, 70)  # Anomaly: high glucose
                else:
                    glucose = self.base_glucose + random.gauss(0, 8)
                
                entries.append({
                    "user_id": self.user_id,
                    "date": current_date,
                    "time_of_day": ChronicTimeOfDay.fasting,
                    "condition_type": ConditionType.diabetes,
                    "blood_glucose_mgdl": round(glucose, 1),
                    "source": source.value,
                    "external_id": f"chronic_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                })
                
                # Post-meal glucose (sometimes)
                if random.random() < 0.5:
                    post_meal_glucose = glucose + random.uniform(30, 60)
                    entries.append({
                        "user_id": self.user_id,
                        "date": current_date,
                        "time_of_day": ChronicTimeOfDay.post_meal,
                        "condition_type": ConditionType.diabetes,
                        "blood_glucose_mgdl": round(post_meal_glucose, 1),
                        "source": source.value,
                        "external_id": f"chronic_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                    })
            
            elif condition == ConditionType.heart:
                # Monthly cholesterol (less frequent)
                if day % 30 == 0:
                    entries.append({
                        "user_id": self.user_id,
                        "date": current_date,
                        "time_of_day": ChronicTimeOfDay.fasting,
                        "condition_type": ConditionType.heart,
                        "cholesterol_total": random.uniform(180, 220),
                        "cholesterol_ldl": random.uniform(90, 130),
                        "cholesterol_hdl": random.uniform(45, 65),
                        "triglycerides": random.uniform(100, 170),
                        "source": source.value,
                        "external_id": f"chronic_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                    })
        
        return entries
    
    def generate_all(self, use_staging: bool = False, source: DataSource = DataSource.manual) -> dict:
        """
        Generate all mock data.
        
        Args:
            use_staging: If True, generate Vital-like raw payloads for staging pipeline
            source: The data source to use (manual, fitbit, etc.)
        """
        if use_staging:
            return self.generate_all_for_staging(source)
        
        return {
            "food_entries": self.generate_food_entries(source=source),
            "sleep_entries": self.generate_sleep_entries(source=source),
            "exercise_entries": self.generate_exercise_entries(source=source),
            "vital_signs": self.generate_vital_signs(source=source),
            "body_metrics": self.generate_body_metrics(source=source),
            "chronic_metrics": self.generate_chronic_metrics(source=source),
        }
    
    def generate_all_for_staging(self, source: DataSource = DataSource.fitbit) -> dict:
        """
        Generate mock data in Vital API format for the staging pipeline.
        
        This simulates what real external data would look like when ingested
        from Vital's API, allowing testing of the full normalization pipeline.
        """
        return {
            "sleep": self._generate_vital_sleep_data(source),
            "workouts": self._generate_vital_workout_data(source),
            "body": self._generate_vital_body_data(source),
            "vitals": self._generate_vital_vitals_data(source),
            "meals": self._generate_vital_meal_data(source),
        }
    
    def _generate_vital_sleep_data(self, source: DataSource) -> List[Dict[str, Any]]:
        """Generate sleep data in Vital API format."""
        data = []
        source_name = source.value.replace("_", " ").title()
        
        for day in range(self.days):
            current_date = self._get_date(day)
            is_anomaly = self._is_anomaly_day(day)
            
            if is_anomaly:
                duration = random.uniform(3.5, 4.5)
                efficiency = random.uniform(0.60, 0.75)
            else:
                duration = self.base_sleep_hours + random.gauss(0, 0.5)
                duration = max(5, min(10, duration))
                efficiency = random.uniform(0.85, 0.95)
            
            bedtime_hour = random.randint(21, 23)
            duration_seconds = int(duration * 3600)
            
            data.append({
                "id": f"sleep_{uuid.uuid4().hex[:12]}",
                "calendar_date": current_date.isoformat(),
                "bedtime_start": f"{current_date - timedelta(days=1)}T{bedtime_hour:02d}:{random.randint(0,59):02d}:00+00:00",
                "bedtime_stop": f"{current_date}T{(bedtime_hour + int(duration)) % 24:02d}:{random.randint(0,59):02d}:00+00:00",
                "duration_in_bed": duration_seconds,
                "duration_asleep": int(duration_seconds * efficiency),
                "sleep_efficiency": efficiency,
                "deep_sleep_duration": int(duration_seconds * random.uniform(0.15, 0.25)),
                "rem_sleep_duration": int(duration_seconds * random.uniform(0.18, 0.28)),
                "light_sleep_duration": int(duration_seconds * random.uniform(0.40, 0.55)),
                "awake_duration": int(duration_seconds * (1 - efficiency)),
                "wake_up_count": random.randint(0, 3) if not is_anomaly else random.randint(5, 10),
                "source": {"name": source_name, "slug": source.value}
            })
        
        return data
    
    def _generate_vital_workout_data(self, source: DataSource) -> List[Dict[str, Any]]:
        """Generate workout data in Vital API format."""
        data = []
        source_name = source.value.replace("_", " ").title()
        
        workout_types = ["running", "cycling", "strength_training", "yoga", "walking", "swimming"]
        
        for day in range(self.days):
            current_date = self._get_date(day)
            
            if random.random() < 0.7:
                workout_type = random.choice(workout_types)
                duration_minutes = random.randint(20, 90)
                start_hour = random.randint(6, 19)
                
                data.append({
                    "id": f"workout_{uuid.uuid4().hex[:12]}",
                    "calendar_date": current_date.isoformat(),
                    "title": workout_type.replace("_", " ").title(),
                    "sport": workout_type,
                    "start_time": f"{current_date}T{start_hour:02d}:{random.randint(0,59):02d}:00+00:00",
                    "end_time": f"{current_date}T{(start_hour + duration_minutes // 60) % 24:02d}:{random.randint(0,59):02d}:00+00:00",
                    "duration_seconds": duration_minutes * 60,
                    "calories": random.randint(150, 600),
                    "distance_meters": random.randint(1000, 10000) if workout_type in ["running", "cycling", "walking"] else None,
                    "average_hr": random.randint(100, 160),
                    "max_hr": random.randint(140, 190),
                    "source": {"name": source_name, "slug": source.value}
                })
        
        return data
    
    def _generate_vital_body_data(self, source: DataSource) -> List[Dict[str, Any]]:
        """Generate body metrics data in Vital API format."""
        data = []
        source_name = source.value.replace("_", " ").title()
        current_weight = self.base_weight
        
        for day in range(0, self.days, 7):
            current_date = self._get_date(day)
            current_weight += random.gauss(0, 0.3)
            current_weight = max(self.base_weight - 5, min(self.base_weight + 5, current_weight))
            
            data.append({
                "id": f"body_{uuid.uuid4().hex[:12]}",
                "calendar_date": current_date.isoformat(),
                "weight_kg": round(current_weight, 1),
                "body_fat_percentage": round(random.uniform(15, 30), 1),
                "bmi": round(current_weight / (1.75 ** 2), 1),
                "source": {"name": source_name, "slug": source.value}
            })
        
        return data
    
    def _generate_vital_vitals_data(self, source: DataSource) -> Dict[str, List[Dict[str, Any]]]:
        """Generate vital signs data in Vital API format (time series)."""
        heartrate = []
        hrv = []
        spo2 = []
        source_name = source.value.replace("_", " ").title()
        
        for day in range(self.days):
            current_date = self._get_date(day)
            is_anomaly = self._is_anomaly_day(day)
            
            if is_anomaly:
                rhr = self.base_rhr + random.randint(15, 25)
                hrv_val = self.base_hrv - random.randint(10, 20)
            else:
                rhr = self.base_rhr + random.randint(-5, 5)
                hrv_val = self.base_hrv + random.randint(-8, 8)
            
            heartrate.append({
                "id": f"hr_{uuid.uuid4().hex[:12]}",
                "timestamp": f"{current_date}T07:00:00+00:00",
                "value": max(45, rhr),
                "type": "resting",
                "source": {"name": source_name, "slug": source.value}
            })
            
            hrv.append({
                "id": f"hrv_{uuid.uuid4().hex[:12]}",
                "timestamp": f"{current_date}T07:00:00+00:00",
                "value": max(15, hrv_val),
                "source": {"name": source_name, "slug": source.value}
            })
            
            spo2.append({
                "id": f"spo2_{uuid.uuid4().hex[:12]}",
                "timestamp": f"{current_date}T07:00:00+00:00",
                "value": random.randint(95, 100),
                "source": {"name": source_name, "slug": source.value}
            })
        
        return {"heartrate": heartrate, "hrv": hrv, "blood_oxygen": spo2}
    
    def _generate_vital_meal_data(self, source: DataSource) -> List[Dict[str, Any]]:
        """Generate meal/nutrition data in Vital API format."""
        data = []
        source_name = source.value.replace("_", " ").title()
        
        meal_types = ["breakfast", "lunch", "dinner", "snack"]
        
        for day in range(self.days):
            current_date = self._get_date(day)
            is_anomaly = self._is_anomaly_day(day)
            
            for meal_type in meal_types:
                if meal_type == "snack" and random.random() < 0.3:
                    continue
                if random.random() < 0.05:
                    continue
                
                base_calories = {
                    "breakfast": random.randint(300, 500),
                    "lunch": random.randint(400, 700),
                    "dinner": random.randint(500, 900),
                    "snack": random.randint(100, 300)
                }[meal_type]
                
                if is_anomaly and meal_type == "dinner":
                    base_calories = int(base_calories * random.uniform(1.8, 2.5))
                
                data.append({
                    "id": f"meal_{uuid.uuid4().hex[:12]}",
                    "calendar_date": current_date.isoformat(),
                    "meal_type": meal_type,
                    "name": f"{meal_type.title()} - {current_date.isoformat()}",
                    "calories": base_calories,
                    "protein_g": round(base_calories * random.uniform(0.1, 0.3) / 4, 1),
                    "carbs_g": round(base_calories * random.uniform(0.3, 0.5) / 4, 1),
                    "fat_g": round(base_calories * random.uniform(0.2, 0.4) / 9, 1),
                    "fiber_g": round(random.uniform(2, 10), 1),
                    "sugar_g": round(random.uniform(5, 30), 1),
                    "sodium_mg": round(random.uniform(200, 1000), 0),
                    "source": {"name": source_name, "slug": source.value}
                })
        
        return data
