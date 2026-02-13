"""Metrics collection and aggregation service for system monitoring."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from core.logger import logger
from database.models import (
    get_all_candidates,
    get_all_positions,
    get_all_feedback_emails,
    get_all_model_responses,
    get_all_validation_errors,
    get_all_tickets,
)


class MetricType(str, Enum):
    """Types of metrics."""

    FEEDBACK_GENERATION = "feedback_generation"
    VALIDATION = "validation"
    EMAIL_PROCESSING = "email_processing"
    RAG_USAGE = "rag_usage"
    AGENT_PERFORMANCE = "agent_performance"
    SYSTEM_HEALTH = "system_health"


@dataclass
class Metric:
    """Single metric data point."""

    metric_type: str
    name: str
    value: float
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "metric_type": self.metric_type,
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {},
        }


class MetricsService:
    """Service for collecting and aggregating system metrics."""

    def __init__(self):
        """Initialize metrics service."""
        self.metrics: List[Metric] = []
        logger.info("MetricsService initialized")

    def record_metric(
        self, metric_type: str, name: str, value: float, metadata: Optional[Dict[str, Any]] = None
    ):
        """Record a single metric."""
        metric = Metric(
            metric_type=metric_type,
            name=name,
            value=value,
            timestamp=datetime.now(),
            metadata=metadata,
        )
        self.metrics.append(metric)
        logger.debug(f"Recorded metric: {name}={value} (type: {metric_type})")

    def record_timing(
        self,
        metric_type: str,
        operation_name: str,
        duration_seconds: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a timing metric."""
        self.record_metric(
            metric_type=metric_type,
            name=f"{operation_name}_duration",
            value=duration_seconds,
            metadata=metadata,
        )

    def record_success(
        self,
        metric_type: str,
        operation_name: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a success/failure metric (1.0 for success, 0.0 for failure)."""
        self.record_metric(
            metric_type=metric_type,
            name=f"{operation_name}_success",
            value=1.0 if success else 0.0,
            metadata=metadata,
        )

    def get_feedback_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get metrics related to feedback generation."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get all feedback emails
            feedback_emails = get_all_feedback_emails()
            recent_feedback = [
                fe for fe in feedback_emails if fe.sent_at and fe.sent_at >= cutoff_date
            ]

            # Get validation errors
            validation_errors = get_all_validation_errors()
            recent_errors = [
                ve for ve in validation_errors if ve.created_at and ve.created_at >= cutoff_date
            ]

            # Get model responses for feedback generation
            model_responses = get_all_model_responses()
            _ = [
                mr
                for mr in model_responses
                if mr.agent_type == "feedback_generator"
                and mr.created_at
                and mr.created_at >= cutoff_date
            ]

            validation_responses = [
                mr
                for mr in model_responses
                if mr.agent_type == "validator" and mr.created_at and mr.created_at >= cutoff_date
            ]

            total_feedback = len(recent_feedback)
            total_errors = len(recent_errors)
            validation_success_rate = (
                max(total_feedback - total_errors, 0) / total_feedback * 100
                if total_feedback > 0
                else 100.0
            )

            # Calculate average validation iterations
            validation_iterations = {}
            for mr in validation_responses:
                metadata = mr.metadata
                if metadata:
                    try:
                        import json

                        if isinstance(metadata, str):
                            metadata = json.loads(metadata)
                        iteration = metadata.get("validation_number", 1)
                        validation_iterations[iteration] = (
                            validation_iterations.get(iteration, 0) + 1
                        )
                    except Exception:
                        pass

            # Calculate timing metrics from recorded metrics
            timing_metrics = self._get_timing_metrics("feedback_generation", days)

            return {
                "total_feedback_generated": total_feedback,
                "validation_errors": total_errors,
                "validation_success_rate": round(validation_success_rate, 2),
                "validation_iterations_distribution": validation_iterations,
                "feedback_per_day": round(total_feedback / days, 2) if days > 0 else 0,
                "error_rate": (
                    round(total_errors / total_feedback * 100, 2) if total_feedback > 0 else 0.0
                ),
                **timing_metrics,  # Add timing metrics
            }
        except Exception as e:
            logger.error(f"Error calculating feedback metrics: {str(e)}", exc_info=True)
            return {}

    def _get_timing_metrics(self, metric_type: str, days: int = 30) -> Dict[str, Any]:
        """Get timing metrics for a specific metric type."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Filter metrics by type and date
            relevant_metrics = [
                m
                for m in self.metrics
                if m.metric_type == metric_type
                and "duration" in m.name
                and m.timestamp >= cutoff_date
            ]

            if not relevant_metrics:
                return {
                    "avg_generation_time_seconds": 0.0,
                    "avg_generation_time_minutes": 0.0,
                    "responses_under_30_seconds": 0,
                    "responses_under_30_seconds_percent": 0.0,
                    "total_timing_measurements": 0,
                }

            # Calculate average time
            durations = [m.value for m in relevant_metrics]
            avg_duration = sum(durations) / len(durations)

            # Count responses under 30 seconds
            under_30_seconds = sum(1 for d in durations if d < 30)
            under_30_percent = (under_30_seconds / len(durations)) * 100 if durations else 0.0

            return {
                "avg_generation_time_seconds": round(avg_duration, 2),
                "avg_generation_time_minutes": round(avg_duration / 60, 2),
                "responses_under_30_seconds": under_30_seconds,
                "responses_under_30_seconds_percent": round(under_30_percent, 2),
                "total_timing_measurements": len(durations),
            }
        except Exception as e:
            logger.error(f"Error calculating timing metrics: {str(e)}", exc_info=True)
            return {}

    def get_cost_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get cost metrics related to AI operations."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get all model responses
            model_responses = get_all_model_responses()
            recent_responses = [
                mr for mr in model_responses if mr.created_at and mr.created_at >= cutoff_date
            ]

            # Extract cost and token information from metadata
            total_cost = 0.0
            total_input_tokens = 0
            total_output_tokens = 0
            total_tokens = 0
            cost_by_agent = {}
            token_count = 0

            for mr in recent_responses:
                metadata = mr.metadata
                if metadata:
                    try:
                        import json

                        if isinstance(metadata, str):
                            metadata = json.loads(metadata)

                        cost = metadata.get("cost_pln", 0.0)
                        input_tokens = metadata.get("input_tokens", 0)
                        output_tokens = metadata.get("output_tokens", 0)
                        tokens = metadata.get("total_tokens", 0)

                        if cost > 0:
                            total_cost += cost
                            token_count += 1

                        if input_tokens > 0:
                            total_input_tokens += input_tokens
                        if output_tokens > 0:
                            total_output_tokens += output_tokens
                        if tokens > 0:
                            total_tokens += tokens

                        # Group by agent type
                        agent_type = mr.agent_type
                        if agent_type not in cost_by_agent:
                            cost_by_agent[agent_type] = {
                                "cost": 0.0,
                                "count": 0,
                                "input_tokens": 0,
                                "output_tokens": 0,
                            }

                        if cost > 0:
                            cost_by_agent[agent_type]["cost"] += cost
                            cost_by_agent[agent_type]["count"] += 1

                        if input_tokens > 0:
                            cost_by_agent[agent_type]["input_tokens"] += input_tokens
                        if output_tokens > 0:
                            cost_by_agent[agent_type]["output_tokens"] += output_tokens
                    except Exception as e:
                        logger.debug(f"Error parsing metadata for cost metrics: {str(e)}")
                        continue

            # Calculate averages
            avg_cost_per_response = total_cost / token_count if token_count > 0 else 0.0
            avg_cost_per_day = total_cost / days if days > 0 else 0.0
            avg_tokens_per_response = total_tokens / token_count if token_count > 0 else 0.0

            # Calculate cost per feedback (only feedback_generator responses)
            feedback_responses = [
                mr for mr in recent_responses if mr.agent_type == "feedback_generator"
            ]
            feedback_cost = 0.0
            feedback_count = 0
            for mr in feedback_responses:
                metadata = mr.metadata
                if metadata:
                    try:
                        import json

                        if isinstance(metadata, str):
                            metadata = json.loads(metadata)
                        cost = metadata.get("cost_pln", 0.0)
                        if cost > 0:
                            feedback_cost += cost
                            feedback_count += 1
                    except Exception:
                        pass

            avg_cost_per_feedback = feedback_cost / feedback_count if feedback_count > 0 else 0.0

            return {
                "total_cost_pln": round(total_cost, 4),
                "avg_cost_per_response_pln": round(avg_cost_per_response, 4),
                "avg_cost_per_feedback_pln": round(avg_cost_per_feedback, 4),
                "avg_cost_per_day_pln": round(avg_cost_per_day, 4),
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_tokens": total_tokens,
                "avg_tokens_per_response": round(avg_tokens_per_response, 0),
                "cost_by_agent": {
                    agent: {
                        "cost_pln": round(stats["cost"], 4),
                        "count": stats["count"],
                        "avg_cost_pln": (
                            round(stats["cost"] / stats["count"], 4) if stats["count"] > 0 else 0.0
                        ),
                        "input_tokens": stats["input_tokens"],
                        "output_tokens": stats["output_tokens"],
                    }
                    for agent, stats in cost_by_agent.items()
                },
                "responses_with_cost_data": token_count,
                "total_responses": len(recent_responses),
            }
        except Exception as e:
            logger.error(f"Error calculating cost metrics: {str(e)}", exc_info=True)
            return {}

    def get_email_processing_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get metrics related to email processing."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get model responses for email processing
            model_responses = get_all_model_responses()
            email_responses = [
                mr
                for mr in model_responses
                if mr.agent_type in ["email_classifier", "query_classifier", "query_responder"]
                and mr.created_at
                and mr.created_at >= cutoff_date
            ]

            # Classify by agent type
            classifier_count = len(
                [mr for mr in email_responses if mr.agent_type == "email_classifier"]
            )

            query_classifier_count = len(
                [mr for mr in email_responses if mr.agent_type == "query_classifier"]
            )

            query_responder_count = len(
                [mr for mr in email_responses if mr.agent_type == "query_responder"]
            )

            # Get tickets (HR and IOD)
            tickets = get_all_tickets()
            recent_tickets = [t for t in tickets if t.created_at and t.created_at >= cutoff_date]

            hr_tickets = [t for t in recent_tickets if t.department.value == "HR"]
            iod_tickets = [t for t in recent_tickets if t.department.value == "IOD"]

            return {
                "emails_classified": classifier_count,
                "queries_classified": query_classifier_count,
                "queries_responded": query_responder_count,
                "total_emails_processed": classifier_count + query_classifier_count,
                "hr_tickets_created": len(hr_tickets),
                "iod_tickets_created": len(iod_tickets),
                "total_tickets": len(recent_tickets),
                "emails_per_day": (
                    round((classifier_count + query_classifier_count) / days, 2) if days > 0 else 0
                ),
            }
        except Exception as e:
            logger.error(f"Error calculating email processing metrics: {str(e)}", exc_info=True)
            return {}

    def get_rag_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get metrics related to RAG usage."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            # Get model responses for query responder with RAG
            model_responses = get_all_model_responses()
            rag_responses = [
                mr
                for mr in model_responses
                if mr.agent_type == "query_responder"
                and mr.metadata
                and mr.created_at
                and mr.created_at >= cutoff_date
            ]

            # Check metadata for RAG usage
            rag_used = 0
            direct_answers = 0

            for mr in rag_responses:
                try:
                    import json

                    metadata = mr.metadata
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata)
                    if isinstance(metadata, dict):
                        if metadata.get("rag_used") or metadata.get("rag_context"):
                            rag_used += 1
                        else:
                            direct_answers += 1
                except Exception:
                    direct_answers += 1

            total_queries = rag_used + direct_answers
            rag_usage_rate = (rag_used / total_queries * 100) if total_queries > 0 else 0.0

            return {
                "rag_queries": rag_used,
                "direct_answers": direct_answers,
                "total_queries": total_queries,
                "rag_usage_rate": round(rag_usage_rate, 2),
            }
        except Exception as e:
            logger.error(f"Error calculating RAG metrics: {str(e)}", exc_info=True)
            return {}

    def get_agent_performance_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for AI agents."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)

            model_responses = get_all_model_responses()
            recent_responses = [
                mr for mr in model_responses if mr.created_at and mr.created_at >= cutoff_date
            ]

            # Group by agent type
            agent_stats = {}
            for mr in recent_responses:
                agent_type = mr.agent_type
                if agent_type not in agent_stats:
                    agent_stats[agent_type] = {
                        "count": 0,
                        "total_tokens": 0,  # Would need to extract from metadata
                        "errors": 0,
                    }
                agent_stats[agent_type]["count"] += 1

            # Calculate averages
            for agent_type, stats in agent_stats.items():
                stats["avg_per_day"] = round(stats["count"] / days, 2) if days > 0 else 0

            return {
                "agent_statistics": agent_stats,
                "total_agent_calls": len(recent_responses),
                "unique_agent_types": len(agent_stats),
            }
        except Exception as e:
            logger.error(f"Error calculating agent performance metrics: {str(e)}", exc_info=True)
            return {}

    def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        try:
            # Get counts from database
            candidates = get_all_candidates()
            positions = get_all_positions()
            feedback_emails = get_all_feedback_emails()
            tickets = get_all_tickets()
            validation_errors = get_all_validation_errors()

            # Calculate health indicators
            total_candidates = len(candidates)
            active_candidates = len([c for c in candidates if c.status.value == "in_progress"])
            rejected_candidates = len([c for c in candidates if c.status.value == "rejected"])
            accepted_candidates = len([c for c in candidates if c.status.value == "accepted"])

            open_tickets = len([t for t in tickets if t.status.value == "open"])
            in_progress_tickets = len([t for t in tickets if t.status.value == "in_progress"])

            return {
                "total_candidates": total_candidates,
                "active_candidates": active_candidates,
                "rejected_candidates": rejected_candidates,
                "accepted_candidates": accepted_candidates,
                "total_positions": len(positions),
                "total_feedback_emails": len(feedback_emails),
                "total_tickets": len(tickets),
                "open_tickets": open_tickets,
                "in_progress_tickets": in_progress_tickets,
                "total_validation_errors": len(validation_errors),
                "system_status": "healthy" if len(validation_errors) < 10 else "warning",
            }
        except Exception as e:
            logger.error(f"Error calculating system health metrics: {str(e)}", exc_info=True)
            return {}

    def get_all_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get all metrics aggregated."""
        return {
            "feedback": self.get_feedback_metrics(days),
            "email_processing": self.get_email_processing_metrics(days),
            "rag": self.get_rag_metrics(days),
            "agent_performance": self.get_agent_performance_metrics(days),
            "system_health": self.get_system_health_metrics(),
            "costs": self.get_cost_metrics(days),  # Add cost metrics
            "period_days": days,
            "generated_at": datetime.now().isoformat(),
        }


# Global metrics service instance
metrics_service = MetricsService()
