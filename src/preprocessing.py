"""Data preprocessing for "Digital Payment Trends in India: UPI and Beyond".

Two raw sources, four analysis-ready tables.

Sources (either .csv or .xlsx; the loader accepts both)
------------------------------------------------------
data/raw/upi_npci.*        NPCI UPI product statistics, one row per month
data/raw/rbi_payments.*    RBI "Payment System Indicators" release, a single
                           sheet with PART I (payment & settlement statistics),
                           PART III (payment infrastructure) and
                           PART V (domestic payment frauds)

Outputs
-------
data/processed/upi_merged.csv        monthly UPI series + derived columns
data/processed/rbi_instruments.csv   tidy instrument x period volume/value table
data/processed/rbi_infrastructure.csv tidy infrastructure table
data/processed/fraud_monthly.csv     monthly domestic payment frauds

Run from the repository root:

    python -m src.preprocessing
"""
from __future__ import annotations

import difflib
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

OUT_SERIES = PROCESSED_DIR / "upi_merged.csv"
OUT_INSTRUMENTS = PROCESSED_DIR / "rbi_instruments.csv"
OUT_INFRA = PROCESSED_DIR / "rbi_infrastructure.csv"
OUT_FRAUD = PROCESSED_DIR / "fraud_monthly.csv"

# Columns the dashboard relies on. Keep these stable.
REQUIRED_SERIES_COLUMNS = [
    "month",
    "upi_volume",
    "upi_value",
    "upi_avg_daily_volume",
    "upi_avg_daily_value",
]

# Units: RBI reports volume in lakh, NPCI in millions. 1 lakh = 0.1 million.
LAKH_TO_MN = 0.1

# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
_MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july",
                "august", "september", "october", "november", "december"]

_MONTH_FORMATS = (
    "%b-%y", "%b %y", "%b-%Y", "%b %Y", "%B-%y", "%B %Y", "%b.%y", "%b.%Y",
    "%B.%Y", "%Y-%m", "%m-%Y", "%m/%Y", "%Y/%m", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d",
)


def _fix_month_words(text: str) -> str:
    """Repair month-name typos in the source ('Jauuary 2025' -> 'January 2025')."""
    tokens = str(text).split()
    if not tokens:
        return str(text)
    first = re.sub(r"[^A-Za-z]", "", tokens[0]).lower()
    if len(first) >= 3 and first not in _MONTH_NAMES:
        match = difflib.get_close_matches(first, _MONTH_NAMES, n=1, cutoff=0.75)
        if match:
            tokens[0] = match[0].capitalize()
    return " ".join(tokens)


def parse_months(series: pd.Series) -> pd.Series:
    """Parse a month column written in any of the usual Indian stats formats."""
    raw = (
        series.astype(str)
        .str.replace(r"(?i)^\s*as\s+on\s+", "", regex=True)   # "As on March 2026"
        .str.strip()
        .str.replace(r"[\u2018\u2019'`]", "-", regex=True)     # Apr'16  -> Apr-16
        .str.replace(r"\.(?=\s*\d{2,4}\s*$)", "-", regex=True)  # Apr.2016 -> Apr-2016
        .str.replace(r"\s+", " ", regex=True)
        .map(_fix_month_words)
    )
    out = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    pending = pd.Series(True, index=series.index)

    for fmt in _MONTH_FORMATS:
        if not pending.any():
            break
        attempt = pd.to_datetime(raw[pending], format=fmt, errors="coerce")
        ok = attempt.notna()
        if ok.any():
            idx = attempt.index[ok]
            out.loc[idx] = attempt[ok]
            pending.loc[idx] = False

    if pending.any():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")          # pandas dateutil fallback notice
            attempt = pd.to_datetime(raw[pending], errors="coerce")
        ok = attempt.notna()
        idx = attempt.index[ok]
        out.loc[idx] = attempt[ok]

    years = out.dt.year
    out = out.where((years >= 1990) & (years <= 2100))
    return out.dt.to_period("M").dt.to_timestamp()


