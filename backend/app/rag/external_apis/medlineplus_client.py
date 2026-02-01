"""
MedlinePlus API Client for consumer health information.

MedlinePlus provides trusted health information from the National 
Library of Medicine (NLM) in consumer-friendly language.
"""

import httpx
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from xml.etree import ElementTree
import re


@dataclass
class HealthTopic:
    """Represents a MedlinePlus health topic."""
    topic_id: str
    title: str
    url: str
    summary: str
    full_summary: Optional[str] = None
    aliases: List[str] = None
    related_topics: List[str] = None
    primary_category: Optional[str] = None
    
    def __post_init__(self):
        self.aliases = self.aliases or []
        self.related_topics = self.related_topics or []
    
    def to_text(self) -> str:
        """Convert to text for embedding."""
        parts = [
            f"Health Topic: {self.title}",
            "",
            self.full_summary or self.summary,
        ]
        
        if self.aliases:
            parts.append(f"\nAlso known as: {', '.join(self.aliases)}")
        
        if self.related_topics:
            parts.append(f"\nRelated topics: {', '.join(self.related_topics[:5])}")
        
        return "\n".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "topic_id": self.topic_id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "full_summary": self.full_summary,
            "aliases": self.aliases,
            "related_topics": self.related_topics,
            "primary_category": self.primary_category,
        }


