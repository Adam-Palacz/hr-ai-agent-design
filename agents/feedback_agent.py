"""LangChain agent for generating personalized candidate feedback."""
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
from models.feedback_models import HRFeedback, CandidateFeedback, FeedbackFormat
from models.job_models import JobOffer
from prompts.feedback_generation_prompt import FEEDBACK_GENERATION_PROMPT
from core.logger import logger

# Import for tracking model responses
try:
    from database.models import save_model_response
except ImportError:
    save_model_response = None


class FeedbackAgent:
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
        Initialize Feedback Agent.
        
        Args:
            model_name: Name of the LLM model to use
            temperature: Temperature for LLM generation (higher for more creative feedback)
            api_key: OpenAI API key (if not set, uses environment variable)
            timeout: Request timeout in seconds (default: 120)
            max_retries: Maximum number of retries on failure (default: 2)
        """
        # Store model name for logging
        self.model_name = model_name
        
        # Handle special temperature requirements for gpt-5 models (non-chat)
        # gpt-5 models (excluding gpt-5-chat) only allow temperature=1 or unset
        model_lower = model_name.lower()
        if model_lower.startswith("gpt-5") and "chat" not in model_lower:
            if temperature != 1.0 and temperature is not None:
                logger.warning(
                    f"Model {model_name} only supports temperature=1.0 or unset. "
                    f"Adjusting temperature from {temperature} to 1.0"
                )
                temperature = 1.0
        
        # Initialize ChatOpenAI with proper parameter names
        # Try 'model' first (newer langchain-openai), fallback to 'model_name' (older versions)
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
            # Note: timeout and max_retries may not be supported in older versions
            try:
                llm_kwargs["timeout"] = timeout
                llm_kwargs["max_retries"] = max_retries
            except TypeError:
                logger.warning("Older LangChain version detected - timeout and max_retries may not be supported")
            self.llm = ChatOpenAI(**llm_kwargs)
        
        self.output_parser = PydanticOutputParser(pydantic_object=CandidateFeedback)
        
        # Get format instructions and enhance them to prevent schema confusion
        base_instructions = self.output_parser.get_format_instructions()
        # Add explicit instruction to return actual data, not schema
        self.format_instructions = f"""{base_instructions}