def to_number(value) -> float:
    """'1,234.56' / 'Rs 1 234' / '-' / 'NA'  ->  float."""
    if value is None:
        return np.nan
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip()
    if text in {"", "-", "--", "nan", "None", "NA", "N/A"}:
        return np.nan
    text = re.sub(r"[,\s\u20b9$]", "", text)
    text = re.sub(r"[^\d.\-]", "", text)
    try:
        return float(text)
    except ValueError:
        return np.nan


def _clean_label(label) -> str:
    text = str(label).replace("\n", " ").strip()
    text = re.sub(r"^[\d.]+\s*", "", text)          # drop the leading code
    text = re.sub(r"[@#$*†‡]+", "", text)           # drop footnote markers
    return re.sub(r"\s+", " ", text).strip()


def _code_of(label) -> str | None:
    match = re.match(r"^\s*(\d+(?:\.\d+)*)\.?\s+\S", str(label))
    return match.group(1) if match else None


def _level_of(code: str | None) -> int:
    return 0 if not code else code.count(".") + 1


# --------------------------------------------------------------------------- #
# Reading raw files
# --------------------------------------------------------------------------- #
def resolve(prefix: str) -> Path | None:
    """Find data/raw/<prefix>.* whether it is a .csv or an .xlsx."""
    if not RAW_DIR.exists():
        return None
    matches = [p for p in RAW_DIR.glob(f"{prefix}*") if p.suffix.lower() in {".csv", ".xlsx"}]
    if not matches:
        return None
    matches.sort(key=lambda p: (p.suffix.lower() != ".csv", len(p.name)))
    return matches[0]


def read_raw(path: Path) -> pd.DataFrame:
    """Read a raw file with no header assumption (the RBI sheet has a title block)."""
    if path.suffix.lower() == ".xlsx":
        try:
            df = pd.read_excel(path, sheet_name=0, header=None)
        except Exception as exc:
            # Some RBI workbooks carry a stylesheet that openpyxl cannot load
            # (it rejects the XML or runs out of memory). The cell data is
            # fine, so fall back to the stylesheet-free streaming reader.
            print(f"[warn] pandas/openpyxl could not read {path.name} ({type(exc).__name__}); "
                  "using the built-in streaming reader")
            from .xlsx_stream import read_xlsx
            df = pd.DataFrame(read_xlsx(path))
    else:
        try:
            df = pd.read_csv(path, header=None)
        except UnicodeDecodeError:
            df = pd.read_csv(path, header=None, encoding="latin-1")
    return df


# --------------------------------------------------------------------------- #
# 1. NPCI monthly UPI series
# --------------------------------------------------------------------------- #
def build_series(path: Path) -> pd.DataFrame:
    df = read_raw(path)
    header_idx = next(
        (i for i, row in df.iterrows()
         if any(isinstance(c, str) and "month" in c.lower() for c in row)),
        None,
    )
    if header_idx is None:
        raise KeyError(f"{path.name}: no header row containing 'Month'")

    header = [str(c) if not pd.isna(c) else "" for c in df.iloc[header_idx]]
    body = df.iloc[header_idx + 1:].reset_index(drop=True)
    body.columns = header

    month_col = next(c for c in header if "month" in c.lower())

    # Skip "Avg. Daily ..." columns: they are derived here, from the day count.
    def pick(*keywords: str) -> str | None:
        for col in header:
            low = col.lower()
            if any(k in low for k in keywords) and not any(
                s in low for s in ("avg", "average", "daily")
            ):
                return col
        return None

    vol_col, val_col = pick("volume"), pick("value")
    if vol_col is None or val_col is None:
        raise KeyError(
            f"{path.name}: could not find a volume and a value column in {header}"
        )

    out = pd.DataFrame({
        "month": parse_months(body[month_col]),
        "upi_volume": body[vol_col].map(to_number),
        "upi_value": body[val_col].map(to_number),
    })
    before = len(out)
    out = out.dropna(subset=["month"]).drop_duplicates(subset=["month"], keep="first")
    out = out.sort_values("month").reset_index(drop=True)
    print(f"[info] NPCI series: {len(out)}/{before} months kept "
          f"({out['month'].min():%b %Y} -> {out['month'].max():%b %Y})")

    days = out["month"].dt.days_in_month
    out["days_in_month"] = days
    out["upi_avg_daily_volume"] = out["upi_volume"] / days
    out["upi_avg_daily_value"] = out["upi_value"] / days
    out["upi_avg_ticket_size"] = np.where(
        out["upi_volume"] > 0, out["upi_value"] * 10 / out["upi_volume"], np.nan
    )
    out["upi_volume_mom_pct"] = out["upi_volume"].pct_change() * 100
    out["upi_value_mom_pct"] = out["upi_value"].pct_change() * 100
    return out


