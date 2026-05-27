import streamlit as st
import io
import os
import re
import json
import base64
import time
import tempfile

import boto3

from core.config import COLOR_PALETTES
from core.ai import (load_s3_context as _load_s3_context,
                generate_resume, sanitize, sanitize_layout,
                mask_pii, extract_text_from_upload)
from core.pdf_render import render_pdf
from core.docx_render import render_docx
from core.prompts import UPLOAD_PARSE_PROMPT, SKILL_SUGGESTION_PROMPT
from core.usage_log import log_generation


# form helpers

def _format_phone(raw):
    """Format a raw phone string into (XXX)-XXX-XXXX."""
    digits = ''.join(c for c in raw if c.isdigit())
    if len(digits) == 10:
        return f"({digits[:3]})-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]})-{digits[4:7]}-{digits[7:]}"
    elif digits:
        return digits
    return raw


def _get_prefill(prefill_list, index, num_fields):
    """Safely get a prefill entry, returning empty strings for missing fields."""
    if index < len(prefill_list):
        entry = prefill_list[index]
        if isinstance(entry, list):
            return [entry[i] if i < len(entry) else "" for i in range(num_fields)]
    return [""] * num_fields


def _render_job_entry(index, prefill_list, prefix, labels):
    """Render a job/volunteer entry form block. Returns (title, org, start, end, desc)."""
    title_label, org_label = labels
    pf = _get_prefill(prefill_list, index, 5)
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input(title_label, key=f"{prefix}_title_{index}", value=pf[0])
        org = st.text_input(org_label, key=f"{prefix}_org_{index}", value=pf[1])
    with c2:
        start = st.text_input("Start Date", key=f"{prefix}_start_{index}", value=pf[2],
                              placeholder="June 2018")
        end = st.text_input("End Date", key=f"{prefix}_end_{index}", value=pf[3],
                            placeholder="May 2023 (or Present)")
    desc = st.text_area("Description / Duties", key=f"{prefix}_desc_{index}", height=80, value=pf[4])
    return (title, org, start, end, desc)


# S3 context (cached)
@st.cache_data(show_spinner="Loading")
def load_s3_context():
    return _load_s3_context()

# streamlit UI
st.set_page_config(page_title='WIN Job Center Resume Assistant', page_icon='📄', layout='centered')

# login gate
# check query params for persistent session
if st.query_params.get('session') == 'active':
    st.session_state['authenticated'] = True

if not st.session_state.get('authenticated'):
    st.markdown("""
    <style>
        .logo-container { display: flex; justify-content: center; margin-top: 2rem; margin-bottom: 1rem; }
        .logo-container img { max-height: 120px; }
        h1, h2, h3 { text-align: center; }
    </style>
    """, unsafe_allow_html=True)
    _logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'mdes_logo.png')
    if os.path.exists(_logo_path):
        with open(_logo_path, 'rb') as _f:
            _logo_b64 = base64.b64encode(_f.read()).decode()
        st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{_logo_b64}"></div>', unsafe_allow_html=True)
    st.title('WIN Job Center Resume Assistant')
    st.subheader('Staff Login')
    with st.form('login_form'):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        if st.form_submit_button('Log In'):
            if username == "admin" and password == "mdes2026":
                st.session_state['authenticated'] = True
                st.session_state['_username'] = username
                st.session_state['_last_activity'] = time.time()
                st.query_params['session'] = 'active'
                st.rerun()
            else:
                st.error('Invalid username or password.')
    st.stop()

# session timeout: 5 minutes of inactivity
_SESSION_TIMEOUT = 300
if time.time() - st.session_state.get('_last_activity', time.time()) > _SESSION_TIMEOUT:
    st.session_state['authenticated'] = False
    st.query_params.clear()
    st.warning("Session expired due to inactivity. Please log in again.")
    st.rerun()
st.session_state['_last_activity'] = time.time()

# logout button
if st.button('Logout', key='logout_btn'):
    st.session_state['authenticated'] = False
    st.query_params.clear()
    st.rerun()


# centered MDES logo + minimal layout styling
st.markdown("""
<style>
    .logo-container { display: flex; justify-content: center; margin-top: 1rem; margin-bottom: 0.5rem; }
    .logo-container img { max-height: 120px; }
    h1 { text-align: center; }
    [data-testid="stForm"] { border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.5rem; }
    .stFormSubmitButton:last-of-type button[kind="primary"] { background-color: #cc0000 !important; color: #ffffff !important; border: none !important; }
    .stFormSubmitButton:last-of-type button[kind="primary"]:hover { background-color: #990000 !important; }
</style>
""", unsafe_allow_html=True)

