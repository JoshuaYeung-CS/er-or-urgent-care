"""Pipeline logic on tiny hand-written fixtures (no network, no real files)."""
import csv
import json

from eruc import trim
from eruc.fetch import cms_distributions

HGI_COLS = ["Facility ID", "Facility Name", "Address", "City/Town", "State", "ZIP Code",
            "Telephone Number", "Hospital Type", "Hospital Ownership", "Emergency Services"]
TEC_COLS = ["Facility ID", "Condition", "Measure ID", "Score", "Sample", "Footnote", "Start Date", "End Date"]


def _write(path, cols, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(dict(zip(cols, r)))


def _fixture(tmp_path):
    hgi = tmp_path / "hgi.csv"
    tec = tmp_path / "tec.csv"
    _write(hgi, HGI_COLS, [
        ["A1", "ALPHA", "1 MAIN", "BOSTON", "MA", "02139", "", "Acute Care Hospitals", "x", "Yes"],
        ["B2", "BETA", "2 MAIN", "BOSTON", "MA", "02140", "", "Acute Care Hospitals", "x", "Yes"],
        ["C3", "GAMMA", "3 MAIN", "ITHACA", "NY", "14850", "", "Acute Care Hospitals", "x", "Yes"],
        ["D4", "DELTA", "PO BOX", "NOWHERE", "NY", "14999", "", "Critical Access Hospitals", "x", "No"],
        ["E5", "NO ED ROWS", "", "", "NY", "14850", "", "Psychiatric", "x", "No"],
    ])
    per = ["10/01/2024", "09/30/2025"]
    _write(tec, TEC_COLS, [
        ["A1", "Emergency Department", "OP_18b", "120", "400", "", *per],
        ["A1", "Emergency Department", "EDV", "high", "", "", "01/01/2024", "12/31/2024"],
        ["B2", "Emergency Department", "OP_18b", "200", "380", "", *per],
        ["C3", "Emergency Department", "OP_18b", "150", "300", "3", *per],
        ["D4", "Emergency Department", "OP_18b", "Not Available", "", "5", *per],
        ["A1", "Heart Attack", "OP_18b", "999", "", "", *per],  # wrong condition: ignored
    ])
    zcta = {"02139": (42.364, -71.104), "02140": (42.392, -71.133), "14850": (42.448, -76.497)}
    return hgi, tec, zcta


def test_hospital_rows_join_and_rank(tmp_path):
    rows, summary = trim.build_hospitals(*_fixture(tmp_path))
    by = {r["id"]: r for r in rows}
    assert set(by) == {"A1", "B2", "C3", "D4"}  # E5 has no ED measures
    assert by["A1"]["zip"] == "02139"  # leading zero kept
    assert by["A1"]["lat"] == 42.364 and by["A1"]["loc"] == "zcta"
    assert by["D4"]["loc"] == "none" and by["D4"]["lat"] == ""
    assert by["D4"]["op18b"] == "Not Available" and by["D4"]["op18b_footnote"] == "5"
    assert by["C3"]["op18b_footnote"] == "3"
    assert by["A1"]["edv"] == "high" and by["B2"]["edv"] == "Not Available"
    # 120 is the shortest of three numeric values: shorter than both other hospitals.
    assert by["A1"]["pct_shorter_nation"] == 100.0
    assert by["C3"]["pct_shorter_nation"] == 50.0
    assert by["B2"]["pct_shorter_nation"] == 0.0
    assert by["A1"]["pct_shorter_state"] == 100.0 and by["B2"]["pct_shorter_state"] == 0.0
    assert by["C3"]["pct_shorter_state"] == ""  # only numeric hospital in NY: no comparison
    assert by["D4"]["pct_shorter_state"] == ""
    assert summary["n_op18b_numeric"] == 3 and summary["n_op18b_not_available"] == 1
    assert summary["n_no_zcta_match"] == 1
    assert summary["periods"]["OP_18b"] == {"start": "10/01/2024", "end": "09/30/2025"}


def test_urgent_care_classifier():
    yes = [
        {"amenity": "clinic", "healthcare": "clinic", "healthcare:speciality": "urgent_care"},
        {"amenity": "clinic", "urgent_care": "yes", "name": "Corner Clinic"},
        {"healthcare": "clinic", "name": "WellNow Urgent Care"},
        {"healthcare": "clinic", "healthcare:speciality": "urgent"},
    ]
    no = [
        {"amenity": "veterinary", "name": "Bishop Ranch Veterinary Center & Urgent Care"},
        {"name": "Sploot Pet Urgent Care"},
        {"amenity": "hospital", "urgent_care": "yes", "name": "Big Hospital"},
        {"amenity": "clinic", "name": "Family Practice"},
    ]
    assert all(trim.is_urgent_care(t)[0] for t in yes)
    assert not any(trim.is_urgent_care(t)[0] for t in no)


def test_build_urgent_care_dedupes_and_uses_way_centers(tmp_path, monkeypatch):
    monkeypatch.setattr(trim, "METROS", [{"id": "t", "name": "Test", "zip": "00000", "bbox": (0, 0, 1, 1)}])
    doc = {"osm3s": {"timestamp_osm_base": "2026-10-29T00:00:00Z"}, "elements": [
        {"type": "node", "id": 1, "lat": 0.5, "lon": 0.5, "tags": {"name": "A Urgent Care"}},
        {"type": "way", "id": 2, "center": {"lat": 0.50001, "lon": 0.50001}, "tags": {"name": "A Urgent Care"}},
        {"type": "way", "id": 3, "center": {"lat": 0.2, "lon": 0.3},
         "tags": {"name": "B Urgent Care", "addr:housenumber": "5", "addr:street": "Elm St",
                  "opening_hours": "Mo-Su 08:00-20:00"}},
        {"type": "node", "id": 4, "lat": 0.1, "lon": 0.1, "tags": {"name": "Pet Urgent Care"}},
    ]}
    (tmp_path / "osm_t.json").write_text(json.dumps(doc))
    out = trim.build_urgent_care(tmp_path)["t"]
    assert [p["name"] for p in out["places"]] == ["A Urgent Care", "B Urgent Care"]
    b = out["places"][1]
    assert b["address"] == "5 Elm St" and b["hours"].startswith("Mo-Su") and b["osm"] == "way/3"
    assert out["osm_timestamp"].startswith("2026-10-29")


def test_metastore_lookup_by_title(tmp_path):
    items = [{"title": t, "identifier": f"id{i}", "modified": "2026-07-22",
              "distribution": [{"downloadURL": f"https://example.org/{i}.csv"}]}
             for i, t in enumerate(["Hospital General Information", "Timely and Effective Care - Hospital",
                                    "Timely and Effective Care - National", "Footnote Crosswalk", "Other"])]
    p = tmp_path / "meta.json"
    p.write_text(json.dumps(items))
    found = cms_distributions(p)
    assert found["Footnote Crosswalk"]["url"] == "https://example.org/3.csv"
    assert "Other" not in found