# --------------------------------------------------------------------------- #
# 2. RBI workbook: locate the PARTs and their tables
# --------------------------------------------------------------------------- #
def _find_parts(rows: pd.DataFrame) -> dict[str, int]:
    """Row index of each 'PART <n>' marker, found in the label column."""
    parts: dict[str, int] = {}
    for i, row in rows.iterrows():
        for cell in row:
            if isinstance(cell, str):
                match = re.match(r"\s*PART\s+([IVX]+)\b", cell.upper())
                if match:
                    parts.setdefault(f"PART {match.group(1)}", i)
    return parts


def _as_int(value) -> int | None:
    """1, 1.0, '1', '1.0' -> 1; anything else -> None.

    CSV exports turn the '1 2 3 4' numbering row into text, so the parser has
    to accept both numbers and numeric strings.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return int(value) if float(value).is_integer() else None
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if re.fullmatch(r"\d+", text):
            return int(text)
        if re.fullmatch(r"\d+\.0+", text):
            return int(float(text))
    return None


def _looks_numeric(value) -> bool:
    """True only for a cell that *is* a number, not one that merely contains digits.

    'As on March 2026' contains 2026 but is a period label, and treating it as
    data makes the parser start the table one row too early.
    """
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return not (isinstance(value, float) and pd.isna(value))
    if isinstance(value, str):
        text = value.strip().replace(",", "").replace(" ", "")
        return bool(re.fullmatch(r"[-+]?\d*\.?\d+", text)) and any(ch.isdigit() for ch in text)
    return False


def _looks_measure(value) -> bool:
    """A number, or a number with a short unit suffix ('0.147 bps', '12 %')."""
    if _looks_numeric(value):
        return True
    if isinstance(value, str):
        return bool(re.fullmatch(r"[-+]?\d*\.?\d+\s*[A-Za-z%]{0,6}", value.strip()))
    return False


def _cell_text(value) -> str:
    """Header cell as text: '2026.0' -> '2026', blanks -> ''."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if isinstance(value, str):
        text = value.replace("\n", " ").strip()
        if text.lower() in {"", "nan", "none"}:
            return ""
        as_int = _as_int(text)
        if as_int is not None and len(text) <= 6:
            return str(as_int)
        return text
    if isinstance(value, (int, float, np.integer, np.floating)):
        return str(int(value)) if float(value).is_integer() else str(value)
    return str(value)


def _dump_rows(rows: pd.DataFrame, start: int, stop: int, limit: int = 10) -> str:
    """A short, readable view of a row range, for error messages."""
    out = []
    for i in range(start, min(stop, start + limit)):
        cells = [_cell_text(rows.iat[i, c])[:18] for c in range(min(rows.shape[1], 8))]
        if any(cells):
            out.append(f"      row {i}: {cells}")
    return "\n".join(out) or "      (these rows are empty)"


def _find_header_row(rows: pd.DataFrame, start: int, stop: int,
                     keywords: tuple[str, ...] = ("volume", "value")) -> int:
    """The row that carries the column units ('Volume (lakh)', 'Value (Cr)')."""
    for i in range(start, stop):
        text = " ".join(str(c).lower() for c in rows.iloc[i] if isinstance(c, str))
        if any(k in text for k in keywords):
            return i
    raise ValueError(
        f"No {'/'.join(keywords)} header row between rows {start} and {stop}. "
        f"Rows seen:\n{_dump_rows(rows, start, stop)}"
    )


