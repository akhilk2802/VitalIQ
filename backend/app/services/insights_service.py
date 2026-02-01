from typing import List, Optional, Dict, Any
from datetime import datetime
import json
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.anomaly import Anomaly
from app.models.correlation import Correlation
from app.schemas.anomaly import InsightResponse


class InsightsService:
    """Service for generating AI-powered health insights with RAG support."""
    
    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self._health_rag = None
        self._user_history_rag = None
        self._prompt_builder = None
    
    @property
    def health_rag(self):
        """Lazy-load HealthKnowledgeRAG."""
        if self._health_rag is None and self.db:
            from app.rag.health_knowledge_rag import HealthKnowledgeRAG
            self._health_rag = HealthKnowledgeRAG(self.db)
        return self._health_rag
    
    @property
    def user_history_rag(self):
        """Lazy-load UserHistoryRAG."""
        if self._user_history_rag is None and self.db:
            from app.rag.user_history_rag import UserHistoryRAG
            self._user_history_rag = UserHistoryRAG(self.db)
        return self._user_history_rag
    
    @property
    def prompt_builder(self):
        """Lazy-load RAGPromptBuilder."""
        if self._prompt_builder is None:
            from app.rag.prompt_builder import RAGPromptBuilder
            self._prompt_builder = RAGPromptBuilder()
        return self._prompt_builder
    
    async def generate_anomaly_explanation(
        self,
        anomaly: Anomaly,
        user_baselines: dict,
    ) -> str:
        """Generate a human-readable explanation for a single anomaly with RAG context."""
        
        if not self.client:
            return self._generate_fallback_explanation(anomaly)
        
        # Gather RAG context if available
        health_context = ""
        user_history_context = ""
        
        if self.health_rag:
            try:
                health_context = await self.health_rag.retrieve_for_anomaly(anomaly, k=2)
            except Exception as e:
                print(f"Error retrieving health context: {e}")
        
        if self.user_history_rag:
            try:
                similar_anomalies = await self.user_history_rag.retrieve_similar_anomalies(
                    user_id=anomaly.user_id,
                    current_anomaly=anomaly,
                    k=2
                )
                if similar_anomalies:
                    user_history_context = self.user_history_rag.format_history_for_prompt(
                        similar_anomalies, max_tokens=500
                    )
            except Exception as e:
                print(f"Error retrieving user history: {e}")
        
        # Build RAG-enhanced prompt
        context_section = ""
        if health_context:
            context_section += f"\n{health_context}\n"
        if user_history_context:
            context_section += f"\n{user_history_context}\n"
        
        prompt = f"""You are a health data analyst explaining an anomaly to a user. 
Be concise, helpful, and non-alarming. Use simple language.
{context_section}
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
2. Possible reasons (use the health knowledge context if relevant)
3. Whether any action is recommended

If the user has had similar anomalies before, mention that pattern.
Do not provide medical advice. Keep it casual and supportive."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=250,
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
    
    # ========== Correlation Insights ==========
    
    async def generate_correlation_insight(
        self,
        correlation: Correlation
    ) -> Optional[Dict[str, str]]:
        """Generate AI insight for a single correlation."""
        
        if not self.client:
            return self._generate_fallback_correlation_insight(correlation)
        
        # Build context based on correlation type
        correlation_context = self._build_correlation_context(correlation)
        
        prompt = f"""You are a health data analyst explaining a correlation to a user.
Be concise, helpful, and actionable. Use simple language.

Correlation Details:
{correlation_context}

Provide a response in this exact JSON format:
{{
    "insight": "A 1-2 sentence explanation of what this correlation means for the user",
    "recommendation": "A specific, actionable recommendation based on this correlation"
}}

Focus on practical lifestyle implications. Do not provide medical advice."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception:
            return self._generate_fallback_correlation_insight(correlation)
    
    async def generate_correlation_insights(
        self,
        correlations: List[Correlation],
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Generate comprehensive insights from multiple correlations."""
        
        if not correlations:
            return {
                'summary': 'No correlations detected yet.',
                'key_findings': [],
                'recommendations': []
            }
        
        if not self.client:
            return self._generate_fallback_correlation_insights(correlations, period_days)
        
        # Prepare correlation summary
        corr_summary = []
        for c in correlations[:10]:  # Limit to top 10
            corr_summary.append({
                'metrics': f"{c.metric_a} ↔ {c.metric_b}",
                'type': c.correlation_type.value,
                'strength': c.strength.value,
                'value': round(c.correlation_value, 3),
                'lag_days': c.lag_days,
                'causal_direction': c.causal_direction.value if c.causal_direction else None,
                'is_actionable': c.is_actionable
            })
        
        prompt = f"""You are a health data analyst providing insights from detected correlations.
Be concise, actionable, and practical. Do not provide medical advice.

Period Analyzed: {period_days} days
Total Correlations Found: {len(correlations)}
Actionable Correlations: {sum(1 for c in correlations if c.is_actionable)}

Top Correlations:
{json.dumps(corr_summary, indent=2)}

Provide a response in this exact JSON format:
{{
    "summary": "A 2-3 sentence overall summary of the user's health relationships",
    "key_findings": ["finding 1", "finding 2", "finding 3"],
    "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"]
}}

