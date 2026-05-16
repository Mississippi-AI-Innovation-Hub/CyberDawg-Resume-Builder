# pdf_render.py — PDF renderer for resume generation.

import os
from core.config import LOGO_PATH
from core.ai import _calc_tenure
from core.layout_measurements import PAGE_WIDTH, PAGE_HEIGHT, SIDEBAR_LEFT, SIDEBAR_RIGHT, SINGLE_COLUMN, balance_sidebar_right_columns

# pdf imports
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                 Paragraph, Spacer, HRFlowable, Table, TableStyle,
                                 KeepTogether, FrameBreak)
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus.flowables import Flowable

PAGE_W, PAGE_H = letter

# register fonts
import platform

if platform.system() == "Darwin":  # macOS
    _arial        = '/System/Library/Fonts/Supplemental/Arial.ttf'
    _arial_bold   = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
    _arial_italic = '/System/Library/Fonts/Supplemental/Arial Italic.ttf'
    _tnr          = '/System/Library/Fonts/Supplemental/Times New Roman.ttf'
    _tnr_bold     = '/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf'
    _tnr_italic   = '/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf'
    _tnr_bi       = '/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf'
elif platform.system() == "Windows":
    _arial        = 'C:/Windows/Fonts/arial.ttf'
    _arial_bold   = 'C:/Windows/Fonts/arialbd.ttf'
    _arial_italic = 'C:/Windows/Fonts/ariali.ttf'
    _tnr          = 'C:/Windows/Fonts/times.ttf'
    _tnr_bold     = 'C:/Windows/Fonts/timesbd.ttf'
    _tnr_italic   = 'C:/Windows/Fonts/timesi.ttf'
    _tnr_bi       = 'C:/Windows/Fonts/timesbi.ttf'
else:  # Linux
    # msttcore-fonts paths (install via: sudo rpm -i msttcore-fonts-installer or sudo apt install ttf-mscorefonts-installer)
    _arial        = '/usr/share/fonts/msttcore/arial.ttf'
    _arial_bold   = '/usr/share/fonts/msttcore/arialbd.ttf'
    _arial_italic = '/usr/share/fonts/msttcore/ariali.ttf'
    _tnr          = '/usr/share/fonts/msttcore/times.ttf'
    _tnr_bold     = '/usr/share/fonts/msttcore/timesbd.ttf'
    _tnr_italic   = '/usr/share/fonts/msttcore/timesi.ttf'
    _tnr_bi       = '/usr/share/fonts/msttcore/timesbi.ttf'
    # fallback to common Linux font dirs if msttcore-fonts not installed
    if not os.path.exists(_arial):
        for alt_dir in ['/usr/share/fonts/truetype/msttcorefonts', '/usr/share/fonts/TTF', '/usr/share/fonts']:
            if os.path.exists(os.path.join(alt_dir, 'Arial.ttf')):
                _arial        = os.path.join(alt_dir, 'Arial.ttf')
                _arial_bold   = os.path.join(alt_dir, 'Arial_Bold.ttf')
                _arial_italic = os.path.join(alt_dir, 'Arial_Italic.ttf')
                _tnr          = os.path.join(alt_dir, 'Times_New_Roman.ttf')
                _tnr_bold     = os.path.join(alt_dir, 'Times_New_Roman_Bold.ttf')
                _tnr_italic   = os.path.join(alt_dir, 'Times_New_Roman_Italic.ttf')
                _tnr_bi       = os.path.join(alt_dir, 'Times_New_Roman_Bold_Italic.ttf')
                break
    # if still not found, set to none (helvetica)
    if not os.path.exists(_arial):
        _arial = _arial_bold = _arial_italic = None
        _tnr = _tnr_bold = _tnr_italic = _tnr_bi = None

if _arial:
    pdfmetrics.registerFont(TTFont('Arial',        _arial))
    pdfmetrics.registerFont(TTFont('Arial-Bold',   _arial_bold))
    pdfmetrics.registerFont(TTFont('Arial-Italic', _arial_italic))
    pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic')
if _tnr:
    pdfmetrics.registerFont(TTFont('TNR',           _tnr))
    pdfmetrics.registerFont(TTFont('TNR-Bold',      _tnr_bold))
    pdfmetrics.registerFont(TTFont('TNR-Italic',    _tnr_italic))
    pdfmetrics.registerFont(TTFont('TNR-BoldItalic', _tnr_bi))
    pdfmetrics.registerFontFamily('TNR', normal='TNR', bold='TNR-Bold', italic='TNR-Italic', boldItalic='TNR-BoldItalic')

#  flexible pdf renderer that takes layout + content dicts and produces a styled resume PDF using ReportLab.

def _c(rgb_list):
    """Convert [r,g,b] floats (0-1) to reportlab Color."""
    return colors.Color(*rgb_list)

def _spaced(text):
    return '  '.join(text)

