"""LangChain agent for correcting candidate feedback emails based on validation feedback."""
import json
from typing import Optional

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    try:
        from langchain.chat_models import ChatOpenAI
    except ImportError:
        from langchain_community.chat_models import ChatOpenAI

# Try modern LangChain imports first, fallback to legacy
try:
    from langchain_core.output_parsers import PydanticOutputParser
except ImportError:
    try:
        from langchain.output_parsers import PydanticOutputParser
    except ImportError:
        from langchain_core.output_parsers.pydantic import PydanticOutputParser

from models.cv_models import CVData
from models.feedback_models import HRFeedback
from models.job_models import JobOffer
from models.validation_models import ValidationResult, CorrectedFeedback
from prompts.correction_prompt import CORRECTION_PROMPT
from core.logger import logger

# Import for tracking model responses
try:
    from database.models import save_model_response
except ImportError:
    save_model_response = None


class FeedbackCorrectionAgent:
    """Agent for correcting candidate feedback emails based on validation feedback."""
    
    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.3,
        api_key: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 2
    ):
        """
        Initialize Feedback Correction Agent.
        
        Args:
            model_name: Name of the LLM model to use (default: gpt-4o)
            temperature: Temperature for LLM generation (default: 0.3 for balanced creativity)
            api_key: OpenAI API key (if not set, uses environment variable)
            timeout: Request timeout in seconds (default: 120)
            max_retries: Maximum number of retries on failure (default: 2)
        """
        self.model_name = model_name
        
        # Handle special temperature requirements for gpt-5 models
        model_lower = model_name.lower()
        if model_lower.startswith("gpt-5") and "chat" not in model_lower:
            if temperature != 1.0 and temperature is not None:
                logger.warning(
                    f"Model {model_name} only supports temperature=1.0 or unset. "
                    f"Adjusting temperature from {temperature} to 1.0"
                )
                temperature = 1.0
        
        # Initialize ChatOpenAI
        try:
            llm_kwargs = {
                "model": model_name,
                "temperature": temperature,
                "timeout": timeout,
                "max_retries": max_retries,
            }
            if api_key:
                llm_kwargs["openai_api_key"] = api_key
            self.llm = ChatOpenAI(**llm_kwargs)
        except TypeError:
            # Fallback for older LangChain versions
            llm_kwargs = {
                "model_name": model_name,
                "temperature": temperature,
            }
            if api_key:
                llm_kwargs["openai_api_key"] = api_key
            try:
                llm_kwargs["timeout"] = timeout
                llm_kwargs["max_retries"] = max_retries
            except TypeError:
                logger.warning("Older LangChain version detected - timeout and max_retries may not be supported")
            self.llm = ChatOpenAI(**llm_kwargs)
        
        self.output_parser = PydanticOutputParser(pydantic_object=CorrectedFeedback)
        
        # Get format instructions
        base_instructions = self.output_parser.get_format_instructions()
        # Add explicit instruction to return actual data, not schema
        self.format_instructions = f"""{base_instructions}

CRITICAL: Return ACTUAL DATA VALUES, not a schema description. 
The response must be a JSON object with the html_content field containing the actual corrected HTML email content.
Example: {{"html_content": "<!DOCTYPE html>\\n<html>...</html>", "corrections_made": ["Fixed factual error", "Removed discriminatory language"]}}
DO NOT return: {{"description": "...", "properties": {{...}}, "required": [...]}}"""
        
        # Store prompt template
        self.prompt_template = CORRECTION_PROMPT
        
        # Try to use modern LCEL approach
        try:
            self.use_lcel = True
        except (TypeError, AttributeError):
            self.use_lcel = False
    
    def correct_feedback(
        self,
        original_html: str,
        validation_result: ValidationResult,
        cv_data: CVData,
        hr_feedback: HRFeedback,
        job_offer: Optional[JobOffer] = None,
        candidate_id: Optional[int] = None
    ) -> CorrectedFeedback:
        """
        Correct feedback email based on validation feedback.
        
        Args:
            original_html: Original HTML content that needs correction
            validation_result: ValidationResult with issues and reasoning
            cv_data: Parsed CV data for fact-checking
            hr_feedback: HR feedback for reference
            job_offer: Optional job offer information
            
        Returns:
            CorrectedFeedback object with corrected HTML and list of corrections made
        """
        logger.info(f"Correcting feedback email for: {cv_data.full_name}")
        
        # Format data for prompt
        cv_data_str = self._format_cv_data(cv_data)
        hr_feedback_str = self._format_hr_feedback(hr_feedback)
        
        if job_offer:
            job_offer_str = self._format_job_offer(job_offer)
        else:
            job_offer_str = "No job offer information provided"
        
        # Format validation feedback
        issues_str = "\n".join([f"- {issue}" for issue in validation_result.issues_found]) if validation_result.issues_found else "None"
        ethical_str = "\n".join([f"- {concern}" for concern in validation_result.ethical_concerns]) if validation_result.ethical_concerns else "None"
        factual_str = "\n".join([f"- {error}" for error in validation_result.factual_errors]) if validation_result.factual_errors else "None"
        
        # Build prompt with format instructions
        prompt_with_format = self.prompt_template.partial(
            format_instructions=self.format_instructions
        )
        
        # Build chain
        try:
            chain = prompt_with_format | self.llm | self.output_parser
            use_lcel = True
        except (TypeError, AttributeError):
            use_lcel = False
        
        # Run correction
        try:
            if use_lcel:
                input_data = {
                    "original_html": original_html,
                    "validation_reasoning": validation_result.reasoning,
                    "issues_found": issues_str,
                    "ethical_concerns": ethical_str,
                    "factual_errors": factual_str,
                    "cv_data": cv_data_str,
                    "hr_feedback": hr_feedback_str,
                    "job_offer": job_offer_str
                }
                corrected_feedback = chain.invoke(input_data)
                logger.info(f"Correction completed for {cv_data.full_name}. Corrections made: {len(corrected_feedback.corrections_made)}")
                
                # Track model response
                if save_model_response:
                    try:
                        save_model_response(
                            agent_type="corrector",
                            model_name=self.model_name,
                            input_data=input_data,
                            output_data=corrected_feedback.dict() if hasattr(corrected_feedback, 'dict') else str(corrected_feedback),
                            candidate_id=candidate_id,
                            metadata={"temperature": getattr(self.llm, 'temperature', None)}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save model response: {str(e)}")
                
                return corrected_feedback
            else:
                # Fallback for older LangChain versions
                formatted_prompt = prompt_with_format.format(
                    original_html=original_html,
                    validation_reasoning=validation_result.reasoning,
                    issues_found=issues_str,
                    ethical_concerns=ethical_str,
                    factual_errors=factual_str,
                    cv_data=cv_data_str,
                    hr_feedback=hr_feedback_str,
                    job_offer=job_offer_str
                )
                response = self.llm.invoke(formatted_prompt)
                result = response.content if hasattr(response, 'content') else str(response)
                
                # Try to extract JSON from the response
                if "```json" in result:
                    json_start = result.find("```json") + 7
                    json_end = result.find("```", json_start)
                    result = result[json_start:json_end].strip()
                elif "```" in result:
                    json_start = result.find("```") + 3
                    json_end = result.find("```", json_start)
                    result = result[json_start:json_end].strip()
                
                corrected_feedback = self.output_parser.parse(result)
                logger.info(f"Correction completed for {cv_data.full_name}. Corrections made: {len(corrected_feedback.corrections_made)}")
                return corrected_feedback
        except Exception as e:
            error_msg = f"Failed to correct feedback: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e
    
    def _format_cv_data(self, cv_data: CVData) -> str:
        """Format CV data for prompt."""
        lines = [
            f"Name: {cv_data.full_name}",
            f"Email: {cv_data.email or 'N/A'}",
            f"Phone: {cv_data.phone or 'N/A'}",
            f"Location: {cv_data.location or 'N/A'}",
        ]
        
        if cv_data.summary:
            lines.append(f"\nSummary:\n{cv_data.summary}")
        
        if cv_data.experience:
            lines.append("\nExperience:")
            for exp in cv_data.experience:
                lines.append(f"  - {exp.position} at {exp.company} ({exp.start_date or 'N/A'} - {exp.end_date or 'N/A'})")
                if exp.description:
                    lines.append(f"    {exp.description}")
        
        if cv_data.education:
            lines.append("\nEducation:")
            for edu in cv_data.education:
                lines.append(f"  - {edu.degree} in {edu.field_of_study or 'N/A'} from {edu.institution}")
        
        if cv_data.skills:
            lines.append("\nSkills:")
            for skill in cv_data.skills:
                lines.append(f"  - {skill.name} ({skill.proficiency or 'N/A'})")
        
        return "\n".join(lines)
    
    def _format_hr_feedback(self, hr_feedback: HRFeedback) -> str:
        """Format HR feedback for prompt."""
        lines = [
            f"Decision: {hr_feedback.decision.value}",
        ]
        
        if hr_feedback.notes:
            lines.append(f"\nHR Notes:\n{hr_feedback.notes}")
        
        if hr_feedback.position_applied:
            lines.append(f"\nPosition Applied: {hr_feedback.position_applied}")
        
        if hr_feedback.missing_requirements:
            lines.append(f"\nMissing Requirements: {', '.join(hr_feedback.missing_requirements)}")
        
        return "\n".join(lines)
    
    def _format_job_offer(self, job_offer: JobOffer) -> str:
        """Format job offer for prompt."""
        lines = [
            f"Job Title: {job_offer.title}",
        ]
        
        if job_offer.company:
            lines.append(f"Company: {job_offer.company}")
        
        if job_offer.location:
            lines.append(f"Location: {job_offer.location}")
        
        if job_offer.description:
            lines.append(f"\nJob Description:\n{job_offer.description}")
        
        return "\n".join(lines)

