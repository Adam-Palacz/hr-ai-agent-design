"""Azure OpenAI agent for classifying incoming emails (no LangChain)."""
from typing import Optional, Literal

from pydantic import BaseModel, Field
from core.logger import logger
from agents.base_agent import BaseAgent
from utils.json_parser import parse_json_safe


class EmailClassification(BaseModel):
    """Email classification result."""
    category: Literal['iod', 'consent_yes', 'consent_no', 'default'] = Field(
        ...,
        description="Email category: 'iod' for IOD/RODO requests, 'consent_yes' for consent to other positions, 'consent_no' for refusal, 'default' for regular HR emails"
    )
    confidence: float = Field(
        ...,
        description="Confidence score from 0.0 to 1.0",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of why the email was classified this way"
    )
    keywords_found: list[str] = Field(
        default_factory=list,
        description="List of relevant keywords found in the email"
    )


class EmailClassifierAgent(BaseAgent):
    """AI agent for classifying incoming emails."""
    
    # Critical IOD keywords - at least a few of these must be present for IOD classification
    CRITICAL_IOD_KEYWORDS = [
        'rodo', 'iod', 'dpo', 'gdpr', 'dane osobowe', 'ochrona danych',
        'uodo', 'organ nadzorczy', 'profilowanie', 'automatyczna decyzja'
    ]
    
    def __init__(
        self,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.1,  # Low temperature for consistent classification
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 2
    ):
        """
        Initialize Email Classifier Agent using Azure OpenAI SDK (no LangChain).
        """
        super().__init__(model_name, temperature, api_key, timeout, max_retries)
        
        # Static format instructions instead of LangChain parser
        self.format_instructions = (
            "Return ONLY a single JSON object with the following structure:\n"
            "{\n"
            '  "category": "iod" | "consent_yes" | "consent_no" | "default",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "reasoning": "short explanation",\n'
            '  "keywords_found": ["keyword1", "keyword2"]\n'
            "}\n\n"
            "- Do NOT return a JSON schema.\n"
            "- Do NOT wrap the JSON in markdown code fences."
        )
        
        # Build prompt
        self.prompt_template = self._create_prompt_template()
    
    def _create_prompt_template(self) -> str:
        """Create prompt template for email classification."""
        return """You are an email classification system for a recruitment department.

Your task is to classify incoming emails from candidates into one of the following categories:

1. **IOD** - Emails related to data protection, GDPR, RODO, privacy rights, or requests to IOD/DPO
   - Keywords that indicate IOD: RODO, IOD, DPO, GDPR, dane osobowe, ochrona danych, sprzeciw, zgoda (in context of data), wycofanie zgody, skarga, UODO, Organ Nadzorczy, profilowanie, automatyczna decyzja, sztuczna inteligencja (in context of data processing), AI (in context of data processing)
   - Examples: "Chcę wycofać zgodę na przetwarzanie danych", "Składam sprzeciw wobec profilowania", "Mam pytanie dotyczące RODO"

2. **consent_yes** - Emails expressing consent to be considered for other positions
   - Keywords: zgoda, zgadzam się, wyrażam zgodę, wyrażam zgodę na udział, wyrażam zgodę na udział w innych rekrutacjach, wyrażam zgodę na udział w innych, wyrażam zgodę na udział w rekrutacjach, tak, chcę, zainteresowany, rozważenie, inne oferty, inne stanowiska, inne pozycje, inne rekrutacje, udział w innych rekrutacjach, udział w innych, udział w rekrutacjach, mogę brać udział, mogę uczestniczyć, jestem zainteresowany innymi ofertami
   - Examples: 
     * "Wyrażam zgodę na udział w innych rekrutacjach"
     * "Wyrażam zgodę na udział w innych"
     * "Zgadzam się na rozważenie mojej kandydatury w kontekście innych stanowisk"
     * "Chcę być brany pod uwagę przy innych ofertach"
     * "Tak, wyrażam zgodę"
     * "Jestem zainteresowany innymi ofertami"
     * "Mogę brać udział w innych rekrutacjach"

3. **consent_no** - Emails refusing consent to be considered for other positions
   - Keywords: nie zgadzam się, nie wyrażam zgody, nie wyrażam zgody na udział, nie wyrażam zgody na udział w innych rekrutacjach, odmawiam, nie, nie chcę, wycofuję zgodę, nie jestem zainteresowany, nie rozważaj, nie chcę brać udziału, nie chcę uczestniczyć, nie jestem zainteresowany innymi ofertami, nie wyrażam zgody na udział w innych, nie wyrażam zgody na udział w rekrutacjach
   - Examples: 
     * "Nie wyrażam zgody na udział w innych rekrutacjach"
     * "Nie wyrażam zgody na udział w innych"
     * "Nie wyrażam zgody"
     * "Nie wyrażam zgody na rozważenie w innych rekrutacjach"
     * "Wycofuję zgodę na inne oferty"
     * "Nie jestem zainteresowany innymi ofertami"
     * "Nie chcę brać udziału w innych rekrutacjach"

4. **default** - All other emails that should go to HR department
   - Regular questions, follow-ups, general inquiries, etc.

CRITICAL RULES:
- For IOD classification: The email MUST contain at least 2-3 of the critical IOD keywords listed above
- If an email mentions "zgoda" but in context of consent for other positions (not data protection), classify as consent_yes/consent_no, NOT IOD
- If an email mentions "AI" or "sztuczna inteligencja" but in context of job requirements or skills, classify as default, NOT IOD
- Be precise - only classify as IOD if it's clearly about data protection/privacy rights
- For consent classification, look for explicit statements about being considered for other positions
- IMPORTANT: If email contains phrases like "wyrażam zgodę na udział w innych rekrutacjach" or "wyrażam zgodę na udział w innych" → classify as consent_yes
- IMPORTANT: If email contains phrases like "nie wyrażam zgody na udział w innych rekrutacjach" or "nie wyrażam zgody na udział w innych" → classify as consent_no
- Pay attention to Polish language variations: "udział w innych rekrutacjach", "udział w innych", "udział w rekrutacjach" all mean consent for other positions

Email to classify:
From: {from_email}
Subject: {subject}
Body: {body}

Provide your classification in the following JSON format:
{format_instructions}

IMPORTANT: Return ACTUAL DATA VALUES, not a schema description.
Example of correct output:
{{
  "category": "iod",
  "confidence": 0.95,
  "reasoning": "Email contains multiple IOD keywords: RODO, dane osobowe, and requests information about data processing",
  "keywords_found": ["rodo", "dane osobowe", "przetwarzanie danych"]
}}

DO NOT return:
{{
  "description": "Email classification model",
  "properties": {{...}},
  "required": [...]
}}
"""
    
    def classify_email(
        self,
        from_email: str,
        subject: str,
        body: str
    ) -> EmailClassification:
        """
        Classify email using AI.
        
        Args:
            from_email: Sender's email address
            subject: Email subject
            body: Email body text
            
        Returns:
            EmailClassification object
        """
        try:
            # Format prompt
            prompt = self.prompt_template.format(
                from_email=from_email,
                subject=subject,
                body=body[:5000],  # Limit body length to avoid token limits
                format_instructions=self.format_instructions
            )
            
            # Get classification from Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an email classification assistant. "
                            "You must respond with JSON exactly as described in the format_instructions."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_completion_tokens=500,
                temperature=self.temperature,
            )
            result_text = response.choices[0].message.content
            
            # Parse response
            classification = self._parse_classification_from_text(result_text)
            
            # Validate IOD classification - must have at least ONE critical keyword
            if classification.category == 'iod':
                body_lower = body.lower()
                subject_lower = subject.lower()
                text_lower = f"{subject_lower} {body_lower}"
                
                found_keywords = [
                    keyword for keyword in self.CRITICAL_IOD_KEYWORDS
                    if keyword.lower() in text_lower
                ]
                
                # Require at least ONE strong IOD keyword in the actual email text
                if len(found_keywords) < 1:
                    logger.warning(
                        f"IOD classification rejected - no critical IOD keywords found in email text. "
                        f"Reclassifying as 'default'."
                    )
                    # Reclassify as default
                    classification.category = 'default'
                    classification.reasoning = (
                        "Originally classified as IOD by the model, but no critical IOD keywords were found "
                        "in the email subject/body. Reclassified as default (HR)."
                    )
                    classification.confidence = 0.7
            
            logger.info(
                f"Email classified as '{classification.category}' "
                f"(confidence: {classification.confidence:.2f}, keywords: {classification.keywords_found})"
            )
            
            return classification
            
        except Exception as e:
            logger.error(f"Error classifying email: {str(e)}", exc_info=True)
            # Fallback to default classification
            return EmailClassification(
                category='default',
                confidence=0.5,
                reasoning=f"Classification failed: {str(e)}. Defaulting to HR routing.",
                keywords_found=[]
            )

    def _parse_classification_from_text(self, text: str) -> EmailClassification:
        """
        Parse EmailClassification from raw model text, handling common JSON issues.
        """
        if not text:
            raise ValueError("Empty response from model")
        
        # Parse JSON with fallback extraction
        data = parse_json_safe(text, fallback_to_extraction=True)
        
        return EmailClassification(**data)

