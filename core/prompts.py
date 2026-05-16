# prompts.py — All AI prompt templates used by the resume builder.

SPELLING_PROMPT = """You are a spelling and grammar correction tool. Fix errors in the text below and return the corrected version.

Rules:
- Fix misspelled common words: job titles, section headers, descriptions, skills, city/state names, and general vocabulary.
- Do NOT correct or change proper nouns like company names, business names, restaurant names, school names, or organization names.
- Do NOT add, remove, or change any information. Only fix common word spelling and grammar.
- Do NOT reformat or restructure. Keep the exact same layout and line breaks.
- Return ONLY the corrected text. No explanation, no commentary.

Text to correct:
{candidate_info}"""


COLOR_INSTRUCTION_TEMPLATE = """For the layout, the user has chosen this color scheme:
- primary_color: {primary}
- accent_color: {accent}
- secondary_color: [0.33, 0.33, 0.33]
- text_color: [0.1, 0.1, 0.1]
You MUST use these exact primary_color and accent_color values. Do NOT change them.
For banner headers: contact text must be a LIGHT color (0.8+) so it reads on the dark banner.
For sidebar layouts: sidebar text must be LIGHT ([0.8+, 0.8+, 0.8+]) on the dark sidebar background.

Use the following layout for this resume level:
- layout_type: "{layout_type}"
- header_style: "{header_style}"
- section_header_style: "{section_header_style}"
- font: "{font}"
Do NOT change these layout choices. Use them exactly as specified."""


BW_INSTRUCTION_TEMPLATE = """For the layout, use a clean black-and-white design with no color:
- primary_color: [0, 0, 0]
- accent_color: [0, 0, 0]
- secondary_color: [0.33, 0.33, 0.33]
- text_color: [0.1, 0.1, 0.1]
- skills_cell_bg: false

Use the following layout for this resume level:
- layout_type: "{layout_type}"
- header_style: "{header_style}"
- section_header_style: "{section_header_style}"
- font: "{font}"
Do NOT change these layout choices. Use them exactly as specified."""


RESUME_GENERATION_PROMPT = """You are a professional resume writer AND layout designer. Create a complete resume with BOTH a unique layout design and polished content.

ABSOLUTE #1 RULE — ZERO HALLUCINATION:
You must ONLY use information the candidate explicitly provided below. Do NOT invent, fabricate, assume, or generate ANY information not explicitly written in the candidate's input. This is non-negotiable.

Resume level: {resume_level}
{level_instr}

{color_instruction}

Style reference (writing style ONLY): {context}

Return ONLY valid JSON with this structure (no markdown, no explanation):
{{
  "layout": {{
    "primary_color": [R, G, B], "accent_color": [R, G, B],
    "secondary_color": [R, G, B], "text_color": [R, G, B],
    "font": "Arial" or "TNR",
    "layout_type": "single_column" or "sidebar_left",
    "header_style": "centered_name" or "left_name" or "banner",
    "section_header_style": "bar_bg" or "bold_rule" or "spaced_rules" or "spaced_colored" or "bold_italic",
    "bullet_marker": "\\u2022", "skills_cell_bg": false,
    "section_order": ["summary", "experience", "education", "certifications", "military", "skills", "volunteer", "references"],
    "sidebar_sections": ["contact", "education", "certifications", "skills"],
    "sidebar_text_color": [R, G, B], "sidebar_school_color": [R, G, B], "main_rule_color": [R, G, B]
  }},
  "content": {{
    "name": "FULL NAME IN CAPS",
    "contact": "City, State  |  Phone  |  Email  |  LinkedIn (only if provided)",
    "subtitle": "Professional Title or Tagline" or null,
    "summary": "Professional summary paragraph",
    "jobs": [["Job Title", "Company", "Month Year - Month Year", ["bullet 1", ...]], ...],
    "education": [["Degree", "School, Location", "Month Year"], ...],
    "certifications": ["cert 1", ...] or null,
    "military": [["Branch", "Role", "Month Year - Month Year", ["bullet 1", ...]], ...] or null,
    "skills": ["Skill 1", "Skill 2", ...],
    "board": ["item 1", ...] or null,
    "volunteer": [["Role", "Organization", "Month Year - Month Year", ["bullet 1", ...]], ...] or null,
    "references": [["Name", "Title, Company", "Phone", "Email"], ...] or null
  }}
}}

Rules:
- If the candidate did NOT provide data for a section, it MUST be null. This includes jobs — if no work experience is listed, "jobs" MUST be null. Do NOT invent jobs.
- SPELLING/GRAMMAR: Fix misspelled common words. Do NOT change proper nouns.
- NEVER invent job titles, companies, dates, achievements, degrees, schools, or any other facts. If the candidate has no work experience, do NOT create fake jobs. Leave "jobs" as null.
- DATES: If no date provided, use empty string "". Do NOT guess or invent dates.
- Rewrite vague or brief job duties into clear, professional bullet points that expand and reinforce what the role obviously entails. Do NOT add fake numbers or statistics — instead, describe the scope, responsibilities, and impact in plain professional language.
- ALWAYS write 3-5 bullet points per job, even if the candidate only provided 1-2 brief descriptions. Expand short or vague duties into multiple professional bullet points by articulating the obvious responsibilities of that job title and role. This is not inventing — it is professionally elaborating on what the role clearly entails. NEVER leave a job with fewer than 3 bullets.
- Skills should be 9 items (multiples of 3).
- Jobs and education MUST be in reverse chronological order.
- REFERENCES FORMATTING: Capitalize names, job titles, and company names professionally.
- Return ONLY valid JSON.

Candidate information:
{candidate_info}"""


