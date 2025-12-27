"""
Agent do generowania odpowiedzi na zapytania emailowe.
Może używać podstawowej wiedzy lub RAG z bazy wektorowej.
"""
import json
from typing import Dict, List, Optional
from agents.base_agent import BaseAgent


class QueryResponderAgent(BaseAgent):
    """
    Agent generujący odpowiedzi na zapytania emailowe.
    Może używać podstawowej wiedzy lub RAG z bazy wektorowej.
    """
    
    def __init__(self, model_name: str = None, temperature: float = 0.7):
        from config import settings
        model_name = model_name or settings.openai_model
        super().__init__(model_name=model_name, temperature=temperature)
        
        # Podstawowa wiedza
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
        Generuj odpowiedź na zapytanie emailowe.
        
        Args:
            email_subject: Temat emaila
            email_body: Treść emaila
            sender_email: Email nadawcy
            rag_context: Kontekst z RAG (lista dokumentów z bazy wektorowej)
        
        Returns:
            Wygenerowana odpowiedź lub None jeśli agent nie jest pewien (wtedy należy przekazać do HR)
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
            
            # Sprawdź czy agent zwrócił sygnał przekazania do HR
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
                "skontaktuje się z państwem w najkrótszym możliwym terminie"  # Typowa fraza gdy przekazujemy do HR
            ]
            
            response_lower = response_text.lower()
            has_uncertainty = any(phrase in response_lower for phrase in uncertainty_phrases)
            
            if has_uncertainty:
                logger.warning(f"Response contains uncertainty phrases - agent not confident enough. Phrases found: {[p for p in uncertainty_phrases if p in response_lower]}")
                return None
            
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

⚠️ CRITICAL RULE: Answer ONLY when you are 100% certain of the answer.
If you have ANY doubts, DO NOT answer - forward to HR.

REQUIREMENTS:
1. ⚠️ CRITICAL: Answer ONLY when you are 100% certain of the answer based on basic knowledge or RAG context
2. ⚠️ CRITICAL: If RAG context does not contain the exact answer to the question, DO NOT answer - return special response forwarding to HR
3. ⚠️ CRITICAL: If the answer requires interpretation, subjective assessment, or is not clearly specified in sources, DO NOT answer - return special response forwarding to HR
4. ⚠️ CRITICAL: If the question concerns details that may vary or require current data, DO NOT answer - return special response forwarding to HR
5. The answer must be factually accurate based on basic knowledge and RAG context (if available)
6. Use professional but friendly tone
7. Be empathetic and supportive
8. ❌ NEVER answer in style: "Although we do not have detailed information..." - this means you should forward to HR
9. ❌ NEVER answer in style: "we do not have detailed information" - this indicates lack of certainty
10. ❌ NEVER answer if you do not have an exact, certain answer
11. ❌ NEVER answer if RAG context does not contain a direct answer to the question
12. ⚠️ CRITICAL: If you are not certain of the answer, ALWAYS return ONLY: "FORWARD_TO_HR" (without any other text, no Polish text, just these exact words)
13. ⚠️ CRITICAL: DO NOT generate a response saying "we forwarded to HR" or "we will forward to HR" - if you are not certain, return ONLY "FORWARD_TO_HR"
14. ⚠️ CRITICAL: DO NOT write "Dziękujemy za Pańskie zapytanie. Przekazaliśmy je do działu HR..." - if you are not certain, return ONLY "FORWARD_TO_HR"
15. ⚠️ CRITICAL: If you cannot answer with 100% certainty, return ONLY "FORWARD_TO_HR" - do NOT write any Polish response
16. Always end the response with: "Z wyrazami szacunku\n\nDział HR" (ONLY if you are answering, not if returning FORWARD_TO_HR)
17. ⚠️ CRITICAL: The response MUST be written in POLISH (Polish language) - this is mandatory (ONLY if you are answering, not if returning FORWARD_TO_HR)
18. If the question concerns a specific candidate application, suggest direct contact with HR

LANGUAGE REQUIREMENT (ONLY if answering, not if returning FORWARD_TO_HR):
- You MUST write the ENTIRE response in POLISH (Polish language)
- Use natural, conversational Polish
- Professional but friendly tone
- All content must be in Polish, including greetings, explanations, and closing
- The response should sound natural and human-like in Polish

REMEMBER:
- If you are 100% certain and can answer → Write response in Polish
- If you are NOT 100% certain → Return ONLY "FORWARD_TO_HR" (no Polish text, no explanation)

ODPOWIEDŹ:
"""