class MedlinePlusClient:
    """
    Async client for MedlinePlus Connect API.
    
    Features:
    - Search health topics
    - Get topic details
    - Consumer-friendly health information
    """
    
    BASE_URL = "https://wsearch.nlm.nih.gov/ws"
    TOPIC_URL = "https://medlineplus.gov/xml"
    
    # Predefined health topics relevant to VitalIQ
    HEALTH_TOPICS = [
        # Sleep
        "Sleep Disorders",
        "Sleep Apnea",
        "Insomnia",
        "Healthy Sleep",
        
        # Heart Health
        "Heart Rate",
        "Heart Health",
        "Blood Pressure",
        "Arrhythmia",
        
        # Nutrition & Metabolism
        "Nutrition",
        "Blood Sugar",
        "Diabetes",
        "Carbohydrates",
        "Dietary Proteins",
        
        # Exercise & Fitness
        "Exercise and Physical Fitness",
        "Benefits of Exercise",
        
        # Weight Management
        "Weight Control",
        "Body Mass Index",
        "Obesity",
        
        # Stress & Mental Health
        "Stress",
        "Anxiety",
        
        # Vital Signs
        "Vital Signs",
    ]
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def search(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search MedlinePlus for health topics.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of search result dicts
        """
        params = {
            "db": "healthTopics",
            "term": query,
            "retmax": str(max_results),
            "rettype": "brief"
        }
        
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/query",
                params=params
            )
            response.raise_for_status()
            
            return self._parse_search_results(response.text)
            
        except httpx.HTTPError as e:
            print(f"MedlinePlus search error: {e}")
            return []
    
    def _parse_search_results(self, xml_text: str) -> List[Dict[str, Any]]:
        """Parse search results XML."""
        results = []
        
        try:
            root = ElementTree.fromstring(xml_text)
            
            for doc in root.findall(".//document"):
                result = {}
                
                for content in doc.findall("content"):
                    name = content.get("name", "")
                    text = content.text or ""
                    
                    if name == "title":
                        result["title"] = text
                    elif name == "FullSummary":
                        result["summary"] = self._clean_html(text)
                    elif name == "url":
                        result["url"] = text
                    elif name == "groupName":
                        result["category"] = text
                
                if result.get("title") and result.get("summary"):
                    results.append(result)
                    
        except ElementTree.ParseError as e:
            print(f"XML parse error: {e}")
        
        return results
    
    async def get_health_topics(
        self, 
        topics: Optional[List[str]] = None
    ) -> List[HealthTopic]:
        """
        Get detailed health topics by name.
        
        Args:
            topics: List of topic names or None for predefined topics
            
        Returns:
            List of HealthTopic objects
        """
        topics = topics or self.HEALTH_TOPICS
        results = []
        
        for topic_name in topics:
            topic_info = await self._search_topic(topic_name)
            if topic_info:
                results.append(topic_info)
            
            # Rate limiting
            await asyncio.sleep(0.2)
        
        return results
    
    async def _search_topic(self, topic_name: str) -> Optional[HealthTopic]:
        """Search for a specific health topic."""
        search_results = await self.search(topic_name, max_results=1)
        
        if not search_results:
            return None
        
        result = search_results[0]
        
        # Create HealthTopic from search result
        return HealthTopic(
            topic_id=self._extract_topic_id(result.get("url", "")),
            title=result.get("title", topic_name),
            url=result.get("url", ""),
            summary=result.get("summary", "")[:500],
            full_summary=result.get("summary"),
            primary_category=result.get("category"),
        )
    
    def _extract_topic_id(self, url: str) -> str:
        """Extract topic ID from URL."""
        if not url:
            return ""
        
        # URL format: https://medlineplus.gov/sleepapnea.html
        match = re.search(r'/([a-zA-Z0-9]+)\.html$', url)
        if match:
            return match.group(1)
        
        return url.split("/")[-1].replace(".html", "")
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()
    
    async def get_topic_by_code(
        self, 
        code: str,
        code_system: str = "ICD-10-CM"
    ) -> Optional[HealthTopic]:
        """
        Get health topic by medical code.
        
        Args:
            code: Medical code (ICD-10, SNOMED, etc.)
            code_system: Code system name
            
        Returns:
            HealthTopic if found
        """
        params = {
            "mainSearchCriteria.v.cs": code_system,
            "mainSearchCriteria.v.c": code,
            "informationRecipient.languageCode.c": "en"
        }
        
        try:
            response = await self.client.get(
                "https://connect.medlineplus.gov/service",
                params=params
            )
            
            if response.status_code == 200:
                return self._parse_connect_response(response.text)
                
        except httpx.HTTPError as e:
            print(f"MedlinePlus Connect error: {e}")
        
        return None
    
    def _parse_connect_response(self, xml_text: str) -> Optional[HealthTopic]:
        """Parse MedlinePlus Connect API response."""
        try:
            root = ElementTree.fromstring(xml_text)
            
            # Find the first entry
            entry = root.find(".//{http://www.w3.org/2005/Atom}entry")
            if entry is None:
                return None
            
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            
            title_elem = entry.find("atom:title", ns)
            summary_elem = entry.find("atom:summary", ns)
            link_elem = entry.find("atom:link[@rel='alternate']", ns)
            
            if title_elem is not None:
                return HealthTopic(
                    topic_id="connect",
                    title=title_elem.text or "",
                    url=link_elem.get("href", "") if link_elem is not None else "",
                    summary=self._clean_html(summary_elem.text or "") if summary_elem is not None else "",
                )
                
        except ElementTree.ParseError as e:
            print(f"XML parse error: {e}")
        
        return None
    
    async def fetch_all_health_topics(self) -> List[HealthTopic]:
        """
        Fetch all predefined health topics for VitalIQ.
        
        Returns:
            List of HealthTopic objects
        """
        return await self.get_health_topics(self.HEALTH_TOPICS)
    
    async def search_by_metric(
        self, 
        metric_name: str
    ) -> List[HealthTopic]:
        """
        Search for health topics related to a VitalIQ metric.
        
        Args:
            metric_name: VitalIQ metric name (e.g., 'sleep_hours', 'resting_hr')
            
        Returns:
            List of related HealthTopic objects
        """
        # Map metrics to search queries
        metric_to_query = {
            "sleep_hours": "sleep health duration",
            "sleep_quality": "sleep quality",
            "resting_hr": "heart rate resting",
            "hrv": "heart rate variability",
            "bp_systolic": "blood pressure systolic",
            "bp_diastolic": "blood pressure diastolic",
            "blood_glucose": "blood sugar glucose",
            "weight_kg": "weight management",
            "body_fat_pct": "body composition fat",
            "total_calories": "calories nutrition",
            "exercise_minutes": "physical activity exercise",
        }
        
        query = metric_to_query.get(
            metric_name.lower(), 
            metric_name.replace("_", " ")
        )
        
        results = await self.search(query, max_results=5)
        
        return [
            HealthTopic(
                topic_id=self._extract_topic_id(r.get("url", "")),
                title=r.get("title", ""),
                url=r.get("url", ""),
                summary=r.get("summary", "")[:500],
                full_summary=r.get("summary"),
                primary_category=r.get("category"),
            )
            for r in results
        ]
