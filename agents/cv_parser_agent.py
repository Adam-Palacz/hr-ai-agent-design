"""Azure OpenAI agent for parsing CV from PDF files (no LangChain)."""

import json
from typing import Optional, Dict, Any

from models.cv_models import CVData
from prompts.cv_parsing_prompt import CV_PARSING_PROMPT
from utils.pdf_reader import extract_text_from_pdf
from core.logger import logger
from config import settings
from agents.base_agent import BaseAgent
from utils.json_parser import strip_code_fences


class CVParserAgent(BaseAgent):
    """Agent for parsing CV information from PDF files."""
    
    def __init__(
        self,
        model_name: str = None,
        temperature: float = None,
        api_key: Optional[str] = None,
        vision_model_name: Optional[str] = None,
        use_ocr: bool = True,
        timeout: int = 240,
        max_retries: int = 2
    ):
        """
        Initialize CV Parser Agent using Azure OpenAI SDK (no LangChain).
        """
        # Store model names and config for logging
        model_name_to_use = model_name or settings.openai_model
        temperature_to_use = temperature if temperature is not None else settings.openai_temperature
        
        # Ensure temperature is at least 1.0 for Azure (some deployments reject 0.0)
        if temperature_to_use is None or temperature_to_use < 1.0:
            temperature_to_use = 1.0
        
        super().__init__(model_name_to_use, temperature_to_use, api_key, timeout, max_retries)
        
        # OCR: we no longer use an LLM-based vision model here; rely on pdf_reader defaults
        self.use_ocr = use_ocr
        self.vision_model = None
        self.vision_model_name = vision_model_name
        
        # We don't use PydanticOutputParser anymore; parsing is done manually via JSON + _transform_llm_response.
    
    def _transform_llm_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform LLM response to match Pydantic model structure.
        Handles common field name mismatches.
        """
        transformed = {}
        
        # Handle nested personal_information
        if "personal_information" in data:
            personal = data["personal_information"]
            transformed["full_name"] = personal.get("full_name", "")
            transformed["email"] = personal.get("email") or personal.get("email_address")
            transformed["phone"] = personal.get("phone") or personal.get("phone_number")
            transformed["location"] = personal.get("location")
            transformed["linkedin"] = personal.get("linkedin")
            transformed["github"] = personal.get("github")
            transformed["portfolio"] = personal.get("portfolio") or personal.get("portfolio_website")
        else:
            transformed["full_name"] = data.get("full_name", "")
            transformed["email"] = data.get("email")
            transformed["phone"] = data.get("phone")
            transformed["location"] = data.get("location")
            transformed["linkedin"] = data.get("linkedin")
            transformed["github"] = data.get("github")
            transformed["portfolio"] = data.get("portfolio")
        
        # Handle summary
        transformed["summary"] = data.get("summary") or data.get("professional_summary")
        
        # Transform education
        education_list = data.get("education", [])
        transformed["education"] = []
        for edu in education_list:
            transformed["education"].append({
                "institution": edu.get("institution") or edu.get("institution_name", ""),
                "degree": edu.get("degree") or edu.get("degree_obtained", ""),
                "field_of_study": edu.get("field_of_study"),
                "start_date": edu.get("start_date"),
                "end_date": edu.get("end_date"),
                "gpa": edu.get("gpa"),
                "honors": edu.get("honors")
            })
        
        # Transform experience
        experience_list = data.get("experience", []) or data.get("work_experience", [])
        transformed["experience"] = []
        for exp in experience_list:
            achievements = exp.get("achievements") or exp.get("key_achievements")
            if isinstance(achievements, str):
                achievements = [achievements] if achievements else []
            elif not isinstance(achievements, list):
                achievements = []
            
            transformed["experience"].append({
                "company": exp.get("company") or exp.get("company_name", ""),
                "position": exp.get("position") or exp.get("job_title", ""),
                "start_date": exp.get("start_date"),
                "end_date": exp.get("end_date"),
                "description": exp.get("description") or exp.get("job_description"),
                "achievements": achievements
            })
        
        # Transform skills - handle both list and dict formats
        skills_data = data.get("skills", [])
        transformed["skills"] = []
        
        if isinstance(skills_data, dict):
            # Handle dict format: {"technical_skills": [...], "language_skills": [...], "soft_skills": [...]}
            for skill_name in skills_data.get("technical_skills", []):
                transformed["skills"].append({
                    "name": skill_name,
                    "category": "Technical",
                    "proficiency": None
                })
            for skill_name in skills_data.get("language_skills", []):
                transformed["skills"].append({
                    "name": skill_name,
                    "category": "Language",
                    "proficiency": None
                })
            for skill_name in skills_data.get("soft_skills", []):
                transformed["skills"].append({
                    "name": skill_name,
                    "category": "Soft",
                    "proficiency": None
                })
        elif isinstance(skills_data, list):
            # Handle list format
            for skill in skills_data:
                if isinstance(skill, str):
                    transformed["skills"].append({
                        "name": skill,
                        "category": None,
                        "proficiency": None
                    })
                elif isinstance(skill, dict):
                    transformed["skills"].append({
                        "name": skill.get("name", ""),
                        "category": skill.get("category"),
                        "proficiency": skill.get("proficiency")
                    })
        
        # Transform certifications
        certs_list = data.get("certifications", [])
        transformed["certifications"] = []
        for cert in certs_list:
            transformed["certifications"].append({
                "name": cert.get("name") or cert.get("certification_name", ""),
                "issuer": cert.get("issuer") or cert.get("issuing_organization"),
                "date": cert.get("date") or cert.get("date_obtained"),
                "expiry_date": cert.get("expiry_date")
            })
        
        # Transform languages
        languages_list = data.get("languages", [])
        transformed["languages"] = []
        for lang in languages_list:
            transformed["languages"].append({
                "language": lang.get("language", ""),
                "proficiency": lang.get("proficiency", "")
            })
        
        # Transform additional_info - convert dict to string if needed
        additional_info = data.get("additional_info") or data.get("additional_information")
        if additional_info:
            if isinstance(additional_info, dict):
                # Convert dict to formatted string
                parts = []
                if additional_info.get("hobbies"):
                    hobbies = additional_info["hobbies"]
                    if isinstance(hobbies, list):
                        parts.append(f"Hobbies: {', '.join(hobbies)}")
                    else:
                        parts.append(f"Hobbies: {hobbies}")
                
                if additional_info.get("projects"):
                    projects = additional_info["projects"]
                    if isinstance(projects, list):
                        parts.append(f"Projects: {'; '.join(projects)}")
                    else:
                        parts.append(f"Projects: {projects}")
                
                if additional_info.get("awards"):
                    awards = additional_info["awards"]
                    if isinstance(awards, list):
                        parts.append(f"Awards: {', '.join(awards)}")
                    else:
                        parts.append(f"Awards: {awards}")
                
                if additional_info.get("other_activities"):
                    activities = additional_info["other_activities"]
                    if isinstance(activities, list):
                        parts.append(f"Other Activities: {', '.join(activities)}")
                    else:
                        parts.append(f"Other Activities: {activities}")
                
                transformed["additional_info"] = "\n".join(parts) if parts else None
            elif isinstance(additional_info, str):
                transformed["additional_info"] = additional_info
            else:
                transformed["additional_info"] = str(additional_info) if additional_info else None
        else:
            transformed["additional_info"] = None
        
        return transformed
    
    def parse_cv_from_pdf(self, pdf_path: str, verbose: bool = False, candidate_id: Optional[int] = None) -> CVData:
        """
        Parse CV from PDF file and return structured data.
        Uses vision model as OCR if enabled.
        
        Args:
            pdf_path: Path to the PDF file
            verbose: If True, print progress messages
            
        Returns:
            CVData object with parsed information
        """
        import time
        start_time = time.time()
        
        logger.info("=" * 80)
        logger.info("CV PARSING PROCESS STARTED")
        logger.info("=" * 80)
        logger.info(f"PDF file: {pdf_path}")
        logger.info(f"OCR enabled: {self.use_ocr}")
        logger.info(f"Vision model: {self.vision_model_name if self.vision_model_name else 'N/A'}")
        logger.info(f"Text model: {self.model_name}")
        
        if verbose:
            print("\n" + "=" * 80)
            print("STEP 1: EXTRACTING TEXT FROM PDF")
            print("=" * 80)
            print("  📄 Extracting text from PDF...")
        
        logger.info("Step 1: Starting text extraction from PDF...")
        extraction_start = time.time()
        
        # Extract text from PDF using vision model OCR if available
        cv_text = extract_text_from_pdf(
            pdf_path, 
            vision_model=self.vision_model if self.use_ocr else None,
            use_ocr=self.use_ocr,
            verbose=verbose
        )
        
        extraction_time = time.time() - extraction_start
        logger.info(f"Step 1 completed: Extracted {len(cv_text)} characters in {extraction_time:.2f}s")
        
        if verbose:
            print(f"  ✅ Extracted {len(cv_text)} characters of text ({extraction_time:.2f}s)")
            print("\n" + "=" * 80)
            print("STEP 2: PARSING STRUCTURED DATA WITH LLM")
            print("=" * 80)
            print(f"  🤖 Parsing structured data...")
        
        # Limit text length to avoid token limits
        # gpt-5 models may have issues with very long prompts, so use smaller limit
        max_text_length = 10000 if "gpt-5" in self.model_name.lower() else 15000
        
        if len(cv_text) > max_text_length:
            logger.warning(
                f"Text is very long ({len(cv_text)} characters), truncating to {max_text_length} characters "
                f"(model: {self.model_name})"
            )
            if verbose:
                print(f"  ⚠️ Text is very long ({len(cv_text)} characters), truncating to {max_text_length} characters...")
            cv_text = cv_text[:max_text_length] + "\n\n[... text was truncated due to length ...]"
        
        # Estimate prompt length (CV text + format instructions + prompt template)
        # Format instructions are typically ~500-1000 chars, prompt template ~500-800 chars
        estimated_prompt_length = len(cv_text) + 1500
        logger.info(
            f"Step 2: Preparing to send CV text ({len(cv_text)} chars) to LLM for parsing. "
            f"Estimated total prompt length: ~{estimated_prompt_length} chars"
        )
        
        if estimated_prompt_length > 20000 and "gpt-5" in self.model_name.lower():
            logger.warning(
                f"Warning: Prompt may be too long for {self.model_name}. "
                f"Consider using gpt-4o or gpt-3.5-turbo for better reliability with long CVs."
            )
        
        # Run LLM via Azure OpenAI
        try:
            if verbose:
                print("    ⏳ Sending request to LLM (this may take 30-120 seconds)...")
                print("    💡 Tip: LLM is analyzing the CV and extracting structured information")
            
            logger.info("Step 2: Sending request to LLM for structured parsing...")
            parsing_start = time.time()
            
            # Build prompt text
            prompt_text = CV_PARSING_PROMPT.format(cv_text=cv_text)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert CV parser. "
                            "You must return valid JSON matching the CVData schema."
                        ),
                    },
                    {"role": "user", "content": prompt_text},
                ],
                # max_completion_tokens=4000,
                temperature=self.temperature,
            )
            
            raw_text = ""
            if response and response.choices:
                msg = response.choices[0].message
                if msg and msg.content:
                    raw_text = msg.content
            
            if not raw_text or not str(raw_text).strip():
                raise Exception(
                    f"Model returned empty response for CV parsing. "
                    f"Check Azure deployment '{self.model_name}' and API availability."
                )
            parsing_time = time.time() - parsing_start
            logger.info(f"Step 2 completed: LLM parsing successful in {parsing_time:.2f}s")
            
            # Track model response (with token usage and cost)
            self._save_model_response(
                agent_type="cv_parser",
                input_data={
                    "cv_text": cv_text[:1000] + "..." if len(cv_text) > 1000 else cv_text
                },
                output_data=raw_text,
                candidate_id=candidate_id,
                metadata={"temperature": self.temperature, "parsing_time": parsing_time},
                response=response,  # Pass response to extract tokens and costs
            )
            
            # Parse raw_text into CVData
            parsed_data = self._parse_cv_from_text_raw(raw_text)
            
            if verbose:
                print(f"    ✅ Received response from LLM ({parsing_time:.2f}s)")
            
            total_time = time.time() - start_time
            logger.info(f"CV parsing completed successfully in {total_time:.2f}s total")
            logger.info("=" * 80)
            
            return parsed_data
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"Failed to parse CV: {error_type}: {error_msg}", exc_info=True)
            raise Exception(f"Failed to parse CV: {error_msg}") from e
    
    def parse_cv_from_text(self, cv_text: str, candidate_id: Optional[int] = None) -> CVData:
        """
        Parse CV from text content.
        
        Args:
            cv_text: CV text content
            
        Returns:
            CVData object with parsed information
        """
        # Run LLM via Azure OpenAI
        try:
            # Build prompt text
            prompt_text = CV_PARSING_PROMPT.format(cv_text=cv_text)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert CV parser. "
                            "You must return valid JSON matching the CVData schema."
                        ),
                    },
                    {"role": "user", "content": prompt_text},
                ],
                # max_completion_tokens=4000,
                temperature=self.temperature,
            )
            raw_text = response.choices[0].message.content
            return self._parse_cv_from_text_raw(raw_text)
        except Exception as e:
            raise Exception(f"Failed to parse CV text: {str(e)}") from e

    def _parse_cv_from_text_raw(self, text: str) -> CVData:
        """
        Parse CVData from raw model text, using JSON + _transform_llm_response.
        """
        if not text:
            raise ValueError("Empty response from CV parser model")

        # Strip code fences
        cleaned_text = strip_code_fences(text)

        # Try to parse JSON and transform
        try:
            data = json.loads(cleaned_text)
            transformed_data = self._transform_llm_response(data)
            return CVData(**transformed_data)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse CV data from model output: {str(e)}") from e
        except Exception as e:
            raise Exception(f"Failed to transform CV data: {str(e)}") from e