# pdf flowables
class PdfSectionHeader(Flowable):
    """Flexible section header supporting multiple styles."""
    def __init__(self, title, width, style, primary, accent, font, font_size):
        super().__init__()
        self.title = title
        self.width = width
        self.style = style  # bar_bg, bold_rule, spaced_rules, spaced_colored, bold_italic
        self.primary = primary
        self.accent = accent
        self.font = font + '-Bold' if not font.endswith('-Bold') else font
        self.font_size = font_size
        self.height = font_size + 14
        self.spaceBefore = 12
        self.spaceAfter = 4

    # for simplicity, set a fixed height and let text overflow if too long
    def wrap(self, aW, aH): return self.width, self.height

    # draw the header based on the chosen style
    def draw(self):
        c = self.canv
        h = self.height
        if self.style == 'bar_bg':
            c.setFillColor(self.accent)
            c.rect(0, 0, self.width, h, fill=1, stroke=0)
            c.setFillColor(self.primary)
            c.setFont(self.font, self.font_size)
            c.drawString(1.4, 2.5, self.title)
        elif self.style == 'bold_rule':
            c.setFillColor(self.primary)
            c.setFont(self.font, self.font_size)
            c.drawString(0, h - self.font_size, self.title)
            c.setStrokeColor(self.primary)
            c.setLineWidth(0.5)
            c.line(0, 0, self.width, 0)
        elif self.style in ('spaced_rules', 'spaced_colored'):
            c.setStrokeColor(self.accent if self.style == 'spaced_rules' else self.primary)
            c.setLineWidth(0.24 if self.style == 'spaced_rules' else 0.6)
            c.line(0, h - 1, self.width, h - 1)
            c.setFillColor(self.primary)
            c.setFont(self.font, self.font_size)
            c.drawString(0, h - self.font_size - 4, _spaced(self.title))
            c.line(0, 0, self.width, 0)
        elif self.style == 'bold_italic':
            bi = self.font.replace('-Bold', '-BoldItalic') if '-Bold' in self.font else self.font
            try:
                c.setFont(bi, self.font_size)
            except Exception:
                c.setFont(self.font, self.font_size)
            c.setFillColor(self.primary)
            c.drawString(0, h - self.font_size, self.title)

# job line flowable
class PdfJobLine(Flowable):
    """Job header: title (wraps if long) + date on line 1, company + optional tenure on last line."""
    def __init__(self, title, company, date, width, primary, secondary, font, company_color=None, tenure=None, tenure_color=None):
        super().__init__()
        self.title = title; self.company = company; self.date = date if isinstance(date, str) else ''
        self.width = width; self.primary = primary; self.secondary = secondary
        self.company_color = company_color or secondary
        self.tenure = tenure; self.tenure_color = tenure_color or primary
        self.font = font; self.spaceBefore = 10
        self._date_w = 0
        self._title_lines = [title]
        self.height = 28  # default: 2 lines (title + company)

    def wrap(self, aW, aH):
        c_width = self.width
        self._date_w = self.canv.stringWidth(self.date, self.font + '-Italic', 9) + 10 if hasattr(self, 'canv') and self.canv else len(self.date) * 5 + 10
        max_title_w = c_width - self._date_w
        # simple word-wrap for title
        words = self.title.split()
        lines = []; current = ''
        for w in words:
            test = (current + ' ' + w).strip()
            # estimate width: ~6px per char at size 10 bold
            if len(test) * 6.2 > max_title_w and current:
                lines.append(current)
                current = w
            else:
                current = test
        if current: lines.append(current)
        self._title_lines = lines if lines else [self.title]
        self.height = 14 * len(self._title_lines) + 14  # title lines + company line
        return self.width, self.height

    def draw(self):
        c = self.canv
        h = self.height
        # title first line baseline
        title_y = h - 12
        # title lines
        c.setFont(self.font + '-Bold', 10); c.setFillColor(self.primary)
        for i, line in enumerate(self._title_lines):
            c.drawString(0, title_y - (i * 14), line)
        # date on same baseline as first title line, right-aligned
        c.setFont(self.font + '-Italic', 9); c.setFillColor(self.secondary)
        dw = c.stringWidth(self.date, self.font + '-Italic', 9)
        c.drawString(self.width - dw, title_y, self.date)
        # company on last line
        c.setFont(self.font + '-Italic', 9); c.setFillColor(self.company_color)
        c.drawString(0, 1, self.company)
        # tenure on same line as company, right-aligned
        if self.tenure:
            c.setFont(self.font + '-Bold', 8.5); c.setFillColor(self.tenure_color)
            tw = c.stringWidth(self.tenure, self.font + '-Bold', 8.5)
            c.drawString(self.width - tw, 1, self.tenure)

class PdfBannerJobLine(Flowable):
    """Job header with tenure: title (wraps if long) + date, company + tenure."""
    def __init__(self, title, company, date, tenure, width, primary, secondary, accent, font):
        super().__init__()
        self.title = title; self.company = company; self.date = date if isinstance(date, str) else ''
        self.tenure = tenure; self.width = width
        self.primary = primary; self.secondary = secondary; self.accent = accent
        self.font = font; self.spaceBefore = 10
        self._title_lines = [title]
        self.height = 30

    def wrap(self, aW, aH):
        date_w = self.canv.stringWidth(self.date, self.font, 9) + 10 if hasattr(self, 'canv') and self.canv else len(self.date) * 5 + 10
        max_title_w = self.width - date_w
        words = self.title.split()
        lines = []; current = ''
        for w in words:
            test = (current + ' ' + w).strip()
            if len(test) * 7.0 > max_title_w and current:
                lines.append(current)
                current = w
            else:
                current = test
        if current: lines.append(current)
        self._title_lines = lines if lines else [self.title]
        self.height = 14 * len(self._title_lines) + 16
        return self.width, self.height

    def draw(self):
        c = self.canv
        h = self.height
        # title first line baseline
        title_y = h - 14
        # title lines
        c.setFillColor(self.primary); c.setFont(self.font + '-Bold', 12)
        for i, line in enumerate(self._title_lines):
            c.drawString(0, title_y - (i * 14), line)
        # date on same baseline as first title line, right-aligned
        c.setFillColor(self.secondary); c.setFont(self.font, 9)
        dw = c.stringWidth(self.date, self.font, 9)
        c.drawString(self.width - dw, title_y, self.date)
        # company bottom left
        c.setFillColor(self.accent); c.setFont(self.font + '-Italic', 10)
        c.drawString(0, 3, self.company)
        # tenure bottom right
        if self.tenure:
            c.setFillColor(self.primary); c.setFont(self.font + '-Bold', 8.5)
            tw = c.stringWidth(self.tenure, self.font + '-Bold', 8.5)
            c.drawString(self.width - tw, 3, self.tenure)

