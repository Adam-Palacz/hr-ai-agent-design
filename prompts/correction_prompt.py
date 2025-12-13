"""Prompt template for feedback correction based on validation feedback."""
try:
    from langchain_core.prompts import PromptTemplate
except ImportError:
    try:
        from langchain.prompts import PromptTemplate
    except ImportError:
        from langchain_core.prompts.prompt import PromptTemplate

CORRECTION_PROMPT = PromptTemplate(
    input_variables=["original_html", "validation_reasoning", "issues_found", "ethical_concerns", "factual_errors", "cv_data", "hr_feedback", "job_offer"],
    template="""You are an AI assistant responsible for correcting candidate feedback emails based on validation feedback.

Your task is to fix the feedback email by addressing all issues identified by the validator while maintaining the original intent and structure.

ORIGINAL FEEDBACK EMAIL (needs correction):
{original_html}

VALIDATION FEEDBACK:
Reasoning: {validation_reasoning}

Issues Found:
{issues_found}

Ethical Concerns:
{ethical_concerns}

Factual Errors:
{factual_errors}

CANDIDATE INFORMATION (from CV):
{cv_data}

HR FEEDBACK:
{hr_feedback}

JOB OFFER INFORMATION:
{job_offer}

CORRECTION INSTRUCTIONS:
1. Address ALL issues listed above
2. Fix ALL factual errors to match the CV data and HR feedback
3. Remove or rewrite ANY content that is discriminatory, offensive, or unethical
4. Ensure the tone remains professional, respectful, and supportive
5. Maintain the original structure and flow of the email
6. Keep the decision announcement and key messages intact (unless they were part of the problem)
7. Ensure the corrected email follows all the original guidelines:
   - Starts with: "Dziękujemy za złożenie aplikacji na stanowisko [Stanowisko] w [Firma]."
   - For rejections: "Z przykrością informujemy, że zdecydowaliśmy się procedować z innymi kandydatami."
   - Then: "Chciałbym/chciałabym podzielić się z Tobą opinią dotyczącą Twojej kandydatury."
   - Natural, flowing text (not separate sections)
   - Warm, friendly closing
8. Do NOT introduce new issues while fixing existing ones
9. Ensure all facts are accurate and match the CV and HR feedback

CRITICAL: The corrected email must be:
- Factually accurate
- Ethically sound
- Professional and respectful
- Free of discrimination
- Free of offensive content
- Supportive and constructive

{format_instructions}
"""
)