def _find_data_start(rows: pd.DataFrame, header_row: int, stop: int,
                     probe_col: int) -> int | None:
    """First row below the header whose probe column holds a number."""
    for i in range(header_row + 1, stop):
        if _looks_numeric(rows.iat[i, probe_col]):
            return i
    return None


def _find_numbering_row(rows: pd.DataFrame, header_row: int, stop: int) -> int | None:
    """The '1 2 3 4' row, whether the file stores real numbers or text."""
    for i in range(header_row + 1, min(header_row + 8, stop)):
        seq = [_as_int(rows.iat[i, c]) for c in range(rows.shape[1])]
        seq = [v for v in seq if v is not None]
        if len(seq) >= 2 and 1 in seq and all(v <= 12 for v in seq):
            return i
    return None


def _find_label_column(rows: pd.DataFrame, header_row: int, stop: int) -> int:
    """The column holding the row names, whatever its position in the file.

    CSV exports differ in whether the sheet's empty first column survives, so
    the label column is found by counting cells that contain letters: the
    leftmost column above a quarter of the best score wins.
    """
    scores: list[int] = []
    for c in range(rows.shape[1]):
        score = 0
        for i in range(header_row + 1, stop):
            value = rows.iat[i, c]
            if pd.isna(value) or isinstance(value, (int, float, np.integer, np.floating)):
                continue
            if re.search(r"[A-Za-z]", str(value)):
                score += 1
        scores.append(score)

    if not scores or max(scores) == 0:
        raise ValueError(
            "Could not find the label column: no text found below the header. "
            f"\n{_dump_rows(rows, header_row, stop)}"
        )
    threshold = max(2, int(max(scores) * 0.25))
    for c, score in enumerate(scores):
        if score >= threshold:
            return c
    return int(np.argmax(scores))


def _content_rows(rows: pd.DataFrame, start: int, stop: int) -> list[int]:
    """Row indices in [start, stop) that hold at least one non-blank cell."""
    out = []
    for i in range(start, min(stop, len(rows))):
        row = rows.iloc[i]
        if any(not pd.isna(v) and str(v).strip() for v in row):
            out.append(i)
    return out


def _last_content_row(rows: pd.DataFrame, start: int, stop: int) -> int:
    """One past the last row with any content - ignores trailing blank padding."""
    found = _content_rows(rows, start, stop)
    return (found[-1] + 1) if found else start


def _numeric_block(rows: pd.DataFrame, data_start: int, stop: int,
                   start_col: int, limit: int, min_density: float = 0.35) -> list[int]:
    """Columns from start_col onwards that actually hold numbers in the data rows."""
    cols: list[int] = []
    live = _content_rows(rows, data_start, stop)
    span = max(len(live), 1)
    col = start_col
    while col < min(limit, rows.shape[1]):
        filled = sum(1 for i in live if _looks_measure(rows.iat[i, col]))
        if filled >= max(2, int(span * min_density)):
            cols.append(col)
            col += 1
        else:
            break
    return cols


def _period_labels(rows: pd.DataFrame, header_row: int, label_stop: int,
                   cols: list[int]) -> list[str]:
    """Join the label rows above the data into one period label per column."""
    labels = []
    for col in cols:
        parts: list[str] = []
        for i in range(header_row + 1, label_stop):
            text = _cell_text(rows.iat[i, col])
            if not text:
                continue
            # a bare 1..12 in a label row is numbering, not a period
            if _as_int(text) is not None and len(text) <= 2:
                continue
            parts.append(text)
        labels.append(" ".join(parts) if parts else f"column {col}")
    return labels


def _period_key(label: str) -> str:
    """'2025 September' / '2026 August' / 'FY 2025-26' / 'As on March 2026'."""
    text = re.sub(r"(?i)^as on\s+", "", label).strip()
    if re.match(r"(?i)^fy\s*\d{4}", text):
        return "FY " + re.sub(r"(?i)^fy\s*", "", text).strip()
    month = parse_months(pd.Series([text])).iloc[0]
    if pd.isna(month):
        return text
    return f"{month:%Y-%m}"