logo_path = os.path.join(os.path.dirname(__file__), 'assets', 'mdes_logo.png')
if os.path.exists(logo_path):
    with open(logo_path, 'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)

st.title("WIN Job Center Resume Assistant")
st.markdown("Fill in the candidate's information below and click **Generate Resume**.")
st.info("**AI-Assisted Draft Notice:** All resume outputs are AI-assisted drafts and require staff review and approval prior to release to citizens.")
st.info("**Data Retention:** No resume data is stored beyond this session. All generated files are temporary and deleted immediately after download.")

with st.spinner("Loading..."):
    context = load_s3_context()

# resume level and color outside the form so they trigger reruns
st.divider()
resume_level = st.selectbox(
    "Resume Level",
    options=["Entry-Level", "Professional", "Skilled Trades",
             "Industry/Technical", "Management", "Executive", "Academic/Research"],
    index=1,
    help="Select the level that best matches the candidate's career stage."
)

# target Industry — always shown
target_industry = st.selectbox(
    "Target Industry (optional)",
    options=["", "Healthcare", "Information Technology", "Finance & Banking",
             "Manufacturing & Skilled Trades", "Retail & Customer Service",
             "Transportation & Logistics", "Construction", "Education",
             "Engineering", "Hospitality & Food Service", "Government & Public Service",
             "Sales & Marketing", "Administrative & Office Support",
             "Military & Defense", "Other"],
    index=0,
    key="target_industry_u"
)
if target_industry == "Other":
    target_industry = st.text_input("Specify Industry", placeholder="e.g., Aerospace, Agriculture, Nonprofit")

_color_options = ["none"] + [k for k in COLOR_PALETTES if k != "none"]
def _color_label(name):
    if name == "none":
        return "No Color (Black & White)"
    return name.title()

color_name = st.selectbox(
    "Color Scheme",
    options=_color_options,
    index=0,
    format_func=_color_label,
    help="Choose a color for your resume, or leave as No Color for black & white."
)

st.divider()

# upload existing resume (outside form so it triggers rerun) 
st.subheader("Upload Existing Resume (optional)")
uploaded_file = st.file_uploader(
    "Upload a PDF, DOCX, or scanned image to auto-fill the form below",
    type=["pdf", "docx", "png", "jpg", "jpeg", "webp"],
    help="We'll extract the text, remove PII, and pre-fill the form fields."
)

if uploaded_file is not None and st.session_state.get("_last_upload") != uploaded_file.name:
    with st.spinner("Extracting text from uploaded file..."):
        try:
            raw_text = extract_text_from_upload(uploaded_file)
            cleaned_text, pii_warnings = mask_pii(raw_text)
            # collapse spaced-out headers like "P  R  O  F  E  S  S  I  O  N  A  L"
            cleaned_text = re.sub(
                r'(?:[A-Z]  ){2,}[A-Z]',
                lambda m: m.group(0).replace('  ', ''),
                cleaned_text
            )
            cleaned_text = re.sub(r'  +', ' ', cleaned_text)
            if pii_warnings:
                st.warning("⚠️ PII detected and removed: " + "; ".join(pii_warnings))

            # Ask Nova to parse the extracted text into structured fields
            _bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
            parse_prompt = UPLOAD_PARSE_PROMPT.format(cleaned_text=cleaned_text)
            resp = _bedrock.invoke_model(
                modelId="us.amazon.nova-pro-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps({
                    "messages": [{"role": "user", "content": [{"text": parse_prompt}]}],
                    "inferenceConfig": {"maxTokens": 8000, "temperature": 0.0}
                })
            )
            result = json.loads(resp["body"].read())
            parsed_raw = result["output"]["message"]["content"][0]["text"].strip()
            if parsed_raw.startswith("```"):
                parsed_raw = parsed_raw.split("```")[1]
                if parsed_raw.startswith("json"):
                    parsed_raw = parsed_raw[4:]
            parsed = json.loads(parsed_raw.strip())

            # store parsed data in session state for form defaults
            st.session_state["_prefill"] = parsed
            st.session_state["_last_upload"] = uploaded_file.name
            st.session_state["_upload_raw_text"] = cleaned_text
            
            # clear stale widget keys so new prefill values take effect
            for key in list(st.session_state.keys()):
                if any(key.startswith(p) for p in [
                    'degree_sel_', 'degree_field_', 'school_', 'school_loc_', 'grad_', 'enrolled_',
                    'job_title_', 'job_org_', 'job_start_', 'job_end_', 'job_desc_',
                    'cert_',
                    'vol_title_', 'vol_org_', 'vol_start_', 'vol_end_', 'vol_desc_',
                    'ref_first_', 'ref_last_', 'ref_title_', 'ref_company_', 'ref_email_', 'ref_phone_',
                    'phone_input', 'suggested_skills'
                ]):
                    del st.session_state[key]
            st.success("✅ Resume parsed! Form fields have been pre-filled below.")
            st.rerun()
        except Exception as e:
            st.error(f"Error parsing uploaded file: {e}")

