"""Command line: python -m eruc {fetch,trim,site,charts,pdf,build,all}."""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="eruc")
    ap.add_argument("step", choices=["fetch", "trim", "site", "charts", "pdf", "build", "all"])
    ap.add_argument("--refresh", action="store_true", help="re-download even if cached")
    args = ap.parse_args(argv)

    if args.step in ("fetch", "all"):
        from .fetch import fetch_all
        fetch_all(RAW, refresh=args.refresh)
        print("fetched raw data into", RAW)
    if args.step in ("trim", "all"):
        from .trim import trim_all
        ref = trim_all(RAW, DATA)
        s = ref["summary"]
        print(f"hospitals with ED rows: {s['n_hospitals']}  numeric OP-18b: {s['n_op18b_numeric']}"
              f"  no ZCTA match: {s['n_no_zcta_match']}")
    if args.step in ("site", "build", "all"):
        from .site import build_site
        print("wrote", build_site(DATA, ROOT / "site"))
    if args.step in ("charts", "build", "all"):
        from .charts import build_charts
        for p in build_charts(DATA, ROOT / "docs"):
            print("wrote", p)
    if args.step in ("pdf", "build", "all"):
        from .onepager import build_pdf
        print("wrote", build_pdf(DATA, ROOT / "docs" / "ER-or-Urgent-Care.pdf"))


if __name__ == "__main__":
    main()
