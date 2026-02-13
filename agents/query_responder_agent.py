"""
Agent for generating responses to email inquiries.
Can use basic knowledge or RAG from the vector database.
"""
import json
from typing import Dict, List, Optional
from agents.base_agent import BaseAgent
from core.logger import logger


class QueryResponderAgent(BaseAgent):
    """
    Agent that generates responses to email inquiries.
    Can use basic knowledge or RAG from the vector database.
    """
    
    def __init__(self, model_name: str = None, temperature: float = 0.7):
        from config import settings
        model_name = model_name or settings.openai_model
        super().__init__(model_name=model_name, temperature=temperature)
        
        # Basic knowledge
        self.basic_knowledge = """
PODSTAWOWA WIEDZA O REKRUTACJI:

1. Proces rekrutacji:
- Pierwsza selekcja (screening) - weryfikacja CV i podstawowych wymagań
- Rozmowa HR - ocena kompetencji miękkich, motywacji, dopasowania kulturowego
- Ocena techniczna - testy, zadania praktyczne (dla stanowisk technicznych)
- Weryfikacja wiedzy - sprawdzenie kompetencji merytorycznych
- Rozmowa finalna - spotkanie z przełożonym, negocjacje warunków

2. Komunikacja z kandydatami:
- Odpowiedzi na aplikacje w ciągu 5 dni roboczych
- Wszystkie komunikaty są profesjonalne, przyjazne i empatyczne
- Informacja zwrotna zawsze zawiera konstruktywne uwagi
- Unikamy słów "odrzucenie", "odmowa" - używamy łagodniejszych sformułowań

3. Zgoda na inne rekrutacje:
- Kandydaci mogą wyrazić zgodę na rozważenie ich kandydatury w innych rekrutacjach
- Zgoda jest dobrowolna i można ją wycofać w każdej chwili
- Jeśli kandydat wyraził zgodę, informujemy go o nowych, odpowiednich ofertach

4. Feedback:
- Zawsze konstruktywny i wspierający
- Zawiera mocne strony kandydata
- Wskazuje obszary do rozwoju w sposób empatyczny
- Zachęca do dalszego rozwoju zawodowego

5. Podpis w emailach:
- "Z wyrazami szacunku\n\nDział HR"
"""
    
    def generate_response(
        self,
        email_subject: str,
        email_body: str,
        sender_email: str,
        rag_context: Optional[List[Dict]] = None
    ) -> Optional[str]:
        """
        Generate a response to an email inquiry.
        
        Args:
            email_subject: Email subject
            email_body: Email body content
            sender_email: Sender email address
            rag_context: RAG context (list of documents from the vector database)
        
        Returns:
            Generated response or None if the agent is not confident (then forward to HR)
        """
        prompt = self._create_response_prompt(
            email_subject, email_body, sender_email, rag_context
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an HR department assistant. You respond to candidate inquiries in a professional, friendly, and helpful manner. You MUST always write responses in POLISH (Polish language). Always end your response with the signature 'Z wyrazami szacunku\n\nDział HR'. If you are not certain of the answer, return the special value: 'FORWARD_TO_HR'."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Check if agent returned the forward-to-HR signal
            if response_text.upper() == "FORWARD_TO_HR" or "FORWARD_TO_HR" in response_text.upper():
                logger.info("Agent returned FORWARD_TO_HR signal - not confident enough to answer")
                return None
            
            # Check if response contains uncertainty phrases (in Polish)
            uncertainty_phrases = [
                "nie posiadamy szczegółowych informacji",
                "chociaż nie posiadamy",
                "nie mamy dokładnych informacji",
                "nie jesteśmy w stanie",
                "nie możemy udzielić",
                "przekazaliśmy do działu hr",
                "przekazaliśmy je do działu hr",
                "przekazaliśmy do hr",
                "przekazaliśmy je do hr",
                "dziękujemy za pańskie zapytanie. przekazaliśmy",
                "przekazaliśmy je do działu",
                "skontaktuje się z państwem w najkrótszym możliwym terminie"  # Typical phrase when forwarding to HR
            ]
            
            response_lower = response_text.lower()
            has_uncertainty = any(phrase in response_lower for phrase in uncertainty_phrases)
            
            if has_uncertainty:
                logger.warning(f"Response contains uncertainty phrases - agent not confident enough. Phrases found: {[p for p in uncertainty_phrases if p in response_lower]}")
                return None
            
            # Add privacy policy link to the end of response (after signature)
            response_text = self._add_privacy_link(response_text)
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return None
    
    def _create_response_prompt(
        self,
        email_subject: str,
        email_body: str,
        sender_email: str,
        rag_context: Optional[List[Dict]] = None
    ) -> str:
        """Create prompt for generating response."""
        context_section_english = ""
        if rag_context:
            context_section_english = "\n\nADDITIONAL CONTEXT FROM KNOWLEDGE BASE:\n"
            for i, doc in enumerate(rag_context, 1):
                context_section_english += f"\n--- Document {i} ---\n"
                context_section_english += f"Source: {doc.get('metadata', {}).get('source', 'N/A')}\n"
                context_section_english += f"Content: {doc.get('document', '')}\n"
        
        return f"""
You are an HR assistant responding to candidate inquiries in the recruitment process.

BASIC KNOWLEDGE:
{self.basic_knowledge}
{context_section_english}

EMAIL:
Subject: {email_subject}
From: {sender_email}
Content: {email_body}

TASK:
Generate a professional, friendly, and helpful response to this inquiry.

DECISION RULES:
1. If RAG context is provided and contains relevant information → Answer based on RAG context (you can be confident)
2. If question can be answered from basic knowledge → Answer from basic knowledge
3. If question requires specific candidate data or personal information → Return "FORWARD_TO_HR"
4. If question requires interpretation or subjective assessment → Return "FORWARD_TO_HR"
5. If RAG context is empty or irrelevant → Return "FORWARD_TO_HR"

REQUIREMENTS:
1. If RAG context is provided, use it to answer the question - you can be confident if RAG found relevant documents
2. The answer must be factually accurate based on basic knowledge and RAG context (if available)
3. Use professional but friendly tone
4. Be empathetic and supportive
5. ❌ NEVER answer in style: "Although we do not have detailed information..." - this means you should forward to HR
6. ❌ NEVER answer in style: "we do not have detailed information" - this indicates lack of certainty
7. ❌ NEVER answer if question requires specific candidate data or personal information
8. ⚠️ CRITICAL: If you cannot answer based on available context, return ONLY: "FORWARD_TO_HR" (without any other text, no Polish text, just these exact words)
9. ⚠️ CRITICAL: DO NOT generate a response saying "we forwarded to HR" or "we will forward to HR" - if you cannot answer, return ONLY "FORWARD_TO_HR"
10. ⚠️ CRITICAL: DO NOT write "Dziękujemy za Pańskie zapytanie. Przekazaliśmy je do działu HR..." - if you cannot answer, return ONLY "FORWARD_TO_HR"
11. Always end the response with: "Z wyrazami szacunku\n\nDział HR" (ONLY if you are answering, not if returning FORWARD_TO_HR)
12. ⚠️ CRITICAL: The response MUST be written in POLISH (Polish language) - this is mandatory (ONLY if you are answering, not if returning FORWARD_TO_HR)
13. If the question concerns a specific candidate application, suggest direct contact with HR

LANGUAGE REQUIREMENT (ONLY if answering, not if returning FORWARD_TO_HR):
- You MUST write the ENTIRE response in POLISH (Polish language)
- Use natural, conversational Polish
- Professional but friendly tone
- All content must be in Polish, including greetings, explanations, and closing
- The response should sound natural and human-like in Polish

REMEMBER:
- If you have RAG context with relevant information → Answer in Polish (you can be confident)
- If you can answer from basic knowledge → Answer in Polish
- If you cannot answer based on available context → Return ONLY "FORWARD_TO_HR" (no Polish text, no explanation)

ODPOWIEDŹ:
"""
    
    def _add_privacy_link(self, response_text: str) -> str:
        """Add privacy policy link to the end of AI-generated response."""
        from config import settings
        
        # Find where the signature ends
        if "Z wyrazami szacunku" in response_text:
            # Add privacy link after signature
            privacy_text = ""
            if settings.privacy_policy_url:
                privacy_text = f"\n\nInformacje o przetwarzaniu danych osobowych, w tym wykorzystaniu narzędzi AI znajdziesz na naszej stronie internetowe: {settings.privacy_policy_url}"
            elif settings.company_website:
                privacy_text = f"\n\nInformacje o przetwarzaniu danych osobowych, w tym wykorzystaniu narzędzi AI znajdziesz na naszej stronie internetowe: {settings.company_website}"
            else:
                privacy_text = '\n\nInformacje o przetwarzaniu danych osobowych, w tym wykorzystaniu narzędzi AI znajdziesz na naszej stronie internetowe: "https://www.example.com/privacy".'
            
            # Insert privacy text after signature
            response_text = response_text.replace(
                "Z wyrazami szacunku\n\nDział HR",
                f"Z wyrazami szacunku\n\nDział HR{privacy_text}"
            )
        
        return response_text

