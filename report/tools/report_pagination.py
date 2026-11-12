"""
Assemble the final report PDF from the original Stage-1 report and the
regenerated chapters, with correct pagination.

Original page index (0-based) -> what happens:
    0-3    cover, certificate, declaration, acknowledgement   kept
    4      Table of Contents                                    regenerated
    5      List of Figures                                      regenerated
    6      List of Tables                                       regenerated
    7      List of Abbreviations                                regenerated
    8      Abstract                                             regenerated
    9-22   Chapters 1-2                                         kept
           (page 12: "Python 3.9 or later" corrected in place)
    23     Chapter 3 first page (introduction + Figure 3.1)     kept
    24-26  Chapter 3 sections 3.1-3.2                           replaced
    27     Stage-1 Conclusion                                   replaced by
                                                                Results + new Conclusion
    28-29  References                                           kept, renumbered

Old text is removed from the PDF (not just covered), so search, copy and
screen readers see only the corrected text.
"""

import io
import re
from pathlib import Path

import pypdfium2 as pdfium
import pypdfium2.raw as raw
from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

from report_text import ABBREVIATIONS, ABSTRACT, KEYWORDS

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
PAGE_W, PAGE_H = 595.92, 843.12
TEXT_LEFT, TEXT_RIGHT = 99.2, 525.5          # measured text block
ROMAN_CENTER_X, ROMAN_BASELINE = 290.3, 40.5
ARABIC_CENTER_X = 305.5

IDX_TOC, IDX_LOF, IDX_LOT, IDX_ABBREV, IDX_ABSTRACT = 4, 5, 6, 7, 8
IDX_REQUIREMENTS = 12                       # page with "Python 3.9 or later"
IDX_CH3_REPLACED = (24, 25, 26)
IDX_CONCLUSION = 27
CH3_FIRST_PRINTED = 15

FRONT_MATTER = [
    ("CERTIFICATE", "i"), ("DECLARATION", "ii"), ("ACKNOWLEDGEMENT", "iii"),
    ("TABLE OF CONTENTS", "iv"), ("LIST OF FIGURES", "v"),
    ("LIST OF TABLES", "vi"), ("LIST OF ABBREVIATIONS", "vii"),
    ("ABSTRACT", "viii"),
]
CHAPTERS_1_2 = [
    ("1.", "INTRODUCTION", 1, [
        ("1.1", "PROBLEM DEFINITION", 1), ("1.2", "EXISTING APPLICATIONS", 2),
        ("1.3", "PROPOSED APPLICATION", 3),
        ("1.4", "OBJECTIVES OF EMPOWER-HER", 3),
        ("1.5", "REQUIREMENT SPECIFICATIONS", 3)]),
    ("2.", "LITERATURE SURVEY", 5, [("2.1", "LITERATURE SURVEY TABLE", 12)]),
]
ORIGINAL_FIGURES = [("3.1", "Proposed Methodology Flow of Empower-Her", 15)]
ORIGINAL_TABLES = [("2.1", "Literature Survey table", 12)]


def _fonts():
    try:
        pdfmetrics.registerFont(TTFont("TNR", FONT_DIR / "Times New Roman.ttf"))
        pdfmetrics.registerFont(
            TTFont("TNR-Bold", FONT_DIR / "Times New Roman Bold.ttf"))
        return "TNR", "TNR-Bold"
    except Exception:
        return "Times-Roman", "Times-Bold"


REGULAR, BOLD = _fonts()


# ---------------------------------------------------------------------
# Locating headings, figures and tables in generated chapters
# ---------------------------------------------------------------------

def _page_texts(path):
    pdf = pdfium.PdfDocument(str(path))
    return [" ".join(pdf[i].get_textpage().get_text_range().split())
            for i in range(len(pdf))]