UPLOAD_PARSE_PROMPT = """Extract ALL structured resume data from the text below. Return ONLY valid JSON, no explanation.

CRITICAL RULES:
- Extract EVERY job listed. Do not skip any. If there are 6 jobs, return 6 jobs.
- Extract EVERY education entry. Include school name, city/state, and graduation year for each.
- Extract EVERY volunteer entry with full description.
- Extract EVERY reference with all available details (name, title, company, email, phone).
- Extract ALL certifications.
- Do NOT summarize or combine entries. Each separate position/entry must be its own array item.
- For degree types, use standard abbreviations: "High School Diploma", "GED", "Certificate", "Associate of Arts (AA)", "Associate of Science (AS)", "Associate of Applied Science (AAS)", "Bachelor of Arts (BA)", "Bachelor of Science (BS)", "Bachelor of Business Administration (BBA)", "Bachelor of Fine Arts (BFA)", "Master of Arts (MA)", "Master of Science (MS)", "Master of Business Administration (MBA)", "Master of Education (MEd)", "Master of Public Administration (MPA)", "Master of Social Work (MSW)", "Doctor of Philosophy (PhD)", "Doctor of Education (EdD)", "Doctor of Medicine (MD)", "Juris Doctor (JD)"
- For field of study, extract it separately (e.g., "Marketing", "Computer Science"). Use empty string if not applicable.

{{
  "first_name": "first name or empty string",
  "last_name": "last name or empty string",
  "city": "city or empty string",
  "state": "2-letter state abbreviation or empty string",
  "email": "email or empty string",
  "phone": "phone number or empty string",
  "linkedin": "linkedin url or empty string",
  "jobs": [["Job Title", "Company", "Start Date", "End Date", "Description of duties"], ...] or [],
  "education": [["Degree Type", "Field of Study", "School Name", "City, State", "Graduation Year"], ...] or [],
  "certifications": ["cert 1", ...] or [],
  "military": "military service description or empty string",
  "skills": "comma-separated skills or empty string",
  "volunteer": [["Role/Title", "Organization", "Start Date", "End Date", "Description"], ...] or [],
  "references": [["First Name", "Last Name", "Job Title", "Company", "Email", "Phone"], ...] or []
}}

Resume text:
{cleaned_text}"""


SKILL_SUGGESTION_PROMPT = """Based on ALL of the candidate information below, suggest exactly 9 relevant professional skills (comma-separated, no numbering, no explanation). Consider their work experience, education, certifications, military service, and volunteer work. Only suggest skills that are realistic and directly supported by the information provided.

{skill_context}"""
