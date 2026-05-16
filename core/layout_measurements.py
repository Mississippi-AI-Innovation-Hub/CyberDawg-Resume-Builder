"""
layout_measurements.py — Shared measurements for PDF and DOCX renderers.

All values are in points (1 inch = 72 points).
Both renderers convert these to their native units:
  - PDF (ReportLab): uses points directly
  - DOCX (python-docx): converts to twips (1 point = 20 twips)

Changing a value here updates both PDF and DOCX output.
"""

# page dimensions (US Letter)
PAGE_WIDTH = 612.0   # 8.5 inches
PAGE_HEIGHT = 792.0  # 11 inches

# sidebar left layout
SIDEBAR_LEFT = {
    'sidebar_width': 163.0,       # colored sidebar width
    'sidebar_padding': 22.0,      # left padding inside sidebar
    'sidebar_rule_x': 146.4,      # where sidebar rules end (from left of sidebar)
    'main_left': 181.0,           # where main content starts
    'main_right': 573.4,          # where main content ends
    'main_right_margin': 36.0,    # right margin for main content (padding from paper edge)
    'bottom_margin': 54.0,        # bottom margin
    'top_margin': 68.0,           # top margin for main frame
}
# derived values
SIDEBAR_LEFT['sidebar_content_width'] = SIDEBAR_LEFT['sidebar_rule_x'] - SIDEBAR_LEFT['sidebar_padding']
SIDEBAR_LEFT['main_width'] = SIDEBAR_LEFT['main_right'] - SIDEBAR_LEFT['main_left']
SIDEBAR_LEFT['gap_width'] = SIDEBAR_LEFT['main_left'] - SIDEBAR_LEFT['sidebar_width']

# sidebar right layout
SIDEBAR_RIGHT = {
    'left_margin': 54.0,
    'divider_x': 384.0,
    'right_col_x': 396.0,
    'right_edge': 558.0,
    'top_margin': 36.0,
    'bottom_margin': 36.0,
}
SIDEBAR_RIGHT['left_width'] = SIDEBAR_RIGHT['divider_x'] - SIDEBAR_RIGHT['left_margin']
SIDEBAR_RIGHT['right_width'] = SIDEBAR_RIGHT['right_edge'] - SIDEBAR_RIGHT['right_col_x']
SIDEBAR_RIGHT['full_width'] = SIDEBAR_RIGHT['right_edge'] - SIDEBAR_RIGHT['left_margin']

# single column layout
SINGLE_COLUMN = {
    'left_margin': 54.0,
    'right_margin': 54.0,
    'top_margin': 43.0,
    'bottom_margin': 54.0,
    'banner_top_margin': 134.0,   # when header_style == 'banner'
}
SINGLE_COLUMN['content_width'] = PAGE_WIDTH - SINGLE_COLUMN['left_margin'] - SINGLE_COLUMN['right_margin']


# helper: convert points to twips (for DOCX)
def pt_to_twips(pt):
    """Convert points to twips (1 pt = 20 twips)."""
    return int(pt * 20)


# ── Column balancing for sidebar_right layout ─────────────────

def balance_sidebar_right_columns(content):
    """
    Decide which sections go in left vs right column for sidebar_right layout.
    Returns (left_sections, right_sections) based on content volume.
    
    Goal: keep columns roughly even. Move sections from right to left
    if the left side would otherwise be too empty.
    """
    # Estimate "weight" of each section (approximate line count)
    def _weight(section_name):
        data = content.get(section_name)
        if not data:
            return 0
        if section_name == 'jobs':
            # Each job ~6 lines (title + company + 3-5 bullets)
            return len(data) * 6
        if section_name == 'military':
            return len(data) * 5
        if section_name == 'volunteer':
            return len(data) * 5
        if section_name == 'education':
            return len(data) * 3
        if section_name == 'certifications':
            return len(data) * 1
        if section_name == 'skills':
            return len(data) * 1
        if section_name == 'references':
            return len(data) * 2
        if section_name == 'board':
            return len(data) * 1
        return 0

    # Default assignment
    left = []
    right = []

    # Always left: experience, volunteer
    for s in ['experience', 'volunteer']:
        if content.get('jobs' if s == 'experience' else s):
            left.append(s)

    # Always right: education, certifications, skills
    for s in ['education', 'certifications', 'skills']:
        if content.get(s):
            right.append(s)

    # Flexible sections: military, references, board — assign based on balance
    flexible = ['military', 'references', 'board']
    left_weight = sum(_weight('jobs' if s == 'experience' else s) for s in left)
    right_weight = sum(_weight(s) for s in right)

    for s in flexible:
        if not content.get(s):
            continue
        w = _weight(s)
        if left_weight < right_weight:
            left.append(s)
            left_weight += w
        else:
            right.append(s)
            right_weight += w

    return left, right