Focus on:
1. Patterns that can improve sleep or energy
2. Exercise and nutrition relationships
3. Predictive relationships (if metric A predicts metric B)

Be supportive and constructive."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
        except Exception:
            return self._generate_fallback_correlation_insights(correlations, period_days)
    
    def _build_correlation_context(self, correlation: Correlation) -> str:
        """Build context string for correlation prompt."""
        context_lines = [
            f"- Metric A: {correlation.metric_a.replace('_', ' ').title()}",
            f"- Metric B: {correlation.metric_b.replace('_', ' ').title()}",
            f"- Correlation Type: {correlation.correlation_type.value}",
            f"- Correlation Value: {correlation.correlation_value:.3f}",
            f"- Strength: {correlation.strength.value}",
        ]
        
        if correlation.lag_days > 0:
            context_lines.append(f"- Time Lag: {correlation.lag_days} day(s)")
            context_lines.append(f"  (Metric A on day T affects Metric B on day T+{correlation.lag_days})")
        
        if correlation.causal_direction:
            direction = correlation.causal_direction.value
            if direction == 'a_causes_b':
                context_lines.append(f"- Causal Direction: {correlation.metric_a} → {correlation.metric_b}")
            elif direction == 'b_causes_a':
                context_lines.append(f"- Causal Direction: {correlation.metric_b} → {correlation.metric_a}")
            elif direction == 'bidirectional':
                context_lines.append("- Causal Direction: Bidirectional relationship")
        
        if correlation.percentile_rank:
            context_lines.append(f"- Population Percentile: {correlation.percentile_rank}th")
        
        return "\n".join(context_lines)
    
    def _generate_fallback_correlation_insight(
        self, 
        correlation: Correlation
    ) -> Dict[str, str]:
        """Generate correlation insight without AI."""
        metric_a = correlation.metric_a.replace('_', ' ').title()
        metric_b = correlation.metric_b.replace('_', ' ').title()
        
        # Build insight based on correlation type and direction
        if correlation.correlation_value > 0:
            direction = "increase together"
            recommendation_direction = "increasing"
        else:
            direction = "move in opposite directions"
            recommendation_direction = "adjusting"
        
        if correlation.causal_direction and correlation.causal_direction.value == 'a_causes_b':
            insight = f"Your {metric_a} appears to predict your {metric_b}. Higher {metric_a} tends to lead to changes in {metric_b}."
        elif correlation.lag_days > 0:
            insight = f"Your {metric_a} affects your {metric_b} about {correlation.lag_days} day(s) later. They {direction}."
        else:
            insight = f"Your {metric_a} and {metric_b} {direction}. This suggests they're connected in your daily patterns."
        
        recommendation = f"Consider tracking how {recommendation_direction} {metric_a} affects your {metric_b} over time."
        
        return {
            'insight': insight,
            'recommendation': recommendation
        }
    
    def _generate_fallback_correlation_insights(
        self,
        correlations: List[Correlation],
        period_days: int
    ) -> Dict[str, Any]:
        """Generate correlation insights summary without AI."""
        from collections import Counter
        
        type_counts = Counter(c.correlation_type.value for c in correlations)
        actionable = [c for c in correlations if c.is_actionable]
        
        # Generate summary
        summary = (
            f"Over the past {period_days} days, we found {len(correlations)} correlations between your health metrics. "
            f"{len(actionable)} are strong enough to act on."
        )
        
        # Generate findings
        findings = []
        for c in correlations[:3]:
            metric_a = c.metric_a.replace('_', ' ')
            metric_b = c.metric_b.replace('_', ' ')
            direction = "positively" if c.correlation_value > 0 else "negatively"
            findings.append(f"Your {metric_a} and {metric_b} are {direction} correlated")
        
        # Add Granger findings
        granger_results = [c for c in correlations if c.correlation_type.value == 'granger_causality']
        for c in granger_results[:2]:
            findings.append(f"{c.metric_a.replace('_', ' ').title()} predicts {c.metric_b.replace('_', ' ')}")
        
        # Generate recommendations
        recommendations = []
        
        # Check for exercise-sleep correlation
        exercise_sleep = [c for c in correlations 
                         if 'exercise' in c.metric_a and 'sleep' in c.metric_b]
        if exercise_sleep and exercise_sleep[0].correlation_value > 0:
            recommendations.append("Regular exercise appears to improve your sleep - aim for 30+ minutes daily")
        
        # Check for nutrition correlations
        nutrition_corrs = [c for c in correlations if 'calorie' in c.metric_a or 'sugar' in c.metric_a]
        if nutrition_corrs:
            recommendations.append("Your nutrition choices show measurable impacts - track meal timing")
        
        recommendations.append("Focus on the actionable correlations to optimize your health patterns")
        
        return {
            'summary': summary,
            'key_findings': findings[:5],
            'recommendations': recommendations[:3]
        }
