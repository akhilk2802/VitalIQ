"""
Vital API Client Wrapper

Provides a unified interface to interact with Vital API for health data aggregation.
Supports both real API calls and mock mode for development/testing.
"""
import uuid
import httpx
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from app.config import settings
from app.utils.enums import DataSource


@dataclass
class VitalUser:
    """Vital user representation"""
    user_id: str
    client_user_id: str
    team_id: str
    connected_sources: List[str]


@dataclass
class VitalLinkResponse:
    """Response from creating a link token"""
    link_token: str
    link_url: str
    expires_at: datetime


class VitalClient:
    """
    Vital API Client with mock mode support.
    
    In mock mode, returns simulated data for development and testing.
    In production mode, makes actual API calls to Vital.
    """
    
    BASE_URL = "https://api.tryvital.io"
    SANDBOX_URL = "https://api.sandbox.tryvital.io"
    
    # Supported providers via Vital
    SUPPORTED_PROVIDERS = [
        DataSource.google_fit,
        DataSource.fitbit,
        DataSource.garmin,
        DataSource.oura,
        DataSource.myfitnesspal,
        DataSource.whoop,
        DataSource.withings,
        DataSource.polar,
        DataSource.strava,
    ]
    
    def __init__(self, mock_mode: bool = True):
        """
        Initialize the Vital client.
        
        Args:
            mock_mode: If True, return simulated data instead of making API calls
        """
        self.mock_mode = mock_mode
        self.api_key = settings.VITAL_API_KEY
        self.environment = getattr(settings, 'VITAL_ENVIRONMENT', 'sandbox')
        self.base_url = self.SANDBOX_URL if self.environment == 'sandbox' else self.BASE_URL
        
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get API headers"""
        return {
            "x-vital-api-key": self.api_key,
            "Content-Type": "application/json",
        }
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=30.0
            )
        return self._client
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # =========================================================================
    # User Management
    # =========================================================================
    
    async def create_user(self, client_user_id: str) -> VitalUser:
        """
        Create a Vital user linked to our internal user ID.
        
        Args:
            client_user_id: Our internal user UUID
        """
        if self.mock_mode:
            return VitalUser(
                user_id=f"vital_{uuid.uuid4().hex[:12]}",
                client_user_id=client_user_id,
                team_id="mock_team_001",
                connected_sources=[]
            )
        
        client = await self.get_client()
        response = await client.post("/v2/user", json={
            "client_user_id": client_user_id
        })
        response.raise_for_status()
        data = response.json()
        
        return VitalUser(
            user_id=data["user_id"],
            client_user_id=data["client_user_id"],
            team_id=data["team_id"],
            connected_sources=data.get("connected_sources", [])
        )
    
    async def get_user(self, vital_user_id: str) -> Optional[VitalUser]:
        """Get a Vital user by ID"""
        if self.mock_mode:
            return VitalUser(
                user_id=vital_user_id,
                client_user_id=f"user_{uuid.uuid4().hex[:8]}",
                team_id="mock_team_001",
                connected_sources=["fitbit", "google_fit"]
            )
        
        client = await self.get_client()
        response = await client.get(f"/v2/user/{vital_user_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        
        return VitalUser(
            user_id=data["user_id"],
            client_user_id=data["client_user_id"],
            team_id=data["team_id"],
            connected_sources=data.get("connected_sources", [])
        )
    
    # =========================================================================
    # Link Management (OAuth flow)
    # =========================================================================
    
    async def create_link_token(
        self, 
        vital_user_id: str, 
        provider: DataSource,
        redirect_url: Optional[str] = None
    ) -> VitalLinkResponse:
        """
        Create a link token for connecting a provider.
        
        Args:
            vital_user_id: Vital's user ID
            provider: The data source provider to connect
            redirect_url: URL to redirect after OAuth completion
        """
        if self.mock_mode:
            return VitalLinkResponse(
                link_token=f"mock_link_{uuid.uuid4().hex}",
                link_url=f"https://link.tryvital.io/mock?token={uuid.uuid4().hex}",
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
        
        client = await self.get_client()
        payload = {
            "user_id": vital_user_id,
            "provider": provider.value,
        }
        if redirect_url:
            payload["redirect_url"] = redirect_url
        
        response = await client.post("/v2/link/token", json=payload)
        response.raise_for_status()
        data = response.json()
        
        return VitalLinkResponse(
            link_token=data["link_token"],
            link_url=data["link_url"],
            expires_at=datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        )
    
    # =========================================================================
    # Data Fetching
    # =========================================================================
    
    async def get_sleep(
        self, 
        vital_user_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Fetch sleep data for a user within date range"""
        if self.mock_mode:
            return self._generate_mock_sleep(start_date, end_date)
        
        client = await self.get_client()
        response = await client.get(
            f"/v2/summary/sleep/{vital_user_id}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        response.raise_for_status()
        return response.json().get("sleep", [])
    
    async def get_activity(
        self, 
        vital_user_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Fetch activity/workout data for a user within date range"""
        if self.mock_mode:
            return self._generate_mock_activity(start_date, end_date)
        
        client = await self.get_client()
        response = await client.get(
            f"/v2/summary/activity/{vital_user_id}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        response.raise_for_status()
        return response.json().get("activity", [])
    
    async def get_workouts(
        self, 
        vital_user_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Fetch workout data for a user within date range"""
        if self.mock_mode:
            return self._generate_mock_workouts(start_date, end_date)
        
        client = await self.get_client()
        response = await client.get(
            f"/v2/summary/workouts/{vital_user_id}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        response.raise_for_status()
        return response.json().get("workouts", [])
    
    async def get_body(
        self, 
        vital_user_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Fetch body metrics data for a user within date range"""
        if self.mock_mode:
            return self._generate_mock_body(start_date, end_date)
        
        client = await self.get_client()
        response = await client.get(
            f"/v2/summary/body/{vital_user_id}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        response.raise_for_status()
        return response.json().get("body", [])
    
    async def get_vitals(
        self, 
        vital_user_id: str, 
        start_date: date, 
        end_date: date
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch vital signs (heart rate, HRV, etc.) for a user"""
        if self.mock_mode:
            return self._generate_mock_vitals(start_date, end_date)
        
        client = await self.get_client()
        
        # Fetch multiple vital types
        vitals = {}
        for vital_type in ["heartrate", "hrv", "blood_oxygen"]:
            response = await client.get(
                f"/v2/timeseries/{vital_user_id}/{vital_type}",
                params={
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )
            if response.status_code == 200:
                vitals[vital_type] = response.json().get(vital_type, [])
        
        return vitals
    
    async def get_meal(
        self, 
        vital_user_id: str, 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Fetch meal/nutrition data for a user (from MyFitnessPal, etc.)"""
        if self.mock_mode:
            return self._generate_mock_meals(start_date, end_date)
        
        client = await self.get_client()
        response = await client.get(
            f"/v2/summary/meal/{vital_user_id}",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        response.raise_for_status()
        return response.json().get("meal", [])
    
    # =========================================================================
    # Mock Data Generators (for development/testing)
    # =========================================================================
    
    def _generate_mock_sleep(self, start_date: date, end_date: date) -> List[Dict]:
        """Generate mock sleep data resembling Vital API response"""
        import random
        data = []
        current = start_date
        
        while current <= end_date:
            bedtime_hour = random.randint(21, 23)
            duration_seconds = random.randint(5*3600, 9*3600)  # 5-9 hours
            
            data.append({
                "id": f"sleep_{uuid.uuid4().hex[:12]}",
                "calendar_date": current.isoformat(),
                "bedtime_start": f"{current}T{bedtime_hour:02d}:{random.randint(0,59):02d}:00+00:00",
                "bedtime_stop": f"{current + timedelta(days=1)}T{(bedtime_hour + duration_seconds//3600) % 24:02d}:{random.randint(0,59):02d}:00+00:00",
                "duration_in_bed": duration_seconds,
                "duration_asleep": int(duration_seconds * random.uniform(0.85, 0.95)),
                "sleep_efficiency": random.uniform(0.80, 0.95),
                "deep_sleep_duration": int(duration_seconds * random.uniform(0.15, 0.25)),
                "rem_sleep_duration": int(duration_seconds * random.uniform(0.18, 0.28)),
                "light_sleep_duration": int(duration_seconds * random.uniform(0.40, 0.55)),
                "awake_duration": int(duration_seconds * random.uniform(0.02, 0.10)),
                "wake_up_count": random.randint(0, 5),
                "source": {
                    "name": random.choice(["Fitbit", "Oura", "Garmin"]),
                    "slug": random.choice(["fitbit", "oura", "garmin"])
                }
            })
            current += timedelta(days=1)
        
        return data
    
    def _generate_mock_activity(self, start_date: date, end_date: date) -> List[Dict]:
        """Generate mock activity data"""
        import random
        data = []
        current = start_date
        
        while current <= end_date:
            data.append({
                "id": f"activity_{uuid.uuid4().hex[:12]}",
                "calendar_date": current.isoformat(),
                "steps": random.randint(3000, 15000),
                "distance_meters": random.randint(2000, 12000),
                "calories_active": random.randint(150, 600),
                "calories_total": random.randint(1800, 3000),
                "floors_climbed": random.randint(0, 30),
                "active_minutes": random.randint(20, 120),
                "source": {
                    "name": random.choice(["Fitbit", "Google Fit", "Garmin"]),
                    "slug": random.choice(["fitbit", "google_fit", "garmin"])
                }
            })
            current += timedelta(days=1)
        
        return data
    
    def _generate_mock_workouts(self, start_date: date, end_date: date) -> List[Dict]:
        """Generate mock workout data"""
        import random
        data = []
        current = start_date
        
        workout_types = ["running", "cycling", "swimming", "strength_training", "yoga", "walking"]
        
        while current <= end_date:
            # ~70% chance of workout on any day
            if random.random() < 0.7:
                workout_type = random.choice(workout_types)
                duration_minutes = random.randint(20, 90)
                
                data.append({
                    "id": f"workout_{uuid.uuid4().hex[:12]}",
                    "calendar_date": current.isoformat(),
                    "title": workout_type.replace("_", " ").title(),
                    "sport": workout_type,
                    "start_time": f"{current}T{random.randint(6,19):02d}:{random.randint(0,59):02d}:00+00:00",
                    "end_time": f"{current}T{random.randint(7,21):02d}:{random.randint(0,59):02d}:00+00:00",
                    "duration_seconds": duration_minutes * 60,
                    "calories": random.randint(150, 600),
                    "distance_meters": random.randint(0, 10000) if workout_type in ["running", "cycling", "walking"] else None,
                    "average_hr": random.randint(100, 160),
                    "max_hr": random.randint(140, 190),
                    "source": {
                        "name": random.choice(["Fitbit", "Strava", "Garmin"]),
                        "slug": random.choice(["fitbit", "strava", "garmin"])
                    }
                })
            current += timedelta(days=1)
        
        return data
    
    def _generate_mock_body(self, start_date: date, end_date: date) -> List[Dict]:
        """Generate mock body metrics data"""
        import random
        data = []
        current = start_date
        base_weight = random.uniform(60, 90)
        
        while current <= end_date:
            # Weekly body measurements
            if (current - start_date).days % 7 == 0:
                data.append({
                    "id": f"body_{uuid.uuid4().hex[:12]}",
                    "calendar_date": current.isoformat(),
                    "weight_kg": round(base_weight + random.gauss(0, 0.5), 1),
                    "body_fat_percentage": round(random.uniform(15, 30), 1),
                    "bmi": round(base_weight / (1.75 ** 2) + random.gauss(0, 0.2), 1),
                    "source": {
                        "name": random.choice(["Withings", "Fitbit"]),
                        "slug": random.choice(["withings", "fitbit"])
                    }
                })
            current += timedelta(days=1)
        
        return data
    
    def _generate_mock_vitals(self, start_date: date, end_date: date) -> Dict[str, List[Dict]]:
        """Generate mock vital signs data"""
        import random
        
        heartrate_data = []
        hrv_data = []
        spo2_data = []
        
        current = start_date
        base_hr = random.randint(55, 75)
        base_hrv = random.randint(35, 55)
        
        while current <= end_date:
            # Morning resting heart rate
            heartrate_data.append({
                "id": f"hr_{uuid.uuid4().hex[:12]}",
                "timestamp": f"{current}T07:00:00+00:00",
                "value": base_hr + random.randint(-5, 10),
                "type": "resting",
                "source": {"name": "Fitbit", "slug": "fitbit"}
            })
            
            # HRV
            hrv_data.append({
                "id": f"hrv_{uuid.uuid4().hex[:12]}",
                "timestamp": f"{current}T07:00:00+00:00",
                "value": base_hrv + random.randint(-10, 10),
                "source": {"name": "Oura", "slug": "oura"}
            })
            
            # SpO2
            spo2_data.append({
                "id": f"spo2_{uuid.uuid4().hex[:12]}",
                "timestamp": f"{current}T07:00:00+00:00",
                "value": random.randint(95, 100),
                "source": {"name": "Fitbit", "slug": "fitbit"}
            })
            
            current += timedelta(days=1)
        
        return {
            "heartrate": heartrate_data,
            "hrv": hrv_data,
            "blood_oxygen": spo2_data
        }
    
    def _generate_mock_meals(self, start_date: date, end_date: date) -> List[Dict]:
        """Generate mock meal/nutrition data"""
        import random
        data = []
        current = start_date
        
        meal_types = ["breakfast", "lunch", "dinner", "snack"]
        
        while current <= end_date:
            for meal_type in meal_types:
                # Skip some meals randomly
                if meal_type == "snack" and random.random() < 0.5:
                    continue
                if random.random() < 0.05:  # 5% chance to skip any meal
                    continue
                
                calories = {
                    "breakfast": random.randint(300, 500),
                    "lunch": random.randint(400, 700),
                    "dinner": random.randint(500, 900),
                    "snack": random.randint(100, 300)
                }[meal_type]
                
                data.append({
                    "id": f"meal_{uuid.uuid4().hex[:12]}",
                    "calendar_date": current.isoformat(),
                    "meal_type": meal_type,
                    "name": f"{meal_type.title()} - {current.isoformat()}",
                    "calories": calories,
                    "protein_g": round(calories * random.uniform(0.1, 0.3) / 4, 1),
                    "carbs_g": round(calories * random.uniform(0.3, 0.5) / 4, 1),
                    "fat_g": round(calories * random.uniform(0.2, 0.4) / 9, 1),
                    "fiber_g": round(random.uniform(2, 10), 1),
                    "sugar_g": round(random.uniform(5, 30), 1),
                    "sodium_mg": round(random.uniform(200, 1000), 0),
                    "source": {
                        "name": "MyFitnessPal",
                        "slug": "myfitnesspal"
                    }
                })
            current += timedelta(days=1)
        
        return data
