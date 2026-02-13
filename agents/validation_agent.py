"""Azure OpenAI agent for validating candidate feedback emails (no LangChain)."""

from typing import Optional

from models.cv_models import CVData
from models.feedback_models import HRFeedback
from models.job_models import JobOffer
from models.validation_models import ValidationResult
from prompts.validation_prompt import VALIDATION_PROMPT
from core.logger import logger
from agents.base_agent import BaseAgent
from utils.json_parser import parse_json_safe


class FeedbackValidatorAgent(BaseAgent):
    """Agent for validating candidate feedback emails."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 2,
    ):
        """
        Initialize Feedback Validator Agent using Azure OpenAI SDK (no LangChain).
        """
        super().__init__(model_name, temperature, api_key, timeout, max_retries)

        # Static format instructions describing ValidationResult JSON schema
        self.format_instructions = (
            "Return ONLY a single JSON object with the following structure:\n"
            "{\n"
            '  "status": "approved" | "rejected",\n'
            '  "is_approved": true | false,\n'
            '  "reasoning": "short explanation",\n'
            '  "issues_found": ["issue 1", "issue 2"],\n'
            '  "ethical_concerns": ["concern 1", "concern 2"],\n'
            '  "factual_errors": ["error 1", "error 2"],\n'
            '  "suggestions": ["suggestion 1", "suggestion 2"]\n'
            "}\n\n"
            "- Do NOT return a JSON schema or description.\n"
            "- Do NOT wrap the JSON in markdown code fences.\n"
            "- All list fields must be valid JSON arrays of strings."
        )

        # Store prompt template
        self.prompt_template = VALIDATION_PROMPT

    def validate_feedback(
        self,
        html_content: str,
        cv_data: CVData,
        hr_feedback: HRFeedback,
        job_offer: Optional[JobOffer] = None,
        candidate_id: Optional[int] = None,
        validation_number: Optional[int] = None,
    ) -> ValidationResult:
        """
        Validate feedback email using Azure OpenAI (no LangChain).
        """
        logger.info(f"Validating feedback email for: {cv_data.full_name}")

        # Format data for prompt
        cv_data_str = self._format_cv_data(cv_data)
        hr_feedback_str = self._format_hr_feedback(hr_feedback)

        if job_offer:
            job_offer_str = self._format_job_offer(job_offer)
        else:
            job_offer_str = "No job offer information provided"

        # Build prompt with format instructions
        prompt_text = self.prompt_template.format(
            html_content=html_content,
            cv_data=cv_data_str,
            hr_feedback=hr_feedback_str,
            job_offer=job_offer_str,
            format_instructions=self.format_instructions,
        )

        # Run validation via Azure OpenAI
        try:
            logger.info(f"Validating feedback email for: {cv_data.full_name}")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful JSON-producing validation assistant. "
                            "You must follow the format_instructions exactly."
                        ),
                    },
                    {"role": "user", "content": prompt_text},
                ],
                max_completion_tokens=2000,
                temperature=self.temperature,
            )

            raw_text = response.choices[0].message.content

            # Track model response (with token usage and cost)
            metadata = {"temperature": self.temperature}
            if validation_number is not None:
                metadata["validation_number"] = validation_number

            self._save_model_response(
                agent_type="validator",
                input_data={
                    "html_content": html_content,
                    "cv_data": cv_data_str,
                    "hr_feedback": hr_feedback_str,
                    "job_offer": job_offer_str,
                },
                output_data=raw_text,
                candidate_id=candidate_id,
                metadata=metadata,
                response=response,  # Pass response to extract tokens and costs
            )

            validation_result = self._parse_validation_from_text(raw_text)
            logger.info(
                f"Validation completed for {cv_data.full_name}: {validation_result.status.value}"
            )
            return validation_result
        except Exception as e:
            error_msg = f"Failed to validate feedback: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # On validation failure, reject by default for safety
            return ValidationResult(
                status="rejected",
                is_approved=False,
                reasoning=f"Validation process failed: {str(e)}. Email rejected for safety.",
                issues_found=["Validation process error"],
                ethical_concerns=[],
                factual_errors=[],
                suggestions=["Please review the validation process and try again."],
            )

    def _parse_validation_from_text(self, text: str) -> ValidationResult:
        """
        Parse ValidationResult from raw model text, handling common JSON issues.
        """
        if not text:
            raise ValueError("Empty response from model")

        # Parse JSON with fallback extraction
        data = parse_json_safe(text, fallback_to_extraction=True)

        # Map to ValidationResult, with sensible defaults
        status = data.get("status", "rejected")
        is_approved = bool(data.get("is_approved", False))
        reasoning = data.get("reasoning") or "No reasoning provided."
        issues_found = data.get("issues_found") or []
        ethical_concerns = data.get("ethical_concerns") or []
        factual_errors = data.get("factual_errors") or []
        suggestions = data.get("suggestions") or []

        # Ensure all list fields are lists of strings
        def ensure_str_list(value):
            if isinstance(value, list):
                return [str(v) for v in value]
            if not value:
                return []
            return [str(value)]

        return ValidationResult(
            status=status,
            is_approved=is_approved,
            reasoning=str(reasoning),
            issues_found=ensure_str_list(issues_found),
            ethical_concerns=ensure_str_list(ethical_concerns),
            factual_errors=ensure_str_list(factual_errors),
            suggestions=ensure_str_list(suggestions),
        )
