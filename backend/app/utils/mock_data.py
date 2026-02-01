import random
import uuid
from datetime import date, datetime, timedelta
from typing import List, Optional
import numpy as np

from app.utils.enums import (
    MealType, ExerciseType, ExerciseIntensity, 
    TimeOfDay, ChronicTimeOfDay, ConditionType
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
    
    def generate_food_entries(self) -> List[dict]:
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
                })
        
        return entries
    
    def generate_sleep_entries(self) -> List[dict]:
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
            })
        
        return entries
    
    def generate_exercise_entries(self) -> List[dict]:
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
                })
        
        return entries
    
    def generate_vital_signs(self) -> List[dict]:
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
            })
        
        return entries
    
    def generate_body_metrics(self) -> List[dict]:
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
            })
        
        return entries
    
    def generate_chronic_metrics(self, condition: ConditionType = ConditionType.diabetes) -> List[dict]:
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
                    })
        
        return entries
    
    def generate_all(self) -> dict:
        """Generate all mock data"""
        return {
            "food_entries": self.generate_food_entries(),
            "sleep_entries": self.generate_sleep_entries(),
            "exercise_entries": self.generate_exercise_entries(),
            "vital_signs": self.generate_vital_signs(),
            "body_metrics": self.generate_body_metrics(),
            "chronic_metrics": self.generate_chronic_metrics(),
        }
