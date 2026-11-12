# Report: Results chapter

| File | What it is |
| --- | --- |
| `results_chapter.docx` | Editable **Chapter 4: Results**. Paste it into the Word source of the report, before "Conclusion and Future Scope" |
| `results_chapter.pdf` | The same chapter as a PDF |
| `final_project-report_with_results.pdf` | Preview: the original report with the chapter inserted before Conclusion (49 pages) |
| `results/screenshots/` | 18 application screenshots (2× resolution) |
| `results/charts/` | 3 charts: operation times, Warangal demand by category, tests per module |
| `results/benchmarks.json` | Raw performance measurements |

## After pasting the chapter into Word

The preview PDF only inserts pages, so a few things must be updated in the Word source:

1. **Renumber the chapter after Results.** "4. Conclusion and Future Scope" becomes **5**, with sections 5.1 and 5.2.
2. **Update the Table of Contents.** Add "4. RESULTS" and sections 4.1–4.13, then update the page numbers.
3. **Add Figures 4.1–4.21 to the List of Figures**, and Tables 4.1–4.3 to the List of Tables. Copy the captions from the chapter.
4. **Update the Python requirement.** Section 1.5 says "Python 3.9 or later"; the finished project needs **Python 3.11–3.13**.
5. **Optionally refresh Chapter 3.** It describes the frontend as "proposed React"; the finished system uses Django-rendered HTML pages with the same REST APIs.

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
.tools-venv/bin/python report/tools/build_results_section.py
```
