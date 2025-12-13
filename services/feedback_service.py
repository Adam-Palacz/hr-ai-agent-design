"""Feedback generation service layer."""
from pathlib import Path
from typing import Optional

from core.logger import logger
from core.exceptions import LLMError
from agents.feedback_agent import FeedbackAgent
from models.cv_models import CVData
from models.feedback_models import HRFeedback, CandidateFeedback, FeedbackFormat
from models.job_models import JobOffer
from utils.html_formatter import format_feedback_as_html


class FeedbackService:
    """Service for generating candidate feedback."""
    
    def __init__(self, feedback_agent: FeedbackAgent):
        """
        Initialize feedback service.
        
        Args:
            feedback_agent: Initialized FeedbackAgent instance
        """
        self.agent = feedback_agent
        logger.info("FeedbackService initialized")
    
    def generate_feedback(
        self,
        cv_data: CVData,
        hr_feedback: HRFeedback,
        job_offer: Optional[JobOffer] = None,
        output_format: FeedbackFormat = FeedbackFormat.HTML,
        save_to_file: bool = False,
        output_dir: Optional[Path] = None
    ) -> CandidateFeedback:
        """
        Generate personalized feedback for candidate.
        
        Args:
            cv_data: Parsed CV data
            hr_feedback: HR evaluation feedback
            job_offer: Optional job offer with requirements
            save_to_file: Whether to save feedback to file
            output_dir: Directory to save feedback file (default: current directory)
            
        Returns:
            Generated CandidateFeedback object
            
        Raises:
            LLMError: If feedback generation fails
        """
        logger.info(f"Generating feedback for: {cv_data.full_name} (format: {output_format.value})")
        
        try:
            feedback = self.agent.generate_feedback(cv_data, hr_feedback, job_offer, output_format=output_format)
            logger.info(f"Successfully generated feedback for: {cv_data.full_name}")
            
            if save_to_file:
                # Save HTML feedback (only format we support now)
                if feedback.html_content:
                    html_path = self._save_feedback_html(feedback, cv_data, output_dir)
                    logger.info(f"HTML feedback saved to: {html_path}")
            
            return feedback
            
        except Exception as e:
            error_msg = f"Failed to generate feedback: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise LLMError(error_msg) from e
    
    # _save_feedback method removed - we only use HTML format now
    
    def _save_feedback_html(
        self,
        feedback: CandidateFeedback,
        cv_data: CVData,
        output_dir: Optional[Path] = None
    ) -> Path:
        """Save feedback to HTML file."""
        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"feedback_{cv_data.full_name.replace(' ', '_')}.html"
        output_path = output_dir / filename
        
        html_content = format_feedback_as_html(feedback)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    def get_feedback_html(self, feedback: CandidateFeedback, consent_for_other_positions: bool = None) -> str:
        """
        Get HTML formatted version of feedback.
        
        Args:
            feedback: CandidateFeedback object
            consent_for_other_positions: Optional boolean indicating if candidate consented to other positions
            
        Returns:
            HTML formatted string
        """
        return format_feedback_as_html(feedback, consent_for_other_positions=consent_for_other_positions)

