# config.py — Shared constants, color palettes, layout maps, and industry instructions.

import os
import boto3

# AWS clients
s3      = boto3.client("s3", region_name="us-east-1")
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
BUCKET   = os.environ.get("RESUME_S3_BUCKET")
MODEL_ID = "us.amazon.nova-pro-v1:0"

# paths
LOGO_PATH = os.path.join(os.path.dirname(__file__), '..', 'assets', 'winjobcenter_logo.png')

# color palettes
COLOR_PALETTES = {
    "navy":      {"primary": [0.12, 0.28, 0.53], "accent": [0.65, 0.74, 0.84]},
    "teal":      {"primary": [0.11, 0.42, 0.42], "accent": [0.60, 0.78, 0.78]},
    "forest":    {"primary": [0.13, 0.33, 0.18], "accent": [0.62, 0.76, 0.65]},
    "burgundy":  {"primary": [0.40, 0.10, 0.13], "accent": [0.78, 0.62, 0.64]},
    "purple":    {"primary": [0.28, 0.15, 0.42], "accent": [0.70, 0.65, 0.80]},
    "charcoal":  {"primary": [0.17, 0.17, 0.17], "accent": [0.60, 0.60, 0.60]},
    "slate":     {"primary": [0.25, 0.32, 0.38], "accent": [0.62, 0.68, 0.74]},
    "brown":     {"primary": [0.33, 0.22, 0.13], "accent": [0.72, 0.65, 0.56]},
    "magenta":   {"primary": [0.42, 0.12, 0.30], "accent": [0.78, 0.60, 0.70]},
    "steel":     {"primary": [0.22, 0.30, 0.42], "accent": [0.62, 0.70, 0.80]},
    "none":      {"primary": [0.0, 0.0, 0.0],    "accent": [0.0, 0.0, 0.0]},
}

# fixed layout per resume level
LAYOUT_MAP = {
    'Entry-Level':        ('sidebar_left', 'left_name', 'bold_rule', 'Arial'),
    'Professional':       ('single_column', 'centered_name', 'bold_rule', 'Arial'),
    'Skilled Trades':     ('single_column', 'banner', 'spaced_colored', 'Arial'),
    'Industry/Technical': ('sidebar_right', 'left_name', 'bold_rule', 'Arial'),
    'Management':         ('single_column', 'centered_name', 'spaced_rules', 'Arial'),
    'Executive':          ('single_column', 'centered_name', 'bold_italic', 'TNR'),
    'Academic/Research':  ('single_column', 'centered_name', 'bold_italic', 'TNR'),
}

# industry-specific layout overrides
INDUSTRY_LAYOUT_MAP = {
    'Healthcare':                     ('single_column', 'centered_name', 'bar_bg'),
    'Information Technology':         ('sidebar_left',  'left_name',     'bold_rule'),
    'Finance & Banking':              ('single_column', 'centered_name', 'spaced_rules'),
    'Manufacturing & Skilled Trades': ('single_column', 'banner',        'spaced_colored'),
    'Retail & Customer Service':      ('sidebar_left',  'left_name',     'bold_rule'),
    'Transportation & Logistics':     ('single_column', 'banner',        'spaced_colored'),
    'Construction':                   ('single_column', 'banner',        'spaced_colored'),
    'Education':                      ('single_column', 'centered_name', 'bold_italic'),
    'Hospitality & Food Service':     ('sidebar_left',  'left_name',     'bold_rule'),
    'Government & Public Service':    ('single_column', 'centered_name', 'spaced_rules'),
    'Sales & Marketing':              ('sidebar_left',  'left_name',     'bar_bg'),
    'Administrative & Office Support':('single_column', 'centered_name', 'bold_rule'),
    'Military & Defense':             ('sidebar_right', 'left_name',     'spaced_rules'),
    'Engineering':                    ('sidebar_right', 'left_name',     'spaced_colored'),
}

