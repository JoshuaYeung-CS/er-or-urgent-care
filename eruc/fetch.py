"""Download the raw public data into data/raw/ (gitignored).

Everything goes through curl. Dataset URLs are never hard-coded for CMS: the
script reads the CMS Provider Data metastore and takes the CSV distribution of
each dataset by its exact title, so a quarterly refresh picks up new files.

Overpass is queried once per demo metro, sequentially, with a pause between
calls, and a cached file is never re-requested.
"""
from __future__ import annotations

import json
import subprocess
import time
import zipfile
from pathlib import Path

from .metros import METROS, overpass_query

METASTORE = "https://data.cms.gov/provider-data/api/1/metastore/schemas/dataset/items"
CMS_TITLES = {
    "Hospital General Information": "hospital_general_information.csv",
    "Timely and Effective Care - Hospital": "timely_effective_care_hospital.csv",
    "Timely and Effective Care - National": "timely_effective_care_national.csv",
    "Footnote Crosswalk": "footnote_crosswalk.csv",
}
GAZETTEER = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
             "2025_Gazetteer/2025_Gaz_zcta_national.zip")
OVERPASS = "https://overpass-api.de/api/interpreter"
USER_AGENT = "er-or-urgent-care-prefetch/0.1 (student hackathon project)"


def curl(url: str, out: Path, data: str | None = None) -> None:
    cmd = ["curl", "-sSfL", "--retry", "2", "-m", "300", "-A", USER_AGENT, "-o", str(out)]
    if data is not None:
        cmd += ["--data-urlencode", f"data={data}"]
    subprocess.run(cmd + [url], check=True)


def cms_distributions(metastore_path: Path) -> dict[str, dict]:
    items = json.loads(metastore_path.read_text(encoding="utf-8"))
    found = {}
    for item in items:
        title = item.get("title", "")
        if title in CMS_TITLES:
            dists = item.get("distribution") or []
            urls = [d.get("downloadURL") for d in dists if d.get("downloadURL", "").endswith(".csv")]
            if urls:
                found[title] = {"url": urls[0], "identifier": item.get("identifier"),
                                "modified": item.get("modified")}
    missing = set(CMS_TITLES) - set(found)
    if missing:
        raise RuntimeError(f"metastore has no CSV for: {sorted(missing)}")
    return found


def fetch_all(raw: Path, refresh: bool = False) -> dict:
    raw.mkdir(parents=True, exist_ok=True)
    meta = raw / "metastore.json"
    if refresh or not meta.exists():
        curl(METASTORE, meta)
    dists = cms_distributions(meta)
    manifest = {"cms": {}, "gazetteer": GAZETTEER, "overpass": {}}
    for title, fname in CMS_TITLES.items():
        out = raw / fname
        if refresh or not out.exists():
            curl(dists[title]["url"], out)
        manifest["cms"][title] = {**dists[title], "file": fname}

    gz = raw / "gazetteer_zcta.zip"
    if refresh or not gz.exists():
        curl(GAZETTEER, gz)
    with zipfile.ZipFile(gz) as z:
        name = [n for n in z.namelist() if n.endswith(".txt")][0]
        (raw / "gazetteer_zcta.txt").write_bytes(z.read(name))

    first = True
    for metro in METROS:
        out = raw / f"osm_{metro['id']}.json"
        q = overpass_query(metro["bbox"])
        manifest["overpass"][metro["id"]] = {"url": OVERPASS, "query": q}
        if out.exists() and not refresh:
            continue
        if not first:
            time.sleep(10)
        first = False
        try:
            curl(OVERPASS, out, data=q)
        except subprocess.CalledProcessError:
            time.sleep(30)  # one polite retry for a busy server
            curl(OVERPASS, out, data=q)
    (raw / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