def _period_label_short(key: str) -> str:
    if key.startswith("FY"):
        return key
    try:
        return pd.Timestamp(key + "-01").strftime("%b %Y")
    except ValueError:
        return key


def build_instruments(rows: pd.DataFrame, parts: dict[str, int]) -> pd.DataFrame:
    start = parts["PART I"]
    stop = parts["PART II"]
    header_row = _find_header_row(rows, start, stop)

    header = rows.iloc[header_row]
    vol_start = next((i for i, c in enumerate(header)
                      if isinstance(c, str) and "volume" in c.lower()), None)
    val_start = next((i for i, c in enumerate(header)
                      if isinstance(c, str) and "value" in c.lower()), None)
    if vol_start is None:
        raise ValueError(
            f"PART I: no 'Volume' column in the header row {header_row}. "
            f"Row reads: {[_cell_text(c) for c in header]}\n{_dump_rows(rows, start, stop)}"
        )

    data_start = _find_data_start(rows, header_row, stop, vol_start)
    if data_start is None:
        raise ValueError(
            f"PART I: no numeric data found under the Volume column {vol_start}. "
            f"\n{_dump_rows(rows, header_row, stop)}"
        )

    label_col = _find_label_column(rows, header_row, stop)
    numbering_row = _find_numbering_row(rows, header_row, stop)
    label_stop = numbering_row if (numbering_row is not None and numbering_row < data_start) else data_start

    # The volume block must stop before the value block starts, or the two
    # would run into each other and every period would be counted twice.
    vol_limit = val_start if (val_start is not None and val_start > vol_start) else rows.shape[1]
    vol_cols = _numeric_block(rows, data_start, stop, vol_start, vol_limit)
    val_cols = (_numeric_block(rows, data_start, stop, val_start, rows.shape[1])
                if val_start is not None and val_start > vol_start else [])

    vol_periods = _period_labels(rows, header_row, label_stop, vol_cols)
    val_periods = _period_labels(rows, header_row, label_stop, val_cols)

    records = []
    for i in range(data_start, stop):
        label = rows.iat[i, label_col]
        if pd.isna(label):
            continue
        volume = [to_number(rows.iat[i, c]) for c in vol_cols]
        value = ([to_number(rows.iat[i, c]) for c in val_cols]
                 if val_cols else [np.nan] * len(vol_cols))
        if all(pd.isna(v) for v in volume):
            continue                                   # section heading row
        code = _code_of(label)
        name = _clean_label(label)
        if not name:
            continue                                   # spacer row
        for k, period in enumerate(vol_periods):
            vol_lakh = volume[k] if k < len(volume) else np.nan
            val_cr = value[k] if k < len(value) else np.nan
            records.append({
                "period": _period_key(period),
                "code": code,
                "level": _level_of(code),
                "instrument": name,
                "is_total": name.lower().startswith("total"),
                "volume_mn": vol_lakh * LAKH_TO_MN if pd.notna(vol_lakh) else np.nan,
                "value_cr": val_cr,
            })

    out = pd.DataFrame(records)
    out["code"] = out["code"].astype("string")
    out["avg_ticket_size"] = np.where(
        out["volume_mn"] > 0, out["value_cr"] * 10 / out["volume_mn"], np.nan
    )
    order = {p: n for n, p in enumerate(dict.fromkeys(_period_key(p) for p in vol_periods))}
    out["period_order"] = out["period"].map(order)
    out["period_label"] = out["period"].map(_period_label_short)
    out = out.sort_values(["period_order", "level", "code"], na_position="last").reset_index(drop=True)
    out = out.drop(columns=["period_order"])

    print(f"[info] PART I: {out['instrument'].nunique()} rows x "
          f"{out['period'].nunique()} periods -> {len(out)} records "
          f"({', '.join(out['period'].unique())})")
    if val_cols and vol_periods != val_periods:
        print(f"[warn] PART I: volume and value periods differ "
              f"({vol_periods} vs {val_periods}); check the header block")
    return out