LEVEL_INSTRUCTIONS = {
    "Entry-Level": (
        "Entry-level resume. Simple, clear, approachable language. "
        "Emphasize reliability, eagerness to learn, transferable skills. "
        "Keep bullet points short. Summary conveys enthusiasm and potential."
    ),
    "Professional": (
        "Professional mid-career resume. Confident, results-driven language. "
        "Quantify achievements with numbers/percentages/dollars. "
        "Emphasize career progression and impact."
    ),
    "Skilled Trades": (
        "Skilled trades resume. Direct technical language, industry terms. "
        "Highlight certifications, safety records, equipment proficiencies. "
        "Reference specific tools, machinery, measurable output."
    ),
    "Industry/Technical": (
        "Technical resume. Precise domain-specific terminology. "
        "Highlight systems expertise, innovation, technical leadership. "
        "Include specific technologies and methodologies."
    ),
    "Management": (
        "Management resume. Team leadership, operational improvements, budgets. "
        "Quantify team sizes, budget amounts, efficiency gains. "
        "Convey a leader who drives results through others."
    ),
    "Executive": (
        "Executive resume. High-level strategic language. "
        "Focus on P&L, board engagement, enterprise initiatives. "
        "Quantify with revenue, headcount, organizational scale."
    ),
    "Academic/Research": (
        "Academic resume. Formal tone. Emphasize credentials, publications, "
        "research, grants, academic leadership, scholarly impact."
    ),
}

INDUSTRY_INSTRUCTIONS = {
    'Healthcare': 
        "Healthcare industry resume. Emphasize patient care, clinical skills, HIPAA compliance, EHR systems, certifications (CNA, RN, LPN), and measurable patient outcomes.",
    'Information Technology': 
        "IT/Software industry resume. Highlight programming languages, frameworks, cloud platforms (AWS, Azure), DevOps tools, system architecture, and quantified project outcomes.",
    'Finance & Banking': 
        "Finance/Banking industry resume. Emphasize regulatory compliance, risk management, financial analysis, portfolio management, and quantified revenue/cost impact.",
    'Manufacturing & Skilled Trades': 
        "Manufacturing resume. Highlight equipment operation, quality control, lean/Six Sigma, safety records, production metrics, and technical certifications.",
    'Retail & Customer Service': 
        "Retail/Customer Service resume. Emphasize sales metrics, customer satisfaction scores, inventory management, POS systems, and team coordination.",
    'Transportation & Logistics': 
        "Transportation/Logistics resume. Highlight CDL certifications, route optimization, fleet management, DOT compliance, and delivery/shipment metrics.",
    'Construction': 
        "Construction resume. Emphasize project management, blueprint reading, OSHA compliance, heavy equipment operation, crew supervision, and project completion metrics.",
    'Education': 
        "Education industry resume. Highlight teaching certifications, curriculum development, student outcomes, classroom management, and professional development.",
    'Hospitality & Food Service': 
        "Hospitality/Food Service resume. Emphasize food safety certifications (ServSafe), customer service, high-volume operations, inventory control, and team leadership.",
    'Government & Public Service': 
        "Government/Public Service resume. Highlight policy compliance, grant management, program administration, stakeholder engagement, and measurable community impact.",
    'Sales & Marketing': 
        "Sales/Marketing resume. Emphasize revenue generation, lead conversion rates, campaign ROI, CRM tools, market analysis, and quota achievement.",
    'Administrative & Office Support': 
        "Administrative resume. Highlight office management, scheduling, data entry accuracy, Microsoft Office proficiency, records management, and process improvements.",
    'Military & Defense': 
        "Military/Defense transition resume. Translate military roles into civilian equivalents, highlight leadership, security clearances, logistics, and team management.",
    'Engineering': 
        "Engineering resume. Emphasize technical design, CAD/CAM proficiency, project engineering, PE licensure, FEA/simulation tools, compliance with industry standards (ASME, IEEE), and quantified project outcomes such as cost savings, efficiency gains, and timelines.",
}

# default section order
DEFAULT_SECTION_ORDER = ['summary', 'experience', 'education', 'military',
                         'volunteer', 'board', 'certifications', 'skills', 'references']

SECTION_DATA_KEYS = {
    'summary': 'summary', 'experience': 'jobs', 'education': 'education',
    'certifications': 'certifications', 'military': 'military',
    'skills': 'skills', 'volunteer': 'volunteer', 'references': 'references',
    'board': 'board',
}
