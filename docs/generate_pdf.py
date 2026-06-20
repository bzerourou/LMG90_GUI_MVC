"""
LMGC90_GUI — la documentation en PDF
============================================
Usage:
    python generate_pdf.py

"""

import os, re, unicodedata
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable, Image as RLImage, KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# ══════════════════════════════════════════════════════════════════════════════
#  la configuration de base du générateur PDF
# ══════════════════════════════════════════════════════════════════════════════
MD_DIR       = Path("docs")                     
CAPTURES_DIR = Path("docs/captures")            
OUT_PDF      = Path("LMGC90_GUI_Documentation.pdf")
# ══════════════════════════════════════════════════════════════════════════════

MAX_IMG_W = 13.5 * cm
MAX_IMG_H = 8.0  * cm

W, H = A4   # page dimensions


# ─── Image finder ─────────────────────────────────────────────────────────────
def _norm(s):
    """Normalize a filename for fuzzy matching (lowercase, NFC unicode)."""
    return unicodedata.normalize("NFC", s).lower()

def _build_img_index(directory: Path) -> dict:
    """Build {normalized_name: real_path} index once."""
    idx = {}
    if directory.exists():
        for f in directory.iterdir():
            if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp'):
                idx[_norm(f.name)] = f
    return idx

_IMG_INDEX = None

def find_image(raw_path: str) -> Path | None:
    global _IMG_INDEX
    if _IMG_INDEX is None:
        _IMG_INDEX = _build_img_index(CAPTURES_DIR)

    filename = Path(raw_path.replace("\\", "/")).name
    # 1. exact normalized match
    hit = _IMG_INDEX.get(_norm(filename))
    if hit:
        return hit
    # 2. strip extension and try again (handles .JPG vs .jpg)
    stem = Path(filename).stem.lower()
    for k, v in _IMG_INDEX.items():
        if Path(k).stem == stem:
            return v
    return None


# ─── Custom flowables ─────────────────────────────────────────────────────────
class Placeholder(Flowable):
    """Dashed box shown when image file is not found."""
    def __init__(self, label, w=MAX_IMG_W, h=5*cm):
        super().__init__()
        self._w, self._h, self.label = w, h, label

    def wrap(self, aw, ah):
        return self._w, self._h + 0.55*cm

    def draw(self):
        c = self.canv
        c.setDash(5, 3)
        c.setStrokeColor(colors.HexColor('#7B9EC5'))
        c.setFillColor(colors.HexColor('#EEF5FC'))
        c.roundRect(0, 0.55*cm, self._w, self._h - 0.55*cm, 6, fill=1, stroke=1)
        c.setDash()
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(colors.HexColor('#7B9EC5'))
        c.drawCentredString(self._w/2, self._h/2 + 0.1*cm, "[ IMAGE ]")
        c.setFont("Helvetica-Oblique", 7)
        c.setFillColor(colors.HexColor('#4A6A8A'))
        lbl = self.label[:100] + "…" if len(self.label) > 100 else self.label
        c.drawCentredString(self._w/2, 0.1*cm, lbl)


