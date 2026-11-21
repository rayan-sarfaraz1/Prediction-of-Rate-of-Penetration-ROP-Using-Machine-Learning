"""
Builds ALL final documents (Word + PDF) with a correct static table of contents,
list of figures and list of tables.

How it works: each Word document is built, converted to PDF with LibreOffice, the page
number of every heading/caption is read back from the PDF, and the document is rebuilt
with those page numbers (repeated until the page numbers are stable).

Usage (from the project root, after running the pipeline):
    python code/export_doc_data.py
    python code/verify.py
    python code/reports/make_final.py
Requires: Node.js with the 'docx' package, LibreOffice (soffice) and poppler (pdftotext).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent            # builder scripts
DOCS = HERE.parents[1] / "documents"             # output folder
TOC = HERE / ".toc"
BUILDS = {  # builder script -> documents it produces
    "build_thesis.js": ["ROP_FYP_Proposal_Ch1-3", "ROP_FYP_Complete_Thesis_Draft"],
    "build_user_guide.js": ["ROP_AI_App_User_Guide"],
    "build_verification.js": ["ROP_FYP_Verification_Report"],
    "build_srs.js": ["ROP_AI_SRS"],
}


def to_pdf(docx: Path, outdir: Path) -> Path:
    """Convert DOCX -> PDF with LibreOffice (an optional helper can be given via ROP_SOFFICE_HELPER)."""
    helper = os.environ.get("ROP_SOFFICE_HELPER")
    if helper:
        sys.path.insert(0, str(Path(helper).parent.parent))
        from office.soffice import run_soffice  # type: ignore
        run_soffice(["--headless", "--convert-to", "pdf", "--outdir", str(outdir), str(docx)])
    else:
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        with tempfile.TemporaryDirectory() as prof:
            subprocess.run([soffice, f"-env:UserInstallation=file://{prof}", "--headless", "--convert-to", "pdf",
                            "--outdir", str(outdir), str(docx)], check=True, capture_output=True)
    return outdir / (docx.stem + ".pdf")


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def page_numbers(pdf: Path, entries: list) -> dict:
    text = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    pages = text.split("\f")
    labels = []
    for pg in pages:
        lines = [l.strip() for l in pg.splitlines() if l.strip()]
        labels.append(lines[-1] if lines and re.fullmatch(r"[ivxlcdm]+|\d+", lines[-1]) else "")
    leader = re.compile(r"(\.\s?){4,}|…")
    result, start = {}, 0
    for i, e in enumerate(entries):
        key = norm(e["text"])
        key = key[:20] if e["kind"] == "h" else key.split(" ")[0] + " " + key.split(" ")[1] + " "
        for p in range(start, len(pages)):
            hit = False
            for line in pages[p].splitlines():
                ln = norm(line)
                # skip TOC / list lines: dot leaders or a trailing page number
                if leader.search(line) or re.search(r"\s([ivxlcdm]+|\d+)$", ln):
                    continue
                if (e["kind"] == "h" and ln.startswith(key)) or (e["kind"] != "h" and (ln + " ").startswith(key)):
                    hit = True
                    break
            if hit:
                result[str(i)] = labels[p] or "?"
                if e["kind"] == "h":   # headings are in document order; captions may interleave
                    start = p
                break
        else:
            result[str(i)] = "?"
    return result


def main():
    tmp = Path(tempfile.mkdtemp())
    for script, names in BUILDS.items():
        prev = None
        for it in range(4):
            subprocess.run(["node", str(HERE / script)], check=True, capture_output=True)
            cur = {}
            for n in names:
                pdf = to_pdf(DOCS / f"{n}.docx", tmp)
                entries = json.loads((TOC / f"{n}.entries.json").read_text())
                cur[n] = page_numbers(pdf, entries)
                (TOC / f"{n}.pages.json").write_text(json.dumps(cur[n]))
            if cur == prev:
                break
            prev = cur
        for n in names:
            shutil.copy(tmp / f"{n}.pdf", DOCS / f"{n}.pdf")
            missing = sum(v == "?" for v in cur[n].values())
            print(f"{n}: {len(cur[n])} TOC entries, {missing} unresolved, {it + 1} passes")


if __name__ == "__main__":
    main()
