"""
Enhanced Mock Data Generator with Persona-Based Profiles

Generates 150 days of realistic health data with embedded patterns for:
- Active Athlete: High exercise, good sleep, high protein, low resting HR
- Poor Sleeper: 4-6hr sleep, high sugar, elevated HR, poor recovery
- Pre-diabetic: Glucose spikes, sugar cravings, moderate activity
- Stress-prone: HRV drops, sleep disruption, comfort eating
- Healthy Balanced: Baseline reference, moderate everything
"""

import random
import uuid
import math
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import numpy as np

from app.utils.enums import (
    MealType, ExerciseType, ExerciseIntensity, 
    TimeOfDay, ChronicTimeOfDay, ConditionType, DataSource
)


class PersonaType(str, Enum):
    """User persona types for synthetic data generation"""
    active_athlete = "active_athlete"
    poor_sleeper = "poor_sleeper"
    pre_diabetic = "pre_diabetic"
    stress_prone = "stress_prone"
    healthy_balanced = "healthy_balanced"


class PersonaConfig:
    """Configuration parameters for each persona type"""
    
    CONFIGS = {
        PersonaType.active_athlete: {
            "name": "Active Athlete",
            "base_weight": (65, 75),
            "base_rhr": (48, 58),
            "base_hrv": (55, 75),
            "base_sleep_hours": (7.5, 8.5),
            "base_calories": (2200, 2800),
            "base_glucose": (80, 95),
            "exercise_frequency": 0.85,
            "exercise_intensity_bias": ExerciseIntensity.high,
            "protein_multiplier": 1.4,
            "sugar_multiplier": 0.6,
            "sleep_quality_base": 75,
            "anomaly_rate": 0.05,
        },
        PersonaType.poor_sleeper: {
            "name": "Poor Sleeper",
            "base_weight": (70, 85),
            "base_rhr": (68, 80),
            "base_hrv": (25, 40),
            "base_sleep_hours": (4.5, 6.0),
            "base_calories": (1900, 2400),
            "base_glucose": (95, 110),
            "exercise_frequency": 0.4,
            "exercise_intensity_bias": ExerciseIntensity.low,
            "protein_multiplier": 0.8,
            "sugar_multiplier": 1.5,
            "sleep_quality_base": 35,
            "anomaly_rate": 0.15,
        },
        PersonaType.pre_diabetic: {
            "name": "Pre-Diabetic",
            "base_weight": (80, 95),
            "base_rhr": (70, 82),
            "base_hrv": (30, 45),
            "base_sleep_hours": (6.0, 7.5),
            "base_calories": (2000, 2600),
            "base_glucose": (105, 125),
            "exercise_frequency": 0.45,
            "exercise_intensity_bias": ExerciseIntensity.moderate,
            "protein_multiplier": 0.9,
            "sugar_multiplier": 1.3,
            "sleep_quality_base": 55,
            "anomaly_rate": 0.12,
        },
        PersonaType.stress_prone: {
            "name": "Stress-Prone",
            "base_weight": (65, 80),
            "base_rhr": (65, 78),
            "base_hrv": (28, 42),
            "base_sleep_hours": (5.5, 7.0),
            "base_calories": (1800, 2500),
            "base_glucose": (90, 105),
            "exercise_frequency": 0.5,
            "exercise_intensity_bias": ExerciseIntensity.moderate,
            "protein_multiplier": 0.9,
            "sugar_multiplier": 1.2,
            "sleep_quality_base": 45,
            "anomaly_rate": 0.1,
            "stress_cycle_days": 7,
        },
        PersonaType.healthy_balanced: {
            "name": "Healthy Balanced",
            "base_weight": (65, 78),
            "base_rhr": (58, 68),
            "base_hrv": (45, 60),
            "base_sleep_hours": (7.0, 8.0),
            "base_calories": (1900, 2300),
            "base_glucose": (85, 100),
            "exercise_frequency": 0.65,
            "exercise_intensity_bias": ExerciseIntensity.moderate,
            "protein_multiplier": 1.0,
            "sugar_multiplier": 1.0,
            "sleep_quality_base": 70,
            "anomaly_rate": 0.06,
        },
    }
    
    @classmethod
    def get(cls, persona: PersonaType) -> dict:
        return cls.CONFIGS.get(persona, cls.CONFIGS[PersonaType.healthy_balanced])


