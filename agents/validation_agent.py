"""LangChain agent for validating candidate feedback emails."""
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
from models.validation_models import ValidationResult
from prompts.validation_prompt import VALIDATION_PROMPT
from core.logger import logger

# Import for tracking model responses
try:
    from database.models import save_model_response
except ImportError:
    save_model_response = None


class FeedbackValidatorAgent:
    """Agent for validating candidate feedback emails."""
    
    def __init__(
        self,
        model_name: str = "gpt-4o",
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        timeout: int = 120,
        max_retries: int = 2
    ):
        """
        Initialize Feedback Validator Agent.
        
        Args:
            model_name: Name of the LLM model to use (default: gpt-4o for better validation)
            temperature: Temperature for LLM generation (default: 0.0 for strict validation)
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
        
        self.output_parser = PydanticOutputParser(pydantic_object=ValidationResult)
        
        # Get format instructions
        self.format_instructions = self.output_parser.get_format_instructions()
        
        # Store prompt template
        self.prompt_template = VALIDATION_PROMPT
        
        # Try to use modern LCEL approach
        try:
            self.use_lcel = True
        except (TypeError, AttributeError):
            self.use_lcel = False
    
    def validate_feedback(
        self,
        html_content: str,
        cv_data: CVData,
        hr_feedback: HRFeedback,
        job_offer: Optional[JobOffer] = None,
        candidate_id: Optional[int] = None
    ) -> ValidationResult:
        """
        Validate feedback email.
        
        Args:
            html_content: HTML content of the feedback email to validate
            cv_data: Parsed CV data for fact-checking
            hr_feedback: HR feedback for comparison
            job_offer: Optional job offer information
            
        Returns:
            ValidationResult object with validation status and reasoning
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
        prompt_with_format = self.prompt_template.partial(
            format_instructions=self.format_instructions
        )
        
        # Build chain
        try:
            chain = prompt_with_format | self.llm | self.output_parser
            use_lcel = True
        except (TypeError, AttributeError):
            use_lcel = False
        
        # Run validation
        try:
            if use_lcel:
                input_data = {
                    "html_content": html_content,
                    "cv_data": cv_data_str,
                    "hr_feedback": hr_feedback_str,
                    "job_offer": job_offer_str
                }
                validation_result = chain.invoke(input_data)
                logger.info(f"Validation completed for {cv_data.full_name}: {validation_result.status.value}")
                
                # Track model response
                if save_model_response:
                    try:
                        save_model_response(
                            agent_type="validator",
                            model_name=self.model_name,
                            input_data=input_data,
                            output_data=validation_result.dict() if hasattr(validation_result, 'dict') else str(validation_result),
                            candidate_id=candidate_id,
                            metadata={"temperature": getattr(self.llm, 'temperature', None)}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save model response: {str(e)}")
                
                return validation_result
            else:
                # Fallback for older LangChain versions
                formatted_prompt = prompt_with_format.format(
                    html_content=html_content,
                    cv_data=cv_data_str,
                    hr_feedback=hr_feedback_str,
                    job_offer=job_offer_str
                )
                response = self.llm.invoke(formatted_prompt)
                result = response.content if hasattr(response, 'content') else str(response)
                validation_result = self.output_parser.parse(result)
                logger.info(f"Validation completed for {cv_data.full_name}: {validation_result.status.value}")
                return validation_result
        except Exception as e:
            error_msg = f"Failed to validate feedback: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Try to parse the error output manually if it's a JSON parsing error
            if "Invalid json output" in str(e) or "OutputParserException" in str(type(e).__name__) or "JSONDecodeError" in str(type(e).__name__):
                try:
                    # Try to get raw response from LLM if available
                    raw_response = None
                    if hasattr(e, 'llm_output'):
                        raw_response = e.llm_output
                    else:
                        # Extract from error message - look for the JSON content
                        import re
                        error_str = str(e)
                        # Try to find JSON block in error message
                        json_match = re.search(r'Invalid json output:\s*(\{.*\})', error_str, re.DOTALL)
                        if json_match:
                            raw_response = json_match.group(1)
                        elif "llm_output=" in error_str:
                            # Try to extract from llm_output= part
                            llm_output_match = re.search(r'llm_output=([^\n]+)', error_str)
                            if llm_output_match:
                                raw_response = llm_output_match.group(1)
                    
                    # If we have raw response, try to extract and fix JSON
                    if raw_response:
                        # Try to extract JSON from response
                        json_str = None
                        
                        # Check for JSON in code blocks
                        if "```json" in raw_response:
                            json_start = raw_response.find("```json") + 7
                            json_end = raw_response.find("```", json_start)
                            if json_end > json_start:
                                json_str = raw_response[json_start:json_end].strip()
                        elif "```" in raw_response:
                            json_start = raw_response.find("```") + 3
                            json_end = raw_response.find("```", json_start)
                            if json_end > json_start:
                                json_str = raw_response[json_start:json_end].strip()
                        else:
                            # Use raw_response directly if it looks like JSON
                            if raw_response.strip().startswith('{'):
                                json_str = raw_response.strip()
                            else:
                                # Try to find JSON object in the response
                                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                                if json_match:
                                    json_str = json_match.group(0)
                        
                        if json_str:
                            # Fix common JSON issues
                            import re
                            
                            # Clean up numbered list items in suggestions
                            json_str = re.sub(r'(\d+)\.\s*"', '"', json_str)
                            
                            # Remove trailing commas before closing braces/brackets
                            json_str = re.sub(r',\s*}', '}', json_str)
                            json_str = re.sub(r',\s*]', ']', json_str)
                            
                            # Try to fix multiline strings by finding and escaping them
                            # This is a simplified approach - find string values that span multiple lines
                            lines = json_str.split('\n')
                            fixed_lines = []
                            in_string = False
                            for i, line in enumerate(lines):
                                # Simple heuristic: if line doesn't end with quote or comma/brace, it might be continuation
                                if i > 0 and not in_string and not line.strip().startswith('"') and '"' in lines[i-1]:
                                    # This might be a continuation of a multiline string
                                    # Escape it and add as part of previous line
                                    fixed_lines[-1] = fixed_lines[-1].rstrip('"') + '\\n' + line.strip().replace('"', '\\"') + '"'
                                else:
                                    fixed_lines.append(line)
                            json_str = '\n'.join(fixed_lines)
                            
                            # Try parsing
                            try:
                                data = json.loads(json_str)
                            except json.JSONDecodeError as json_err:
                                # If still fails, try to extract just the essential fields using regex
                                logger.warning(f"Full JSON parsing failed: {str(json_err)}, attempting partial extraction")
                                
                                # Extract key fields using regex
                                status_match = re.search(r'"status"\s*:\s*"([^"]+)"', json_str)
                                is_approved_match = re.search(r'"is_approved"\s*:\s*(true|false)', json_str, re.IGNORECASE)
                                reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]+)"', json_str, re.DOTALL)
                                
                                # Extract lists (issues_found, etc.) - simplified
                                issues_match = re.search(r'"issues_found"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
                                
                                data = {
                                    "status": status_match.group(1) if status_match else "rejected",
                                    "is_approved": is_approved_match.group(1).lower() == "true" if is_approved_match else False,
                                    "reasoning": (reasoning_match.group(1) if reasoning_match else "Validation failed due to JSON parsing error").replace('\n', ' ').strip(),
                                    "issues_found": [],
                                    "ethical_concerns": [],
                                    "factual_errors": [],
                                    "suggestions": []
                                }
                            
                            # Clean suggestions if they exist
                            if 'suggestions' in data and isinstance(data['suggestions'], list):
                                cleaned_suggestions = []
                                for suggestion in data['suggestions']:
                                    # Remove numbering from suggestions
                                    cleaned = re.sub(r'^\d+\.\s*', '', str(suggestion)).strip()
                                    if cleaned:
                                        cleaned_suggestions.append(cleaned)
                                data['suggestions'] = cleaned_suggestions
                            
                            # Create ValidationResult from parsed data
                            validation_result = ValidationResult(**data)
                            logger.warning(f"Successfully parsed validation result from error output for {cv_data.full_name}")
                            return validation_result
                except Exception as parse_error:
                    logger.warning(f"Failed to parse error output manually: {str(parse_error)}")
            
            # On validation failure, reject by default for safety
            return ValidationResult(
                status="rejected",
                is_approved=False,
                reasoning=f"Validation process failed: {str(e)}. Email rejected for safety.",
                issues_found=["Validation process error"],
                ethical_concerns=[],
                factual_errors=[],
                suggestions=["Please review the validation process and try again."]
            )
    
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

