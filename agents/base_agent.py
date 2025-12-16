"""Base agent class with common functionality."""

from typing import Optional
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
        max_retries: int = 2
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
    
    def _format_hr_feedback(self, hr_feedback: HRFeedback, include_extraction_note: bool = False) -> str:
        """Format HR feedback for prompt."""
        return format_hr_feedback(hr_feedback, include_extraction_note=include_extraction_note)
    
    def _format_job_offer(self, job_offer: JobOffer) -> str:
        """Format job offer for prompt."""
        return format_job_offer(job_offer)
    
    def _save_model_response(
        self,
        agent_type: str,
        input_data: dict,
        output_data: str,
        candidate_id: Optional[int] = None,
        metadata: Optional[dict] = None
    ):
        """Save model response to database if tracking is enabled."""
        if save_model_response:
            try:
                save_model_response(
                    agent_type=agent_type,
                    model_name=self.model_name,
                    input_data=input_data,
                    output_data=output_data,
                    candidate_id=candidate_id,
                    metadata=metadata or {},
                )
            except Exception as e:
                from core.logger import logger
                logger.warning(f"Failed to save model response: {str(e)}")

