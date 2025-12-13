"""Feedback generation service layer."""
from pathlib import Path
from typing import Optional, Dict, Any

from core.logger import logger
from core.exceptions import LLMError
from agents.feedback_agent import FeedbackAgent
from agents.validation_agent import FeedbackValidatorAgent
from agents.correction_agent import FeedbackCorrectionAgent
from models.cv_models import CVData
from models.feedback_models import HRFeedback, CandidateFeedback, FeedbackFormat
from models.job_models import JobOffer
from models.validation_models import ValidationResult
from utils.html_formatter import format_feedback_as_html


class FeedbackService:
    """Service for generating candidate feedback."""
    
    def __init__(
        self, 
        feedback_agent: FeedbackAgent,
        validator_agent: Optional[FeedbackValidatorAgent] = None,
        correction_agent: Optional[FeedbackCorrectionAgent] = None,
        max_validation_iterations: int = 3
    ):
        """
        Initialize feedback service.
        
        Args:
            feedback_agent: Initialized FeedbackAgent instance
            validator_agent: Optional FeedbackValidatorAgent instance (if None, validation is skipped)
            correction_agent: Optional FeedbackCorrectionAgent instance (if None, correction is skipped)
            max_validation_iterations: Maximum number of validation-correction cycles (default: 3)
        """
        self.agent = feedback_agent
        self.validator = validator_agent
        self.corrector = correction_agent
        self.max_iterations = max_validation_iterations
        self.validation_failed = False
        self.validation_error_info = None
        logger.info("FeedbackService initialized")
    
    def generate_feedback(
        self,
        cv_data: CVData,
        hr_feedback: HRFeedback,
        job_offer: Optional[JobOffer] = None,
        output_format: FeedbackFormat = FeedbackFormat.HTML,
        save_to_file: bool = False,
        output_dir: Optional[Path] = None,
        enable_validation: bool = True,
        candidate_id: Optional[int] = None
    ) -> tuple[CandidateFeedback, bool, Optional[Dict[str, Any]]]:
        """
        Generate personalized feedback for candidate with optional validation and correction.
        
        Args:
            cv_data: Parsed CV data
            hr_feedback: HR evaluation feedback
            job_offer: Optional job offer with requirements
            output_format: Feedback format (default: HTML)
            save_to_file: Whether to save feedback to file
            output_dir: Directory to save feedback file (default: current directory)
            enable_validation: Whether to enable validation and correction (default: True)
            
        Returns:
            Tuple of (CandidateFeedback, is_validated: bool, error_info: Optional[Dict])
            - is_validated: True if feedback was validated successfully, False if validation failed
            - error_info: Dict with error details if validation failed, None otherwise
            
        Raises:
            LLMError: If feedback generation fails
        """
        logger.info(f"Generating feedback for: {cv_data.full_name} (format: {output_format.value})")
        
        try:
            # Step 1: Generate initial feedback
            feedback = self.agent.generate_feedback(cv_data, hr_feedback, job_offer, output_format=output_format, candidate_id=candidate_id)
            logger.info(f"Successfully generated initial feedback for: {cv_data.full_name}")
            
            # Step 2: Validate and correct if validation is enabled
            is_validated = True
            validation_error_info = None
            if enable_validation and self.validator and self.corrector:
                feedback, is_validated, validation_error_info = self._validate_and_correct(
                    feedback, 
                    cv_data, 
                    hr_feedback, 
                    job_offer,
                    candidate_id=candidate_id
                )
                # Store validation status for potential error saving
                self.validation_failed = not is_validated
                self.validation_error_info = validation_error_info
            
            # Return feedback with validation status
            return feedback, is_validated, validation_error_info
            
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
    
    def _validate_and_correct(
        self,
        feedback: CandidateFeedback,
        cv_data: CVData,
        hr_feedback: HRFeedback,
        job_offer: Optional[JobOffer] = None,
        candidate_id: Optional[int] = None
    ) -> tuple[CandidateFeedback, bool, Optional[Dict[str, Any]]]:
        """
        Validate feedback and correct if needed.
        
        Args:
            feedback: Initial CandidateFeedback object
            cv_data: Parsed CV data
            hr_feedback: HR evaluation feedback
            job_offer: Optional job offer information
            candidate_id: Optional candidate ID
            
        Returns:
            Tuple of (CandidateFeedback, is_validated: bool, error_info: Optional[Dict])
            - is_validated: True if feedback was approved, False if validation failed after max iterations
            - error_info: Dict with error details if validation failed, None otherwise
        """
        current_feedback = feedback
        iteration = 0
        all_validation_results = []
        
        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"Validation iteration {iteration}/{self.max_iterations} for {cv_data.full_name}")
            
            # Validate current feedback
            validation_result = self.validator.validate_feedback(
                current_feedback.html_content,
                cv_data,
                hr_feedback,
                job_offer,
                candidate_id=candidate_id
            )
            
            # Store validation result
            all_validation_results.append({
                'iteration': iteration,
                'is_approved': validation_result.is_approved,
                'status': validation_result.status.value,
                'reasoning': validation_result.reasoning,
                'issues_found': validation_result.issues_found,
                'ethical_concerns': validation_result.ethical_concerns,
                'factual_errors': validation_result.factual_errors,
                'suggestions': validation_result.suggestions
            })
            
            if validation_result.is_approved:
                logger.info(f"Feedback approved after {iteration} iteration(s) for {cv_data.full_name}")
                return current_feedback, True, None
            
            # Feedback was rejected, need to correct
            logger.warning(
                f"Feedback rejected in iteration {iteration} for {cv_data.full_name}. "
                f"Reason: {validation_result.reasoning}"
            )
            
            if iteration >= self.max_iterations:
                logger.error(
                    f"Maximum validation iterations ({self.max_iterations}) reached for {cv_data.full_name}. "
                    f"Validation failed - feedback will not be sent."
                )
                # Return error info
                error_info = {
                    'validation_results': all_validation_results,
                    'final_feedback_html': current_feedback.html_content,
                    'max_iterations_reached': True
                }
                return current_feedback, False, error_info
            
            # Correct the feedback
            try:
                corrected = self.corrector.correct_feedback(
                    current_feedback.html_content,
                    validation_result,
                    cv_data,
                    hr_feedback,
                    job_offer,
                    candidate_id=candidate_id
                )
                
                # Update current feedback with corrected version
                current_feedback = CandidateFeedback(html_content=corrected.html_content)
                logger.info(
                    f"Feedback corrected for {cv_data.full_name}. "
                    f"Corrections made: {', '.join(corrected.corrections_made)}"
                )
            except Exception as e:
                logger.error(f"Failed to correct feedback in iteration {iteration}: {str(e)}")
                # If correction fails, return error info
                error_info = {
                    'validation_results': all_validation_results,
                    'final_feedback_html': current_feedback.html_content,
                    'correction_failed': True,
                    'correction_error': str(e)
                }
                return current_feedback, False, error_info
        
        # Should not reach here, but return current feedback as fallback
        return current_feedback, False, {'validation_results': all_validation_results}
    
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

