"""Minimal, memory-safe .xlsx reader built on the standard library.

Some RBI workbooks carry a stylesheet that openpyxl cannot load (it runs out of
memory or rejects the XML), even though the cell data is fine. This reader
ignores styles completely and streams the sheet XML, so it always works.
"""
from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree as ET

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _col_index(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    out: list[str] = []
    with zf.open("xl/sharedStrings.xml") as fh:
        for _, elem in ET.iterparse(fh, events=("end",)):
            if elem.tag == _NS + "si":
                out.append("".join(t.text or "" for t in elem.iter(_NS + "t")))
                elem.clear()
    return out


def _first_sheet_path(zf: zipfile.ZipFile) -> str:
    try:
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        sheets = wb.find(_NS + "sheets")
        first = sheets.find(_NS + "sheet")
        rid = first.get(_REL_NS + "id")
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        for rel in rels.findall(_PKG_REL + "Relationship"):
            if rel.get("Id") == rid:
                target = rel.get("Target").lstrip("/")
                return target if target.startswith("xl/") else "xl/" + target
    except Exception:
        pass
    return "xl/worksheets/sheet1.xml"


def read_xlsx(path) -> "list[list]":
    """Return the first sheet as a list of rows (ragged, cells may be None)."""
    with zipfile.ZipFile(path) as zf:
        strings = _shared_strings(zf)
        sheet_path = _first_sheet_path(zf)
        grid: dict[int, dict[int, object]] = {}
        max_col = 0
        with zf.open(sheet_path) as fh:
            for _, elem in ET.iterparse(fh, events=("end",)):
                if elem.tag != _NS + "row":
                    continue
                r_idx = int(elem.get("r")) - 1
                cells: dict[int, object] = {}
                for c in elem.findall(_NS + "c"):
                    ref = c.get("r")
                    if not ref:
                        continue
                    col = _col_index(ref)
                    ctype = c.get("t")
                    v = c.find(_NS + "v")
                    if ctype == "s" and v is not None:
                        val = strings[int(v.text)]
                    elif ctype == "inlineStr":
                        val = "".join(t.text or "" for t in c.iter(_NS + "t"))
                    elif v is not None and v.text is not None:
                        try:
                            val = float(v.text)
                        except ValueError:
                            val = v.text
                    else:
                        val = None
                    if val is not None:
                        cells[col] = val
                        max_col = max(max_col, col)
                if cells:
                    grid[r_idx] = cells
                elem.clear()
        if not grid:
            return []
        n_rows = max(grid) + 1
        return [[grid.get(r, {}).get(c) for c in range(max_col + 1)] for r in range(n_rows)]