class PersonaMockDataGenerator:
    """Generate realistic mock health data based on persona profiles."""
    
    def __init__(
        self, 
        user_id: uuid.UUID, 
        persona: PersonaType = PersonaType.healthy_balanced,
        days: int = 150
    ):
        self.user_id = user_id
        self.persona = persona
        self.days = days
        self.start_date = date.today() - timedelta(days=days)
        self.config = PersonaConfig.get(persona)
        
        self._init_baselines()
        self._state_history: Dict[int, Dict[str, float]] = {}
        self._precompute_daily_states()
    
    def _init_baselines(self):
        cfg = self.config
        self.base_weight = random.uniform(*cfg["base_weight"])
        self.base_rhr = random.uniform(*cfg["base_rhr"])
        self.base_hrv = random.uniform(*cfg["base_hrv"])
        self.base_sleep_hours = random.uniform(*cfg["base_sleep_hours"])
        self.base_calories = random.randint(*cfg["base_calories"])
        self.base_glucose = random.uniform(*cfg["base_glucose"])
        self.exercise_frequency = cfg["exercise_frequency"]
        self.protein_multiplier = cfg["protein_multiplier"]
        self.sugar_multiplier = cfg["sugar_multiplier"]
        self.sleep_quality_base = cfg["sleep_quality_base"]
        self.anomaly_rate = cfg["anomaly_rate"]
        num_anomalies = max(3, int(self.days * self.anomaly_rate))
        self.anomaly_days = set(random.sample(range(self.days), num_anomalies))
    
    def _precompute_daily_states(self):
        for day in range(self.days):
            prev_state = self._state_history.get(day - 1, {})
            state = {}
            
            if self.persona == PersonaType.stress_prone:
                cycle_days = self.config.get("stress_cycle_days", 7)
                stress_phase = (day % cycle_days) / cycle_days
                state["stress_level"] = 0.3 + 0.5 * math.sin(stress_phase * 2 * math.pi)
            else:
                state["stress_level"] = random.uniform(0.1, 0.4)
            
            state["exercised"] = random.random() < self.exercise_frequency
            state["exercise_intensity"] = random.uniform(0.5, 1.0) if state["exercised"] else 0
            
            prev_exercise = prev_state.get("exercise_intensity", 0.5)
            prev_stress = prev_state.get("stress_level", 0.3)
            sleep_modifier = (prev_exercise * 15) - (prev_stress * 20)
            state["sleep_quality"] = max(20, min(100, self.sleep_quality_base + sleep_modifier + random.gauss(0, 8)))
            
            quality_ratio = state["sleep_quality"] / 100
            state["sleep_hours"] = self.base_sleep_hours * (0.7 + 0.3 * quality_ratio) + random.gauss(0, 0.3)
            state["sleep_hours"] = max(3.5, min(10, state["sleep_hours"]))
            
            prev_sleep = prev_state.get("sleep_hours", self.base_sleep_hours)
            state["sugar_craving"] = 0.3 + (6 - prev_sleep) * 0.15 if prev_sleep < 6 else random.uniform(0, 0.2)
            state["sugar_multiplier"] = self.sugar_multiplier * (1 + state["sugar_craving"])
            
            hrv_sleep_effect = (state["sleep_quality"] - 50) * 0.3
            hrv_stress_effect = -state["stress_level"] * 15
            state["hrv"] = max(15, self.base_hrv + hrv_sleep_effect + hrv_stress_effect + random.gauss(0, 5))
            
            rhr_sleep_effect = -(state["sleep_quality"] - 50) * 0.1
            rhr_exercise_effect = -state["exercise_intensity"] * 3 if state["exercised"] else 2
            rhr_stress_effect = state["stress_level"] * 8
            state["rhr"] = max(45, self.base_rhr + rhr_sleep_effect + rhr_exercise_effect + rhr_stress_effect + random.gauss(0, 3))
            
            sugar_effect = state["sugar_craving"] * 15
            exercise_glucose_effect = -state["exercise_intensity"] * 8 if state["exercised"] else 0
            state["glucose_base"] = self.base_glucose + sugar_effect + exercise_glucose_effect + random.gauss(0, 5)
            state["is_anomaly"] = day in self.anomaly_days
            
            self._state_history[day] = state
    
    def _get_date(self, day_offset: int) -> date:
        return self.start_date + timedelta(days=day_offset)
    
    def _get_state(self, day: int) -> dict:
        return self._state_history.get(day, {})
    
    def generate_food_entries(self, source: DataSource = DataSource.manual) -> List[dict]:
        entries = []
        foods = {
            MealType.breakfast: [
                ("Oatmeal with berries", 350, 12, 55, 8, 15, 6),
                ("Eggs and toast", 400, 20, 30, 18, 3, 2),
                ("Greek yogurt parfait", 300, 15, 40, 8, 20, 3),
                ("Avocado toast", 380, 10, 35, 22, 2, 8),
                ("Protein smoothie", 320, 25, 45, 5, 15, 4),
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
                ("Banana", 105, 1, 27, 0, 14, 3),
                ("Yogurt", 150, 12, 18, 3, 12, 0),
            ],
        }
        high_sugar_snacks = [
            ("Cookie", 200, 2, 28, 9, 18, 1),
            ("Candy bar", 250, 3, 35, 12, 28, 1),
            ("Soda", 150, 0, 40, 0, 38, 0),
            ("Pastry", 320, 4, 42, 16, 22, 1),
            ("Ice cream", 280, 4, 32, 15, 24, 0),
        ]
        
        for day in range(self.days):
            current_date = self._get_date(day)
            state = self._get_state(day)
            is_anomaly = state.get("is_anomaly", False)
            sugar_mult = state.get("sugar_multiplier", 1.0)
            
            for meal_type in [MealType.breakfast, MealType.lunch, MealType.dinner]:
                if random.random() < 0.95:
                    food = random.choice(foods[meal_type])
                    multiplier = random.uniform(1.8, 2.5) if is_anomaly and meal_type == MealType.dinner else 1.0
                    protein_adj = self.protein_multiplier
                    entries.append({
                        "user_id": self.user_id, "date": current_date, "meal_type": meal_type,
                        "food_name": food[0], "calories": round(food[1] * multiplier),
                        "protein_g": round(food[2] * multiplier * protein_adj, 1),
                        "carbs_g": round(food[3] * multiplier, 1), "fats_g": round(food[4] * multiplier, 1),
                        "sugar_g": round(food[5] * multiplier * sugar_mult, 1), "fiber_g": round(food[6] * multiplier, 1),
                        "source": source.value,
                        "external_id": f"food_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                    })
            
            num_snacks = 1 if random.random() < 0.6 else 0
            if state.get("sugar_craving", 0) > 0.3:
                num_snacks += 1 if random.random() < 0.7 else 0
            for _ in range(num_snacks):
                snack = random.choice(high_sugar_snacks if state.get("sugar_craving", 0) > 0.4 and random.random() < 0.6 else foods[MealType.snack])
                entries.append({
                    "user_id": self.user_id, "date": current_date, "meal_type": MealType.snack,
                    "food_name": snack[0], "calories": round(snack[1] * sugar_mult),
                    "protein_g": round(snack[2], 1), "carbs_g": round(snack[3] * sugar_mult, 1),
                    "fats_g": round(snack[4], 1), "sugar_g": round(snack[5] * sugar_mult, 1),
                    "fiber_g": round(snack[6], 1), "source": source.value,
                    "external_id": f"food_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                })
        return entries
    
    def generate_sleep_entries(self, source: DataSource = DataSource.manual) -> List[dict]:
        entries = []
        for day in range(self.days):
            current_date = self._get_date(day)
            state = self._get_state(day)
            is_anomaly = state.get("is_anomaly", False)
            duration = random.uniform(3.0, 4.5) if is_anomaly else state.get("sleep_hours", self.base_sleep_hours)
            quality = random.randint(15, 30) if is_anomaly else state.get("sleep_quality", self.sleep_quality_base)
            deep_pct = 0.15 + (quality / 100) * 0.10
            rem_pct = 0.18 + (quality / 100) * 0.10
            bedtime_hour = random.randint(23, 25) % 24 if self.persona == PersonaType.poor_sleeper else random.randint(21, 23)
            bedtime = datetime.combine(current_date - timedelta(days=1), datetime.min.time().replace(hour=bedtime_hour, minute=random.randint(0, 59)))
            wake_time = bedtime + timedelta(hours=duration)
            awakenings = random.randint(4, 8) if is_anomaly or quality < 40 else random.randint(0, 2)
            entries.append({
                "user_id": self.user_id, "date": current_date, "bedtime": bedtime, "wake_time": wake_time,
                "duration_hours": round(duration, 2), "quality_score": int(quality),
                "deep_sleep_minutes": int(duration * 60 * deep_pct), "rem_sleep_minutes": int(duration * 60 * rem_pct),
                "awakenings": awakenings, "source": source.value,
                "external_id": f"sleep_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
            })
        return entries
    
    def generate_exercise_entries(self, source: DataSource = DataSource.manual) -> List[dict]:
        entries = []
        exercises = {
            ExerciseType.cardio: [("Running", 30, 60, 300, 550), ("Cycling", 40, 75, 350, 600), ("Walking", 30, 60, 120, 200)],
            ExerciseType.strength: [("Weight Training", 45, 75, 200, 350), ("Bodyweight Exercises", 30, 50, 150, 280)],
            ExerciseType.flexibility: [("Yoga", 30, 60, 100, 200), ("Stretching", 15, 30, 50, 100)],
        }
        type_weights = {ExerciseType.cardio: 0.5, ExerciseType.strength: 0.4, ExerciseType.flexibility: 0.1} if self.persona == PersonaType.active_athlete else {ExerciseType.cardio: 0.4, ExerciseType.strength: 0.35, ExerciseType.flexibility: 0.25}
        
        for day in range(self.days):
            current_date = self._get_date(day)
            state = self._get_state(day)
            if state.get("exercised", False):
                exercise_type = random.choices(list(type_weights.keys()), weights=list(type_weights.values()))[0]
                exercise = random.choice(exercises[exercise_type])
                intensity_factor = state.get("exercise_intensity", 0.7)
                duration = int(random.randint(exercise[1], exercise[2]) * (0.7 + intensity_factor * 0.5))
                calories = int(random.randint(exercise[3], exercise[4]) * intensity_factor)
                intensity = ExerciseIntensity.high if intensity_factor > 0.75 else ExerciseIntensity.moderate if intensity_factor > 0.5 else ExerciseIntensity.low
                base_workout_hr = 100 + int(intensity_factor * 60) - (10 if self.persona == PersonaType.active_athlete else 0)
                entries.append({
                    "user_id": self.user_id, "date": current_date, "exercise_type": exercise_type,
                    "exercise_name": exercise[0], "duration_minutes": duration, "intensity": intensity,
                    "calories_burned": calories, "heart_rate_avg": min(180, base_workout_hr + random.randint(-5, 15)),
                    "heart_rate_max": min(200, base_workout_hr + random.randint(20, 40)), "source": source.value,
                    "external_id": f"exercise_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                })
        return entries
    
    def generate_vital_signs(self, source: DataSource = DataSource.manual) -> List[dict]:
        entries = []
        for day in range(self.days):
            current_date = self._get_date(day)
            state = self._get_state(day)
            is_anomaly = state.get("is_anomaly", False)
            rhr = state.get("rhr", self.base_rhr) + (random.randint(10, 20) if is_anomaly else 0)
            hrv = state.get("hrv", self.base_hrv) - (random.randint(10, 15) if is_anomaly else 0)
            stress = state.get("stress_level", 0.3)
            sleep_quality = state.get("sleep_quality", 70)
            bp_sys = int(115 + stress * 15 - (sleep_quality - 50) * 0.2 + random.gauss(0, 5))
            bp_dia = int(70 + stress * 8 + random.gauss(0, 3))
            entries.append({
                "user_id": self.user_id, "date": current_date, "time_of_day": TimeOfDay.morning,
                "resting_heart_rate": max(45, int(rhr)), "hrv_ms": max(15, int(hrv)),
                "blood_pressure_systolic": max(90, min(160, bp_sys)),
                "blood_pressure_diastolic": max(55, min(100, bp_dia)), "spo2": random.randint(96, 100),
                "source": source.value, "external_id": f"vitals_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
            })
        return entries
    
    def generate_body_metrics(self, source: DataSource = DataSource.manual) -> List[dict]:
        entries = []
        current_weight = self.base_weight
        weight_trend = -0.02 if self.persona == PersonaType.active_athlete else 0.03 if self.persona == PersonaType.pre_diabetic else 0
        for day in range(0, self.days, 7):
            current_date = self._get_date(day)
            current_weight = max(self.base_weight - 5, min(self.base_weight + 5, current_weight + weight_trend + random.gauss(0, 0.3)))
            body_fat = random.uniform(12, 18) if self.persona == PersonaType.active_athlete else random.uniform(25, 32) if self.persona == PersonaType.pre_diabetic else random.uniform(18, 26)
            entries.append({
                "user_id": self.user_id, "date": current_date, "weight_kg": round(current_weight, 1),
                "body_fat_pct": round(body_fat, 1), "bmi": round(current_weight / (1.75 ** 2), 1),
                "source": source.value, "external_id": f"body_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
            })
        return entries
    
    def generate_chronic_metrics(self, condition: ConditionType = ConditionType.diabetes, source: DataSource = DataSource.manual) -> List[dict]:
        entries = []
        for day in range(self.days):
            current_date = self._get_date(day)
            state = self._get_state(day)
            is_anomaly = state.get("is_anomaly", False)
            if condition == ConditionType.diabetes:
                base_glucose = state.get("glucose_base", self.base_glucose)
                glucose = base_glucose + (random.uniform(30, 60) if is_anomaly else random.gauss(0, 5))
                entries.append({
                    "user_id": self.user_id, "date": current_date, "time_of_day": ChronicTimeOfDay.fasting,
                    "condition_type": ConditionType.diabetes, "blood_glucose_mgdl": round(max(70, glucose), 1),
                    "source": source.value, "external_id": f"chronic_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                })
                if random.random() < 0.5:
                    sugar_mult = state.get("sugar_multiplier", 1.0)
                    post_meal_glucose = glucose + 30 + (sugar_mult - 1.0) * 40 + random.uniform(10, 30)
                    entries.append({
                        "user_id": self.user_id, "date": current_date, "time_of_day": ChronicTimeOfDay.post_meal,
                        "condition_type": ConditionType.diabetes, "blood_glucose_mgdl": round(post_meal_glucose, 1),
                        "source": source.value, "external_id": f"chronic_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                    })
            elif condition == ConditionType.heart and day % 30 == 0:
                entries.append({
                    "user_id": self.user_id, "date": current_date, "time_of_day": ChronicTimeOfDay.fasting,
                    "condition_type": ConditionType.heart, "cholesterol_total": random.uniform(170, 230),
                    "cholesterol_ldl": random.uniform(85, 140), "cholesterol_hdl": random.uniform(40, 70),
                    "triglycerides": random.uniform(90, 180), "source": source.value,
                    "external_id": f"chronic_{uuid.uuid4().hex[:12]}" if source != DataSource.manual else None,
                })
        return entries
    
    def generate_all(self, use_staging: bool = False, source: DataSource = DataSource.manual) -> dict:
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
        return {"sleep": [], "workouts": [], "body": [], "vitals": {}, "meals": []}
    
    def get_embedded_patterns(self) -> List[str]:
        patterns = ["Sleep quality affects next-day HRV and resting HR", "Exercise improves same-day sleep quality",
                    "Low sleep triggers next-day sugar cravings", "Sugar intake correlates with post-meal glucose spikes"]
        if self.persona == PersonaType.active_athlete:
            patterns.extend(["High exercise frequency with low resting HR", "High protein intake"])
        elif self.persona == PersonaType.poor_sleeper:
            patterns.extend(["Chronic sleep deprivation with elevated HR", "High sugar consumption from cravings"])
        elif self.persona == PersonaType.pre_diabetic:
            patterns.extend(["Elevated fasting glucose", "High post-meal glucose spikes"])
        elif self.persona == PersonaType.stress_prone:
            patterns.extend(["Weekly stress cycle affecting HRV and sleep", "Comfort eating patterns"])
        return patterns


# Backwards compatibility
MockDataGenerator = PersonaMockDataGenerator
