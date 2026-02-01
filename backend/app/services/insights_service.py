from typing import List, Optional
from datetime import datetime
import json
from openai import AsyncOpenAI

from app.config import settings
from app.models.anomaly import Anomaly
from app.schemas.anomaly import InsightResponse


class InsightsService:
    """Service for generating AI-powered health insights"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
    async def generate_anomaly_explanation(
        self,
        anomaly: Anomaly,
        user_baselines: dict,
    ) -> str:
        """Generate a human-readable explanation for a single anomaly"""
        
        if not self.client:
            return self._generate_fallback_explanation(anomaly)
        
        prompt = f"""You are a health data analyst explaining an anomaly to a user. 
Be concise, helpful, and non-alarming. Use simple language.

Anomaly Details:
- Date: {anomaly.date}
- Metric: {anomaly.metric_name}
- Recorded Value: {anomaly.metric_value}
- User's Typical Value: {anomaly.baseline_value}
- Severity: {anomaly.severity.value}
- Detection Method: {anomaly.detector_type.value}

User's typical baselines:
{json.dumps(user_baselines, indent=2)}

Provide a brief explanation (2-3 sentences) of:
1. What was detected
2. Possible reasons (lifestyle, health, etc.)
3. Whether any action is recommended

Do not provide medical advice. Keep it casual and supportive."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return self._generate_fallback_explanation(anomaly)
    
    async def generate_insights_summary(
        self,
        anomalies: List[Anomaly],
        user_baselines: dict,
        period_days: int = 30,
    ) -> InsightResponse:
        """Generate a comprehensive insights summary from multiple anomalies"""
        
        if not anomalies:
            return InsightResponse(
                summary="No anomalies detected in the analyzed period. Your health metrics appear stable.",
                key_findings=[],
                recommendations=["Continue your current healthy habits!"],
                anomaly_count=0,
                period_days=period_days,
                generated_at=datetime.utcnow()
            )
        
        if not self.client:
            return self._generate_fallback_summary(anomalies, period_days)
        
        # Prepare anomaly summary for the prompt
        anomaly_summary = []
        for a in anomalies[:10]:  # Limit to top 10
            anomaly_summary.append({
                'date': str(a.date),
                'metric': a.metric_name,
                'value': a.metric_value,
                'baseline': a.baseline_value,
                'severity': a.severity.value,
            })
        
        prompt = f"""You are a health data analyst providing insights from detected anomalies.
Be concise, actionable, and non-alarming. Do not provide medical advice.

Period Analyzed: {period_days} days
Total Anomalies Detected: {len(anomalies)}

Anomaly Details:
{json.dumps(anomaly_summary, indent=2)}

User Baselines:
{json.dumps(user_baselines, indent=2)}

Provide a response in this exact JSON format:
{{
    "summary": "A 1-2 sentence overall summary of the user's health patterns",
    "key_findings": ["finding 1", "finding 2", "finding 3"],
    "recommendations": ["recommendation 1", "recommendation 2"]
}}

Focus on patterns across multiple anomalies. Be supportive and constructive."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            return InsightResponse(
                summary=result.get('summary', 'Analysis complete.'),
                key_findings=result.get('key_findings', []),
                recommendations=result.get('recommendations', []),
                anomaly_count=len(anomalies),
                period_days=period_days,
                generated_at=datetime.utcnow()
            )
        except Exception as e:
            return self._generate_fallback_summary(anomalies, period_days)
    
    def _generate_fallback_explanation(self, anomaly: Anomaly) -> str:
        """Generate explanation without AI"""
        metric_name = anomaly.metric_name.replace('_', ' ').title()
        direction = "higher" if anomaly.metric_value > anomaly.baseline_value else "lower"
        
        return (
            f"Your {metric_name} on {anomaly.date} was {direction} than your usual pattern. "
            f"This could be due to recent lifestyle changes, stress, or natural variation. "
            f"If this persists, consider discussing with a healthcare provider."
        )
    
    def _generate_fallback_summary(
        self, 
        anomalies: List[Anomaly], 
        period_days: int
    ) -> InsightResponse:
        """Generate summary without AI"""
        from collections import Counter
        
        severity_counts = Counter(a.severity.value for a in anomalies)
        metric_counts = Counter(a.metric_name for a in anomalies)
        most_common_metric = metric_counts.most_common(1)[0][0] if metric_counts else "various metrics"
        
        summary = (
            f"Over the past {period_days} days, we detected {len(anomalies)} anomalies, "
            f"primarily related to {most_common_metric.replace('_', ' ')}."
        )
        
        findings = []
        if severity_counts.get('high', 0) > 0:
            findings.append(f"{severity_counts['high']} high-severity anomalies require attention")
        
        most_frequent = metric_counts.most_common(3)
        for metric, count in most_frequent:
            findings.append(f"{metric.replace('_', ' ').title()}: {count} unusual readings")
        
        recommendations = [
            "Review your sleep patterns and stress levels",
            "Ensure consistent meal timing and nutrition",
            "Consider tracking potential triggers for anomalies",
        ]
        
        return InsightResponse(
            summary=summary,
            key_findings=findings[:5],
            recommendations=recommendations[:3],
            anomaly_count=len(anomalies),
            period_days=period_days,
            generated_at=datetime.utcnow()
        )
    
    async def update_anomaly_explanations(
        self,
        anomalies: List[Anomaly],
        user_baselines: dict,
    ) -> int:
        """Update explanations for anomalies that don't have one"""
        updated_count = 0
        
        for anomaly in anomalies:
            if not anomaly.explanation:
                explanation = await self.generate_anomaly_explanation(
                    anomaly, 
                    user_baselines
                )
                anomaly.explanation = explanation
                updated_count += 1
        
        return updated_count
