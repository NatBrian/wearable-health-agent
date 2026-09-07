"""Extract symptom onset dates from the paper's Supplementary Table 3.

Reads the .xlsx directly as a zip of XML rather than adding openpyxl as a dependency for
one spreadsheet read. The sheet holds four columns per participant, with cell values that
are the string repr of a pandas list, for example:

    AFPB8J2 | COVID-19 | [Timestamp('2026-07-14 00:00:00')] | [Timestamp('2026-07-17...')]

Those dates are shifted, and so are the dates in the wearable files, by the same amount.
That is stated in the sheet's own second row: "Dates have been shifted to obscure PHI".

**Several participants report more than one symptom episode**, sometimes months apart, and
the column is titled "All Symptom Onset". Six of the thirty do. The one that matters is the
episode that led to the COVID-19 diagnosis, so onset is the LATEST symptom date at or
before the earliest diagnosis date. Anchoring on the earliest instead would score the
detector against an unrelated illness eight months away for AOYM4KG and would not be a
harder test, just the wrong one.

The rule never looks at what the detector did, so it cannot flatter it.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "data" / "cohort" / "supplementary-data-1.xlsx"
DEST = REPO / "data" / "cohort" / "labels.json"

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SHEET = "SuppTable3_Fig2a_COVID-19"
TIMESTAMP = re.compile(r"Timestamp\('(\d{4}-\d{2}-\d{2})")


def read_sheet(book: zipfile.ZipFile, name: str) -> list[list[str | None]]:
    """Rows of a named worksheet, shared strings resolved, as plain text."""
    rels = dict(
        re.findall(
            r'Id="(rId\d+)"[^>]*Target="([^"]+)"',
            book.read("xl/_rels/workbook.xml.rels").decode("utf-8"),
        )
    )
    sheets = {
        n: r
        for n, r in re.findall(
            r'<sheet name="([^"]+)"[^>]*r:id="(rId\d+)"',
            book.read("xl/workbook.xml").decode("utf-8"),
        )
    }
    if name not in sheets:
        raise SystemExit(f"{name} is not in this workbook. Sheets: {sorted(sheets)}")

    shared: list[str] = []
    if "xl/sharedStrings.xml" in book.namelist():
        for item in ET.fromstring(book.read("xl/sharedStrings.xml")):
            shared.append("".join(t.text or "" for t in item.iter(NS + "t")))

    target = rels[sheets[name]].lstrip("/")
    path = target if target.startswith("xl/") else f"xl/{target}"
    rows: list[list[str | None]] = []
    for row in ET.fromstring(book.read(path)).iter(NS + "row"):
        cells: list[str | None] = []
        for cell in row.iter(NS + "c"):
            value = cell.find(NS + "v")
            text = value.text if value is not None else None
            if cell.get("t") == "s" and text is not None:
                text = shared[int(text)]
            cells.append(text)
        rows.append(cells)
    return rows


def onset_for(symptoms: list[str], diagnoses: list[str]) -> str | None:
    """The symptom episode that led to the diagnosis, as an ISO date.

    Sorted ISO date strings compare correctly as text, so no parsing is needed here.
    """
    if not symptoms:
        return None
    if not diagnoses:
        return symptoms[0]
    first_diagnosis = diagnoses[0]
    before = [s for s in symptoms if s <= first_diagnosis]
    # Falling back to the earliest symptom covers the case where every reported onset is
    # after the diagnosis date, which happens when a positive test precedes symptoms.
    return before[-1] if before else symptoms[0]


def main() -> int:
    if not SOURCE.exists():
        raise SystemExit(f"{SOURCE} is missing. Run experiments/detection/cohort/fetch.py first.")

    rows = read_sheet(zipfile.ZipFile(SOURCE), SHEET)
    header = next(
        (i for i, r in enumerate(rows) if r and r[0] == "ParticipantID"),
        None,
    )
    if header is None:
        raise SystemExit(
            "No ParticipantID header row. The publisher may have changed the sheet layout; "
            "check it by hand rather than guessing at the columns."
        )

    out = []
    for row in rows[header + 1 :]:
        if not row or not row[0]:
            continue
        padded = list(row) + [None] * (5 - len(row))
        pid, category, symptoms, diagnosis = padded[0], padded[1], padded[2], padded[3]
        symptom_dates = sorted(set(TIMESTAMP.findall(symptoms or "")))
        diagnosis_dates = sorted(set(TIMESTAMP.findall(diagnosis or "")))
        out.append(
            {
                "pid": pid,
                "category": category,
                "symptom": onset_for(symptom_dates, diagnosis_dates),
                "diagnosis": diagnosis_dates[0] if diagnosis_dates else None,
                "all_symptom_dates": symptom_dates,
            }
        )

    DEST.write_text(json.dumps(out, indent=1), encoding="utf-8")
    covid = sum(1 for r in out if r["category"] == "COVID-19")
    dated = sum(1 for r in out if r["category"] == "COVID-19" and r["symptom"])
    print(f"wrote {DEST}")
    print(f"  participants listed        : {len(out)}")
    print(f"  COVID-19                   : {covid}")
    print(f"  COVID-19 with an onset date: {dated}")
    print("\nNext: uv run python experiments/detection/cohort/evaluate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
