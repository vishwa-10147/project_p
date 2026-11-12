"""Check page numbers, TOC, List of Figures and List of Tables of a report PDF.

Usage: python report/tools/verify_report.py report/final_project-report_with_results.pdf
"""

import pypdfium2 as pdfium, re, sys
pdf=pdfium.PdfDocument(sys.argv[1])
texts=[pdf[i].get_textpage().get_text_range() for i in range(len(pdf))]
norm=lambda t:" ".join(t.split()).upper()
printed={}
for i,t in enumerate(texts):
    toks=[l.strip() for l in t.splitlines() if l.strip()]
    nums=[x for x in toks if re.fullmatch(r"\d{1,2}|[ivx]{1,4}",x)]
    printed[i]=nums
dups=[(i+1,v) for i,v in printed.items() if len(v)>1]
print("pages with more than one page number:", dups)
arabic=[printed[i][0] if printed[i] else None for i in range(9,len(pdf))]
print("printed 1..N continuous:", arabic==[str(n) for n in range(1,len(arabic)+1)], f"(1..{arabic[-1]})")
roman=[printed[i][0] if printed[i] else None for i in range(1,9)]
print("front matter numbering:", roman)
page_of={v[0]:k for k,v in printed.items() if v}
def on(needle,page):
    k=page_of.get(str(page)); return k is not None and norm(needle) in norm(texts[k])
toc=norm(texts[4])
entries=re.findall(r"((?:\d+\.\d*\s+)?[A-Z][A-Z \-,&]+?)\s+(\d+|[ivx]+)(?=\s|$)", toc)
alias={"REQUIREMENT SPECIFICATIONS":"REQUIREMENTS SPECIFICATION","LITERATURE SURVEY TABLE":"TABLE 2.1","LIST OF TABLES":"LIST OF TABLES"}
bad=[(t,p) for t,p in ((re.sub(r"^\d+\.\d*\s+","",a).strip(),p) for a,p in entries) if not on(alias.get(t,t),p)]
print(f"TOC: {len(entries)} entries, mismatches: {bad}")
for idx,label in ((5,"Figure"),(6,"Table")):
    rows=re.findall(rf"{label} (\d+\.\d+)\s+(.+?)\s+(\d+)\s", " ".join(texts[idx].split())+" ")
    bad=[(n,p) for n,_,p in rows if not any(on(f"{label}{sep}{n}",p) for sep in (" ","  ")) and not on(f"{label} {n} :",p) and not on(f"{label.upper()} {n}",p)]
    print(f"{label} list: {len(rows)} rows, mismatches: {bad}")
# chapter / figure / table numbering sequences in body
body=norm(" ".join(texts[9:]))
caps=re.findall(r"FIGURE (\d+)\.(\d+):", body); tabs=re.findall(r"TABLE (\d+)\.(\d+) ?:", body)
print("figure captions:", [f"{a}.{b}" for a,b in caps])
print("table captions:", [f"{a}.{b}" for a,b in tabs])
chap=re.findall(r"(?:^|\s)(\d)\. ?([A-Z][A-Z\- ]{4,}?)(?= \d| [A-Z][a-z]|$)", " ".join(norm(t) for t in texts[9:]))
print("chapter headings found:", sorted(set(re.findall(r"\b([1-5])\. ?(INTRODUCTION|LITERATURE SURVEY|METHODOLOGY|RESULTS|CONCLUSION)", body))))