def build_infrastructure(rows: pd.DataFrame, parts: dict[str, int]) -> pd.DataFrame:
    start = parts["PART III"]
    stop = parts.get("PART IV", len(rows))
    # PART III carries its unit in the PART title, not in a column header.
    header_row = _find_header_row(rows, start, stop,
                                  keywords=("infrastructure", "volume", "value"))

    # The first column to the right of the labels that carries numbers.
    label_col = _find_label_column(rows, header_row, stop)
    first_col = data_start = None
    for c in range(label_col + 1, rows.shape[1]):
        probe = _find_data_start(rows, header_row, stop, c)
        if probe is not None:
            first_col, data_start = c, probe
            break
    if first_col is None:
        raise ValueError(
            f"PART III: no numeric columns found.\n{_dump_rows(rows, start, stop)}"
        )

    numbering_row = _find_numbering_row(rows, header_row, stop)
    label_stop = numbering_row if (numbering_row is not None and numbering_row < data_start) else data_start

    cols = _numeric_block(rows, data_start, stop, first_col, rows.shape[1])
    periods = _period_labels(rows, header_row, label_stop, cols)

    records = []
    for i in range(data_start, stop):
        label = rows.iat[i, label_col]
        if pd.isna(label) or not _clean_label(label):
            continue                                   # blank or spacer row
        values = [to_number(rows.iat[i, c]) for c in cols]
        if all(pd.isna(v) for v in values):
            continue
        for k, period in enumerate(periods):
            records.append({
                "period": _period_key(period),
                "metric": _clean_label(label),
                "value_lakh": values[k],
            })

    out = pd.DataFrame(records)
    out["period_label"] = out["period"].map(_period_label_short)
    print(f"[info] PART III: {out['metric'].nunique()} metrics x "
          f"{out['period'].nunique()} periods -> {len(out)} records")
    return out


def build_fraud(rows: pd.DataFrame, parts: dict[str, int]) -> pd.DataFrame:
    start = parts["PART V"]
    stop = _last_content_row(rows, start, len(rows))

    header_row = None
    for i in range(start, min(start + 8, len(rows))):
        text = " ".join(str(c).lower() for c in rows.iloc[i] if isinstance(c, str))
        if "volume" in text and "value" in text:
            header_row = i
            break
    if header_row is None:
        raise ValueError(
            f"PART V: no 'Volume'/'Value' header row.\n{_dump_rows(rows, start, start + 12)}"
        )

    label_col = _find_label_column(rows, header_row, stop)

    first_col = data_start = None
    for c in range(label_col + 1, rows.shape[1]):
        probe = _find_data_start(rows, header_row, stop, c)
        if probe is not None:
            first_col, data_start = c, probe
            break
    if first_col is None:
        raise ValueError(
            f"PART V: no numeric columns to the right of column {label_col}.\n"
            f"{_dump_rows(rows, header_row, stop)}"
        )

    # volume, value, one-in-X and FTS sit side by side; FTS is stored as text
    # ("0.147 bps") but still parses to a number.
    cols = _numeric_block(rows, data_start, stop, first_col, first_col + 4, min_density=0.5)[:4]
    if len(cols) < 4:
        raise ValueError(
            f"PART V: expected volume, value, one-in-X and FTS columns, found {len(cols)} "
            f"from column {first_col}.\n{_dump_rows(rows, header_row, stop)}"
        )
    vol_c, val_c, one_c, fts_c = cols

    records = []
    for i in range(data_start, stop):
        label = rows.iat[i, label_col]
        if pd.isna(label):
            continue
        text = str(label).strip()
        if not re.search(r"[A-Za-z]{3}", text):
            continue                                   # footnote block
        month = parse_months(pd.Series([text])).iloc[0]
        if pd.isna(month):
            continue
        fts_raw = rows.iat[i, fts_c]
        fts = to_number(re.sub(r"(?i)bps", "", str(fts_raw))) if fts_raw is not None else np.nan
        records.append({
            "month": month,
            "fraud_volume_lakh": to_number(rows.iat[i, vol_c]),
            "fraud_value_cr": to_number(rows.iat[i, val_c]),
            "one_in_x_transactions": to_number(rows.iat[i, one_c]),
            "fts_bps": fts,
        })

    if not records:
        raise ValueError(
            "PART V: no month rows could be parsed. The label column was read as "
            f"column {label_col}; rows seen:\n{_dump_rows(rows, data_start, stop)}"
        )

    out = pd.DataFrame(records).dropna(subset=["month"]).sort_values("month")
    out = out.drop_duplicates(subset=["month"], keep="last").reset_index(drop=True)
    print(f"[info] PART V: {len(out)} months of fraud data "
          f"({out['month'].min():%b %Y} -> {out['month'].max():%b %Y})")
    return out


