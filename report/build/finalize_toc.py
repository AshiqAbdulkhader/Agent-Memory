"""Two-pass page numbering for the final report.

Renders Final_Report.docx to PDF with LibreOffice, locates every heading / figure caption / table title,
converts PDF page indices to the printed page labels (front matter: i, ii, ...; body: 1, 2, ...),
writes toc_pages.json and rebuilds the document so the contents and lists carry real page numbers.
Run twice if the contents length changes.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
SOFFICE = "/Users/ashiq/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/c6453bb5-b07f-47da-b0e7-26b41053b597/ad4d3d34-1221-4441-9bdb-fc65811c03df/skills/docx/scripts/office/soffice.py"


def roman(n: int) -> str:
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def render() -> Path:
    out = REPORT / "render_final"
    out.mkdir(exist_ok=True)
    subprocess.run([sys.executable, SOFFICE, "--headless", "--convert-to", "pdf", "--outdir", str(out),
                    str(REPORT / "Final_Report.docx")], check=True, capture_output=True)
    return out / "Final_Report.pdf"


def pages_text(pdf: Path) -> list[list[str]]:
    txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    return [[re.sub(r"\s+", " ", l).strip() for l in p.splitlines() if l.strip()] for p in txt.split("\f")]


def main():
    subprocess.run(["node", "build_final.js"], cwd=HERE, check=True, capture_output=True)
    pdf = render()
    pages = pages_text(pdf)
    keys = json.loads((HERE / "toc_keys.json").read_text())
    is_list = lambda l: "...." in l or re.search(r"\.\s?\.\s?\.", l)  # noqa: E731
    body_start = next(i for i, p in enumerate(pages) if any(l == "CHAPTER 1: INTRODUCTION" for l in p) and not any(is_list(l) for l in p))
    front_start = 2  # cover + title page are unnumbered

    def label(i: int) -> str:
        return str(i - body_start + 1) if i >= body_start else roman(i - front_start + 1)

    found, missing = {}, []

    def locate(key, pred, body_only=False):
        for i, p in enumerate(pages):
            if i < (body_start if body_only else front_start):
                continue
            if any(pred(l) and not is_list(l) for l in p):
                found[key] = label(i)
                return
        missing.append(key)

    for h in keys["headings"]:
        head = h[:45]
        is_body = h.startswith(("CHAPTER", "APPENDIX", "REFERENCES", "GLOSSARY", "CHECKLIST")) or re.match(r"\d+\.\d", h)
        locate(f"h:{h}", lambda l, h=h, head=head: l == h or (len(h) > 45 and l.startswith(head)), body_only=bool(is_body))
    for f in keys["figures"]:
        locate(f"f:{f}", lambda l, f=f: l.startswith(f + ":"), body_only=True)
    for t in keys["tables"]:
        locate(f"t:{t}", lambda l, t=t: l.startswith(t + ":"), body_only=True)
    (HERE / "toc_pages.json").write_text(json.dumps(found, indent=1))
    subprocess.run(["node", "build_final.js"], cwd=HERE, check=True, capture_output=True)
    pdf = render()
    n = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    print(f"located {len(found)} entries; missing: {missing}")
    print(re.search(r"Pages:\s+\d+", n).group(0), "| body starts at PDF page", body_start + 1, "| PDF:", pdf)


if __name__ == "__main__":
    main()
