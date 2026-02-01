"""
RAG Prompt Builder for assembling context-rich prompts.

Handles:
- System prompt construction
- Context assembly from multiple sources
- Token management
- Conversation history formatting
"""

from typing import List, Dict, Any, Optional
from datetime import date

from app.models.chat import ChatMessage
from app.rag.health_knowledge_rag import KnowledgeChunk
from app.rag.user_history_rag import HistoryChunk
from app.utils.enums import MessageRole


class RAGPromptBuilder:
    """Builds context-rich prompts for RAG-powered chat responses."""
    
    SYSTEM_PROMPT = """You are VitalIQ's health assistant, an AI that helps users understand their personal health data and patterns.

YOUR CAPABILITIES:
- Analyze and explain the user's health metrics (sleep, exercise, nutrition, vitals)
- Explain detected anomalies and correlations in their data
- Provide evidence-based health information
- Offer practical lifestyle suggestions based on their patterns

RULES YOU MUST FOLLOW:
1. NEVER provide medical diagnoses or treatment recommendations
2. NEVER tell users to start, stop, or change medications
3. Always recommend consulting a healthcare provider for medical concerns
4. Be specific to the user's data when context is provided
5. Cite health knowledge sources when relevant
6. If you don't know something, say so honestly
7. Keep responses concise but informative
8. Be supportive and non-judgmental

RESPONSE STYLE:
- Use clear, simple language
- Break down complex concepts
- Be encouraging and constructive
- Focus on actionable insights"""

    MAX_CONTEXT_TOKENS = 3000
    MAX_HISTORY_TOKENS = 1500
    
    def build_chat_prompt(
        self,
        user_message: str,
        health_context: Optional[str] = None,
        user_history_context: Optional[str] = None,
        recent_metrics: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[ChatMessage]] = None,
        include_system_prompt: bool = True
    ) -> List[Dict[str, str]]:
        """
        Build complete prompt messages for chat completion.
        
        Args:
            user_message: Current user message
            health_context: Formatted health knowledge context
            user_history_context: Formatted user history context
            recent_metrics: Recent metric values
            conversation_history: Previous messages in this session
            include_system_prompt: Whether to include system prompt
            
        Returns:
            List of message dicts for OpenAI API
        """
        messages = []
        
        # System prompt with context
        if include_system_prompt:
            system_content = self._build_system_content(
                health_context=health_context,
                user_history_context=user_history_context,
                recent_metrics=recent_metrics
            )
            messages.append({
                "role": "system",
                "content": system_content
            })
        
        # Add conversation history
        if conversation_history:
            history_messages = self._format_conversation_history(conversation_history)
            messages.extend(history_messages)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    def _build_system_content(
        self,
        health_context: Optional[str] = None,
        user_history_context: Optional[str] = None,
        recent_metrics: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build the system message content with all context."""
        parts = [self.SYSTEM_PROMPT]
        
        # Add recent metrics
        if recent_metrics:
            metrics_text = self._format_recent_metrics(recent_metrics)
            if metrics_text:
                parts.append("\n\n" + "=" * 50)
                parts.append("USER'S RECENT HEALTH DATA:")
                parts.append(metrics_text)
        
        # Add health knowledge context
        if health_context:
            parts.append("\n\n" + "=" * 50)
            parts.append(health_context)
        
        # Add user history context
        if user_history_context:
            parts.append("\n\n" + "=" * 50)
            parts.append(user_history_context)
        
        return "\n".join(parts)
    
    def _format_recent_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format recent metrics for context."""
        if not metrics:
            return ""
        
        lines = []
        
        # Group metrics by category
        categories = {
            "sleep": ["sleep_hours", "sleep_quality", "awakenings"],
            "exercise": ["exercise_minutes", "exercise_calories"],
            "nutrition": ["total_calories", "total_protein_g", "total_carbs_g", "total_sugar_g"],
            "vitals": ["resting_hr", "hrv", "bp_systolic", "bp_diastolic"],
            "body": ["weight_kg", "body_fat_pct"],
        }
        
        for category, metric_names in categories.items():
            category_values = []
            for metric in metric_names:
                if metric in metrics and metrics[metric] is not None:
                    # Format metric name nicely
                    display_name = metric.replace("_", " ").title()
                    value = metrics[metric]
                    
                    # Format value appropriately
                    if isinstance(value, float):
                        value = f"{value:.1f}"
                    
                    category_values.append(f"  - {display_name}: {value}")
            
            if category_values:
                lines.append(f"\n{category.title()}:")
                lines.extend(category_values)
        
        return "\n".join(lines) if lines else ""
    
    def _format_conversation_history(
        self, 
        messages: List[ChatMessage],
        max_messages: int = 10
    ) -> List[Dict[str, str]]:
        """Format conversation history for context."""
        # Take last N messages
        recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
        
        formatted = []
        for msg in recent_messages:
            role = "user" if msg.role == MessageRole.user else "assistant"
            formatted.append({
                "role": role,
                "content": msg.content
            })
        
        return formatted
    
    def build_anomaly_explanation_prompt(
        self,
        metric_name: str,
        metric_value: float,
        baseline_value: float,
        severity: str,
        health_context: Optional[str] = None,
        user_history_context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Build prompt for explaining an anomaly.
        
        Args:
            metric_name: Name of the anomalous metric
            metric_value: Recorded value
            baseline_value: User's typical value
            severity: Anomaly severity level
            health_context: Health knowledge context
            user_history_context: User's past similar anomalies
            
        Returns:
            List of message dicts
        """
        system_content = self._build_system_content(
            health_context=health_context,
            user_history_context=user_history_context
        )
        
        direction = "higher" if metric_value > baseline_value else "lower"
        metric_display = metric_name.replace("_", " ").title()
        
        user_prompt = f"""Please explain this health anomaly for the user:

Metric: {metric_display}
Recorded Value: {metric_value}
User's Typical Value: {baseline_value}
Deviation: {direction} than usual
Severity: {severity}

Provide:
1. A brief explanation of what this means (1-2 sentences)
2. Possible lifestyle factors that could cause this
3. Whether any action is recommended

Keep it friendly and non-alarming. Don't provide medical advice."""

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt}
        ]
    
    def build_correlation_insight_prompt(
        self,
        metric_a: str,
        metric_b: str,
        correlation_value: float,
        correlation_type: str,
        lag_days: int = 0,
        causal_direction: Optional[str] = None,
        health_context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Build prompt for explaining a correlation.
        
        Args:
            metric_a: First metric
            metric_b: Second metric
            correlation_value: Correlation coefficient
            correlation_type: Type of correlation
            lag_days: Time lag in days
            causal_direction: Direction of causality if known
            health_context: Health knowledge context
            
        Returns:
            List of message dicts
        """
        system_content = self._build_system_content(
            health_context=health_context
        )
        
        metric_a_display = metric_a.replace("_", " ").title()
        metric_b_display = metric_b.replace("_", " ").title()
        direction = "positively" if correlation_value > 0 else "negatively"
        
        # Build relationship description
        relationship = f"{metric_a_display} and {metric_b_display} are {direction} correlated"
        
        if lag_days > 0:
            relationship += f" with a {lag_days}-day delay"
        
        if causal_direction == "a_causes_b":
            relationship += f". {metric_a_display} appears to influence {metric_b_display}."
        elif causal_direction == "b_causes_a":
            relationship += f". {metric_b_display} appears to influence {metric_a_display}."
        
        user_prompt = f"""Please explain this correlation found in the user's health data:

{relationship}
Correlation Value: {correlation_value:.3f}
Correlation Type: {correlation_type}

Provide:
1. A clear explanation of what this relationship means
2. How the user can use this insight to improve their health
3. A specific, actionable recommendation

Keep it practical and encouraging."""

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt}
        ]
    
    def build_insights_summary_prompt(
        self,
        anomaly_count: int,
        correlation_count: int,
        key_findings: List[str],
        health_context: Optional[str] = None,
        period_days: int = 30
    ) -> List[Dict[str, str]]:
        """
        Build prompt for generating an insights summary.
        
        Args:
            anomaly_count: Number of anomalies detected
            correlation_count: Number of correlations found
            key_findings: List of key finding strings
            health_context: Health knowledge context
            period_days: Analysis period in days
            
        Returns:
            List of message dicts
        """
        system_content = self._build_system_content(
            health_context=health_context
        )
        
        findings_text = "\n".join(f"- {f}" for f in key_findings) if key_findings else "None specific"
        
        user_prompt = f"""Generate a brief health insights summary for the user based on their data from the past {period_days} days:

Anomalies Detected: {anomaly_count}
Correlations Found: {correlation_count}

Key Findings:
{findings_text}

Provide:
1. A 2-3 sentence overview of their health patterns
2. 3 key findings (bullet points)
3. 2-3 actionable recommendations

Focus on patterns and be constructive."""

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_prompt}
        ]
    
    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate token count for messages."""
        # Rough estimate: 4 characters per token
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return total_chars // 4
