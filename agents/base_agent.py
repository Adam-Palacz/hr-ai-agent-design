"""Base agent class with common functionality."""

from typing import Optional, Any
from openai import AzureOpenAI

from config import settings
from utils.formatting import format_cv_data, format_hr_feedback, format_job_offer
from models.cv_models import CVData
from models.feedback_models import HRFeedback
from models.job_models import JobOffer

# Import for tracking model responses
try:
    from database.models import save_model_response
except ImportError:
    save_model_response = None


class BaseAgent:
    """Base class for all Azure OpenAI agents."""

    def __init__(
        self,
        model_name: str,
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 2,
    ):
        """
        Initialize base agent with Azure OpenAI client.

        Args:
            model_name: Azure OpenAI deployment name
            temperature: Model temperature
            api_key: Optional API key (uses settings if not provided)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.model_name = model_name
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries

        api_key_to_use = api_key or settings.api_key
        self.client = AzureOpenAI(
            api_version=settings.azure_openai_api_version,
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=api_key_to_use,
        )

    def _format_cv_data(self, cv_data: CVData) -> str:
        """Format CV data for prompt."""
        return format_cv_data(cv_data)

    def _format_hr_feedback(
        self, hr_feedback: HRFeedback, include_extraction_note: bool = False
    ) -> str:
        """Format HR feedback for prompt."""
        return format_hr_feedback(hr_feedback, include_extraction_note=include_extraction_note)

    def _format_job_offer(self, job_offer: JobOffer) -> str:
        """Format job offer for prompt."""
        return format_job_offer(job_offer)

    def _calculate_cost(
        self, input_tokens: int, output_tokens: int, model_name: Optional[str] = None
    ) -> float:
        """
        Calculate cost based on token usage and model pricing.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model_name: Optional model name (uses self.model_name if not provided)

        Returns:
            Cost in PLN (approximate, based on Azure OpenAI pricing)
        """
        model = model_name or self.model_name

        # Azure OpenAI pricing (per 1M tokens, approximate as of December 2025)
        # These are approximate values - actual pricing may vary by deployment
        pricing = {
            # GPT-4o mini (common for cost-effective operations)
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},  # USD per 1M tokens
            "gpt-4o": {"input": 2.50, "output": 10.00},  # USD per 1M tokens
            "gpt-4": {"input": 10.00, "output": 30.00},  # USD per 1M tokens
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},  # USD per 1M tokens
            # Default fallback (assume GPT-4o mini pricing)
            "default": {"input": 0.15, "output": 0.60},
        }

        # Try to match model name (case-insensitive, partial match)
        model_lower = model.lower()
        selected_pricing = pricing.get("default")

        for key, value in pricing.items():
            if key in model_lower or model_lower in key:
                selected_pricing = value
                break

        # Calculate cost in USD
        input_cost_usd = (input_tokens / 1_000_000) * selected_pricing["input"]
        output_cost_usd = (output_tokens / 1_000_000) * selected_pricing["output"]
        total_cost_usd = input_cost_usd + output_cost_usd

        # Convert to PLN (approximate exchange rate: 1 USD = 4.0 PLN)
        # This is a rough estimate - actual exchange rate may vary
        exchange_rate = 4.0
        total_cost_pln = total_cost_usd * exchange_rate

        return round(total_cost_pln, 4)

    def _extract_usage_from_response(self, response: Any) -> Optional[dict]:
        """
        Extract token usage from Azure OpenAI response.

        Args:
            response: Azure OpenAI response object

        Returns:
            Dict with token usage info or None if not available
        """
        try:
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                return {
                    "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(usage, "completion_tokens", 0),
                    "total_tokens": getattr(usage, "total_tokens", 0),
                }
        except Exception as e:
            from core.logger import logger

            logger.warning(f"Failed to extract usage from response: {str(e)}")

        return None

    def _save_model_response(
        self,
        agent_type: str,
        input_data: dict,
        output_data: str,
        candidate_id: Optional[int] = None,
        metadata: Optional[dict] = None,
        response: Optional[Any] = None,
    ):
        """
        Save model response to database if tracking is enabled.

        Args:
            agent_type: Type of agent
            input_data: Input data dictionary
            output_data: Output data (response text)
            candidate_id: Optional candidate ID
            metadata: Optional metadata dictionary
            response: Optional Azure OpenAI response object (for extracting tokens and costs)
        """
        if save_model_response:
            try:
                # Extract token usage and calculate cost if response is provided
                enhanced_metadata = metadata.copy() if metadata else {}

                if response:
                    usage_info = self._extract_usage_from_response(response)
                    if usage_info:
                        enhanced_metadata.update(
                            {
                                "input_tokens": usage_info["prompt_tokens"],
                                "output_tokens": usage_info["completion_tokens"],
                                "total_tokens": usage_info["total_tokens"],
                            }
                        )

                        # Calculate cost
                        cost = self._calculate_cost(
                            usage_info["prompt_tokens"],
                            usage_info["completion_tokens"],
                            self.model_name,
                        )
                        enhanced_metadata["cost_pln"] = cost

                save_model_response(
                    agent_type=agent_type,
                    model_name=self.model_name,
                    input_data=input_data,
                    output_data=output_data,
                    candidate_id=candidate_id,
                    metadata=enhanced_metadata,
                )
            except Exception as e:
                from core.logger import logger

                logger.warning(f"Failed to save model response: {str(e)}")