class PdfEduLine(Flowable):
    """Education: degree + date on line 1, school on line 2."""
    def __init__(self, degree, school, date, width, primary, secondary, font, school_color=None):
        super().__init__()
        self.degree = degree; self.school = school; self.date = date if isinstance(date, str) else ''
        self.width = width; self.primary = primary; self.secondary = secondary
        self.school_color = school_color or secondary
        self.font = font; self.spaceBefore = 10
        self.height = 28 if school else 14

    def wrap(self, aW, aH):
        self.height = 28 if self.school else 14
        return self.width, self.height

    def draw(self):
        c = self.canv
        h = self.height
        # line 1: degree left, date right
        baseline = h - 12 if self.school else 2
        c.setFont(self.font + '-Bold', 10); c.setFillColor(self.primary)
        c.drawString(0, baseline, self.degree)
        if self.date:
            c.setFont(self.font + '-Italic', 9); c.setFillColor(self.secondary)
            dw = c.stringWidth(self.date, self.font + '-Italic', 9)
            c.drawString(self.width - dw, baseline, self.date)
        # line 2: school
        if self.school:
            c.setFont(self.font, 9); c.setFillColor(self.school_color)
            c.drawString(0, 1, self.school)


def _pdf_bullet(text, font, text_color, marker='\u2022'):
    style = ParagraphStyle('B', fontName=font, fontSize=9, textColor=text_color,
                           leading=11, leftIndent=18, bulletIndent=6, spaceAfter=0,
                           bulletFontName=font, bulletFontSize=9)
    return Paragraph(text, style, bulletText=marker)

def _pdf_skills_table(items, width, font, text_color, cell_bg=None):
    while len(items) % 3 != 0: items.append('')
    cw = width / 3
    style = ParagraphStyle('S', fontName=font, fontSize=8.5, textColor=text_color,
                           leading=10, alignment=1 if cell_bg else 0, spaceAfter=0)
    rows = []
    for i in range(0, len(items), 3):
        rows.append([Paragraph(('\u2022\u00a0\u00a0' + items[i+j]) if items[i+j] else '', style) for j in range(3)])
    t = Table(rows, colWidths=[cw]*3)
    ts = [('VALIGN',(0,0),(-1,-1),'TOP'), ('LEFTPADDING',(0,0),(-1,-1),0),
          ('RIGHTPADDING',(0,0),(-1,-1),0), ('TOPPADDING',(0,0),(-1,-1),3),
          ('BOTTOMPADDING',(0,0),(-1,-1),3)]
    if cell_bg:
        ts.append(('BACKGROUND',(0,0),(-1,-1), cell_bg))
        ts.append(('ALIGN',(0,0),(-1,-1),'CENTER'))
    t.setStyle(TableStyle(ts))
    return t


