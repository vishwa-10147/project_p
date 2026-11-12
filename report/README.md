# Report: Results chapter

| File | What it is |
| --- | --- |
| `final_project-report_with_results.pdf` | **The complete, corrected report (50 pages)**: submit this |
| `updated_sections.docx` | Corrected **Abstract**, **List of Abbreviations** and **Chapter 3 sections 3.1–3.2**, for the Word source |
| `results_chapter.docx` | **Chapter 4: Results**, for the Word source |
| `conclusion_chapter.docx` | Rewritten **Chapter 5: Conclusion and Future Scope**, for the Word source |
| `chapter3_sections.pdf`, `results_chapter.pdf`, `conclusion_chapter.pdf` | Building blocks of the complete PDF (do not submit separately) |
| `source/final_project-report-original.pdf` | The original Stage-1 report the corrections are applied to |
| `results/screenshots/`, `results/charts/` | 19 screenshots and 3 charts used in Chapter 4 |
| `results/benchmarks.json` | Raw performance measurements |
| `tools/` | Scripts that regenerate and verify everything; the corrected wording is in `tools/report_text.py` |

## What was corrected (verified by `tools/verify_report.py`)

| Item | Result |
| --- | --- |
| Page numbering | i–viii, then 1–41 continuous, none missing or duplicated |
| Table of Contents | 29 entries, all on the stated page |
| List of Figures | 23 entries (3.1, 4.1–4.22), all correct |
| List of Tables | 4 entries (2.1, 4.1–4.3), all correct |
| Chapter 3 (pages 15–18) | Sections 3.1 and 3.2 rewritten for the implemented system: Django templates instead of React, RapidOCR instead of Tesseract, Web Speech API instead of Whisper, and the actual HE/ZKP methods |
| Chapter 4 Results | pages 19–37 |
| Chapter 5 Conclusion and Future Scope | rewritten, pages 38–39 |
| References | pages 40–41 |
| Abstract | Homomorphic Encryption is now described accurately: it computes on financial figures, while documents are encrypted at rest. ZKP proves idea ownership |
| Section 1.5 | "Python 3.9 or later" changed to "Python 3.11 to 3.13" |
| List of Abbreviations | 12 → 34 entries, covering every abbreviation used in Chapters 3–5 |
| Original errors | Figure 3.1's missing page number added (15); Table 2.1 corrected from page 10 to 12; "List of Tables" title added |
| Page layout | Regenerated pages use the original margins (text from x = 99.2 to 525.5 pt), Times New Roman 12 pt and 20.7 pt line spacing |

**Not changed (your decision):** the cover page still says "Project Stage – 1 Report (CS753PC)".

## If you edit the Word source instead

1. **Replace** the Abstract, List of Abbreviations and sections 3.1–3.2 with `updated_sections.docx`.
2. **In section 1.5,** change "Python 3.9 or later" to "Python 3.11 to 3.13".
3. **Paste** `results_chapter.docx` as Chapter 4.
4. **Replace** the old Conclusion with `conclusion_chapter.docx` (Chapter 5).
5. **Update** the Table of Contents and the lists of figures and tables using the page numbers above.

## Regenerating everything

The tools need their own Python environment, separate from the app:

```bash
python3.12 -m venv .tools-venv
.tools-venv/bin/pip install playwright matplotlib python-docx reportlab pypdf pillow
```

Screenshots use the installed Google Chrome, headless with its own profile.

Then, with the app running (`./setup.sh`):

```bash
cd empowerher/backend
../../.venv/bin/python manage.py seed_demo           # note the witness secret it prints
../../.venv/bin/python manage.py run_benchmarks
cd ../..
.tools-venv/bin/python report/tools/capture_screenshots.py --witness <secret>
.tools-venv/bin/python report/tools/make_charts.py
.tools-venv/bin/python report/tools/build_results_section.py   # also rebuilds TOC/LOF/LOT and page numbers
```
