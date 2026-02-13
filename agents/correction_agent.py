"""Azure OpenAI agent for correcting candidate feedback emails (no LangChain)."""

from typing import Optional

from models.cv_models import CVData
from models.feedback_models import HRFeedback
from models.job_models import JobOffer
from models.validation_models import ValidationResult, CorrectedFeedback
from prompts.correction_prompt import CORRECTION_PROMPT
from core.logger import logger
from agents.base_agent import BaseAgent
from utils.json_parser import parse_json_safe


class FeedbackCorrectionAgent(BaseAgent):
    """Agent for correcting candidate feedback emails based on validation feedback."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.3,
        api_key: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 2,
    ):
        """
        Initialize Feedback Correction Agent using Azure OpenAI SDK (no LangChain).
        """
        super().__init__(model_name, temperature, api_key, timeout, max_retries)

        # Static format instructions describing CorrectedFeedback schema
        self.format_instructions = (
            "Return ONLY a single JSON object with the following structure:\n"
            "{\n"
            '  "html_content": "<!DOCTYPE html>\\n<html>...corrected email HTML...</html>",\n'
            '  "corrections_made": ["correction 1", "correction 2"],\n'
            '  "explanation": "short explanation of changes"\n'
            "}\n\n"
            "- corrections_made must be a list of strings, each describing one change.\n"
            "- Do NOT return a JSON schema or description.\n"
            "- Do NOT wrap the JSON in markdown code fences."
        )

        # Store prompt template
        self.prompt_template = CORRECTION_PROMPT

    def correct_feedback(
        self,
        original_html: str,
        validation_result: ValidationResult,
        cv_data: CVData,
        hr_feedback: HRFeedback,
        job_offer: Optional[JobOffer] = None,
        candidate_id: Optional[int] = None,
        correction_number: Optional[int] = None,
    ) -> CorrectedFeedback:
        """
        Correct feedback email based on validation feedback using Azure OpenAI.
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
        issues_str = (
            "\n".join([f"- {issue}" for issue in validation_result.issues_found])
            if validation_result.issues_found
            else "None"
        )
        ethical_str = (
            "\n".join([f"- {concern}" for concern in validation_result.ethical_concerns])
            if validation_result.ethical_concerns
            else "None"
        )
        factual_str = (
            "\n".join([f"- {error}" for error in validation_result.factual_errors])
            if validation_result.factual_errors
            else "None"
        )

        # Build prompt with format instructions
        prompt_text = self.prompt_template.format(
            original_html=original_html,
            validation_reasoning=validation_result.reasoning,
            issues_found=issues_str,
            ethical_concerns=ethical_str,
            factual_errors=factual_str,
            cv_data=cv_data_str,
            hr_feedback=hr_feedback_str,
            job_offer=job_offer_str,
            format_instructions=self.format_instructions,
        )

        # Run correction
        try:
            logger.info(f"Correcting feedback email for: {cv_data.full_name}")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful JSON-producing correction assistant. "
                            "You must follow the format_instructions exactly."
                        ),
                    },
                    {"role": "user", "content": prompt_text},
                ],
                max_completion_tokens=3000,
                temperature=self.temperature,
            )

            raw_text = response.choices[0].message.content

            # Track model response (with token usage and cost)
            metadata = {"temperature": self.temperature}
            if correction_number is not None:
                metadata["correction_number"] = correction_number

            self._save_model_response(
                agent_type="corrector",
                input_data={
                    "original_html": original_html,
                    "validation_reasoning": validation_result.reasoning,
                    "issues_found": issues_str,
                    "ethical_concerns": ethical_str,
                    "factual_errors": factual_str,
                    "cv_data": cv_data_str,
                    "hr_feedback": hr_feedback_str,
                    "job_offer": job_offer_str,
                },
                output_data=raw_text,
                candidate_id=candidate_id,
                response=response,  # Pass response to extract tokens and costs
                metadata=metadata,
            )

            corrected_feedback = self._parse_correction_from_text(raw_text)
            logger.info(
                f"Correction completed for {cv_data.full_name}. "
                f"Corrections made: {len(corrected_feedback.corrections_made)}"
            )
            return corrected_feedback
        except Exception as e:
            error_msg = f"Failed to correct feedback: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg) from e

    def _parse_correction_from_text(self, text: str) -> CorrectedFeedback:
        """
        Parse CorrectedFeedback from raw model text, handling common JSON issues.
        """
        if not text:
            raise ValueError("Empty response from model")

        original_text = text

        # Try to parse JSON
        try:
            data = parse_json_safe(text, fallback_to_extraction=True)
        except ValueError:
            # No JSON at all – treat as plain HTML correction without metadata
            logger.warning("No JSON detected in correction output, using raw text as HTML.")
            return CorrectedFeedback(
                html_content=self._wrap_html_if_needed(original_text),
                corrections_made=["Used raw model output as HTML (no structured JSON)"],
                explanation="Model did not return valid JSON; raw output was wrapped as HTML.",
            )

        html = data.get("html_content")
        if not html or not isinstance(html, str):
            raise ValueError("html_content field is required and must be a non-empty string")

        corrections = data.get("corrections_made") or []
        explanation = data.get("explanation") or ""

        # Ensure corrections_made is a list of strings
        if not isinstance(corrections, list):
            corrections = [str(corrections)]
        else:
            corrections = [str(c) for c in corrections]

        return CorrectedFeedback(
            html_content=html,
            corrections_made=corrections,
            explanation=str(explanation),
        )

    @staticmethod
    def _wrap_html_if_needed(content: str) -> str:
        """If content is not full HTML, wrap it in a minimal HTML template."""
        lower = content.lower()
        if "<html" in lower or "<body" in lower:
            return content

        return (
            "<!DOCTYPE html>\n"
            '<html lang="pl">\n'
            "<head>\n"
            '    <meta charset="UTF-8">\n'
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            "    <title>Odpowiedź na aplikację</title>\n"
            "</head>\n"
            '<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; '
            'max-width: 600px; margin: 0 auto; padding: 20px;">\n'
            f"    {content}\n"
            "</body>\n"
            "</html>"
        )
