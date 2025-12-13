"""LangChain agent for parsing CV from PDF files."""
import json
from typing import Optional, Dict, Any, Dict, Any

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
from prompts.cv_parsing_prompt import CV_PARSING_PROMPT
from utils.pdf_reader import extract_text_from_pdf
from core.logger import logger

# Import for tracking model responses
try:
    from database.models import save_model_response
except ImportError:
    save_model_response = None


class CVParserAgent:
    """Agent for parsing CV information from PDF files."""
    
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        vision_model_name: Optional[str] = None,
        use_ocr: bool = True,
        timeout: int = 120,
        max_retries: int = 2
    ):
        """
        Initialize CV Parser Agent.
        
        Args:
            model_name: Name of the LLM model to use for parsing
            temperature: Temperature for LLM generation
            api_key: OpenAI API key (if not set, uses environment variable)
            vision_model_name: Name of vision model for OCR (e.g., "gpt-4o", "gpt-4-vision-preview")
                              If None, will use model_name if it supports vision
            use_ocr: If True, use vision model for OCR when reading PDFs
            timeout: Request timeout in seconds (default: 120)
            max_retries: Maximum number of retries on failure (default: 2)
        """
        # Store model names and config for logging
        self.model_name = model_name
        # gpt-5 models may need longer timeout for complex prompts
        if "gpt-5" in model_name.lower():
            self.timeout = max(timeout, 180)  # At least 3 minutes for gpt-5
            logger.info(f"Using extended timeout ({self.timeout}s) for {model_name} due to potential longer processing time")
        else:
            self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize ChatOpenAI with proper parameter names
        # Try 'model' first (newer langchain-openai), fallback to 'model_name' (older versions)
        try:
            llm_kwargs = {
                "model": model_name,
                "temperature": temperature,
                "timeout": self.timeout,
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
                llm_kwargs["timeout"] = self.timeout
                llm_kwargs["max_retries"] = max_retries
            except TypeError:
                logger.warning("Older LangChain version detected - timeout and max_retries may not be supported")
            self.llm = ChatOpenAI(**llm_kwargs)
        
        # Initialize vision model for OCR if needed
        self.use_ocr = use_ocr
        self.vision_model = None
        self.vision_model_name = None
        
        if use_ocr:
            # Determine vision model name
            if vision_model_name:
                ocr_model = vision_model_name
            elif "gpt-4" in model_name.lower() or "gpt-4o" in model_name.lower():
                # Model supports vision
                ocr_model = model_name
            else:
                # Default to gpt-4o for OCR
                ocr_model = "gpt-4o"
            
            # Store vision model name for logging
            self.vision_model_name = ocr_model
            
            try:
                # Use longer timeout for OCR (can be slower), but same retry count
                vision_timeout = max(timeout, 180)  # At least 3 minutes for OCR
                vision_kwargs = {
                    "model": ocr_model,
                    "temperature": 0.0,  # Low temperature for accurate OCR
                    "timeout": vision_timeout,
                    "max_retries": max_retries,
                }
                if api_key:
                    vision_kwargs["openai_api_key"] = api_key
                self.vision_model = ChatOpenAI(**vision_kwargs)
            except TypeError:
                vision_kwargs = {
                    "model_name": ocr_model,
                    "temperature": 0.0,
                }
                if api_key:
                    vision_kwargs["openai_api_key"] = api_key
                # Note: timeout and max_retries may not be supported in older versions
                try:
                    vision_timeout = max(timeout, 180)
                    vision_kwargs["timeout"] = vision_timeout
                    vision_kwargs["max_retries"] = max_retries
                except TypeError:
                    logger.warning("Older LangChain version detected - timeout and max_retries may not be supported for vision model")
                self.vision_model = ChatOpenAI(**vision_kwargs)
        else:
            self.vision_model_name = None
        
        self.output_parser = PydanticOutputParser(pydantic_object=CVData)
        
        # Update prompt with format instructions
        self.prompt_with_format = CV_PARSING_PROMPT.partial(
            format_instructions=self.output_parser.get_format_instructions()
        )
        
        # Try to use modern LCEL approach (LangChain Expression Language)
        # Chain: prompt -> llm -> output_parser
        try:
            self.chain = self.prompt_with_format | self.llm | self.output_parser
            self.use_lcel = True
        except (TypeError, AttributeError):
            # Fallback: use direct invocation (for older LangChain versions)
            self.use_lcel = False
    
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
        
        # Run LLM chain using modern invoke method or fallback
        try:
            if verbose:
                print("    ⏳ Sending request to LLM (this may take 30-120 seconds)...")
                print("    💡 Tip: LLM is analyzing the CV and extracting structured information")
            
            logger.info("Step 2: Sending request to LLM for structured parsing...")
            parsing_start = time.time()
            
            if self.use_lcel:
                input_data = {"cv_text": cv_text[:1000] + "..." if len(cv_text) > 1000 else cv_text}  # Truncate for storage
                parsed_data = self.chain.invoke({"cv_text": cv_text})
                parsing_time = time.time() - parsing_start
                logger.info(f"Step 2 completed: LLM parsing successful in {parsing_time:.2f}s")
                
                # Track model response
                if save_model_response:
                    try:
                        save_model_response(
                            agent_type="cv_parser",
                            model_name=self.model_name,
                            input_data=input_data,
                            output_data=parsed_data.dict() if hasattr(parsed_data, 'dict') else str(parsed_data),
                            candidate_id=candidate_id,
                            metadata={"temperature": getattr(self.llm, 'temperature', None), "parsing_time": parsing_time}
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save model response: {str(e)}")
                
                if verbose:
                    print(f"    ✅ Received response from LLM ({parsing_time:.2f}s)")
                
                total_time = time.time() - start_time
                logger.info(f"CV parsing completed successfully in {total_time:.2f}s total")
                logger.info("=" * 80)
                
                return parsed_data
            else:
                # Fallback for older LangChain versions
                logger.info("Using fallback method (older LangChain version)")
                formatted_prompt = self.prompt_with_format.format(cv_text=cv_text)
                response = self.llm.invoke(formatted_prompt)
                result = response.content if hasattr(response, 'content') else str(response)
                parsed_data = self.output_parser.parse(result)
                parsing_time = time.time() - parsing_start
                logger.info(f"Step 2 completed: LLM parsing successful in {parsing_time:.2f}s")
                
                if verbose:
                    print(f"    ✅ Received response from LLM ({parsing_time:.2f}s)")
                
                total_time = time.time() - start_time
                logger.info(f"CV parsing completed successfully in {total_time:.2f}s total")
                logger.info("=" * 80)
                
                return parsed_data
        except Exception as e:
            # Fallback: try to get raw response and parse manually
            result = None
            error_type = type(e).__name__
            error_msg = str(e)
            logger.warning(f"First parsing attempt failed: {error_type}: {error_msg}")
            
            # Provide helpful error context
            is_connection_error = (
                "connection" in error_msg.lower() or 
                "APIConnectionError" in error_type or
                "ConnectionError" in error_type or
                "timeout" in error_msg.lower() or
                "disconnected" in error_msg.lower() or
                "RemoteProtocolError" in error_type or
                "server disconnected" in error_msg.lower()
            )
            
            if is_connection_error:
                logger.warning(
                    f"Connection error detected. This may be due to:\n"
                    f"  - Network connectivity issues\n"
                    f"  - API timeout (current timeout: {self.timeout}s)\n"
                    f"  - OpenAI API service issues\n"
                    f"  - Model '{self.model_name}' may be experiencing high load\n"
                    f"  - Prompt may be too long for this model\n"
                    f"Retrying with direct LLM call..."
                )
            
            try:
                if verbose:
                    print(f"    ⚠️ First parsing attempt failed: {error_type}")
                    if is_connection_error:
                        print(f"    🔄 Connection issue detected. Retrying...")
                    else:
                        print("    🔄 Retrying with direct LLM call...")
                
                logger.debug(f"Retrying with direct LLM call. Error details: {error_msg}")
                
                # Get raw response from LLM
                response = self.llm.invoke(self.prompt_with_format.format(cv_text=cv_text))
                result = response.content if hasattr(response, 'content') else str(response)
                
                logger.debug(f"Received raw response from LLM (length: {len(result) if result else 0})")
                
                # Try to extract JSON from the response
                if "```json" in result:
                    json_start = result.find("```json") + 7
                    json_end = result.find("```", json_start)
                    result = result[json_start:json_end].strip()
                    logger.debug("Extracted JSON from ```json code block")
                elif "```" in result:
                    json_start = result.find("```") + 3
                    json_end = result.find("```", json_start)
                    result = result[json_start:json_end].strip()
                    logger.debug("Extracted JSON from ``` code block")
                
                parsed_data = self.output_parser.parse(result)
                logger.info("Successfully parsed CV data on retry")
                if verbose:
                    print("    ✅ Successfully parsed on retry")
                return parsed_data
            except Exception as parse_error:
                parse_error_type = type(parse_error).__name__
                parse_error_msg = str(parse_error)
                logger.error(f"Retry parsing failed: {parse_error_type}: {parse_error_msg}")
                
                # Final fallback: try to parse as JSON directly
                if result is None:
                    # Check if it's a connection error
                    is_connection_error = (
                        "connection" in parse_error_msg.lower() or 
                        "APIConnectionError" in parse_error_type or
                        "ConnectionError" in parse_error_type or
                        "timeout" in parse_error_msg.lower() or
                        "disconnected" in parse_error_msg.lower() or
                        "RemoteProtocolError" in parse_error_type or
                        "server disconnected" in parse_error_msg.lower()
                    )
                    
                    if is_connection_error:
                        error_msg = (
                            f"Failed to connect to OpenAI API after retries.\n"
                            f"Error: {parse_error_msg}\n"
                            f"Model: {self.model_name}\n"
                            f"Timeout: {self.timeout}s\n"
                            f"Possible causes:\n"
                            f"  - Network connectivity issues - check your internet connection\n"
                            f"  - API timeout - the request took too long (timeout: {self.timeout}s)\n"
                            f"  - OpenAI API service issues - check OpenAI status page\n"
                            f"  - Model '{self.model_name}' may be experiencing high load - try again later\n"
                            f"  - Prompt may be too long for this model - try using a different model (e.g., gpt-4o)\n"
                            f"  - API key issues - verify your OPENAI_API_KEY is correct\n"
                            f"\nTip: Try running 'python test_openai_connection.py' to test your connection.\n"
                            f"Tip: Models gpt-5 and gpt-5-mini may have issues with long prompts.\n"
                            f"     For CV parsing, consider using:\n"
                            f"     - gpt-4o (recommended for CV parsing)\n"
                            f"     - gpt-3.5-turbo (faster, cheaper)\n"
                            f"     Set OPENAI_MODEL=gpt-4o in your .env file or settings.py"
                        )
                    else:
                        error_msg = f"Failed to get response from LLM: {parse_error_msg}. Please check your API key and internet connection."
                    
                    logger.error(error_msg)
                    raise Exception(error_msg)
                
                try:
                    logger.debug("Attempting final fallback: parsing JSON and transforming data")
                    
                    if isinstance(result, str):
                        data = json.loads(result)
                        logger.debug(f"Parsed JSON string (keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'})")
                    else:
                        data = result
                    
                    # Log the structure of additional_info if present
                    if isinstance(data, dict) and "additional_info" in data:
                        additional_info = data["additional_info"]
                        logger.debug(f"additional_info type: {type(additional_info)}, value: {str(additional_info)[:200] if additional_info else 'None'}")
                    
                    # Transform data to match Pydantic model
                    transformed_data = self._transform_llm_response(data)
                    
                    # Log transformed additional_info
                    if "additional_info" in transformed_data:
                        logger.debug(f"Transformed additional_info type: {type(transformed_data['additional_info'])}, value: {str(transformed_data['additional_info'])[:200] if transformed_data['additional_info'] else 'None'}")
                    
                    logger.info("Successfully transformed and validated CV data")
                    return CVData(**transformed_data)
                except Exception as final_error:
                    error_msg = f"Failed to parse CV data: {str(final_error)}. Original error: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    
                    # Log validation errors in detail
                    if "validation error" in str(final_error).lower():
                        logger.error(f"Pydantic validation error details: {str(final_error)}")
                        if isinstance(data, dict):
                            logger.debug(f"Problematic data structure: {json.dumps(data, indent=2, default=str)[:1000]}")
                    
                    raise Exception(error_msg)
    
    def parse_cv_from_text(self, cv_text: str, candidate_id: Optional[int] = None) -> CVData:
        """
        Parse CV from text content.
        
        Args:
            cv_text: CV text content
            
        Returns:
            CVData object with parsed information
        """
        # Run LLM chain using modern invoke method or fallback
        try:
            if self.use_lcel:
                parsed_data = self.chain.invoke({"cv_text": cv_text})
                return parsed_data
            else:
                # Fallback for older LangChain versions
                formatted_prompt = self.prompt_with_format.format(cv_text=cv_text)
                response = self.llm.invoke(formatted_prompt)
                result = response.content if hasattr(response, 'content') else str(response)
                parsed_data = self.output_parser.parse(result)
                return parsed_data
        except Exception as e:
            # Fallback: try to get raw response and parse manually
            result = None
            try:
                # Get raw response from LLM
                response = self.llm.invoke(self.prompt_with_format.format(cv_text=cv_text))
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
                
                parsed_data = self.output_parser.parse(result)
                return parsed_data
            except Exception as parse_error:
                # Final fallback: try to parse as JSON directly
                if result is None:
                    raise Exception(f"Failed to get response from LLM. Connection error: {str(e)}. Please check your API key and internet connection.")
                
                try:
                    if isinstance(result, str):
                        data = json.loads(result)
                    else:
                        data = result
                    
                    # Transform data to match Pydantic model
                    transformed_data = self._transform_llm_response(data)
                    return CVData(**transformed_data)
                except Exception as final_error:
                    raise Exception(f"Failed to parse CV data: {str(final_error)}. Original error: {str(e)}")

