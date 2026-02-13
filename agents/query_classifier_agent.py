"""
Agent for classifying email inquiries and deciding how to respond.
"""

import json
from typing import Dict
from agents.base_agent import BaseAgent


class QueryClassifierAgent(BaseAgent):
    """
    Agent that classifies email inquiries and decides how to respond.

    Can decide:
    - "direct_answer" - can answer based on basic knowledge
    - "rag_answer" - must use RAG from the vector database
    - "forward_to_hr" - forward to HR (specific, sensitive, or human-intervention questions)
    """

    def __init__(self, model_name: str = None, temperature: float = 0.3):
        from config import settings

        model_name = model_name or settings.openai_model
        super().__init__(model_name=model_name, temperature=temperature)

        # Basic knowledge for the agent (can answer without RAG)
        self.basic_knowledge = """
PODSTAWOWA WIEDZA O REKRUTACJI:

1. Proces rekrutacji:
- Pierwsza selekcja (screening) - weryfikacja CV
- Rozmowa HR - ocena kompetencji miękkich
- Ocena techniczna - dla stanowisk technicznych
- Weryfikacja wiedzy
- Rozmowa finalna

2. Komunikacja:
- Odpowiedzi w ciągu 5 dni roboczych
- Profesjonalne i empatyczne komunikaty
- Konstruktywny feedback

3. Zgoda na inne rekrutacje:
- Dobrowolna i można ją wycofać
- Informujemy o nowych ofertach jeśli zgoda wyrażona

4. Feedback:
- Zawsze konstruktywny
- Zawiera mocne strony i obszary do rozwoju
- Motywujący i wspierający

5. Decyzje:
- Akceptacja - przejście do kolejnego etapu
- Odrzucenie - generowanie feedbacku i wysłanie emaila
"""

        # RAG knowledge base description – so the agent knows when to use it
        self.rag_knowledge_description = """
DODATKOWA BAZA WIEDZY (RAG – vektorowa baza dokumentów):

Ta baza zawiera przede wszystkim TREŚCI FORMALNE I POLITYKI firmy, w szczególności:
- rodo_ai_act.txt – fragmenty dokumentów dotyczących RODO, ochrony danych osobowych,
  wykorzystania AI w rekrutacji, podstawy prawne, obowiązki informacyjne itp.
- polityka_rekrutacji.txt – wewnętrzna polityka rekrutacyjna firmy: zasady procesu,
  standardy komunikacji z kandydatami, przechowywania danych, okresy retencji itp.
- informacje_o_firmie.txt – ogólne informacje o firmie, misja, wartości, opis działalności.

RAG jest szczególnie przydatny gdy:
- pytanie dotyczy RODO, ochrony danych, AI Act, podstaw prawnych i formalnych obowiązków,
- pytanie dotyczy wewnętrznych procedur lub polityki rekrutacyjnej,
- kandydat pyta o „jak firma przetwarza dane”, „jak długo przechowujecie CV”, „jak działa AI w rekrutacji”.

Jeśli pytanie DOTYCZY powyższych obszarów, preferuj użycie \"rag_answer\".
Jeśli po użyciu RAG nadal nie ma wystarczających, jednoznacznych informacji – wtedy przekaż sprawę do HR (forward_to_hr).
"""

    def classify_query(self, email_subject: str, email_body: str, sender_email: str) -> Dict:
        """
        Classify the inquiry and decide how to respond.

        Returns:
            Dict with keys:
            - action: "direct_answer" | "rag_answer" | "forward_to_hr"
            - reasoning: decision justification
            - confidence: confidence level (0.0-1.0)
            - suggested_response: response suggestion (if action="direct_answer")
        """
        prompt = self._create_classification_prompt(email_subject, email_body, sender_email)

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in classifying email inquiries in the recruitment process. You analyze inquiries and decide on the best way to respond.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content.strip()
            result = json.loads(result_text)

            # Validate result
            if result.get("action") not in ["direct_answer", "rag_answer", "forward_to_hr"]:
                result["action"] = "forward_to_hr"
                result["reasoning"] = "Invalid classification - forwarded to HR for safety"
                result["confidence"] = 0.0

            # CRITICAL VALIDATION: Different thresholds for different actions
            # For rag_answer: allow trying even with lower confidence (0.5+), as RAG may find the answer
            # For direct_answer and forward_to_hr: require higher confidence (0.7+)
            confidence = result.get("confidence", 0.0)
            try:
                confidence = float(confidence)
            except (ValueError, TypeError):
                confidence = 0.0

            action = result.get("action", "forward_to_hr")
            if action == "rag_answer" and confidence < 0.5:
                # For rag_answer: threshold 0.5 (lower, as RAG may find the answer)
                result["action"] = "forward_to_hr"
                result["reasoning"] = (
                    f"Confidence level ({confidence}) is too low for rag_answer (< 0.5). Forwarded to HR for safety."
                )
                result["confidence"] = confidence
            elif action != "rag_answer" and confidence < 0.7:
                # For direct_answer and forward_to_hr: threshold 0.7
                result["action"] = "forward_to_hr"
                result["reasoning"] = (
                    f"Confidence level ({confidence}) is below required (0.7). Forwarded to HR for safety."
                )
                result["confidence"] = confidence

            return result

        except Exception as e:
            # On error, safer to forward to HR
            return {
                "action": "forward_to_hr",
                "reasoning": f"Error during classification: {str(e)}",
                "confidence": 0.0,
            }

    def _create_classification_prompt(
        self, email_subject: str, email_body: str, sender_email: str
    ) -> str:
        """Create prompt for query classification."""
        return f"""
You are analyzing an email inquiry from a candidate in the recruitment process.

AGENT'S BASIC KNOWLEDGE:
{self.basic_knowledge}

RAG KNOWLEDGE BASE (VECTOR DOCUMENTS AVAILABLE FOR YOU):
{self.rag_knowledge_description}

EMAIL:
Subject: {email_subject}
From: {sender_email}
Content: {email_body}

TASK:
Decide how to best respond to this inquiry. You have 3 options:

⚠️ CRITICAL RULES (BALANCE BETWEEN SAFETY AND USEFULNESS):
- Jeśli możesz odpowiedzieć na podstawie PODSTAWOWEJ WIEDZY lub dokumentów RAG z wysoką pewnością (confidence blisko 1.0),
  wybierz odpowiednio "direct_answer" lub "rag_answer".
- Jeśli po przeanalizowaniu treści nadal masz poważne wątpliwości lub temat dotyczy indywidualnej sytuacji kandydata,
  przekaż sprawę do HR (forward_to_hr).

1. "direct_answer" - You can answer based on basic knowledge (recruitment process, general information, standard procedures)
   - ⚠️ Use when: you are highly confident (confidence is high, np. >= 0.7)
   - ⚠️ Use ONLY when: the question concerns standard procedures that are clearly defined in basic knowledge
   - Examples: "What are the recruitment stages?", "How can I express consent for other recruitments?"
   - ❌ DO NOT use for: questions about details that may vary, questions requiring interpretation

2. "rag_answer" - You must use RAG from vector database (detailed information from company documents)
   - ⚠️ Prefer this option when: the question touches GDPR/RODO, AI Act, data protection, internal recruitment policy,
     or other topics that are TYPICZNIE opisane w dokumentach (regulaminy, polityki, oficjalne zasady).
   - ⚠️ Use when: the question requires detailed knowledge from documents and you reasonably expect the documents to contain the answer.
   - Examples:
     * "Jak dokładnie przetwarzacie moje dane w procesie rekrutacji?"
     * "Jak długo przechowujecie CV?"
     * "Jakie są wymagania RODO w kontekście rekrutacji?"
     * "Jak używacie AI w procesie rekrutacji i jakie są zasady?"
   - Jeśli po skorzystaniu z RAG odpowiedź nadal nie jest wystarczająco jednoznaczna lub pełna – wtedy lepiej wybrać forward_to_hr.

3. "forward_to_hr" - Forward to HR (ALWAYS when you are not 100% certain)
   - ⚠️ Use ALWAYS when:
     * You have serious doubts and confidence is low (np. < 0.7)
     * The question concerns a specific candidate application (status, decision, details)
     * The question is sensitive or requires access to candidate data
     * The question should not be handled by AI
     * RAG documents do not contain sufficiently clear / reliable answer
     * The question requires interpretation or subjective assessment
   - Examples: "What is the status of my application?", "Why was I rejected?", "I want to change data in my CV", "What are the details of AI Act?" (if you are not certain that documents contain the answer)

RETURN JSON in format:
{{
    "action": "direct_answer" | "rag_answer" | "forward_to_hr",
    "reasoning": "Detailed justification of the decision",
    "confidence": 0.0-1.0,
    "suggested_response": "Response suggestion (only if action='direct_answer', otherwise null)"
}}
"""
