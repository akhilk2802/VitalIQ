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


class CorrelationType(str, Enum):
    pearson = "pearson"
    spearman = "spearman"
    cross_correlation = "cross_correlation"
    granger_causality = "granger_causality"
    mutual_information = "mutual_information"


class CorrelationStrength(str, Enum):
    strong_positive = "strong_positive"      # r > 0.7
    moderate_positive = "moderate_positive"  # 0.4 < r <= 0.7
    weak_positive = "weak_positive"          # 0.2 < r <= 0.4
    negligible = "negligible"                # -0.2 <= r <= 0.2
    weak_negative = "weak_negative"          # -0.4 <= r < -0.2
    moderate_negative = "moderate_negative"  # -0.7 <= r < -0.4
    strong_negative = "strong_negative"      # r < -0.7


class CausalDirection(str, Enum):
    a_causes_b = "a_causes_b"
    b_causes_a = "b_causes_a"
    bidirectional = "bidirectional"
    none = "none"


# Integration-related enums
class DataSource(str, Enum):
    manual = "manual"
    google_fit = "google_fit"
    fitbit = "fitbit"
    garmin = "garmin"
    oura = "oura"
    myfitnesspal = "myfitnesspal"
    apple_health = "apple_health"
    whoop = "whoop"
    withings = "withings"
    polar = "polar"
    strava = "strava"


class ConnectionStatus(str, Enum):
    pending = "pending"
    connected = "connected"
    disconnected = "disconnected"
    error = "error"


class SyncStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class SyncDataType(str, Enum):
    sleep = "sleep"
    activity = "activity"
    nutrition = "nutrition"
    body = "body"
    vitals = "vitals"
    workout = "workout"


# RAG-related enums
class KnowledgeSourceType(str, Enum):
    curated = "curated"
    pubmed = "pubmed"
    medlineplus = "medlineplus"


class HistoryEntityType(str, Enum):
    anomaly = "anomaly"
    correlation = "correlation"
    insight = "insight"
    chat_message = "chat_message"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
