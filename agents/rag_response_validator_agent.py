"""Azure OpenAI agent for validating RAG-generated responses to candidate inquiries (no LangChain)."""

from typing import Optional, List, Dict

from models.validation_models import ValidationResult
from prompts.rag_response_validation_prompt import RAG_RESPONSE_VALIDATION_PROMPT
from core.logger import logger
from agents.base_agent import BaseAgent
from utils.json_parser import parse_json_safe


class RAGResponseValidatorAgent(BaseAgent):
    """Agent for validating RAG-generated responses to candidate inquiries."""

    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        timeout: int = 60,
        max_retries: int = 2,
    ):
        """
        Initialize RAG Response Validator Agent using Azure OpenAI SDK (no LangChain).
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
        self.prompt_template = RAG_RESPONSE_VALIDATION_PROMPT

    def validate_rag_response(
        self,
        generated_response: str,
        email_subject: str,
        email_body: str,
        sender_email: str,
        rag_sources: List[Dict],
        validation_number: Optional[int] = None,
    ) -> ValidationResult:
        """
        Validate RAG-generated response using Azure OpenAI (no LangChain).

        Args:
            generated_response: The AI-generated response to validate
            email_subject: Original email subject
            email_body: Original email body
            sender_email: Sender's email address
            rag_sources: List of RAG source documents used to generate the response
            validation_number: Optional validation number for tracking

        Returns:
            ValidationResult object
        """
        logger.info(f"Validating RAG response for inquiry from {sender_email}")

        # Format RAG sources for prompt
        rag_sources_str = self._format_rag_sources(rag_sources)

        # Build prompt with format instructions
        prompt_text = self.prompt_template.format(
            generated_response=generated_response,
            email_subject=email_subject,
            email_body=email_body,
            sender_email=sender_email,
            rag_sources=rag_sources_str,
            format_instructions=self.format_instructions,
        )

        # Run validation via Azure OpenAI
        try:
            logger.info(f"Validating RAG response for inquiry from {sender_email}")

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

            # Track model response (optional - can be extended to save to database)
            # For now, just log it
            logger.debug(f"Validation response: {raw_text[:500]}...")

            validation_result = self._parse_validation_from_text(raw_text)
            logger.info(
                f"Validation completed for {sender_email}: {validation_result.status.value} "
                f"(is_approved: {validation_result.is_approved})"
            )
            return validation_result
        except Exception as e:
            error_msg = f"Failed to validate RAG response: {str(e)}"
            logger.error(error_msg, exc_info=True)

            # On validation failure, reject by default for safety
            return ValidationResult(
                status="rejected",
                is_approved=False,
                reasoning=f"Validation process failed: {str(e)}. Response rejected for safety.",
                issues_found=["Validation process error"],
                ethical_concerns=[],
                factual_errors=[],
                suggestions=["Please review the validation process and try again."],
            )

    def _format_rag_sources(self, rag_sources: List[Dict]) -> str:
        """Format RAG sources for prompt."""
        if not rag_sources:
            return "No RAG sources provided."

        formatted = []
        for i, source in enumerate(rag_sources, 1):
            metadata = source.get("metadata", {})
            document = source.get("document", "")
            source_name = metadata.get("source", "Unknown source")
            score = metadata.get("score", None)

            source_text = f"--- Source {i}: {source_name} ---\n"
            if score is not None:
                source_text += f"Relevance score: {score:.4f}\n"
            source_text += f"Content:\n{document}\n"
            formatted.append(source_text)

        return "\n".join(formatted)

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