def render_pdf(layout, content, output_path):
    """Flexible PDF renderer driven by layout + content dicts."""
    L = layout
    primary = _c(L['primary_color'])
    accent = _c(L.get('accent_color', L['primary_color']))
    secondary = _c(L.get('secondary_color', [0.33, 0.33, 0.33]))
    text_color = _c(L.get('text_color', [0.1, 0.1, 0.1]))
    font = L.get('font', 'Arial')
    header_style = L.get('header_style', 'centered_name')
    section_style = L.get('section_header_style', 'bold_rule')
    layout_type = L.get('layout_type', 'single_column')
    bullet_marker = L.get('bullet_marker', '\u2022')
    section_order = L.get('section_order', ['summary','experience','education','certifications','military','skills'])
    sidebar_sections = L.get('sidebar_sections', ['contact','education','certifications','skills'])

    # force all main-column text to be dark and readable on white background.
    # any color with average brightness > 0.45 or any single channel > 0.7 is too light.
    def _is_light(c): return sum(c)/3 > 0.45 or max(c) > 0.7
    if _is_light(L.get('text_color', [0.1,0.1,0.1])):
        text_color = _c([0.1, 0.1, 0.1])
    if _is_light(L.get('secondary_color', [0.33,0.33,0.33])):
        secondary = _c([0.33, 0.33, 0.33])
    if _is_light(L.get('primary_color', [0.12,0.28,0.53])):
        primary = _c([0.12, 0.28, 0.53])

    # sidebar layout measurements
    if layout_type == 'sidebar_left':
        SB_W = SIDEBAR_LEFT['sidebar_width']
        SB_PAD = SIDEBAR_LEFT['sidebar_padding']
        SB_RULE_X1 = SIDEBAR_LEFT['sidebar_rule_x']
        SB_CW = SIDEBAR_LEFT['sidebar_content_width']
        MAIN_X = SIDEBAR_LEFT['main_left']
        MAIN_RIGHT = SIDEBAR_LEFT['main_right']
        MAIN_W = SIDEBAR_LEFT['main_width']
        CW = MAIN_W
        BOT = SIDEBAR_LEFT['bottom_margin']
        # sidebar text colors
        _is_bw_sb = sum(L['primary_color']) / 3 < 0.15
        if _is_bw_sb:
            sb_text = _c([0.2, 0.2, 0.2])
            sb_heading = _c([0, 0, 0])
            sb_degree_c = _c([0, 0, 0])
            sb_school_c = _c([0.33, 0.33, 0.33])
        else:
            sb_text = _c(L.get('sidebar_text_color', [0.82, 0.86, 0.91]))
            sb_heading = accent
            sb_degree_c = colors.white
            sb_school_c = _c(L.get('sidebar_school_color', [0.66, 0.74, 0.82]))
    else:
        LEFT = int(SINGLE_COLUMN['left_margin'])
        RIGHT = int(PAGE_WIDTH - SINGLE_COLUMN['right_margin'])
        CW = RIGHT - LEFT

    def make_section_header(title, width=None):
        return PdfSectionHeader(title, width or CW, section_style, primary, accent, font, 10)

    def make_rule():
        return HRFlowable(width='100%', thickness=0.6, color=primary, spaceBefore=2, spaceAfter=4)

    def make_bullet(text):
        return _pdf_bullet(text, font, text_color, bullet_marker)

    body = ParagraphStyle('Body', fontName=font, fontSize=9, textColor=text_color, leading=11, spaceAfter=0)

    # build section content blocks
    def build_summary():
        if not content.get('summary'): return []
        return [KeepTogether([make_section_header('PROFESSIONAL SUMMARY'),
                Paragraph(content['summary'], body)])]

    def build_experience():
        jobs = content.get('jobs')
        if not jobs: return []
        items = []
        for i, job in enumerate(jobs):
            title, company, date = job[0], job[1], job[2]
            bullets = job[-1] if isinstance(job[-1], list) else []
            tenure = job[3] if len(job) == 5 and isinstance(job[3], str) else None
            if not tenure and header_style == 'banner':
                tenure = _calc_tenure(date)
            if tenure:
                job_line = PdfBannerJobLine(title, company, date, tenure, CW, primary, secondary, accent, font)
            else:
                job_line = PdfJobLine(title, company, date, CW, text_color, secondary, font)
            # keep header + job line + first bullet together; rest flows freely
            keep = [job_line]
            if i == 0:
                keep.insert(0, make_section_header('PROFESSIONAL EXPERIENCE'))
            if bullets:
                keep.append(make_bullet(bullets[0]))
            items.append(KeepTogether(keep))
            for b in bullets[1:]:
                items.append(make_bullet(b))
        return items

    def build_education():
        edu = content.get('education')
        if not edu: return []
        items = [make_section_header('EDUCATION')]
        for e in edu:
            degree = e[0]
            school = e[1] if len(e) > 1 and isinstance(e[1], str) else ''
            date = e[2] if len(e) > 2 and isinstance(e[2], str) else None
            _school_c = accent if header_style == 'banner' else None
            items.append(PdfEduLine(degree, school, date, CW, text_color, secondary, font, school_color=_school_c))
        return [KeepTogether(items)]

    def build_certifications():
        certs = content.get('certifications')
        if not certs: return []
        items = [make_section_header('CERTIFICATIONS')]
        for c in certs: items.append(make_bullet(c))
        return [KeepTogether(items)]

    def build_military():
        mil = content.get('military')
        if not mil: return []
        items = []
        for i, m in enumerate(mil):
            branch, role, date = m[0], m[1], m[2]
            bullets = m[-1] if isinstance(m[-1], list) else []
            _mil_c = accent if header_style == 'banner' else None
            _mil_tenure = _calc_tenure(date) if header_style == 'banner' else None
            job_line = PdfJobLine(branch, role, date, CW, text_color, secondary, font,
                       company_color=_mil_c, tenure=_mil_tenure, tenure_color=primary)
            keep = [job_line]
            if i == 0:
                keep.insert(0, make_section_header('MILITARY SERVICE'))
            if bullets:
                keep.append(make_bullet(bullets[0]))
            items.append(KeepTogether(keep))
            for b in bullets[1:]:
                items.append(make_bullet(b))
        return items

    def build_skills():
        skills = content.get('skills')
        if not skills: return []
        cell_bg = accent if L.get('skills_cell_bg') else None
        return [KeepTogether([make_section_header('CORE COMPETENCIES'),
                _pdf_skills_table(list(skills), CW, font, primary if cell_bg else text_color, cell_bg)])]

    def build_board():
        board = content.get('board')
        if not board: return []
        items = [make_section_header('BOARD SERVICE & LEADERSHIP')]
        for item in board: items.append(Paragraph(item, body))
        return [KeepTogether(items)]

    def build_volunteer():
        vol = content.get('volunteer')
        if not vol: return []
        items = []
        for i, v in enumerate(vol):
            title, org, date = v[0], v[1], v[2]
            bullets = v[-1] if isinstance(v[-1], list) else []
            _vol_c = accent if header_style == 'banner' else None
            job_line = PdfJobLine(title, org, date, CW, text_color, secondary, font, company_color=_vol_c)
            keep = [job_line]
            if i == 0:
                keep.insert(0, make_section_header('VOLUNTEER WORK'))
            if bullets:
                keep.append(make_bullet(bullets[0]))
            items.append(KeepTogether(keep))
            for b in bullets[1:]:
                items.append(make_bullet(b))
        return items

    def build_references():
        refs = content.get('references')
        if not refs: return []
        ref_style = ParagraphStyle('Ref', fontName=font, fontSize=9, textColor=text_color,
                                    leading=11, spaceAfter=6)
        items = [make_section_header('REFERENCES')]
        for r in refs:
            name_r = r[0] if len(r) > 0 else ''
            title_r = r[1] if len(r) > 1 else ''
            phone_r = r[2] if len(r) > 2 else ''
            email_r = r[3] if len(r) > 3 else ''
            parts = [f'<b>{name_r}</b>']
            if title_r: parts.append(title_r)
            if phone_r: parts.append(phone_r)
            if email_r: parts.append(email_r)
            items.append(Paragraph('  |  '.join(parts), ref_style))
        return [KeepTogether(items)]

    section_builders = {
        'summary': build_summary, 'experience': build_experience,
        'education': build_education, 'certifications': build_certifications,
        'military': build_military, 'skills': build_skills, 'board': build_board,
        'volunteer': build_volunteer, 'references': build_references,
    }

    name = content.get('name', '')
    contact = content.get('contact', '')
    if isinstance(contact, list): contact_list = contact; contact = '  |  '.join(contact)
    else: contact_list = [c.strip() for c in contact.split('|')] if contact else []
    subtitle = content.get('subtitle') or content.get('job_subtitle', '')

    #  sidebar left layout
    if layout_type == 'sidebar_left':
        # Sidebar flowable: spaced gold header + gold rule
        class SbHeader(Flowable):
            def __init__(self, title):
                super().__init__()
                self.title = '  '.join(title)
                self.width = SB_CW; self.height = 20
                self.spaceBefore = 12; self.spaceAfter = 4
            def wrap(self, aW, aH): return self.width, self.height
            def draw(self):
                c = self.canv
                c.setFillColor(sb_heading); c.setFont(font+'-Bold', 8.5)
                c.drawString(0, self.height - 10, self.title)
                c.setStrokeColor(sb_heading); c.setLineWidth(0.48)
                c.line(0, 0, SB_RULE_X1 - SB_PAD, 0)

        sb_contact_s = ParagraphStyle('SbC', fontName=font, fontSize=8.5,
                                       textColor=sb_text, leading=11, spaceAfter=0)
        sb_degree_s = ParagraphStyle('SbD', fontName=font+'-Bold', fontSize=8.5,
                                      textColor=sb_degree_c, leading=11, spaceAfter=0)
        sb_school_s = ParagraphStyle('SbS', fontName=font, fontSize=8.5,
                                      textColor=sb_school_c, leading=11, spaceAfter=0)
        sb_bullet_s = ParagraphStyle('SbB', fontName=font, fontSize=8.5,
                                      textColor=sb_text, leading=11, leftIndent=10, spaceAfter=0)

        # build sidebar story
        # split name for sidebar
        name_parts = name.split()
        if len(name_parts) >= 2:
            first_name = ' '.join(name_parts[:-1])
            last_name = name_parts[-1]
        else:
            first_name = name; last_name = ''

        _sb_name_color = _c([0,0,0]) if _is_bw_sb else colors.white
        _sb_last_color = _c([0,0,0]) if _is_bw_sb else accent

        class SbNameBlock(Flowable):
            """Auto-fitting name block for sidebar. Shrinks font to fit width."""
            def __init__(self, first, last, width, name_color, last_color, font_name):
                super().__init__()
                self.first = first; self.last = last
                self.width = width
                self.name_color = name_color; self.last_color = last_color
                self.font_name = font_name + '-Bold'
                self.spaceBefore = 0; self.spaceAfter = 8
                self._fn_sz = 22; self._ln_sz = 22
                self.height = 60

            def wrap(self, aW, aH):
                c = self.canv
                max_w = self.width
                for sz in range(26, 9, -1):
                    if c.stringWidth(self.first, self.font_name, sz) <= max_w:
                        self._fn_sz = sz; break
                if self.last:
                    for sz in range(26, 9, -1):
                        if c.stringWidth(self.last, self.font_name, sz) <= max_w:
                            self._ln_sz = sz; break
                    self.height = self._fn_sz + self._ln_sz + 10
                else:
                    self.height = self._fn_sz + 8
                return self.width, self.height

            def draw(self):
                c = self.canv
                h = self.height
                c.setFillColor(self.name_color)
                c.setFont(self.font_name, self._fn_sz)
                c.drawString(0, h - self._fn_sz, self.first)
                if self.last:
                    c.setFillColor(self.last_color)
                    c.setFont(self.font_name, self._ln_sz)
                    c.drawString(0, h - self._fn_sz - self._ln_sz - 4, self.last)

        sb_story = [Spacer(1, 36)]
        sb_story.append(SbNameBlock(first_name, last_name, SB_CW,
                                     _sb_name_color, _sb_last_color, font))
        for sec in sidebar_sections:
            if sec == 'contact' and contact_list:
                sb_story.append(SbHeader('CONTACT'))
                for line in contact_list:
                    sb_story.append(Paragraph(line, sb_contact_s))
            elif sec == 'education' and content.get('education'):
                sb_story.append(SbHeader('EDUCATION'))
                for e in content['education']:
                    sb_story.append(Paragraph(e[0], sb_degree_s))
                    if len(e) > 1 and isinstance(e[1], str):
                        sb_story.append(Paragraph(e[1], sb_school_s))
            elif sec == 'certifications' and content.get('certifications'):
                sb_story.append(SbHeader('CERTIFICATIONS'))
                for c in content['certifications']:
                    sb_story.append(Paragraph('\u2014\u00a0' + c, sb_bullet_s))
            elif sec == 'skills' and content.get('skills'):
                sb_story.append(SbHeader('SKILLS'))
                for s in content['skills']:
                    sb_story.append(Paragraph('\u2014\u00a0' + s, sb_bullet_s))

        # build main story
        main_story = []
        if subtitle:
            sub_ps = ParagraphStyle('Sub', fontName=font+'-Bold', fontSize=14,
                                    textColor=primary, leading=17, spaceAfter=4)
            main_story.append(Paragraph(subtitle, sub_ps))
            main_story.append(HRFlowable(width='100%', thickness=0.24,
                              color=_c(L.get('main_rule_color', [0.77, 0.82, 0.87])),
                              spaceBefore=2, spaceAfter=8))

        main_sections = [s for s in section_order if s not in sidebar_sections]
        for sec_name in main_sections:
            builder = section_builders.get(sec_name)
            if builder:
                main_story.extend(builder())

        # detect no-color sidebar mode
        _is_bw = sum(L['primary_color']) / 3 < 0.15

        # page callback: draw sidebar bg + name
        # page callback: draw sidebar bg (no name — name is in sidebar story)
        def on_page_sidebar(canvas, doc):
            canvas.saveState()
            if _is_bw:
                canvas.setStrokeColor(colors.black)
                canvas.setLineWidth(0.75)
                canvas.line(SB_W, 0, SB_W, PAGE_H)
            else:
                canvas.setFillColor(primary)
                canvas.rect(0, 0, SB_W, PAGE_H, fill=1, stroke=0)
            canvas.restoreState()
            if os.path.exists(LOGO_PATH):
                canvas.drawImage(LOGO_PATH, PAGE_W/2-50, 10, width=100, height=30,
                                 preserveAspectRatio=True, mask='auto')

        # page 2+ callback: colored sidebar strip only, content in main area
        def on_page_continuation(canvas, doc):
            canvas.saveState()
            if _is_bw:
                canvas.setStrokeColor(colors.black)
                canvas.setLineWidth(0.75)
                canvas.line(SB_W, 0, SB_W, PAGE_H)
            else:
                canvas.setFillColor(primary)
                canvas.rect(0, 0, SB_W, PAGE_H, fill=1, stroke=0)
            canvas.restoreState()
            if os.path.exists(LOGO_PATH):
                canvas.drawImage(LOGO_PATH, PAGE_W/2-50, 10, width=100, height=30,
                                 preserveAspectRatio=True, mask='auto')

        # two-frame document
        doc = BaseDocTemplate(output_path, pagesize=letter,
                              leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)
        sb_frame = Frame(SB_PAD, BOT, SB_CW, PAGE_H - BOT,
                         id='sidebar', leftPadding=0, rightPadding=0,
                         topPadding=0, bottomPadding=0)
        main_frame = Frame(MAIN_X, BOT, MAIN_W, PAGE_H - 68 - BOT,
                           id='main', leftPadding=0, rightPadding=0,
                           topPadding=0, bottomPadding=0)
        # page 2+ only has the main column frame (content stays on white area)
        cont_frame = Frame(MAIN_X, BOT, MAIN_W, PAGE_H - BOT - 43,
                           id='cont_main', leftPadding=0, rightPadding=0,
                           topPadding=0, bottomPadding=0)
        page1 = PageTemplate(id='sidebar_page',
                             frames=[sb_frame, main_frame], onPage=on_page_sidebar)
        page2 = PageTemplate(id='continuation',
                             frames=[cont_frame], onPage=on_page_continuation)
        doc.addPageTemplates([page1, page2])
        # After page 1, switch to continuation template
        from reportlab.platypus import NextPageTemplate, KeepInFrame
        # Wrap sidebar content in KeepInFrame so it shrinks to fit, never overflows
        sb_flowable = KeepInFrame(SB_CW, PAGE_H - BOT, sb_story, mode='shrink')
        story = [sb_flowable, FrameBreak(), NextPageTemplate('continuation')] + main_story
        doc.build(story)
        print(f'Saved PDF: {output_path}')
        return

    # sidebar right layout (template 3 style)
    if layout_type == 'sidebar_right':
        LEFT_X = SIDEBAR_RIGHT['left_margin']
        DIVIDER_X = SIDEBAR_RIGHT['divider_x']
        RIGHT_COL_X = SIDEBAR_RIGHT['right_col_x']
        RIGHT_EDGE = SIDEBAR_RIGHT['right_edge']
        LEFT_W = SIDEBAR_RIGHT['left_width']
        RIGHT_W = SIDEBAR_RIGHT['right_width']
        FULL_W = SIDEBAR_RIGHT['full_width']
        BOT = SIDEBAR_RIGHT['bottom_margin']
        TOP = SIDEBAR_RIGHT['top_margin']
        CW = LEFT_W  # main content width for section builders

        # use layout colors if colorful, else grey tones
        _sr_is_bw = sum(L['primary_color']) / 3 < 0.15
        if _sr_is_bw:
            sr_dark = _c([0.169, 0.169, 0.169])
            sr_med = _c([0.29, 0.29, 0.29])
            sr_grey = _c([0.463, 0.463, 0.463])
            sr_light = _c([0.733, 0.733, 0.733])
        else:
            sr_dark = primary
            sr_med = accent
            sr_grey = secondary
            sr_light = _c([0.733, 0.733, 0.733])

        # right-column styles
        rc_body = ParagraphStyle('RCBody', fontName=font, fontSize=8.5,
                                  textColor=sr_grey, leading=11, spaceAfter=0)
        rc_bullet_s = ParagraphStyle('RCBul', fontName=font, fontSize=8.5,
                                      textColor=sr_med, leading=11, leftIndent=12, spaceAfter=0)
        rc_degree = ParagraphStyle('RCDeg', fontName=font+'-Bold', fontSize=9.5,
                                    textColor=_c([0.102,0.102,0.102]), leading=12, spaceAfter=0)
        rc_school = ParagraphStyle('RCSch', fontName=font+'-Italic', fontSize=9,
                                    textColor=sr_med, leading=11, spaceAfter=0)

        # right-column section header
        class RcSectionHeader(Flowable):
            def __init__(self, title, width):
                super().__init__()
                self.title = '  '.join(title); self.width = width
                self.height = 22; self.spaceBefore = 8; self.spaceAfter = 2
            def wrap(self, aW, aH): return self.width, self.height
            def draw(self):
                c = self.canv
                c.setStrokeColor(sr_light); c.setLineWidth(0.24)
                c.line(0, self.height - 1, self.width, self.height - 1)
                c.setFillColor(sr_dark); c.setFont(font+'-Bold', 9)
                c.drawString(0, self.height - 13, self.title)
                c.line(0, 0, self.width, 0)

        # Build full-width header content (drawn on canvas, page 1 only)
        _sr_header_name = name
        _sr_header_contact = contact
        _sr_header_summary = content.get('summary', '')

        # Build left column: experience, volunteer, military, references
        from reportlab.platypus import KeepInFrame
        left_story = []
        left_sections, right_sections = balance_sidebar_right_columns(content)
        if 'experience' in left_sections and content.get('jobs'):
            left_story.append(RcSectionHeader('PROFESSIONAL EXPERIENCE', LEFT_W))
            for job in content['jobs']:
                title_j, company, date = job[0], job[1], job[2]
                bullets = job[-1] if isinstance(job[-1], list) else []
                left_story.append(PdfJobLine(title_j, company, date, LEFT_W, text_color, secondary, font))
                for b in bullets: left_story.append(make_bullet(b))
        if 'military' in left_sections and content.get('military'):
            left_story.append(RcSectionHeader('MILITARY SERVICE', LEFT_W))
            for m in content['military']:
                branch, role, date = m[0], m[1], m[2]
                bullets = m[-1] if isinstance(m[-1], list) else []
                left_story.append(PdfJobLine(branch, role, date, LEFT_W, text_color, secondary, font))
                for b in bullets: left_story.append(make_bullet(b))
        if 'volunteer' in left_sections and content.get('volunteer'):
            left_story.append(RcSectionHeader('VOLUNTEER WORK', LEFT_W))
            for v in content['volunteer']:
                title_v, org, date = v[0], v[1], v[2]
                bullets = v[-1] if isinstance(v[-1], list) else []
                left_story.append(PdfJobLine(title_v, org, date, LEFT_W, text_color, secondary, font))
                for b in bullets: left_story.append(make_bullet(b))
        if 'references' in left_sections and content.get('references'):
            left_story.append(RcSectionHeader('REFERENCES', LEFT_W))
            ref_style_l = ParagraphStyle('RefL', fontName=font, fontSize=9, textColor=text_color, leading=11, spaceAfter=6)
            for r in content['references']:
                parts = [f'<b>{r[0]}</b>'] + [r[i] for i in range(1, len(r)) if r[i]]
                left_story.append(Paragraph('  |  '.join(parts), ref_style_l))

        # Build right column
        right_story = []
        for sec in right_sections:
            if sec == 'education' and content.get('education'):
                right_story.append(RcSectionHeader('EDUCATION', RIGHT_W))
                right_story.append(Spacer(1, 6))
                for e in content['education']:
                    right_story.append(Paragraph(e[0], rc_degree))
                    if len(e) > 1 and isinstance(e[1], str):
                        right_story.append(Paragraph(e[1], rc_school))
                    if len(e) > 2 and isinstance(e[2], str):
                        right_story.append(Paragraph(e[2], rc_body))
            elif sec == 'certifications' and content.get('certifications'):
                right_story.append(RcSectionHeader('CERTIFICATIONS', RIGHT_W))
                right_story.append(Spacer(1, 4))
                for cert in content['certifications']:
                    right_story.append(Paragraph('\u25aa\u00a0\u00a0' + cert, rc_bullet_s))
            elif sec == 'skills' and content.get('skills'):
                right_story.append(RcSectionHeader('CORE SKILLS', RIGHT_W))
                right_story.append(Spacer(1, 4))
                for s in content['skills']:
                    right_story.append(Paragraph('\u25aa\u00a0\u00a0' + s, rc_bullet_s))
            elif sec == 'military' and content.get('military'):
                right_story.append(RcSectionHeader('MILITARY SERVICE', RIGHT_W))
                right_story.append(Spacer(1, 6))
                for m in content['military']:
                    right_story.append(Paragraph(m[0], rc_degree))
                    if len(m) > 1: right_story.append(Paragraph(m[1], rc_school))
                    if len(m) > 2: right_story.append(Paragraph(m[2], rc_body))
            elif sec == 'references' and content.get('references'):
                right_story.append(RcSectionHeader('REFERENCES', RIGHT_W))
                right_story.append(Spacer(1, 4))
                for r in content['references']:
                    right_story.append(Paragraph(f'<b>{r[0]}</b>', rc_degree))
                    rest = [r[i] for i in range(1, len(r)) if r[i]]
                    if rest: right_story.append(Paragraph('  |  '.join(rest), rc_body))
            elif sec == 'board' and content.get('board'):
                right_story.append(RcSectionHeader('BOARD SERVICE', RIGHT_W))
                right_story.append(Spacer(1, 4))
                for item in content['board']:
                    right_story.append(Paragraph(item, rc_body))

        # Two-column table — uses full column height since header is drawn on canvas
        col_h = PAGE_H - TOP - BOT - 150
        left_frame = KeepInFrame(LEFT_W, col_h, left_story, mode='shrink')
        right_frame = KeepInFrame(RIGHT_W, col_h, right_story, mode='shrink')
        tbl = Table([[left_frame, right_frame]],
                    colWidths=[LEFT_W + 10, RIGHT_W + 2])
        tbl.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('LEFTPADDING', (1,0), (1,-1), 10),
            ('LINEAFTER', (0,0), (0,-1), 0.24, sr_light),
        ]))
        story = [Spacer(1, 12), tbl]

        def on_page_sr(canvas, doc):
            # Draw name, contact, rule, and summary at top of page 1
            canvas.saveState()
            y = PAGE_H - TOP - 40
            canvas.setFont(font + '-Bold', 36)
            canvas.setFillColor(sr_dark)
            canvas.drawString(LEFT_X, y, _sr_header_name)
            y -= 18
            canvas.setFont(font, 9.5)
            canvas.setFillColor(sr_grey)
            canvas.drawString(LEFT_X, y, _sr_header_contact)
            y -= 10
            canvas.setStrokeColor(sr_dark)
            canvas.setLineWidth(2.16)
            canvas.line(LEFT_X, y, RIGHT_EDGE, y)
            # Summary
            if _sr_header_summary:
                y -= 10
                canvas.setStrokeColor(sr_light)
                canvas.setLineWidth(0.24)
                canvas.line(LEFT_X, y, RIGHT_EDGE, y)
                y -= 14
                canvas.setFont(font + '-Bold', 9)
                canvas.setFillColor(sr_dark)
                canvas.drawString(LEFT_X, y, '  '.join('PROFESSIONAL SUMMARY'))
                y -= 14
                canvas.setFont(font, 9)
                canvas.setFillColor(_c([0.1, 0.1, 0.1]))
                # Word-wrap summary text
                from reportlab.lib.utils import simpleSplit
                lines = simpleSplit(_sr_header_summary, font, 9, FULL_W)
                for line in lines:
                    canvas.drawString(LEFT_X, y, line)
                    y -= 11
            canvas.restoreState()
            if os.path.exists(LOGO_PATH):
                canvas.drawImage(LOGO_PATH, PAGE_W/2-50, 4, width=100, height=30,
                                 preserveAspectRatio=True, mask='auto')

        doc = BaseDocTemplate(output_path, pagesize=letter, leftMargin=LEFT_X,
                              rightMargin=PAGE_W-RIGHT_EDGE, topMargin=TOP + 150, bottomMargin=BOT)
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                      id='normal', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        doc.addPageTemplates([PageTemplate(id='sr', frames=[frame], onPage=on_page_sr)])
        doc.build(story)
        return

    # single column layout (original)
    LEFT = int(SINGLE_COLUMN['left_margin'])
    RIGHT = int(PAGE_WIDTH - SINGLE_COLUMN['right_margin'])

    # header
    story = []
    name_style = ParagraphStyle('Name', fontName=font+'-Bold', fontSize=24, textColor=primary,
                                 leading=29, spaceAfter=0,
                                 alignment=1 if header_style == 'centered_name' else 0)
    contact_ps = ParagraphStyle('Contact', fontName=font, fontSize=8.5, textColor=secondary,
                                 leading=10, spaceAfter=0,
                                 alignment=1 if header_style == 'centered_name' else 0)

    if header_style != 'banner':
        story.append(Paragraph(name, name_style))
        story.append(make_rule())
        if subtitle:
            sub_ps = ParagraphStyle('Sub', fontName=font+'-Bold', fontSize=14, textColor=primary,
                                    leading=17, spaceAfter=4,
                                    alignment=1 if header_style == 'centered_name' else 0)
            story.append(Paragraph(subtitle, sub_ps))
        story.append(Paragraph(contact, contact_ps))

    # sections
    for sec_name in section_order:
        builder = section_builders.get(sec_name)
        if builder:
            story.extend(builder())

    # page template
    def on_page(canvas, doc):
        if header_style == 'banner':
            canvas.saveState()
            canvas.setFillColor(primary)
            canvas.rect(0, PAGE_H - 120, PAGE_W, 120, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.setFont(font + '-Bold', 36)
            canvas.drawString(LEFT, PAGE_H - 80, name)
            # use white for contact text on dark banner
            _banner_contact_color = colors.white if sum(L['primary_color'])/3 < 0.3 else accent
            canvas.setFont(font, 9); canvas.setFillColor(_banner_contact_color)
            canvas.drawString(LEFT, PAGE_H - 100, contact)
            canvas.restoreState()
        if os.path.exists(LOGO_PATH):
            canvas.drawImage(LOGO_PATH, PAGE_W/2-50, 10, width=100, height=30,
                             preserveAspectRatio=True, mask='auto')

    top_margin = 134 if header_style == 'banner' else 43
    doc = BaseDocTemplate(output_path, pagesize=letter, leftMargin=LEFT,
                          rightMargin=PAGE_W-RIGHT, topMargin=top_margin, bottomMargin=54)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id='normal', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=on_page)])
    doc.build(story)
    print(f'Saved PDF: {output_path}')