CRITICAL: Return ACTUAL DATA VALUES, not a schema description. 
The response must be a JSON object with the html_content field containing the actual HTML email content.
Example: {{"html_content": "<!DOCTYPE html>\\n<html>...</html>"}}
DO NOT return: {{"description": "...", "properties": {{...}}, "required": [...]}}"""
        
        # Store prompt template for later use
        self.prompt_template = FEEDBACK_GENERATION_PROMPT
        
        # Note: We'll build the chain dynamically based on output_format
        try:
            self.use_lcel = True
        except (TypeError, AttributeError):
            # Fallback: use direct invocation (for older LangChain versions)
            self.use_lcel = False
    
    def generate_feedback(
        self,
        cv_data: CVData,
        hr_feedback: HRFeedback,
        job_offer: Optional[JobOffer] = None,
        output_format: FeedbackFormat = FeedbackFormat.HTML,
        candidate_id: Optional[int] = None
    ) -> CandidateFeedback:
        """
        Generate personalized feedback for a candidate.
        
        Args:
            cv_data: Parsed CV data
            hr_feedback: HR evaluation and feedback
            
        Returns:
            CandidateFeedback object with personalized feedback
        """
        # Convert CV data to formatted string
        cv_data_str = self._format_cv_data(cv_data)
        
        # Convert HR feedback to formatted string
        hr_feedback_str = self._format_hr_feedback(hr_feedback)
        
        # Convert job offer to formatted string
        if job_offer:
            job_offer_str = self._format_job_offer(job_offer)
        else:
            job_offer_str = "No job offer information provided"
        
        # Get candidate name
        candidate_name = cv_data.full_name
        
        # Format output format for prompt
        format_str = output_format.value if isinstance(output_format, FeedbackFormat) else str(output_format)
        
        # Build prompt with format instructions and output format
        prompt_with_format = self.prompt_template.partial(
            format_instructions=self.format_instructions,
            output_format=format_str
        )
        
        # Build chain dynamically
        try:
            chain = prompt_with_format | self.llm | self.output_parser
            use_lcel = True
        except (TypeError, AttributeError):
            use_lcel = False
        
        # Run LLM chain using modern invoke method or fallback
        try:
            if use_lcel:
                input_data = {
                    "cv_data": cv_data_str,
                    "hr_feedback": hr_feedback_str,
                    "job_offer": job_offer_str,
                    "candidate_name": candidate_name
                }
                parsed_feedback = chain.invoke(input_data)
                # If html_content is missing, generate it from other fields
                if not hasattr(parsed_feedback, 'html_content') or not parsed_feedback.html_content:
                    parsed_feedback = self._generate_html_fallback(parsed_feedback)
                
                # Track model response
                if save_model_response:
                    try:
                        save_model_response(
                            agent_type="feedback_generator",
                            model_name=self.model_name,
                            input_data=input_data,
                            output_data=parsed_feedback.dict() if hasattr(parsed_feedback, 'dict') else str(parsed_feedback),
                            candidate_id=candidate_id,
                            metadata={"temperature": getattr(self.llm, 'temperature', None)}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save model response: {str(e)}")
                
                return parsed_feedback
            else:
                # Fallback for older LangChain versions
                formatted_prompt = prompt_with_format.format(
                    cv_data=cv_data_str,
                    hr_feedback=hr_feedback_str,
                    job_offer=job_offer_str,
                    candidate_name=candidate_name
                )
                response = self.llm.invoke(formatted_prompt)
                result = response.content if hasattr(response, 'content') else str(response)
                parsed_feedback = self.output_parser.parse(result)
                # Ensure html_content exists
                if not hasattr(parsed_feedback, 'html_content') or not parsed_feedback.html_content:
                    raise ValueError("html_content field is required but was not generated by AI")
                return parsed_feedback
        except Exception as e:
            # Fallback: try to get raw response and parse manually
            try:
                # Format prompt manually
                prompt_text = prompt_with_format.format(
                    cv_data=cv_data_str,
                    hr_feedback=hr_feedback_str,
                    job_offer=job_offer_str,
                    candidate_name=candidate_name
                )
                
                # Get raw response from LLM
                response = self.llm.invoke(prompt_text)
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
                
                # Parse feedback - only html_content is required
                try:
                    parsed_feedback = self.output_parser.parse(result)
                    # Ensure html_content exists
                    if not hasattr(parsed_feedback, 'html_content') or not parsed_feedback.html_content:
                        raise ValueError("html_content field is required but was not generated by AI")
                    return parsed_feedback
                except Exception as parse_error:
                    # If parsing fails, try to extract just html_content from JSON
                    error_str = str(parse_error)
                    if 'html_content' in error_str or 'Field required' in error_str:
                        logger.warning("Attempting to extract html_content directly from response")
                        try:
                            data = json.loads(result)
                            # Only html_content is required
                            if 'html_content' in data and data['html_content']:
                                return CandidateFeedback(html_content=data['html_content'])
                            else:
                                raise ValueError("html_content not found in AI response")
                        except Exception as e2:
                            logger.error(f"Failed to extract html_content: {str(e2)}")
                    raise parse_error
            except Exception as parse_error:
                # Final fallback: try to extract structured data from plain text response
                try:
                    # result should be defined from the previous try block
                    if 'result' in locals() and isinstance(result, str):
                        # Try to parse as JSON first
                        try:
                            data = json.loads(result)
                            
                            # Check if model returned schema instead of data
                            if 'properties' in data or ('description' in data and 'properties' in str(data)):
                                logger.warning("Model returned schema instead of data in fallback. This indicates a prompt issue.")
                                raise ValueError("Model returned schema description instead of actual data. The AI misunderstood the format instructions.")
                            
                            # Only html_content is required
                            if 'html_content' in data and data['html_content']:
                                return CandidateFeedback(html_content=data['html_content'])
                            else:
                                raise ValueError("html_content not found in AI response")
                        except json.JSONDecodeError:
                            # If not JSON, try to use raw response as HTML (last resort)
                            logger.warning("LLM returned plain text instead of JSON. Attempting to use as HTML...")
                            
                            # Try to extract HTML from the response if it contains HTML tags
                            if '<html' in result.lower() or '<body' in result.lower():
                                # Extract HTML content
                                html_start = result.lower().find('<html')
                                if html_start == -1:
                                    html_start = result.lower().find('<body')
                                html_content = result[html_start:] if html_start != -1 else result
                            else:
                                # Wrap in basic HTML structure
                                html_content = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Odpowiedź na aplikację</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    {result}
</body>
</html>"""
                            
                            return CandidateFeedback(html_content=html_content)
                    else:
                        raise Exception(f"Could not extract result from LLM response. Parse error: {str(parse_error)}")
                except Exception as final_error:
                    raise Exception(f"Failed to parse feedback: {str(final_error)}. Original error: {str(e)}")
    
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
        
        # Notes contain all feedback - AI will extract strengths and weaknesses from notes
        if hr_feedback.notes:
            lines.append(f"\nHR Notes and Evaluation:\n{hr_feedback.notes}")
            lines.append("\nIMPORTANT: Extract and identify candidate's strengths and areas for improvement from the HR notes above.")
        
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
    

