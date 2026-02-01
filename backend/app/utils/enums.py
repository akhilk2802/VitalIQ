from enum import Enum


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class ExerciseType(str, Enum):
    cardio = "cardio"
    strength = "strength"
    flexibility = "flexibility"
    sports = "sports"
    other = "other"


class ExerciseIntensity(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    very_high = "very_high"


class TimeOfDay(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"
    night = "night"


class ChronicTimeOfDay(str, Enum):
    fasting = "fasting"
    pre_meal = "pre_meal"
    post_meal = "post_meal"
    bedtime = "bedtime"
    other = "other"


class ConditionType(str, Enum):
    diabetes = "diabetes"
    hypertension = "hypertension"
    heart = "heart"
    other = "other"


class DetectorType(str, Enum):
    zscore = "zscore"
    isolation_forest = "isolation_forest"
    ensemble = "ensemble"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