class ChapterBanner(Flowable):
    """Dark blue chapter header band."""
    def __init__(self, num, title, w=17*cm):
        super().__init__()
        self.num, self.title, self._w = str(num), title, w

    def wrap(self, aw, ah):
        return self._w, 2.1*cm

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor('#1A3A5C'))
        c.roundRect(0, 0, self._w, 1.9*cm, 8, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(0.4*cm, 1.38*cm, f"Chapitre {self.num}")
        c.setFont("Helvetica-Bold", 13.5)
        t = self.title if len(self.title) < 75 else self.title[:72] + "…"
        c.drawString(0.4*cm, 0.38*cm, t)


# ─── Styles ────────────────────────────────────────────────────────────────────
def make_styles():
    base = getSampleStyleSheet()
    def S(name, **kw):
        return ParagraphStyle(name, parent=base['Normal'], **kw)

    return {
        # Body text
        'body':    S('body',  fontSize=9,   leading=13.5, spaceAfter=3,
                      textColor=colors.HexColor('#1E1E1E'), alignment=TA_JUSTIFY),
        # Headings
        'h1':      S('h1',   fontSize=15,  leading=19, fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#1A3A5C'), spaceBefore=16, spaceAfter=7),
        'h2':      S('h2',   fontSize=12,  leading=16, fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#1A3A5C'), spaceBefore=13, spaceAfter=5),
        'h3':      S('h3',   fontSize=10.5,leading=14, fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#2B5A8A'), spaceBefore=10, spaceAfter=3),
        'h4':      S('h4',   fontSize=9.5, leading=13, fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#3A6A9A'), spaceBefore=7,  spaceAfter=2),
        'h5':      S('h5',   fontSize=9,   leading=12, fontName='Helvetica-BoldOblique',
                      textColor=colors.HexColor('#4A7AAA'), spaceBefore=5,  spaceAfter=2),
        # Code
        'code':    S('code', fontSize=7.8, leading=11, fontName='Courier',
                      textColor=colors.HexColor('#1E1E1E'),
                      backColor=colors.HexColor('#F5F5F5'),
                      borderColor=colors.HexColor('#CCCCCC'), borderWidth=0.5,
                      borderPad=5, leftIndent=6, rightIndent=6,
                      spaceBefore=4, spaceAfter=4),
        # Blockquotes
        'note':    S('note', fontSize=8.5, leading=12,
                      textColor=colors.HexColor('#5A4000'),
                      backColor=colors.HexColor('#FFFBE6'),
                      borderColor=colors.HexColor('#F0C040'), borderWidth=0.9,
                      borderPad=5, leftIndent=8, spaceBefore=4, spaceAfter=4),
        'tip':     S('tip',  fontSize=8.5, leading=12,
                      textColor=colors.HexColor('#1A4A1A'),
                      backColor=colors.HexColor('#F0FBF0'),
                      borderColor=colors.HexColor('#50A050'), borderWidth=0.9,
                      borderPad=5, leftIndent=8, spaceBefore=4, spaceAfter=4),
        'warn':    S('warn', fontSize=8.5, leading=12,
                      textColor=colors.HexColor('#6A1A1A'),
                      backColor=colors.HexColor('#FBF0F0'),
                      borderColor=colors.HexColor('#C05050'), borderWidth=0.9,
                      borderPad=5, leftIndent=8, spaceBefore=4, spaceAfter=4),
        # Lists
        'li':      S('li',   fontSize=9,   leading=13, spaceAfter=2,
                      leftIndent=16, firstLineIndent=-10,
                      textColor=colors.HexColor('#1E1E1E')),
        'li2':     S('li2',  fontSize=9,   leading=13, spaceAfter=1,
                      leftIndent=28, firstLineIndent=-10,
                      textColor=colors.HexColor('#333333')),
        # Caption
        'caption': S('cap',  fontSize=7.5, leading=10,
                      textColor=colors.HexColor('#555555'),
                      fontName='Helvetica-Oblique',
                      alignment=TA_CENTER, spaceBefore=1, spaceAfter=5),
        # Table cell
        'tc':      S('tc',   fontSize=8,   leading=11,
                      textColor=colors.HexColor('#1E1E1E')),
        'th':      S('th',   fontSize=8,   leading=11,
                      fontName='Helvetica-Bold', textColor=colors.white),
        # TOC
        'toc_h':   S('toch', fontSize=11,  leading=15, fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#1A3A5C'), spaceBefore=6, spaceAfter=1),
        'toc_s':   S('tocs', fontSize=8.5, leading=12,
                      textColor=colors.HexColor('#444'), leftIndent=14, spaceBefore=1),
        # Cover
        'cov_t':   S('covt', fontSize=34,  leading=40, fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#1A3A5C'), alignment=TA_CENTER),
        'cov_s':   S('covs', fontSize=15,  leading=20,
                      textColor=colors.HexColor('#2B5A8A'), alignment=TA_CENTER),
        'cov_v':   S('covv', fontSize=11,  leading=15,
                      textColor=colors.HexColor('#4A7AAA'), alignment=TA_CENTER),
    }

ST = make_styles()


# ─── Small helpers ─────────────────────────────────────────────────────────────
def SP(h=0.2):
    return Spacer(1, h * cm)

def HR():
    return HRFlowable(width="100%", thickness=0.5,
                      color=colors.HexColor('#2B5A8A'), spaceAfter=3, spaceBefore=5)

def safe(t):
    """Escape bare & < > not already inside an XML tag or entity."""
    t = str(t)
    result = []
    i = 0
    while i < len(t):
        ch = t[i]
        if ch == '&':
            # check if already an entity like &amp; &lt; &gt; &nbsp; &#nnn;
            m = re.match(r'&(?:#\d+|#x[\da-fA-F]+|[a-zA-Z]\w*);', t[i:])
            if m:
                result.append(m.group()); i += len(m.group())
            else:
                result.append('&amp;'); i += 1
        elif ch == '<':
            # keep valid RL tags: <b> </b> <i> </i> <u> </u> <br/> <font ...> </font>
            m = re.match(
                r'<(/?(b|i|u|br\s*/)|(font)[^>]*|(/font))>',
                t[i:], re.I)
            if m:
                result.append(m.group()); i += len(m.group())
            else:
                result.append('&lt;'); i += 1
        elif ch == '>':
            result.append('&gt;'); i += 1
        else:
            result.append(ch); i += 1
    return ''.join(result)

def P(text, sty=None):
    sty = sty or ST['body']
    t = safe(str(text))
    try:
        return Paragraph(t, sty)
    except Exception:
        return Paragraph(re.sub(r'<[^>]+>', '', t), sty)


def make_table(headers, rows, col_widths=None):
    """Styled table with blue header row and alternating body rows."""
    avail = 16.5 * cm
    if col_widths is None:
        col_widths = [avail / len(headers)] * len(headers)

    data = [[P(f'<b>{h}</b>', ST['th']) for h in headers]]
    for row in rows:
        data.append([P(str(c), ST['tc']) for c in row])

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1,  0), colors.HexColor('#1A3A5C')),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1),
            [colors.HexColor('#EEF3FA'), colors.white]),
        ('GRID',          (0, 0), (-1, -1), 0.35, colors.HexColor('#BBBBBB')),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return t


def embed_image(raw_path, caption="", max_w=MAX_IMG_W, max_h=MAX_IMG_H):
    """
    Return a list of flowables containing the real image (scaled to fit)
    and its caption, or a placeholder if the file is not found.
    """
    found = find_image(raw_path)
    label = caption if caption else raw_path

    if found:
        try:
            from PIL import Image as PILImage
            with PILImage.open(str(found)) as pi:
                pi = pi.convert("RGB")
                orig_w, orig_h = pi.size

            # Convert pixels → points (assume 96 dpi screen captures)
            w_pt = orig_w / 96 * 72
            h_pt = orig_h / 96 * 72
            scale = min(max_w / w_pt, max_h / h_pt, 1.0)
            ri = RLImage(str(found), width=w_pt * scale, height=h_pt * scale)
            ri.hAlign = 'CENTER'
            items = [ri]
            if caption:
                items.append(P(caption, ST['caption']))
            items.append(SP(0.25))
            return items
        except Exception as e:
            print(f"  [WARN] Could not embed {found.name}: {e}")

    # fallback placeholder
    return [Placeholder(label, max_w, 5*cm), SP(0.2)]


def code_block(text):
    lines = text.strip('\n').split('\n')
    escaped = '<br/>'.join(
        l.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        for l in lines)
    return [P(f'<font name="Courier" size="7.8">{escaped}</font>', ST['code']),
            SP(0.1)]


# ─── Inline markdown → safe RL XML ────────────────────────────────────────────
def inline(text):
    """Convert inline markdown to ReportLab-safe XML markup."""
    t = text.strip()
    # Bold + italic
    t = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', t)
    # Bold
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    # Italic
    t = re.sub(r'\*(.+?)\*', r'<i>\1</i>', t)
    # Inline code → Courier red
    def fmt_code(m):
        inner = m.group(1).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        return f'<font name="Courier" size="8" color="#C7254E">{inner}</font>'
    t = re.sub(r'`([^`]+)`', fmt_code, t)
    # Strip markdown links → keep text
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    # Strip image references entirely
    t = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', t)
    # Escape bare &, <, >
    t = safe(t)
    return t


# ─── Markdown → flowable list ─────────────────────────────────────────────────
def md_to_story(md_text):
    """
    Convert a full Markdown document to a list of ReportLab flowables.

    Supported:
      - # to ##### headings
      - Fenced code blocks (``` … ```)
      - Pipe tables  | col | col |
      - Blockquotes  > text
      - Unordered lists  - / * / +  (nested)
      - Ordered lists  1.  2.  …
      - Inline images  ![alt](path)
      - Horizontal rules  ---
      - Plain paragraphs (multi-line accumulation)
      - Inline: **bold**, *italic*, `code`, [links]
    """
    story = []
    lines = md_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    n = len(lines)
    i = 0

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # ── fenced code block ───────────────────────────────────────────────
        if stripped.startswith('```'):
            code_lines = []
            i += 1
            while i < n and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            story += code_block('\n'.join(code_lines))
            i += 1
            continue

        # ── horizontal rule ─────────────────────────────────────────────────
        if re.match(r'^[-_*]{3,}\s*$', stripped):
            story.append(HR())
            i += 1
            continue

        # ── headings ────────────────────────────────────────────────────────
        hm = re.match(r'^(#{1,5})\s+(.*)', line)
        if hm:
            lvl  = len(hm.group(1))
            text = inline(hm.group(2))
            smap = {1: 'h1', 2: 'h2', 3: 'h3', 4: 'h4', 5: 'h5'}
            story.append(P(text, ST[smap[min(lvl, 5)]]))
            i += 1
            continue

        # ── standalone image line ───────────────────────────────────────────
        img_m = re.match(r'^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$', line)
        if img_m:
            alt  = img_m.group(1).strip()
            path = img_m.group(2).strip()
            if 'youtube' not in path and 'img.youtube' not in path:
                story += embed_image(path, alt if alt else path)
            i += 1
            continue

        # ── pipe table ──────────────────────────────────────────────────────
        if '|' in line and stripped.startswith('|'):
            tbl_lines = []
            while i < n and '|' in lines[i] and lines[i].strip().startswith('|'):
                tbl_lines.append(lines[i])
                i += 1
            # drop separator lines like |---|---|
            rows_raw = [r for r in tbl_lines
                        if not re.match(r'^\s*\|[\s\-:|]+\|\s*$', r)]
            if rows_raw:
                parsed = []
                for r in rows_raw:
                    cells = [c.strip() for c in r.strip().strip('|').split('|')]
                    parsed.append(cells)
                if len(parsed) >= 1:
                    max_c = max(len(r) for r in parsed)
                    parsed = [r + [''] * (max_c - len(r)) for r in parsed]
                    headers  = [inline(c) for c in parsed[0]]
                    body_rows = [[inline(c) for c in r] for r in parsed[1:]]
                    avail = 16.5 * cm
                    cw = [avail / max_c] * max_c
                    story.append(make_table(headers, body_rows, cw))
                    story.append(SP(0.2))
            continue

        # ── blockquote ──────────────────────────────────────────────────────
        if line.startswith('>'):
            bq = []
            while i < n and lines[i].startswith('>'):
                bq.append(lines[i].lstrip('> ').strip())
                i += 1
            text = ' '.join(bq)
            lo = text.lower()
            if any(w in lo for w in ['attention', 'avertissement', 'warning',
                                      'erreur', 'error', '⚠']):
                sty = ST['warn']
            elif any(w in lo for w in ['conseil', 'astuce', 'tip',
                                        'recommandé', '💡']):
                sty = ST['tip']
            else:
                sty = ST['note']
            story.append(P(f'<i>{inline(text)}</i>', sty))
            continue

        # ── unordered list ──────────────────────────────────────────────────
        if re.match(r'^\s*[-*+]\s+', line):
            while i < n and re.match(r'^\s*[-*+]\s+', lines[i]):
                indent = len(lines[i]) - len(lines[i].lstrip())
                text   = re.sub(r'^\s*[-*+]\s+', '', lines[i])
                sty    = ST['li2'] if indent >= 4 else ST['li']
                story.append(P(f'• {inline(text)}', sty))
                i += 1
            continue

        # ── ordered list ────────────────────────────────────────────────────
        if re.match(r'^\s*\d+\.\s+', line):
            while i < n and re.match(r'^\s*\d+\.\s+', lines[i]):
                m    = re.match(r'^\s*(\d+)\.\s+(.*)', lines[i])
                num  = m.group(1)
                text = m.group(2)
                story.append(P(f'<b>{num}.</b> {inline(text)}', ST['li']))
                i += 1
            continue

        # ── empty line ──────────────────────────────────────────────────────
        if stripped == '':
            story.append(SP(0.15))
            i += 1
            continue

        # ── plain paragraph (accumulate continuation lines) ─────────────────
        para_lines = [line]
        i += 1
        while i < n:
            nxt = lines[i]
            stop = (
                nxt.strip() == '' or
                nxt.startswith('#') or
                nxt.startswith('>') or
                nxt.startswith('```') or
                re.match(r'^\s*[-*+]\s+', nxt) or
                re.match(r'^\s*\d+\.\s+', nxt) or
                ('|' in nxt and nxt.strip().startswith('|')) or
                re.match(r'^[-_*]{3,}\s*$', nxt.strip()) or
                re.match(r'^\s*!\[', nxt)
            )
            if stop:
                break
            para_lines.append(nxt)
            i += 1

        text = ' '.join(l.strip() for l in para_lines).strip()
        if text:
            story.append(P(inline(text), ST['body']))

    return story


# ─── Page footer / header ──────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    # footer
    canvas.setFillColor(colors.HexColor('#1A3A5C'))
    canvas.rect(0, 0, w, 1.0*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawString(1.5*cm, 0.33*cm,
                      "LMGC90_GUI — Documentation officielle v0.4.0")
    canvas.drawRightString(w - 1.5*cm, 0.33*cm, f"Page {doc.page}")
    # top rule
    canvas.setStrokeColor(colors.HexColor('#1A3A5C'))
    canvas.setLineWidth(0.5)
    canvas.line(1.5*cm, h - 1.35*cm, w - 1.5*cm, h - 1.35*cm)
    canvas.restoreState()


# ─── Cover ─────────────────────────────────────────────────────────────────────
def build_cover():
    s = []
    s.append(SP(5))
    s.append(P("LMGC90_GUI", ST['cov_t']))
    s.append(SP(0.5))
    s.append(P("Official Documentation", ST['cov_s']))
    s.append(SP(0.3))
    s.append(P("Version 0.4.5", ST['cov_v']))
    s.append(SP(1.0))
    s.append(P("© 2026 LMGC90_GUI", ST['cov_v']))
    s.append(SP(0.3))
    s.append(HRFlowable(width="65%", thickness=2,
                         color=colors.HexColor('#1A3A5C'),
                         hAlign='CENTER', spaceAfter=1.2*cm))
    for line in [
        "Graphical User Interface · Materials · Models",
        "Avatars · Loops · Granulometry",
        "Boundary Conditions · Contact Laws",
        "Masonry · Deformable Bodies · Simulation",
        "Post-processing · Dynamic Variables · Architecture",
    ]:
        s.append(P(line, ST['cov_s']))
        s.append(SP(0.12))
    s.append(PageBreak())
    return s


# ─── Table of contents ─────────────────────────────────────────────────────────
CHAPTERS = [
    ("1",  "Introduction to the interface",        "interface.md"),
    ("2",  "Configuration Assistant",         "project_wizard.md"),
    ("3",  "Materials",                          "material_creation.md"),
    ("4",  "Models",                            "model_creation.md"),
    ("5",  "Avatars — Rigid Bodies",            "avatar_creation.md"),
    ("6",  "Empty Avatar",                        "empty_avatar.md"),
    ("7",  "Templates",                       "templates.md"),
    ("8",  "Parametric Loops",              "loops.md"),
    ("9",  "Granulometry",                      "granulometry.md"),
    ("10", "Boundary Conditions (DOF)",       "dof.md"),
    ("11", "Contact Laws",                    "contact_laws.md"),
    ("12", "Visibility Tables",               "visibility.md"),
    ("13", "Masonry Assistant",            "masonry.md"),
    ("14", "Deformable Bodies (EF)",             "meshed.md"),
    ("15", "Simulation (chipy)",                     "calculs.md"),
    ("16", "Post-processing",                    "postpro.md"),
    ("17", "Dynamic Variables",               "dynam_variables.md"),
    ("18", "Visualization",                      "visualisation.md"),
    ("19", "Architecture & Developer Guide",   "dev.md"),
]

def build_toc():
    s = []
    s.append(P("<b>TABLE DES MATIÈRES</b>",
               ParagraphStyle('tit', parent=ST['h1'],
                               fontSize=18, spaceAfter=14)))
    s.append(HRFlowable(width="100%", thickness=1,
                         color=colors.HexColor('#1A3A5C'), spaceAfter=10))
    for num, title, _ in CHAPTERS:
        s.append(P(f"<b>{num}.</b>  {title}", ST['toc_h']))
    s.append(PageBreak())
    return s


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("LMGC90_GUI Book Generator")
    print("=" * 60)
    print(f"MD_DIR       : {MD_DIR.resolve()}")
    print(f"CAPTURES_DIR : {CAPTURES_DIR.resolve()}")
    print(f"OUT_PDF      : {OUT_PDF.resolve()}")

    # Pre-build image index and report
    global _IMG_INDEX
    _IMG_INDEX = _build_img_index(CAPTURES_DIR)
    print(f"Images found : {len(_IMG_INDEX)}")
    if not _IMG_INDEX:
        print("  WARNING: no images found – all figures will be placeholders.")
        print(f"  Make sure CAPTURES_DIR points to your captures folder.")

    doc = SimpleDocTemplate(
        str(OUT_PDF), pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2.4*cm, bottomMargin=1.8*cm,
        title="LMGC90_GUI — Documentation Officielle v0.4.0",
        author="LMGC90_GUI",
        subject="Documentation technique complète",
    )

    story = []
    story += build_cover()
    story += build_toc()

    for num, title, fname in CHAPTERS:
        md_path = MD_DIR / fname
        if not md_path.exists():
            print(f"  [SKIP] {fname} — file not found in {MD_DIR}")
            continue
        print(f"  Chapter {num:>2}: {fname}")
        md_text = md_path.read_text(encoding='utf-8', errors='replace')

        story.append(ChapterBanner(num, title))
        story.append(SP(0.3))
        story += md_to_story(md_text)
        story.append(PageBreak())

    print("Building PDF …")
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Done  →  {OUT_PDF.resolve()}")
    print("=" * 60)


if __name__ == '__main__':
    main()