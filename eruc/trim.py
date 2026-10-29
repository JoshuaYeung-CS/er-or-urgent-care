"""Turn the raw downloads in data/raw/ into the small committed caches in data/.

Outputs (all committed, a few MB in total, so tests run offline):
  data/hospitals.csv     one row per hospital with ED measures + ZIP-centroid location
  data/zcta.csv          every ZCTA centroid (3 decimals, about 100 m)
  data/urgent_care.json  OpenStreetMap urgent-care places for the demo metros
  data/reference.json    national benchmarks, footnote text, periods, source URLs
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import re
from pathlib import Path

from . import stats
from .metros import METROS

ED_MEASURES = ("OP_18b", "OP_18c", "OP_22", "EDV")
HOSPITAL_FIELDS = [
    "id", "name", "address", "city", "state", "zip", "phone", "type", "ownership",
    "emergency_services",
    "op18b", "op18b_footnote", "op18b_sample",
    "op18c", "op18c_footnote",
    "op22", "op22_footnote",
    "edv", "edv_footnote",
    "lat", "lon", "loc",
    "pct_shorter_state", "pct_shorter_nation",
]
NON_HUMAN = re.compile(r"\b(vet|veterinary|animal|pet|pets|dog|cat)\b", re.I)


def _num(s: str):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def load_zcta(path: Path) -> dict[str, tuple[float, float]]:
    out = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = csv.reader(f, delimiter="|")
        header = [h.strip() for h in next(rows)]
        gi, la, lo = header.index("GEOID"), header.index("INTPTLAT"), header.index("INTPTLONG")
        for r in rows:
            if len(r) > lo:
                out[r[gi].strip()] = (round(float(r[la]), 3), round(float(r[lo].strip()), 3))
    return out


def read_ed_measures(path: Path) -> tuple[dict[str, dict], dict[str, tuple[str, str]]]:
    by_id: dict[str, dict] = {}
    periods: dict[str, tuple[str, str]] = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            m = r["Measure ID"]
            if r["Condition"] != "Emergency Department" or m not in ED_MEASURES:
                continue
            by_id.setdefault(r["Facility ID"], {})[m] = r
            periods.setdefault(m, (r["Start Date"], r["End Date"]))
    return by_id, periods


def build_hospitals(hgi_path: Path, tec_path: Path, zcta: dict) -> tuple[list[dict], dict]:
    ed, periods = read_ed_measures(tec_path)
    rows = []
    with open(hgi_path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            fid = r["Facility ID"]
            meas = ed.get(fid)
            if not meas:
                continue
            zip5 = r["ZIP Code"].strip().zfill(5)[:5]
            loc = zcta.get(zip5)

            def score(m):
                return meas.get(m, {}).get("Score", "Not Available") or "Not Available"

            def foot(m):
                return meas.get(m, {}).get("Footnote", "")

            rows.append({
                "id": fid, "name": r["Facility Name"].strip(), "address": r["Address"].strip(),
                "city": r["City/Town"].strip(), "state": r["State"].strip(), "zip": zip5,
                "phone": r["Telephone Number"].strip(), "type": r["Hospital Type"].strip(),
                "ownership": r["Hospital Ownership"].strip(),
                "emergency_services": r["Emergency Services"].strip(),
                "op18b": score("OP_18b"), "op18b_footnote": foot("OP_18b"),
                "op18b_sample": meas.get("OP_18b", {}).get("Sample", ""),
                "op18c": score("OP_18c"), "op18c_footnote": foot("OP_18c"),
                "op22": score("OP_22"), "op22_footnote": foot("OP_22"),
                "edv": score("EDV"), "edv_footnote": foot("EDV"),
                "lat": loc[0] if loc else "", "lon": loc[1] if loc else "",
                "loc": "zcta" if loc else "none",
            })

    nation = [v for v in (_num(h["op18b"]) for h in rows) if v is not None]
    by_state: dict[str, list[float]] = {}
    for h in rows:
        v = _num(h["op18b"])
        if v is not None:
            by_state.setdefault(h["state"], []).append(v)
    nation_sorted = sorted(nation)
    state_sorted = {k: sorted(v) for k, v in by_state.items()}

    def pct(v, group):
        r = stats.share_longer_than_others(v, group)
        return "" if r is None else round(100 * r, 1)

    for h in rows:
        v = _num(h["op18b"])
        if v is None:
            h["pct_shorter_state"] = h["pct_shorter_nation"] = ""
            continue
        h["pct_shorter_nation"] = pct(v, nation_sorted)
        h["pct_shorter_state"] = pct(v, state_sorted[h["state"]])

    q = stats.quantiles(nation, [0.1, 0.25, 0.5, 0.75, 0.9])
    summary = {
        "n_hospitals": len(rows),
        "n_op18b_numeric": len(nation),
        "n_op18b_not_available": len(rows) - len(nation),
        "n_no_zcta_match": sum(1 for h in rows if h["loc"] == "none"),
        "op18b_hospital_quantiles": dict(zip(["p10", "p25", "p50", "p75", "p90"],
                                             [round(x, 1) for x in q])),
        "state_medians": {s: round(stats.quantiles(v, [0.5])[0], 1)
                          for s, v in sorted(by_state.items())},
        "state_counts": {s: len(v) for s, v in sorted(by_state.items())},
        "periods": {m: {"start": a, "end": b} for m, (a, b) in periods.items()},
    }
    return rows, summary


def read_national(path: Path) -> dict:
    keep = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            mid = r.get("Measure ID", "")
            if mid.startswith(("OP_18b", "OP_18c", "OP_22")):
                keep[mid] = {"score": r.get("Score"), "footnote": r.get("Footnote", ""),
                             "start": r.get("Start Date"), "end": r.get("End Date"),
                             "name": r.get("Measure Name")}
    return keep


def read_footnotes(path: Path) -> dict[str, str]:
    with open(path, encoding="utf-8", newline="") as f:
        return {r["Footnote"].strip(): r["Footnote Text"].strip() for r in csv.DictReader(f)}


def is_urgent_care(tags: dict) -> tuple[bool, str]:
    """Decide whether an OSM element is a human urgent-care clinic, and why."""
    name = tags.get("name", "")
    if tags.get("amenity") in ("veterinary",) or NON_HUMAN.search(name):
        return False, "non-human"
    if tags.get("amenity") == "hospital" or tags.get("healthcare") == "hospital":
        return False, "hospital (covered by CMS data)"
    spec = tags.get("healthcare:speciality", "")
    if tags.get("urgent_care") == "yes":
        return True, "urgent_care=yes"
    if re.search(r"\burgent", spec):
        return True, "healthcare:speciality"
    if tags.get("healthcare") == "urgent_care" or tags.get("amenity") == "urgent_care":
        return True, "urgent_care tag"
    if re.search(r"urgent\s*care", name, re.I):
        return True, "name"
    return False, "no match"


def build_urgent_care(raw: Path) -> dict:
    out = {}
    for metro in METROS:
        path = raw / f"osm_{metro['id']}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        places, seen = [], set()
        for el in doc.get("elements", []):
            tags = el.get("tags", {})
            ok, why = is_urgent_care(tags)
            if not ok:
                continue
            lat = el.get("lat", el.get("center", {}).get("lat"))
            lon = el.get("lon", el.get("center", {}).get("lon"))
            if lat is None or lon is None:
                continue
            name = tags.get("name") or tags.get("brand") or "Urgent care (unnamed in OSM)"
            key = (name.lower(), round(lat, 3), round(lon, 3))
            if key in seen:
                continue
            seen.add(key)
            addr = " ".join(x for x in (tags.get("addr:housenumber", ""),
                                        tags.get("addr:street", "")) if x)
            city = tags.get("addr:city", "")
            places.append({
                "name": name, "lat": round(lat, 5), "lon": round(lon, 5),
                "address": ", ".join(x for x in (addr, city) if x),
                "hours": tags.get("opening_hours", ""),
                "osm": f"{el['type']}/{el['id']}", "match": why,
            })
        places.sort(key=lambda p: p["name"].lower())
        out[metro["id"]] = {
            "name": metro["name"], "zip": metro["zip"], "bbox": metro["bbox"],
            "osm_timestamp": doc.get("osm3s", {}).get("timestamp_osm_base", ""),
            "places": places,
        }
    return out


def trim_all(raw: Path, data: Path) -> dict:
    data.mkdir(parents=True, exist_ok=True)
    zcta = load_zcta(raw / "gazetteer_zcta.txt")
    with open(data / "zcta.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["zip", "lat", "lon"])
        for z in sorted(zcta):
            w.writerow([z, f"{zcta[z][0]:.3f}", f"{zcta[z][1]:.3f}"])

    hospitals, summary = build_hospitals(raw / "hospital_general_information.csv",
                                         raw / "timely_effective_care_hospital.csv", zcta)
    with open(data / "hospitals.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HOSPITAL_FIELDS)
        w.writeheader()
        w.writerows(hospitals)

    uc = build_urgent_care(raw)
    (data / "urgent_care.json").write_text(json.dumps(uc, indent=1), encoding="utf-8")

    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    ref = {
        "built": dt.date.today().isoformat(),
        "summary": summary,
        "national": read_national(raw / "timely_effective_care_national.csv"),
        "footnotes": read_footnotes(raw / "footnote_crosswalk.csv"),
        "sources": {
            "cms_metastore": "https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items",
            "cms": manifest["cms"],
            "gazetteer": manifest["gazetteer"],
            "overpass": {k: v["url"] for k, v in manifest["overpass"].items()},
            "red_flags": "https://medlineplus.gov/ency/patientinstructions/000593.htm",
        },
        "sigma": {"default": stats.SIGMA_DEFAULT, "low": stats.SIGMA_LOW,
                  "high": stats.SIGMA_HIGH},
    }
    (data / "reference.json").write_text(json.dumps(ref, indent=1), encoding="utf-8")
    return ref
