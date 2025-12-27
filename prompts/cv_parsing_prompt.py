"""Prompt template for CV parsing agent."""

CV_PARSING_PROMPT_TEMPLATE = """You are an expert CV parser. Your task is to extract and structure all information from a CV document.

Extract the following information from the CV text provided below:

1. Personal Information:
   - Full name
   - Email address
   - Phone number
   - Location/Address
   - LinkedIn profile
   - GitHub profile
   - Portfolio website

2. Professional Summary:
   - Extract the summary or objective section if present

3. Education:
   - For each education entry, extract:
     * Institution name
     * Degree obtained
     * Field of study
     * Start and end dates
     * GPA (if mentioned)
     * Honors or distinctions

4. Work Experience:
   - For each position, extract:
     * Company name
     * Job title/position
     * Start and end dates
     * Job description
     * Key achievements

5. Skills:
   - List all skills mentioned
   - Categorize them if possible (Technical, Language, Soft skills)
   - Note proficiency levels if mentioned

6. Certifications:
   - Certification name
   - Issuing organization
   - Date obtained
   - Expiry date (if applicable)

7. Languages:
   - Language name
   - Proficiency level

8. Additional Information:
   - Any other relevant information (projects, publications, awards, etc.)

CV Text:
{cv_text}

IMPORTANT: Return the data in EXACT JSON structure matching the CVData Pydantic model. Use these EXACT field names:

Top level fields:
- full_name (NOT personal_information.full_name)
- email
- phone
- location
- linkedin
- github
- portfolio
- summary (NOT professional_summary)
- education (list)
- experience (list)
- skills (list of objects with: name, category, proficiency)
- certifications (list)
- languages (list)
- additional_info

Education objects must have:
- institution (NOT institution_name)
- degree (NOT degree_obtained)
- field_of_study
- start_date
- end_date
- gpa
- honors

Experience objects must have:
- company (NOT company_name)
- position (NOT job_title)
- start_date
- end_date
- description (NOT job_description)
- achievements (list, NOT key_achievements as string)

Skill objects must have:
- name
- category
- proficiency

Certification objects must have:
- name (NOT certification_name)
- issuer (NOT issuing_organization)
- date (NOT date_obtained)
- expiry_date

Language objects must have:
- language
- proficiency

Return ONLY valid JSON matching this exact structure. Do not nest personal_information or use alternative field names.
"""

# Simple wrapper class to maintain compatibility with .format() calls
class CV_PARSING_PROMPT:
    def format(self, **kwargs):
        return CV_PARSING_PROMPT_TEMPLATE.format(**kwargs)

CV_PARSING_PROMPT = CV_PARSING_PROMPT()

