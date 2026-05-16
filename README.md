# WIN Job Center Resume Assistant

An AI-powered resume generation tool built for Mississippi Department of Employment Security (MDES) WIN Job Centers. Staff input candidate information and receive professionally formatted, standardized resumes in PDF and DOCX formats.

## Overview

This Proof of Concept (PoC) standardizes resume creation across 35+ WIN Job Centers statewide, replacing inconsistent manual formatting with AI-assisted generation that maintains uniform quality, tone, and structure.

## Features

- Structured intake form — Work history, education, certifications, skills, military service, volunteer work, references, and professional summary notes
- Resume upload & auto-fill — Upload existing PDF, DOCX, or scanned images to pre-populate the form
- 7 resume levels — Entry-Level, Professional, Skilled Trades, Industry/Technical, Management, Executive, Academic/Research
- 14 target industries — Healthcare, IT, Finance, Manufacturing, and more with industry-specific language
- 10 color schemes — Plus black-and-white option
- AI enhancements— Grammar/spelling correction, bullet-point expansion, professional summary drafting, skill suggestions
- Dual output — PDF (pixel-perfect) and DOCX (editable in Word)
- PII protection — Automatic detection and masking of SSNs, DOBs, passport numbers, license numbers, and credit card numbers
- Staff approval gate — All outputs marked as AI-assisted drafts requiring review before release
- Usage logging — Audit trail of all generations (timestamp, username, candidate name, cost)
- Session management — Login authentication with 5-minute inactivity timeout
- No data retention — Generated resumes exist only in session memory; no permanent storage

## Architecture

```
app.py                  — Streamlit web UI (form, upload, generation, download)
ai.py                   — AI functions (Bedrock calls, PII masking, text extraction, sanitization)
prompts.py              — All AI prompt templates
config.py               — Constants, color palettes, layout maps, industry instructions
pdf_render.py           — PDF renderer (ReportLab)
docx_render.py          — DOCX renderer (python-docx)
layout_measurements.py  — Shared measurements for consistent PDF/DOCX output
usage_log.py            — Generation audit logging
.streamlit/config.toml  — Streamlit theme configuration
```

## Tech Stack

- UI: Streamlit
- AI: Amazon Bedrock (Nova Pro v1)
- Storage: Amazon S3 (training data/style references only)
- PDF: ReportLab
- DOCX: python-docx, lxml
- Text Extraction: pypdf, PyMuPDF, AWS Textract (fallback)
- Language: Python 3.10+

## Prerequisites

- Python 3.10 or higher
- AWS account with access to:
  - Amazon Bedrock (Nova Pro model enabled in us-east-1)
  - Amazon S3 (bucket: `tpmb-resume-training-data`)
  - AWS Textract (optional, for scanned PDF fallback)
- AWS credentials configured (`aws configure` or IAM role)

## Setup

```bash
# Clone the repository
git clone <repository-url>
cd <repository-folder>

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

## Configuration

### Environment Variables (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_USERNAME` | `admin` | Login username |
| `APP_PASSWORD` | `mdes2026` | Login password |

### Streamlit Theme

The app has a light/white theme via `.streamlit/config.toml`. No additional configuration needed.

## Usage

1. Log in with staff credentials
2. Select resume level, target industry, and color scheme
3. (Optional) Upload an existing resume to auto-fill the form
4. Fill in candidate information
5. Click "Suggest Skills" for AI-recommended skills
6. Click "Generate Resume"
7. Review the PDF preview
8. Check the approval box
9. Download PDF and/or DOCX

## Resume Levels & Layouts

| Level | Layout | Header Style |
|-------|--------|-------------|
| Entry-Level | Sidebar Left | Left Name |
| Professional | Single Column | Centered Name |
| Skilled Trades | Single Column | Banner |
| Industry/Technical | Sidebar Right | Left Name |
| Management | Single Column | Centered Name |
| Executive | Single Column | Centered Name |
| Academic/Research | Single Column | Centered Name |

## Testing

```bash

## Security

- PII automatically masked before AI processing
- No resume data persisted beyond session
- Staff login required for access. (Please note the current login in the project does not implement AWS Cognito and is just a basic username and password login.  If in production, this will change)
- 5-minute inactivity timeout
- All outputs labeled as AI-assisted drafts
- Usage logging for audit compliance

## Data Retention

No candidate resume data is stored permanently. Generated files exist only in temporary memory during the active session and are deleted immediately after download. The only persistent data is the usage log (`logs/generation_log.jsonl`) which records timestamps, usernames, candidate names, and cost metrics.

## License

MIT License
