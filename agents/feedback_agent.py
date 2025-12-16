"""Azure OpenAI agent for generating personalized candidate feedback (no LangChain)."""

from typing import Optional

from models.cv_models import CVData
from models.feedback_models import HRFeedback, CandidateFeedback, FeedbackFormat
from models.job_models import JobOffer
from prompts.feedback_generation_prompt import FEEDBACK_GENERATION_PROMPT
from core.logger import logger
from agents.base_agent import BaseAgent
from utils.json_parser import parse_json_safe


class FeedbackAgent(BaseAgent):
    """Agent for generating personalized feedback to candidates."""
    
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 2
    ):
        """
        Initialize Feedback Agent using Azure OpenAI SDK (no LangChain).
        """
        super().__init__(model_name, temperature, api_key, timeout, max_retries)

        # Static format instructions (we no longer rely on LangChain parsers)
        self.format_instructions = (
            "Return ONLY a single JSON object with the following structure:\n"
            '{\n'
            '  "html_content": "<!DOCTYPE html>\\n<html>...complete email HTML...</html>"\n'
            "}\n\n"
            "- Do NOT return a JSON schema, OpenAPI schema, or description of fields.\n"
            "- Do NOT wrap the JSON in markdown code fences.\n"
            "- Do NOT include any extra top-level keys besides html_content.\n"
            "- The html_content value must be a valid HTML email as a single string."
        )

        # Store prompt template for later use
        self.prompt_template = FEEDBACK_GENERATION_PROMPT
    
    def generate_feedback(
        self,
        cv_data: CVData,
        hr_feedback: HRFeedback,
        job_offer: Optional[JobOffer] = None,
        output_format: FeedbackFormat = FeedbackFormat.HTML,
        candidate_id: Optional[int] = None,
        recruitment_stage: Optional[str] = None
    ) -> CandidateFeedback:
        """
        Generate personalized feedback for a candidate using Azure OpenAI.
        """
        # Convert CV data to formatted string
        cv_data_str = self._format_cv_data(cv_data)
        
        # Convert HR feedback to formatted string (with extraction note for feedback generation)
        hr_feedback_str = self._format_hr_feedback(hr_feedback, include_extraction_note=True)
        
        # Convert job offer to formatted string
        if job_offer:
            job_offer_str = self._format_job_offer(job_offer)
        else:
            job_offer_str = "No job offer information provided"
        
        # Get candidate name
        candidate_name = cv_data.full_name
        
        # Format output format for prompt
        format_str = output_format.value if isinstance(output_format, FeedbackFormat) else str(output_format)
        
        # Format recruitment stage for prompt
        recruitment_stage_str = recruitment_stage or "Pierwsza selekcja"
        
        # Build prompt with format instructions and output format
        prompt_text = self.prompt_template.format(
            cv_data=cv_data_str,
            hr_feedback=hr_feedback_str,
            job_offer=job_offer_str,
            candidate_name=candidate_name,
            recruitment_stage=recruitment_stage_str,
            format_instructions=self.format_instructions,
            output_format=format_str,
        )

        # Call Azure OpenAI chat completions
        try:
            logger.info(f"Generating feedback for candidate: {candidate_name} (stage: {recruitment_stage_str})")

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a careful JSON-producing assistant. "
                            "You must follow the format_instructions exactly."
                        ),
                    },
                    {"role": "user", "content": prompt_text},
                ],
                max_completion_tokens=4000,
                temperature=self.temperature,
            )

            raw_text = response.choices[0].message.content

            # Track model response
            self._save_model_response(
                agent_type="feedback_generator",
                input_data={
                    "cv_data": cv_data_str,
                    "hr_feedback": hr_feedback_str,
                    "job_offer": job_offer_str,
                    "candidate_name": candidate_name,
                    "recruitment_stage": recruitment_stage_str,
                },
                output_data=raw_text,
                candidate_id=candidate_id,
                metadata={"temperature": self.temperature},
            )

            # Parse JSON into CandidateFeedback
            feedback = self._parse_feedback_from_text(raw_text)
            logger.info(f"Feedback generated successfully for {candidate_name}")
            return feedback
        except Exception as e:
            # Fallback: try to parse whatever we got in `raw_text`
            try:
                feedback = self._parse_feedback_from_text(raw_text)
                logger.warning("Feedback parsed using fallback parser after initial error.")
                return feedback
            except Exception as final_error:
                raise Exception(f"Failed to parse feedback: {str(final_error)}. Original error: {str(e)}")

    def _parse_feedback_from_text(self, text: str) -> CandidateFeedback:
        """
        Parse CandidateFeedback from raw model text, handling common JSON issues.
        """
        if not text:
            raise ValueError("Empty response from model")

        # Try to parse JSON
        try:
            data = parse_json_safe(text, fallback_to_extraction=True)
        except ValueError:
            # No JSON at all – treat full text as HTML
            logger.warning("No JSON detected in model output, using raw text as HTML.")
            return CandidateFeedback(html_content=self._wrap_html_if_needed(text))

        # Validate html_content
        html = data.get("html_content")
        if not html or not isinstance(html, str):
            raise ValueError("html_content field is required and must be a non-empty string")

        return CandidateFeedback(html_content=html)

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
    
    

