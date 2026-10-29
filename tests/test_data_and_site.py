"""Checks on the committed caches, the generated site, the charts and the PDF."""
import csv
import json
from pathlib import Path

import pypdf
import pytest

from conftest import DATA, ROOT, SITE, run_node
from eruc import stats
from eruc.charts import build_charts
from eruc.onepager import build_pdf
from eruc.site import build_site, read_data_js


@pytest.fixture(scope="module")
def hospitals():
    with open(DATA / "hospitals.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_caches_are_small_and_consistent(hospitals, reference):
    total = sum(p.stat().st_size for p in DATA.glob("*.*"))
    assert total < 5_000_000
    s = reference["summary"]
    assert len(hospitals) == s["n_hospitals"]
    numeric = [h for h in hospitals if h["op18b"] != "Not Available"]
    assert len(numeric) == s["n_op18b_numeric"]
    assert all(h["op18b"].isdigit() for h in numeric)
    assert all(len(h["zip"]) == 5 for h in hospitals)
    assert s["periods"]["OP_18b"]["end"] == "09/30/2025"
    assert reference["national"]["OP_18b"]["score"].isdigit()
    # Every Not Available row's footnote codes resolve to CMS text.
    for h in hospitals:
        for code in filter(None, (c.strip() for c in h["op18b_footnote"].split(","))):
            assert code in reference["footnotes"]


def test_committed_percentiles_recompute(hospitals):
    vals = [float(h["op18b"]) for h in hospitals if h["op18b"].isdigit()]
    h = next(x for x in hospitals if x["op18b"].isdigit())
    x = float(h["op18b"])
    others = list(vals)
    others.remove(x)
    assert float(h["pct_shorter_nation"]) == round(100 * stats.share_longer(x, others), 1)


def test_urgent_care_cache(reference):
    uc = json.loads((DATA / "urgent_care.json").read_text(encoding="utf-8"))
    assert set(uc) == {"ithaca", "nyc", "bayarea", "miami", "chicago"}
    for metro in uc.values():
        assert metro["osm_timestamp"]
        for p in metro["places"]:
            assert "wait" not in json.dumps(p).lower()  # no invented wait numbers
            s, w, n, e = metro["bbox"]
            assert s <= p["lat"] <= n and w <= p["lon"] <= e


def test_build_site_roundtrip(tmp_path):
    out = build_site(DATA, tmp_path)
    d = read_data_js(out)
    assert set(d) == {"hospitals", "zcta", "urgentCare", "reference"}
    assert d["zcta"]["02139"] and len(d["zcta"]) > 30000
    assert out.stat().st_size < 3_000_000
    committed = read_data_js(SITE / "data.js")
    assert committed == d, "site/data.js is stale: run `make site`"


def test_page_has_required_disclosures():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    for needle in ("OpenStreetMap contributors", "openstreetmap.org/copyright", "not medical advice",
                   "ZIP-centroid distance", "No public source publishes urgent-care wait times",
                   "tel:911", "tel:988", "medlineplus.gov"):
        assert needle.lower() in html.lower(), needle
    assert "http" not in "".join(l for l in html.splitlines() if "<script" in l)  # no remote scripts


def test_core_js_matches_python():
    v = run_node(ROOT / "tests" / "js" / "core_values.js", SITE / "core.js")
    for m, s, p, q in v["quantile"]:
        assert q == pytest.approx(stats.lognormal_quantile(m, s, p), rel=1e-6)
    for m, s, t, e in v["exceed"]:
        assert e == pytest.approx(stats.lognormal_exceed(m, s, t), abs=1e-6)
    for m, s, n, se in v["se"]:
        assert se == pytest.approx(stats.median_se(m, s, n))
    assert v["miles"] == pytest.approx(stats.haversine_miles(40.7128, -74.006, 41.8781, -87.6298))
    t = v["triage"]
    assert t["none"]["level"] == "none" and t["uc"]["level"] == "urgent" and t["uc"]["showWaits"]
    assert t["er"]["level"] == "er" and not t["er"]["showWaits"]
    assert t["e911"]["level"] == "call911"
    assert t["crisis"]["level"] == "crisis" and t["both"]["level"] == "call911" and t["both"]["crisis"]
    assert v["zip"] == ["14850", "02139", "94539", None, None, None]
    levels = {s["level"] for s in v["symptoms"]}
    assert levels == {"call911", "crisis", "er", "urgent"}


def test_page_renders_ithaca_urgent_case():
    r = run_node(ROOT / "tests" / "js" / "app_smoke.js", SITE, "#zip=14850&check=cold")
    assert r["checklistCount"] >= 15 and r["metroChips"] == 5
    assert r["verdictClass"] == "verdict v-urgent"
    assert not r["resultsHidden"] and not r["demoted"]
    assert "Cayuga Medical Center At Ithaca" in r["hospitals"]
    assert "4 h 4 min" in r["hospitals"]  # OP-18b 244 minutes
    assert "assumed" in r["hospitals"] and "ZIP-centroid distance" in r["hospitals"]
    assert "WellNow Urgent Care" in r["urgent"] and "no public data" in r["urgent"]
    assert r["sigmaOut"] == "0.90" and r["hospitalsAfterSigma"] != r["hospitals"]


def test_page_red_flag_demotes_waits():
    r = run_node(ROOT / "tests" / "js" / "app_smoke.js", SITE, "#zip=60611&check=sprain,chest")
    assert r["verdictClass"] == "verdict v-call911" and "Call 911" in r["verdict"]
    assert r["demoted"]


def test_page_outside_demo_metros_and_bad_zip():
    r = run_node(ROOT / "tests" / "js" / "app_smoke.js", SITE, "#zip=59801")  # Missoula, MT
    assert "cached only for the demo areas" in r["urgent"]
    assert r["hospitals"].count("<article") >= 3
    bad = run_node(ROOT / "tests" / "js" / "app_smoke.js", SITE, "#zip=00000")
    assert "not in the Census" in bad["zipError"] and bad["resultsHidden"]


def test_not_available_rows_show_footnote():
    r = run_node(ROOT / "tests" / "js" / "app_smoke.js", SITE, "#zip=94539")
    assert "Not Available" in r["hospitals"] and "CMS footnote" in r["hospitals"]


def test_charts_and_one_page_pdf(tmp_path):
    for p in build_charts(DATA, tmp_path):
        assert p.stat().st_size > 10_000
    pdf = build_pdf(DATA, tmp_path / "one.pdf")
    assert len(pypdf.PdfReader(pdf).pages) == 1
    assert len(pypdf.PdfReader(ROOT / "docs" / "ER-or-Urgent-Care.pdf").pages) == 1
    text = pypdf.PdfReader(pdf).pages[0].extract_text()
    assert "assumption" in text and "OpenStreetMap" in text
