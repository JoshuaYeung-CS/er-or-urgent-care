"""The one-page project description PDF required by DSH Hacks V2."""
from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .charts import chart_assumed_spread, chart_by_volume, chart_distribution

TEAL = colors.HexColor("#0b6e79")
INK = colors.HexColor("#17202a")
MUTED = colors.HexColor("#55606e")
REPO = "github.com/JoshuaYeung-CS/er-or-urgent-care"


def _styles():
    base = dict(fontName="Helvetica", fontSize=9.6, leading=12.8, textColor=INK)
    return {
        "title": ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=19, leading=22, textColor=TEAL),
        "tag": ParagraphStyle("g", fontName="Helvetica", fontSize=10, leading=13, textColor=MUTED),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.6, leading=13, textColor=TEAL,
                            spaceBefore=7, spaceAfter=1),
        "p": ParagraphStyle("p", **base),
        "small": ParagraphStyle("s", fontName="Helvetica", fontSize=8.2, leading=10.4, textColor=MUTED),
    }


def build_pdf(data: Path, out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    ref = json.loads((data / "reference.json").read_text(encoding="utf-8"))
    s = ref["summary"]
    p18 = s["periods"]["OP_18b"]
    q = s["op18b_hospital_quantiles"]
    nat = ref["national"]
    st = _styles()

    dist_png = chart_distribution(data, out.parent / "op18b-distribution.png")
    spread_png = chart_assumed_spread(data, out.parent / "assumed-spread.png")
    vol_png = chart_by_volume(data, out.parent / "by-volume.png")

    def P(text, style="p"):
        return Paragraph(text, st[style])

    left = [
        P("The problem", "h"),
        P("At 11 pm with a sprained wrist or a feverish kid, people choose between the ER and urgent care "
          "with almost no information. Hospital ED times are public (CMS publishes them), but as raw CSV "
          "columns with codes nobody outside health policy can read, and with no hint of uncertainty."),
        P("What it does", "h"),
        P("1. A short checklist of red-flag signs, paraphrased from MedlinePlus. Any chest pain, stroke sign, "
          "trouble breathing or similar check turns the page into a large <b>Call 911</b> message and greys "
          "out the wait numbers, because those do not apply to emergencies.<br/>"
          "2. For any US ZIP: the nearest emergency departments with CMS's median visit time, a range "
          "of plausible visit lengths, the chance of going over 4 hours, and where that hospital ranks in "
          "its state and nationally.<br/>"
          "3. Nearby urgent-care clinics from OpenStreetMap for five demo areas, labelled honestly: "
          "<b>no public source publishes urgent-care waits</b>, so none are invented."),
        P("Honest statistics", "h"),
        P(f"OP-18b is one number per hospital: the median minutes from arrival to departure for patients "
          f"sent home ({p18['start']} to {p18['end']}). It is <i>not</i> time-to-be-seen and not live. CMS "
          f"publishes no spread, so any range is an assumption: I model a visit as lognormal with the median "
          f"pinned to OP-18b and dispersion σ = 0.6 (0.4 to 0.8 shown as a band; a slider lets the reader "
          f"move it). Every assumed number carries an \"assumed\" label. Rankings are computed from the data: "
          f"{s['n_op18b_numeric']:,} hospitals report a value, {s['n_op18b_not_available']:,} show "
          f"\"Not Available\" with the CMS footnote explaining why."),
        P("Why it matters", "h"),
        P("Not every urgent problem is an emergency, and the ones that are should never wait on a comparison. "
          "The design puts safety first, then gives non-emergency patients a calibrated sense of time: "
          "the published median as fact, the spread as a clearly marked, adjustable assumption."),
        P("What's next", "h"),
        P("Join hour-of-day arrival patterns if a public source appears; add drive time; ask urgent-care "
          "chains to publish wait data in an open format; Spanish translation of the checklist."),
        P("Built with", "h"),
        P("Python (csv, statistics) for the data pipeline; matplotlib and reportlab for figures and this page; "
          "a static HTML/CSS/JavaScript site with all data inlined, so it runs offline from a file and nothing "
          "a user types leaves the device. pytest suite covers the statistics, the triage rules, the data "
          "joins and this page's length."),
    ]
    right = [
        Image(str(dist_png), width=3.45 * inch, height=3.45 * inch * 3.4 / 7.2),
        P(f"Across hospitals: 10th pct {q['p10']:.0f} min, median {q['p50']:.0f}, 90th pct {q['p90']:.0f}. "
          f"CMS national figure {nat['OP_18b']['score']} min. Busier EDs run longer: national medians "
          f"{nat['OP_18b_LOW_MIN']['score']} min (low volume) vs {nat['OP_18b_VERY_HIGH_MIN']['score']} min (very high).",
          "small"),
        Spacer(1, 5),
        Image(str(spread_png), width=3.45 * inch, height=3.45 * inch * 3.2 / 7.2),
        P("The same 165-minute median under three assumed spreads. The page shows the band, not one "
          "confident number.", "small"),
        P("Data sources", "h"),
        P("CMS Provider Data Catalog (data.cms.gov): Timely and Effective Care - Hospital, Hospital General "
          "Information, Timely and Effective Care - National, Footnote Crosswalk; dataset URLs taken from the "
          "CMS metastore. US Census 2025 ZCTA Gazetteer for ZIP centroids (distances are ZIP-centroid, "
          "straight-line). Urgent care: © OpenStreetMap contributors (ODbL), one cached Overpass query per "
          "metro. Red flags: MedlinePlus, <i>When to use the emergency room - adult</i>.", "small"),
        P("Limits", "h"),
        P(f"Year-old medians, not live. ZIP-centroid distance, not drive time ({s['n_no_zcta_match']} hospitals "
          "with non-ZCTA ZIPs omitted from distance results). OpenStreetMap urgent-care coverage is incomplete. "
          "Not medical advice; in an emergency, call 911.", "small"),
        Spacer(1, 6),
        Image(str(vol_png), width=3.45 * inch, height=3.45 * inch * 3.0 / 7.2),
    ]
    body = Table([[left, right]], colWidths=[3.85 * inch, 3.55 * inch])
    body.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (0, 0), 12),
        ("RIGHTPADDING", (1, 0), (1, 0), 0),
    ]))
    story = [
        P("ER or Urgent Care?", "title"),
        P("Public hospital emergency-department times, explained with the uncertainty left in. "
          "Joshua Yeung · DSH Hacks V2, AI x Healthcare · " + REPO, "tag"),
        Spacer(1, 6),
        body,
    ]
    doc = SimpleDocTemplate(str(out), pagesize=letter, leftMargin=0.55 * inch, rightMargin=0.55 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.45 * inch,
                            title="ER or Urgent Care?", author="Joshua Yeung")
    doc.build(story)
    return out