def locate(chapter_pdf, content, first_page):
    """Printed page of each section heading, figure and table."""
    texts = _page_texts(chapter_pdf)

    def page_of(needle):
        for i, text in enumerate(texts):
            if needle in text:
                return first_page + i
        raise ValueError(f"Not found in chapter: {needle}")

    sections, figures, tables = [], [], []
    for block in content:
        if block[0] == "h2":
            number, title = block[1].split(" ", 1)
            sections.append((number, title.rstrip(":").upper(),
                             page_of(block[1])))
        elif block[0] == "fig":
            number, title = re.match(r"Figure (\S+): (.*)", block[2]).groups()
            figures.append((number, title, page_of(f"Figure {number}:")))
        elif block[0] == "table":
            number, title = re.match(r"Table (\S+): (.*)", block[1]).groups()
            tables.append((number, title, page_of(f"Table {number}:")))
    return sections, figures, tables, len(texts)


# ---------------------------------------------------------------------
# Generated front-matter pages
# ---------------------------------------------------------------------

def _new_canvas():
    buffer = io.BytesIO()
    return buffer, rl_canvas.Canvas(buffer, pagesize=(PAGE_W, PAGE_H))


def _finish(buffer, c):
    c.save()
    buffer.seek(0)
    return PdfReader(buffer).pages[0]


def _right(c, x, y, text, font, size):
    c.setFont(font, size)
    c.drawRightString(x, y, str(text))


def _roman(c, numeral):
    c.setFont(REGULAR, 11)
    c.drawCentredString(ROMAN_CENTER_X, ROMAN_BASELINE, numeral)


