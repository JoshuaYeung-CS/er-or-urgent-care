"""Write site/data.js: every committed cache inlined as one JS assignment.

The page has to work from file:// (no server, no fetch), so the data ships as
`window.ERUC_DATA = {...};`. Hospitals are packed as column arrays to keep the
file small.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HOSPITAL_COLS = [
    "id", "name", "address", "city", "state", "zip", "phone", "type",
    "emergency_services", "op18b", "op18b_footnote", "op18b_sample",
    "op18c", "op18c_footnote", "op22", "op22_footnote", "edv", "edv_footnote",
    "lat", "lon", "pct_shorter_state", "pct_shorter_nation",
]
NUMERIC = {"lat", "lon", "pct_shorter_state", "pct_shorter_nation", "op18b_sample"}
PREFIX = "window.ERUC_DATA = "


def _val(col: str, v: str):
    if col in NUMERIC:
        try:
            return float(v)
        except (TypeError, ValueError):
            return None  # blank or "Not Available"
    return v


def payload(data: Path) -> dict:
    with open(data / "hospitals.csv", encoding="utf-8", newline="") as f:
        rows = [[_val(c, r[c]) for c in HOSPITAL_COLS] for r in csv.DictReader(f)]
    zcta = {}
    with open(data / "zcta.csv", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            zcta[r["zip"]] = [float(r["lat"]), float(r["lon"])]
    return {
        "hospitals": {"cols": HOSPITAL_COLS, "rows": rows},
        "zcta": zcta,
        "urgentCare": json.loads((data / "urgent_care.json").read_text(encoding="utf-8")),
        "reference": json.loads((data / "reference.json").read_text(encoding="utf-8")),
    }


def build_site(data: Path, site: Path) -> Path:
    site.mkdir(parents=True, exist_ok=True)
    out = site / "data.js"
    body = json.dumps(payload(data), separators=(",", ":"), ensure_ascii=False)
    out.write_text(f"// Built by `python -m eruc site` from data/. Do not edit by hand.\n"
                   f"{PREFIX}{body};\n", encoding="utf-8")
    return out


def read_data_js(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    start = text.index(PREFIX) + len(PREFIX)
    return json.loads(text[start:].rstrip().rstrip(";"))