# load prefill data from session state
_pf = st.session_state.get("_prefill", {})
# convert any None values to empty strings throughout prefill
for key in ['first_name', 'last_name', 'city', 'state', 'email', 'phone', 'linkedin', 'military', 'skills']:
    if _pf.get(key) is None:
        _pf[key] = ""
for key in ['jobs', 'education', 'certifications', 'volunteer', 'references']:
    if _pf.get(key) is None:
        _pf[key] = []
    elif isinstance(_pf.get(key), list):
        cleaned = []
        for item in _pf[key]:
            if isinstance(item, list):
                cleaned.append([x if x is not None else "" for x in item])
            elif isinstance(item, str):
                cleaned.append(item if item is not None else "")
            elif item is not None:
                cleaned.append(item)
        _pf[key] = cleaned



# normalize education prefill: handle both 4-element and 5-element arrays
_pf_edu_raw = _pf.get("education", [])
_pf_edu_normalized = []
for edu in _pf_edu_raw:
    if not isinstance(edu, list):
        continue
    # Convert None to empty string in all elements
    edu = [x if x is not None else "" for x in edu]
    if len(edu) == 5:
        _pf_edu_normalized.append(edu)
    elif len(edu) == 4:
        deg = edu[0] or ""
        field = ""
        for sep in [' in ', ' In ']:
            if sep in deg:
                deg, field = deg.split(sep, 1)
                break
        _pf_edu_normalized.append([deg.strip(), field.strip(), edu[1] or "", edu[2] or "", edu[3] or ""])
    else:
        padded = list(edu) + [""] * (5 - len(edu))
        _pf_edu_normalized.append(padded[:5])
_pf["education"] = _pf_edu_normalized

st.divider()