# --------------------------------------------------------------------------- #
# 3. Cross-validation between the two sources
# --------------------------------------------------------------------------- #
def cross_validate(series: pd.DataFrame, instruments: pd.DataFrame) -> None:
    """NPCI and RBI both report UPI volume and value: they must agree."""
    rbi_upi = instruments[(instruments["code"] == "2.6") & (~instruments["is_total"])]
    if rbi_upi.empty:
        return
    for _, row in rbi_upi.iterrows():
        month = pd.Timestamp(row["period"] + "-01") if not str(row["period"]).startswith("FY") else None
        if month is None or pd.isna(row["volume_mn"]):
            continue
        hit = series.loc[series["month"] == month]
        if hit.empty:
            continue
        npci_vol = float(hit["upi_volume"].iloc[0])
        diff = abs(npci_vol - row["volume_mn"]) / npci_vol * 100
        status = "match" if diff < 0.5 else f"DIFFERS by {diff:.2f}%"
        print(f"[check] UPI {month:%b %Y}: NPCI {npci_vol:,.2f} Mn vs "
              f"RBI {row['volume_mn']:,.2f} Mn -> {status}")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build(verbose: bool = True) -> dict[str, pd.DataFrame]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result: dict[str, pd.DataFrame] = {}

    npci_path = resolve("upi_npci")
    rbi_path = resolve("rbi_payments")
    if npci_path is None and rbi_path is None:
        raise FileNotFoundError(
            f"No raw inputs found in {RAW_DIR}. Expected upi_npci.* and rbi_payments.*"
        )

    if npci_path is not None:
        print(f"[info] NPCI file: {npci_path.name}")
        series = build_series(npci_path)
        series.to_csv(OUT_SERIES, index=False)
        result["series"] = series
    else:
        print("[warn] no NPCI file - the monthly UPI series will be missing")

    if rbi_path is not None:
        print(f"[info] RBI file: {rbi_path.name}")
        rows = read_raw(rbi_path)
        parts = _find_parts(rows)
        print(f"[info] RBI parts found: {sorted(parts)}")

        instruments = build_instruments(rows, parts)
        instruments.to_csv(OUT_INSTRUMENTS, index=False)
        result["instruments"] = instruments

        infra = build_infrastructure(rows, parts)
        infra.to_csv(OUT_INFRA, index=False)
        result["infrastructure"] = infra

        if "PART V" in parts:
            fraud = build_fraud(rows, parts)
            fraud.to_csv(OUT_FRAUD, index=False)
            result["fraud"] = fraud

        if "series" in result:
            cross_validate(result["series"], instruments)
    else:
        print("[warn] no RBI file - instrument, infrastructure and fraud tables will be missing")

    if "series" in result:
        missing = [c for c in REQUIRED_SERIES_COLUMNS if c not in result["series"].columns]
        if missing:
            raise KeyError(f"Series output is missing required columns: {missing}")

    if verbose:
        print("\n" + "=" * 74)
        for name, frame in result.items():
            print(f"{name:>14}: {len(frame):>4} rows  {list(frame.columns)[:6]}")
        print(f"written to {PROCESSED_DIR}")
        if "series" in result:
            s = result["series"]
            print(f"\nUPI series: {s['month'].min():%b %Y} -> {s['month'].max():%b %Y}")
            print(s[["month", "upi_volume", "upi_value", "upi_avg_ticket_size"]].to_string(index=False))
        print("=" * 74)

    return result


if __name__ == "__main__":
    build()
