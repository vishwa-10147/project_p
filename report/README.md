# Report: Results chapter

| File | What it is |
| --- | --- |
| `results_chapter.docx` | Editable **Chapter 4: Results**. Paste it into the Word source of the report, before "Conclusion and Future Scope" |
| `results_chapter.pdf` | The same chapter as a PDF |
| `final_project-report_with_results.pdf` | **Complete report (50 pages)** with the chapter inserted, correct page numbers, and regenerated Table of Contents, List of Figures and List of Tables |
| `results/screenshots/` | 19 application screenshots (2× resolution) |
| `results/charts/` | 3 charts: operation times, Warangal demand by category, tests per module |
| `results/benchmarks.json` | Raw performance measurements |

## Pagination (checked automatically)

`final_project-report_with_results.pdf` has been checked page by page with a script:

| Item | Result |
| --- | --- |
| Printed page numbers | i–viii, then 1–41 continuous, with none missing or duplicated |
| Results chapter | pages 19–38 |
| Conclusion | renumbered to **Chapter 5** (5.1, 5.2), page 39 |
| References | pages 40–41 |
| Table of Contents | 29 entries, each one on the page it states |
| List of Figures | 23 entries (3.1, 4.1–4.22), all correct |
| List of Tables | 4 entries (2.1, 4.1–4.3), all correct |

**Errors fixed from the original report:**
1. **List of Figures:** Figure 3.1 had no page number. It is on page **15**.
2. **List of Tables:** Table 2.1 was listed on page **10**. It is actually on page **12**.
3. **List of Tables:** the page had no "LIST OF TABLES" title.

## If you edit the Word source instead

Make the same changes there:
1. **Paste** `results_chapter.docx` before Conclusion.
2. **Renumber Conclusion as Chapter 5** (sections 5.1, 5.2).
3. **Update the Table of Contents** and the lists of figures and tables using the pages above, including the three fixes.
4. **Update the Python requirement:** change "Python 3.9 or later" in section 1.5 to **Python 3.11–3.13**.

## Content to review (not page numbering)

Some text was written when the project was only proposed, and now contradicts the Results chapter:
- **Conclusion (5.1):** says "some modules are still under development". All modules are now implemented.
- **Future Scope (5.2):** lists multilingual voice assistance, Homomorphic Encryption, Zero-Knowledge Proofs and automated document processing as future work. All of these are now built.
- **Chapter 3:** describes these features as "proposed", and names React as the frontend. The finished system uses Django-rendered pages.

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