with st.form("resume_form"):
    st.subheader("Personal Information")
    col1, col2 = st.columns(2)
    with col1:
        first_name = st.text_input("First Name *", value=_pf.get("first_name", ""))
    with col2:
        last_name  = st.text_input("Last Name *", value=_pf.get("last_name", ""))

    col3, col4 = st.columns(2)
    with col3:
        city = st.text_input("City *", value=_pf.get("city", ""))
    with col4:
        _state_options = [
            "", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
            "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
            "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
            "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
            "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
        ]
        _pf_state = _pf.get("state", "").upper()
        _state_idx = _state_options.index(_pf_state) if _pf_state in _state_options else 0
        state = st.selectbox("State *", options=_state_options, index=_state_idx,
                             help="Select the candidate's state.")

    col5, col6 = st.columns(2)
    with col5:
        email = st.text_input("Email Address *", value=_pf.get("email", ""))
    with col6:
        raw_phone = st.text_input("Phone Number * (digits only)", value=_pf.get("phone", ""),
                                  placeholder="(555)-555-6655", key="phone_input")
        # strip non-digits and auto-format
        phone = _format_phone(raw_phone)
        if raw_phone and phone != raw_phone:
            st.caption(f"📞 Formatted: {phone}")

    linkedin = st.text_input("LinkedIn URL (optional)", value=_pf.get("linkedin", ""))

    full_name = f"{first_name} {last_name}".strip()
    city_state = f"{city}, {state}" if city and state else city or state

    st.subheader("Work Experience")
    _pf_jobs = _pf.get("jobs", [])
    num_jobs = st.number_input("Number of employers", min_value=0, max_value=10,
                               value=len(_pf_jobs) if _pf_jobs else 0, step=1)
    jobs = []
    for j in range(int(num_jobs)):
        st.markdown(f"**Employer {j + 1}**")
        jobs.append(_render_job_entry(j, _pf_jobs, "job", ("Job Title", "Company Name")))

    st.subheader("Education")
    _pf_edu = _pf.get("education", [])
    num_edu = st.number_input("Number of education entries", min_value=0, max_value=10,
                              value=len(_pf_edu) if _pf_edu else 0, step=1)
    edu_entries = []
    for e in range(int(num_edu)):
        st.markdown(f"**Education {e + 1}**")
        _pe = _pf_edu[e] if e < len(_pf_edu) else ["", "", "", "", ""]
        _degree_options = [
            "", "High School Diploma", "GED", "Certificate", "Associate of Arts (AA)",
            "Associate of Science (AS)", "Associate of Applied Science (AAS)",
            "Bachelor of Arts (BA)", "Bachelor of Science (BS)",
            "Bachelor of Business Administration (BBA)", "Bachelor of Fine Arts (BFA)",
            "Master of Arts (MA)", "Master of Science (MS)",
            "Master of Business Administration (MBA)", "Master of Education (MEd)",
            "Master of Public Administration (MPA)", "Master of Social Work (MSW)",
            "Doctor of Philosophy (PhD)", "Doctor of Education (EdD)",
            "Doctor of Medicine (MD)", "Juris Doctor (JD)"
        ]
        _pf_deg = _pe[0] if len(_pe) > 0 else ""
        _pf_field = _pe[1] if len(_pe) > 1 else ""
        # if AI combined degree+field into one string (e.g. "PhD in Computer Science"), split them
        if _pf_deg and not _pf_field:
            for sep in [' in ', ' In ']:
                if sep in _pf_deg:
                    _pf_deg, _pf_field = _pf_deg.split(sep, 1)
                    _pf_deg = _pf_deg.strip()
                    _pf_field = _pf_field.strip()
                    break
        # fuzzy match prefill degree to dropdown options
        _deg_idx = 0
        if _pf_deg:
            _pf_deg_lower = _pf_deg.strip().lower().replace('.', '')
            for i, opt in enumerate(_degree_options):
                if not opt:
                    continue
                opt_lower = opt.lower().replace('.', '')
                opt_abbr = opt.split('(')[1].rstrip(')').lower().replace('.', '') if '(' in opt else ''
                if (opt_lower == _pf_deg_lower
                    or _pf_deg_lower in opt_lower
                    or opt_lower in _pf_deg_lower
                    or opt_abbr == _pf_deg_lower):
                    _deg_idx = i
                    break
        e1, e2 = st.columns(2)
        with e1:
            degree = st.selectbox("Degree / Diploma", options=_degree_options, index=_deg_idx, key=f"degree_sel_{e}")
        with e2:
            degree_field = st.text_input("Field of Study (if applicable)", key=f"degree_field_{e}",
                value=_pf_field, placeholder="e.g., Marketing, Nursing")
        if degree and degree_field:
            degree = f"{degree} in {degree_field}"
        e3, e4 = st.columns(2)
        with e3:
            school = st.text_input("School Name", key=f"school_{e}", value=_pe[2] if len(_pe) > 2 else "", placeholder="Central High School")
        with e4:
            school_city = st.text_input("School City, State", key=f"school_loc_{e}", value=_pe[3] if len(_pe) > 3 else "", placeholder="Jackson, MS")
        grad_year = st.text_input("Graduation Year", key=f"grad_{e}", value=_pe[4] if len(_pe) > 4 else "", placeholder="2017")
        still_enrolled = st.checkbox("Currently enrolled", key=f"enrolled_{e}")
        if still_enrolled:
            grad_year = "Present"
        edu_entries.append((degree, school, school_city, grad_year))

    st.subheader("Certifications (optional)")
    _pf_certs = _pf.get("certifications", [])
    num_certs = st.number_input("Number of certifications", min_value=0, max_value=10,
                                value=len(_pf_certs) if _pf_certs else 0, step=1)
    cert_entries = []
    for c in range(int(num_certs)):
        _pc = _pf_certs[c] if c < len(_pf_certs) else ""
        cert_name = st.text_input("Certification Name", key=f"cert_{c}", value=_pc, placeholder="OSHA 10-Hour")
        cert_entries.append(cert_name)

    st.subheader("Military Service (optional)")
    military = st.text_area("Military Service", height=80, value=_pf.get("military", ""),
        placeholder="U.S. Army, Combat Engineer, January 2006 to January 2012, led team of 8 soldiers")

    # board service — only for Executive level
    board_entries = []
    if resume_level == "Executive":
        st.subheader("Board Service & Leadership (optional)")
        num_board = st.number_input("Number of board/leadership entries", min_value=0, max_value=10, value=0, step=1)
        for bd in range(int(num_board)):
            board_item = st.text_input("Board / Leadership Role", key=f"board_{bd}",
                placeholder="Mississippi Workforce Investment Board — Member")
            if board_item:
                board_entries.append(board_item)

    st.subheader("Volunteer Work (optional)")
    _pf_vol = _pf.get("volunteer", [])
    num_vol = st.number_input("Number of volunteer entries", min_value=0, max_value=10,
                              value=len(_pf_vol) if _pf_vol else 0, step=1)
    vol_entries = []
    for v in range(int(num_vol)):
        st.markdown(f"**Volunteer {v + 1}**")
        vol_entries.append(_render_job_entry(v, _pf_vol, "vol", ("Role / Title", "Organization")))

    st.subheader("Professional Summary Notes (optional)")
    summary_notes = st.text_area(
        "Key points for the professional summary",
        height=80,
        placeholder="e.g., Career changer from retail to healthcare, strong customer service background, looking for CNA roles",
        help="Staff notes about the citizen's goals, strengths, or talking points to guide the AI-generated summary."
    )

    st.subheader("Skills")
    # check if at least one background section has data
    has_background = (
        int(num_jobs) > 0 or
        int(num_edu) > 0 or
        int(num_certs) > 0 or
        int(num_vol) > 0 or
        bool(military.strip()) or
        len(board_entries) > 0
    )
    if not has_background:
        st.info("Add at least one entry in Experience, Education, Certifications, Military, or Volunteer Work to enable skills.")
    suggest_skills = st.form_submit_button("✨ Suggest Skills Based on Info Above")
    if suggest_skills:
        # build rich context from ALL form fields
        skill_context = ""
        if full_name: skill_context += f"Candidate: {full_name}\n"
        skill_context += f"Resume level: {resume_level}\n"
        for jt, co, sd, ed, desc in jobs:
            if jt or co or desc:
                skill_context += f"Job: {jt} at {co}, {sd} to {ed}. Duties: {desc}\n"
        for deg, sch, loc, yr in edu_entries:
            if deg or sch:
                parts = [p for p in [deg, sch, loc, yr] if p]
                skill_context += f"Education: {', '.join(parts)}\n"
        for c in cert_entries:
            if c: skill_context += f"Certification: {c}\n"
        if military.strip():
            skill_context += f"Military Service: {military.strip()}\n"
        for bi in board_entries:
            skill_context += f"Board Service: {bi}\n"
        for vr, vo, vs, ve, vd in vol_entries:
            if vr or vo or vd:
                date_part = f", {vs} to {ve}" if vs or ve else ""
                desc_part = f". {vd}" if vd else ""
                skill_context += f"Volunteer: {vr} at {vo}{date_part}{desc_part}\n"
        if skill_context.strip():
            bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")
            skill_prompt = SKILL_SUGGESTION_PROMPT.format(skill_context=skill_context)
            try:
                resp = bedrock_client.invoke_model(
                    modelId="us.amazon.nova-pro-v1:0",
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps({
                        "messages": [{"role": "user", "content": [{"text": skill_prompt}]}],
                        "inferenceConfig": {"maxTokens": 200, "temperature": 0.3}
                    })
                )
                result = json.loads(resp["body"].read())
                suggested = result["output"]["message"]["content"][0]["text"].strip()
                st.session_state["suggested_skills"] = suggested
            except Exception as e:
                st.warning(f"Could not suggest skills: {e}")
        else:
            st.warning("Fill in some work experience or education first.")

    default_skills = st.session_state.get("suggested_skills", _pf.get("skills", ""))
    skills = st.text_input("Skills" + (" *" if has_background else ""),
        value=default_skills,
        placeholder="Add experience, education, or other background first" if not has_background else "customer service, cash handling, teamwork, inventory management")

    st.subheader("References (optional)")
    _pf_refs = _pf.get("references", [])
    num_refs = st.number_input("Number of references", min_value=0, max_value=10,
                               value=len(_pf_refs) if _pf_refs else 0, step=1)
    ref_entries = []
    for r in range(int(num_refs)):
        st.markdown(f"**Reference {r + 1}**")
        pf_r = _get_prefill(_pf_refs, r, 6)
        r1, r2 = st.columns(2)
        with r1:
            ref_first = st.text_input("First Name", key=f"ref_first_{r}", value=pf_r[0])
        with r2:
            ref_last = st.text_input("Last Name", key=f"ref_last_{r}", value=pf_r[1])
        r3, r4 = st.columns(2)
        with r3:
            ref_title = st.text_input("Job Title", key=f"ref_title_{r}", value=pf_r[2])
        with r4:
            ref_company = st.text_input("Company / Organization", key=f"ref_company_{r}", value=pf_r[3])
        r5, r6 = st.columns(2)
        with r5:
            ref_email = st.text_input("Email", key=f"ref_email_{r}", value=pf_r[4])
        with r6:
            raw_ref_phone = st.text_input("Phone", key=f"ref_phone_{r}", value=pf_r[5])
            ref_phone = _format_phone(raw_ref_phone)
            if raw_ref_phone and ref_phone != raw_ref_phone:
                st.caption(f"📞 Formatted: {ref_phone}")
        ref_name = f"{ref_first} {ref_last}".strip()
        ref_title_co = f"{ref_title}, {ref_company}".strip(', ')
        ref_entries.append((ref_name, ref_title_co, ref_phone, ref_email))

    submitted = st.form_submit_button("Generate Resume", type="primary", use_container_width=True)

