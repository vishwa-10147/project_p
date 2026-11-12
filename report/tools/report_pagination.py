"""
Assemble the final report PDF with correct pagination.

- Inserts the Results chapter (already numbered from 19) before Conclusion.
- Regenerates the Table of Contents, List of Figures and List of Tables
  (pages iv, v, vi) in the report's style, with every entry's real page.
- Renumbers "4. Conclusion and Future Scope" to Chapter 5 and continues the
  printed page numbers of the Conclusion and References pages.
- Fixes two errors in the original front matter: Figure 3.1 had no page
  number, and Table 2.1 was listed on page 10 instead of 12.
"""

import io
import re
from pathlib import Path

import pypdfium2 as pdfium
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
PAGE_W, PAGE_H = 595.92, 843.12          # the report's A4 page size

# Front matter positions measured from the original PDF.
ROMAN_CENTER_X, ROMAN_BASELINE = 290.3, 40.5
ARABIC_CENTER_X, ARABIC_BASELINE = 305.5, 33.0

# Original chapters and front matter (printed pages verified in the PDF).
FRONT_MATTER = [
    ("CERTIFICATE", "i"), ("DECLARATION", "ii"), ("ACKNOWLEDGEMENT", "iii"),
    ("TABLE OF CONTENTS", "iv"), ("LIST OF FIGURES", "v"),
    ("LIST OF TABLES", "vi"), ("LIST OF ABBREVIATIONS", "vii"),
    ("ABSTRACT", "viii"),
]
CHAPTERS_BEFORE = [
    ("1.", "INTRODUCTION", 1, [
        ("1.1", "PROBLEM DEFINITION", 1), ("1.2", "EXISTING APPLICATIONS", 2),
        ("1.3", "PROPOSED APPLICATION", 3),
        ("1.4", "OBJECTIVES OF EMPOWER-HER", 3),
        ("1.5", "REQUIREMENT SPECIFICATIONS", 3)]),
    ("2.", "LITERATURE SURVEY", 5, [("2.1", "LITERATURE SURVEY TABLE", 12)]),
    ("3.", "METHODOLOGY OF EMPOWER-HER", 15, [
        ("3.1", "TECHNOLOGIES USED", 16), ("3.2", "DEVELOPMENT PROCESS", 17)]),
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


def _page_texts(path):
    pdf = pdfium.PdfDocument(str(path))
    return [" ".join(pdf[i].get_textpage().get_text_range().split())
            for i in range(len(pdf))]


def locate(chapter_pdf, content, first_page):
    """Printed page of each Results heading, figure and table."""
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
            sections.append((number, title.upper(), page_of(block[1])))
        elif block[0] == "fig":
            number, title = re.match(r"Figure (\S+): (.*)", block[2]).groups()
            figures.append((number, title, page_of(f"Figure {number}:")))
        elif block[0] == "table":
            number, title = re.match(r"Table (\S+): (.*)", block[1]).groups()
            tables.append((number, title, page_of(f"Table {number}:")))
    return sections, figures, tables, len(texts)


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


def toc_page(sections, results_page, conclusion_page, conclusion_sections,
             references_page):
    buffer, c = _new_canvas()
    c.setFont(BOLD, 14)
    c.drawCentredString(ROMAN_CENTER_X, 772, "TABLE OF CONTENTS")
    y, step = 742, 16.6
    right = 538

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

    for number, title, page, subs in CHAPTERS_BEFORE:
        chapter(number, title, page, subs)
    chapter("4.", "RESULTS", results_page, sections)
    chapter("5.", "CONCLUSION AND FUTURE SCOPE", conclusion_page,
            conclusion_sections)
    c.setFont(BOLD, 10.5)
    c.drawString(72, y, "REFERENCES")
    _right(c, right, y, references_page, BOLD, 10.5)

    c.setFont(REGULAR, 11)
    c.drawCentredString(ROMAN_CENTER_X, ROMAN_BASELINE, "iv")
    if y < 60:
        raise ValueError("Table of contents does not fit on one page.")
    return _finish(buffer, c)


def list_page(title, label, rows, roman):
    """List of Figures / List of Tables in the report's three-column style."""
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
    c.setFont(REGULAR, 11)
    c.drawCentredString(ROMAN_CENTER_X, ROMAN_BASELINE, roman)
    return _finish(buffer, c)


def _wrap(text, font, size, width):
    words, lines, line = text.split(), [], ""
    for word in words:
        trial = f"{line} {word}".strip()
        if pdfmetrics.stringWidth(trial, font, size) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def _overlay(page, draw):
    """Draw new text on top of an existing page (already in the writer)."""
    buffer, c = _new_canvas()
    draw(c)
    page.merge_page(_finish(buffer, c))
    return page


def _object_text(obj, textpage):
    import ctypes
    import pypdfium2.raw as raw

    n = raw.FPDFTextObj_GetText(obj.raw, textpage.raw, None, 0)
    buffer = (ctypes.c_ushort * n)()
    raw.FPDFTextObj_GetText(obj.raw, textpage.raw, buffer, n)
    return bytes(buffer).decode("utf-16-le").rstrip("\x00")


def clean_tail_pages(original_pdf, conclusion_index, references_page):
    """
    Remove (not just cover) the old page numbers from the References
    pages (which follow the original Conclusion page) and return the
    cleaned PDF bytes plus the new numbers to draw in their place.
    """
    import pypdfium2.raw as raw

    pdf = pdfium.PdfDocument(str(original_pdf))
    replacements = {}
    renames = {"4.": "5.", "4.1 ": "5.1 ", "4.2 ": "5.2 "}

    for index in range(conclusion_index + 1, len(pdf)):
        page = pdf[index]
        textpage = page.get_textpage()
        old_number = str(19 + index - conclusion_index)
        new_number = str(references_page + index - conclusion_index - 1)
        drawn, remove = [], []
        for obj in page.get_objects():
            if obj.type != raw.FPDF_PAGEOBJ_TEXT:
                continue
            text = _object_text(obj, textpage)
            matrix = obj.get_matrix()
            x, y = matrix.e, matrix.f
            size = obj.get_font_size() * matrix.a
            if text == old_number and y < 60:
                remove.append(obj)
                drawn.append((new_number, x, y, size, REGULAR))
            elif index == conclusion_index and text in renames:
                remove.append(obj)
                drawn.append((renames[text], x, y, size, BOLD))
        expected = 1
        if len(remove) != expected:
            raise ValueError(
                f"Page {index + 1}: expected {expected} items to renumber, "
                f"found {len(remove)}")
        for obj in remove:
            page.remove_obj(obj)
        page.gen_content()
        replacements[index] = drawn

    buffer = io.BytesIO()
    pdf.save(buffer)
    buffer.seek(0)
    return buffer, replacements


def _draw_replacements(c, items):
    c.setFillColorRGB(0, 0, 0)
    for text, x, y, size, font in items:
        c.setFont(font, size)
        c.drawString(x, y, text)


def assemble_report(original_pdf, chapter_pdf, conclusion_pdf, out_path,
                    content, conclusion_content, conclusion_index,
                    first_page):
    sections, figures, tables, chapter_pages = locate(
        chapter_pdf, content, first_page)
    conclusion_page = first_page + chapter_pages
    conclusion_sections, _, _, conclusion_pages = locate(
        conclusion_pdf, conclusion_content, conclusion_page)
    references_page = conclusion_page + conclusion_pages

    cleaned, replacements = clean_tail_pages(
        original_pdf, conclusion_index, references_page)
    original = PdfReader(cleaned)

    toc = toc_page(sections, first_page, conclusion_page,
                   conclusion_sections, references_page)
    lof = list_page("LIST OF FIGURES", "Figure",
                    ORIGINAL_FIGURES + figures, "v")
    lot = list_page("LIST OF TABLES", "Table",
                    ORIGINAL_TABLES + tables, "vi")

    writer = PdfWriter()
    for i, page in enumerate(original.pages):
        if i == 4:
            writer.add_page(toc)
        elif i == 5:
            writer.add_page(lof)
        elif i == 6:
            writer.add_page(lot)
        elif i == conclusion_index:
            # Results chapter, then the rewritten Conclusion, which
            # replaces the original Stage-1 Conclusion page.
            for new_page in PdfReader(str(chapter_pdf)).pages:
                writer.add_page(new_page)
            for new_page in PdfReader(str(conclusion_pdf)).pages:
                writer.add_page(new_page)
        else:
            added = writer.add_page(page)
            if i in replacements:
                _overlay(added, lambda c, items=replacements[i]:
                         _draw_replacements(c, items))

    with open(out_path, "wb") as handle:
        writer.write(handle)
    last = references_page + len(original.pages) - conclusion_index - 2
    print(f"saved {Path(out_path).name}: {len(writer.pages)} pages; "
          f"Results {first_page}-{conclusion_page - 1}, Conclusion "
          f"{conclusion_page}-{references_page - 1}, References "
          f"{references_page}-{last}")
    return sections, figures, tables