def _wrap(text, font, size, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if pdfmetrics.stringWidth(trial, font, size) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def _justified(c, x, y, text, font, size, width, leading):
    """Draw a justified paragraph; returns the next baseline."""
    lines = _wrap(text, font, size, width)
    for k, line in enumerate(lines):
        words = line.split()
        c.setFont(font, size)
        if k == len(lines) - 1 or len(words) == 1:
            c.drawString(x, y, line)
        else:
            used = sum(pdfmetrics.stringWidth(w, font, size) for w in words)
            space = (width - used) / (len(words) - 1)
            cursor = x
            for w in words:
                c.drawString(cursor, y, w)
                cursor += pdfmetrics.stringWidth(w, font, size) + space
        y -= leading
    return y


def toc_page(ch3_sections, results_page, results_sections, conclusion_page,
             conclusion_sections, references_page):
    buffer, c = _new_canvas()
    c.setFont(BOLD, 14)
    c.drawCentredString(ROMAN_CENTER_X, 772, "TABLE OF CONTENTS")
    y, step, right = 742, 15.4, 538

    for title, page in FRONT_MATTER:
        c.setFont(REGULAR, 10.5)
        c.drawString(84, y, title)
        _right(c, right, y, page, REGULAR, 10.5)
        y -= step

    def chapter(number, title, page, subs):
        nonlocal y
        c.setFont(BOLD, 10.5)
        c.drawString(72, y, f"{number}  {title}")
        _right(c, right, y, page, BOLD, 10.5)
        y -= step
        for sub_number, sub_title, sub_page in subs:
            c.setFont(REGULAR, 8.5)
            c.drawString(72, y, sub_number)
            c.drawString(110, y, sub_title)
            _right(c, right, y, sub_page, REGULAR, 8.5)
            y -= step

    for number, title, page, subs in CHAPTERS_1_2:
        chapter(number, title, page, subs)
    chapter("3.", "METHODOLOGY OF EMPOWER-HER", CH3_FIRST_PRINTED,
            ch3_sections)
    chapter("4.", "RESULTS", results_page, results_sections)
    chapter("5.", "CONCLUSION AND FUTURE SCOPE", conclusion_page,
            conclusion_sections)
    c.setFont(BOLD, 10.5)
    c.drawString(72, y, "REFERENCES")
    _right(c, right, y, references_page, BOLD, 10.5)
    if y < 60:
        raise ValueError("Table of contents does not fit on one page.")
    _roman(c, "iv")
    return _finish(buffer, c)


def list_page(title, label, rows, roman):
    """List of Figures / List of Tables in a three-column layout."""
    buffer, c = _new_canvas()
    c.setFont(BOLD, 14)
    c.drawCentredString(ROMAN_CENTER_X, 772, title)
    y = 742
    c.setFont(BOLD, 11)
    c.drawString(84, y, f"{label} No.")
    c.drawString(160, y, "Title")
    _right(c, 530, y, "Page No.", BOLD, 11)
    y -= 22
    step = 21 if len(rows) < 10 else 25.5
    for number, text, page in rows:
        c.setFont(REGULAR, 10.5)
        c.drawString(84, y, f"{label} {number}")
        lines = _wrap(text, REGULAR, 10.5, 300)
        for k, line in enumerate(lines):
            c.drawString(160, y - k * 12.5, line)
        _right(c, 515, y, page, REGULAR, 10.5)
        y -= step + (len(lines) - 1) * 12.5
    if y < 60:
        raise ValueError(f"{title} does not fit on one page.")
    _roman(c, roman)
    return _finish(buffer, c)


def abbreviations_page():
    buffer, c = _new_canvas()
    c.setFont(BOLD, 16.08)
    c.drawCentredString((TEXT_LEFT + TEXT_RIGHT) / 2, 771.3,
                        "LIST OF ABBREVIATIONS")
    y, step = 735, 19.6
    for short, meaning in ABBREVIATIONS:
        c.setFont(REGULAR, 12)
        c.drawString(TEXT_LEFT + 20, y, short)
        c.drawString(TEXT_LEFT + 95, y, meaning)
        y -= step
    if y < 60:
        raise ValueError("Abbreviations do not fit on one page.")
    _roman(c, "vii")
    return _finish(buffer, c)


def abstract_page():
    buffer, c = _new_canvas()
    c.setFont(BOLD, 16.08)
    c.drawCentredString((TEXT_LEFT + TEXT_RIGHT) / 2, 754.8, "ABSTRACT")
    width, leading = TEXT_RIGHT - TEXT_LEFT, 20.7
    y = 699.1
    for paragraph in ABSTRACT:
        y = _justified(c, TEXT_LEFT, y, paragraph, REGULAR, 12, width,
                       leading) - 4
    # Bold "Keywords:" label followed by the keyword list.
    label = "Keywords: "
    c.setFont(BOLD, 12)
    c.drawString(TEXT_LEFT, y, label)
    indent = pdfmetrics.stringWidth(label, BOLD, 12)
    first = _wrap(KEYWORDS, REGULAR, 12, width - indent)[0]
    c.setFont(REGULAR, 12)
    c.drawString(TEXT_LEFT + indent, y, first)
    remaining = KEYWORDS[len(first):].strip()
    end = _justified(c, TEXT_LEFT, y - leading, remaining, REGULAR, 12,
                     width, leading)
    if end < 60:
        raise ValueError("Abstract does not fit on one page.")
    _roman(c, "viii")
    return _finish(buffer, c)


# ---------------------------------------------------------------------
# In-place corrections of kept pages (old text removed, new text drawn)
# ---------------------------------------------------------------------

def _object_text(obj, textpage):
    import ctypes

    n = raw.FPDFTextObj_GetText(obj.raw, textpage.raw, None, 0)
    buffer = (ctypes.c_ushort * n)()
    raw.FPDFTextObj_GetText(obj.raw, textpage.raw, buffer, n)
    return bytes(buffer).decode("utf-16-le").rstrip("\x00")


def clean_kept_pages(original_pdf, references_page):
    """
    Remove outdated text objects. Returns the cleaned PDF bytes and
    {page index: [(text, x, y, size, font), ...]} to draw in their place.
    """
    pdf = pdfium.PdfDocument(str(original_pdf))
    draws = {}

    # Section 1.5: "Python 3.9 or later" -> "Python 3.11 to 3.13".
    page = pdf[IDX_REQUIREMENTS]
    textpage = page.get_textpage()
    objects = [(o, _object_text(o, textpage), o.get_matrix())
               for o in page.get_objects() if o.type == raw.FPDF_PAGEOBJ_TEXT]
    python = next(m for o, t, m in objects if t == "Python ")
    version = [(o, t, m) for o, t, m in objects
               if abs(m.f - python.f) < 0.5 and m.e > python.e + 30]
    if [t.strip() for _, t, _ in version if t.strip()] != ["3.9", "or", "later"]:
        raise ValueError("Unexpected text on the requirements page.")
    for o, _, _ in version:
        page.remove_obj(o)
    page.gen_content()
    old_version_x = next(m.e for _, t, m in version if t.strip() == "3.9")
    draws[IDX_REQUIREMENTS] = [("3.11 to 3.13", old_version_x,
                                python.f, 12, REGULAR)]

    # References: continue the page numbering.
    for index in range(IDX_CONCLUSION + 1, len(pdf)):
        page = pdf[index]
        textpage = page.get_textpage()
        old = str(19 + index - IDX_CONCLUSION)
        new = str(references_page + index - IDX_CONCLUSION - 1)
        hits = []
        for o in page.get_objects():
            if o.type != raw.FPDF_PAGEOBJ_TEXT:
                continue
            matrix = o.get_matrix()
            if _object_text(o, textpage) == old and matrix.f < 60:
                hits.append((o, matrix, o.get_font_size() * matrix.a))
        if len(hits) != 1:
            raise ValueError(f"Page number not found on page {index + 1}")
        o, matrix, size = hits[0]
        page.remove_obj(o)
        page.gen_content()
        draws[index] = [(new, matrix.e, matrix.f, size, REGULAR)]

    buffer = io.BytesIO()
    pdf.save(buffer)
    buffer.seek(0)
    return buffer, draws


def _overlay(page, items):
    buffer, c = _new_canvas()
    c.setFillColorRGB(0, 0, 0)
    for text, x, y, size, font in items:
        c.setFont(font, size)
        c.drawString(x, y, text)
    page.merge_page(_finish(buffer, c))


# ---------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------

def assemble_report(original_pdf, out_path, parts):
    """
    parts: {"chapter3" | "results" | "conclusion":
            (pdf path, content blocks, first printed page)}
    """
    located = {name: locate(path, content, first)
               for name, (path, content, first) in parts.items()}
    ch3_sections, _, _, ch3_pages = located["chapter3"]
    results_sections, figures, tables, results_pages = located["results"]
    conclusion_sections, _, _, conclusion_pages = located["conclusion"]
    results_page = parts["results"][2]
    conclusion_page = parts["conclusion"][2]
    references_page = conclusion_page + conclusion_pages

    if results_page != parts["chapter3"][2] + ch3_pages:
        raise ValueError("Chapter 3 and Results are not continuous.")
    if conclusion_page != results_page + results_pages:
        raise ValueError("Results and Conclusion are not continuous.")

    cleaned, draws = clean_kept_pages(original_pdf, references_page)
    original = PdfReader(cleaned)
    generated = {
        IDX_TOC: toc_page(ch3_sections, results_page, results_sections,
                          conclusion_page, conclusion_sections,
                          references_page),
        IDX_LOF: list_page("LIST OF FIGURES", "Figure",
                           ORIGINAL_FIGURES + figures, "v"),
        IDX_LOT: list_page("LIST OF TABLES", "Table",
                           ORIGINAL_TABLES + tables, "vi"),
        IDX_ABBREV: abbreviations_page(),
        IDX_ABSTRACT: abstract_page(),
    }

    writer = PdfWriter()
    for i, page in enumerate(original.pages):
        if i in generated:
            writer.add_page(generated[i])
        elif i in IDX_CH3_REPLACED:
            if i == IDX_CH3_REPLACED[0]:
                for new in PdfReader(str(parts["chapter3"][0])).pages:
                    writer.add_page(new)
        elif i == IDX_CONCLUSION:
            for name in ("results", "conclusion"):
                for new in PdfReader(str(parts[name][0])).pages:
                    writer.add_page(new)
        else:
            added = writer.add_page(page)
            if i in draws:
                _overlay(added, draws[i])

    with open(out_path, "wb") as handle:
        writer.write(handle)
    last = references_page + len(original.pages) - IDX_CONCLUSION - 2
    print(f"saved {Path(out_path).name}: {len(writer.pages)} pages; "
          f"Chapter 3 {CH3_FIRST_PRINTED}-{results_page - 1}, Results "
          f"{results_page}-{conclusion_page - 1}, Conclusion "
          f"{conclusion_page}-{references_page - 1}, References "
          f"{references_page}-{last}")