if submitted:
    # get uploaded text from session state if available
    uploaded_text = st.session_state.get("_upload_raw_text", "")

    if not uploaded_text and (not first_name or not last_name or not city or not state or not phone or not email):
        st.error("Please fill in all required fields marked with * or upload an existing resume.")
    elif not uploaded_text and not has_background:
        st.error("Please add at least one entry in Experience, Education, Certifications, Military, or Volunteer Work, or upload an existing resume.")
    elif not uploaded_text and not skills:
        st.error("Please add skills — you have background info that needs skills to go with it.")
    else:
        # sort jobs by end date (most recent first)
        def _parse_date_rank(date_str):
            """Return a sortable number from a date string. Higher = more recent."""
            if not date_str:
                return 0
            d = date_str.strip().lower()
            if d == 'present':
                return 999999
            months = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
                      'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
            parts = d.replace(',', ' ').split()
            year = 0; month = 1
            for p in parts:
                if p.isdigit() and len(p) == 4:
                    year = int(p)
                else:
                    for m, v in months.items():
                        if p.startswith(m):
                            month = v; break
            return year * 100 + month

        sorted_jobs = sorted(jobs, key=lambda j: _parse_date_rank(j[3]), reverse=True)
        sorted_edu = sorted(edu_entries, key=lambda e: _parse_date_rank(e[3]), reverse=True)

        # build candidate info string
        candidate_info = f"Name: {full_name}\nLocation: {city_state}\nPhone: {phone}\nEmail: {email}"
        if linkedin:
            candidate_info += f"\nLinkedIn: {linkedin}"
        if target_industry:
            candidate_info += f"\nTarget Industry: {target_industry}"
        for idx, (jt, co, sd, ed, desc) in enumerate(sorted_jobs):
            if jt or co:
                candidate_info += f"\nJob {idx+1}: {jt} at {co}, {sd} to {ed}. Duties: {desc}"
        education_parts = []
        for idx, (deg, sch, loc, yr) in enumerate(sorted_edu):
            if deg or sch:
                parts = [p for p in [deg, sch, loc, yr] if p]
                education_parts.append(', '.join(parts))
        if education_parts:
            candidate_info += f"\nEducation: {'; '.join(education_parts)}"
        certifications_str = ', '.join(c for c in cert_entries if c)
        if certifications_str:
            candidate_info += f"\nCertifications: {certifications_str}"
        if skills:
            candidate_info += f"\nSkills: {skills}"
        if military:
            candidate_info += f"\nMilitary Service: {military}"
        if board_entries:
            candidate_info += f"\nBoard Service & Leadership: {'; '.join(board_entries)}"
        volunteer_parts = []
        for vr, vo, vs, ve, vd in vol_entries:
            if vr or vo:
                date_part = f", {vs} to {ve}" if vs or ve else ""
                desc_part = f". {vd}" if vd else ""
                volunteer_parts.append(f"{vr} at {vo}{date_part}{desc_part}")
        if volunteer_parts:
            candidate_info += f"\nVolunteer Work: {'; '.join(volunteer_parts)}"
        reference_parts = []
        for rn, rt, rp, re in ref_entries:
            if rn:
                parts = [p for p in [rn, rt, rp, re] if p]
                reference_parts.append(', '.join(parts))
        if reference_parts:
            candidate_info += f"\nReferences: {'; '.join(reference_parts)}"

        if summary_notes:
            candidate_info += f"\nProfessional Summary Notes: {summary_notes}"

        # mask PII from final candidate info
        candidate_info, pii_final = mask_pii(candidate_info)
        if pii_final:
            st.warning("PII detected and removed: " + "; ".join(pii_final))

        # generate layout + content via Bedrock
        with st.spinner("Creating your personalized resume..."):
            try:
                layout, content_data, latency, usage = generate_resume(
                    candidate_info, context, resume_level, color_name, target_industry)
                content_data = sanitize(content_data)
                layout = sanitize_layout(layout, content_data)
            except Exception as e:
                st.error(f"Error generating resume: {e}")
                st.stop()

        layout_desc = f"{layout.get('layout_type', 'single_column')} | {layout.get('header_style', '')} | {layout.get('section_header_style', '')} | {layout.get('font', '')}"
        st.info(f"📋 Layout: **{layout_desc}** | Level: **{resume_level}**")
        st.success("Resume generated! Please review the content below before downloading.")
        st.caption(f"⏱ {latency:.2f}s")

        # log this generation for audit trail
        log_generation(
            username=st.session_state.get('_username', 'unknown'),
            candidate_name=full_name,
            latency=latency,
            usage=usage
        )

        # build PDF and DOCX
        with st.spinner("Building files..."):
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                    pdf_path = tmp_pdf.name
                with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_docx:
                    docx_path = tmp_docx.name

                render_pdf(layout, content_data, pdf_path)
                render_docx(layout, content_data, docx_path)

                pdf_buf = io.BytesIO()
                with open(pdf_path, "rb") as f:
                    pdf_buf.write(f.read())
                pdf_buf.seek(0)

                docx_buf = io.BytesIO()
                with open(docx_path, "rb") as f:
                    docx_buf.write(f.read())
                docx_buf.seek(0)

                # Store in session state so buttons persist
                st.session_state["pdf_buf"] = pdf_buf
                st.session_state["docx_buf"] = docx_buf
                st.session_state["dl_filename"] = full_name.replace(' ', '_')
                st.session_state["_review_content"] = content_data
                st.session_state["staff_approved"] = False
            except Exception as e:
                st.error(f"Error building resume files: {e}")
                st.exception(e)
                st.stop()
            finally:
                for p in [pdf_path, docx_path]:
                    if os.path.exists(p):
                        os.unlink(p)

# show review section and download buttons if data exists in session state
if "pdf_buf" in st.session_state and "docx_buf" in st.session_state:
    st.divider()
    st.subheader("Staff Review & Approval")
    st.warning("Please review the generated resume before releasing to the citizen. This is an AI-assisted draft.")

    # show inline PDF preview
    st.session_state["pdf_buf"].seek(0)
    pdf_b64 = base64.b64encode(st.session_state["pdf_buf"].read()).decode()
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{pdf_b64}" '
        f'width="100%" height="800" type="application/pdf"></iframe>',
        unsafe_allow_html=True
    )

    approved = st.checkbox("I have reviewed this resume and approve it for release to the citizen.", key="staff_approved")

    if approved:
        st.session_state["pdf_buf"].seek(0)
        st.session_state["docx_buf"].seek(0)
        fname = st.session_state.get("dl_filename", "resume")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="⬇️ Download Word (.docx)",
                data=st.session_state["docx_buf"],
                file_name=f"{fname}_resume.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )
        with col2:
            st.download_button(
                label="⬇️ Download PDF (.pdf)",
                data=st.session_state["pdf_buf"],
                file_name=f"{fname}_resume.pdf",
                mime="application/pdf",
                use_container_width=True
            )
    else:
        st.caption("Check the approval box above to enable downloads.")
