"""Build data/tracker_summary.json from data/tracker.csv (+ data/tracker_flags.txt).

Totals are computed from the CSV only; nothing is typed by hand.
  booked_inr / pipeline_inr per month for 2026-12 .. 2027-03 (baseline rows ignored)
  gap_inr = target_inr - booked_inr - pipeline_inr
Flags: one per line in data/tracker_flags.txt (lines starting with "FLAG:").
Usage: python3 -I analysis/build_tracker_summary.py
"""
import csv
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSV_P = ROOT / "data" / "tracker.csv"
FLAGS_P = ROOT / "data" / "tracker_flags.txt"
OUT_P = ROOT / "data" / "tracker_summary.json"

TARGET_INR = 1_000_000_000  # Rs 25 Cr x 4 months (Dec 2026 - Mar 2027)
MONTHS = ["2026-12", "2027-01", "2027-02", "2027-03"]
COLS = ["month", "type", "customer", "product", "qty_kg", "value_inr", "date", "source"]


def main() -> int:
    with CSV_P.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLS:
            print(f"bad columns: {reader.fieldnames}")
            return 1
        rows = list(reader)

    months = {m: {"booked_inr": 0.0, "pipeline_inr": 0.0} for m in MONTHS}
    counts = {"booked": 0, "pipeline": 0, "baseline": 0}
    for n, r in enumerate(rows, start=2):
        t, m = r["type"], r["month"]
        if t not in counts:
            print(f"line {n}: bad type {t!r}")
            return 1
        counts[t] += 1
        if t == "baseline":
            continue
        if m not in months:
            print(f"line {n}: month {m!r} outside Dec-Mar")
            return 1
        months[m][f"{t}_inr"] += float(r["value_inr"])

    flags = []
    if FLAGS_P.exists():
        flags = [l.strip() for l in FLAGS_P.read_text().splitlines() if l.strip().startswith("FLAG:")]

    booked = sum(v["booked_inr"] for v in months.values())
    pipeline = sum(v["pipeline_inr"] for v in months.values())
    summary = {
        "target_inr": TARGET_INR,
        "months": {m: {k: round(v, 2) for k, v in d.items()} for m, d in months.items()},
        "booked_inr": round(booked, 2),
        "pipeline_inr": round(pipeline, 2),
        "gap_inr": round(TARGET_INR - booked - pipeline, 2),
        "row_counts": counts,
        "flags": flags,
    }
    OUT_P.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    cr = 10_000_000
    for m, d in months.items():
        print(f"{m}: booked {d['booked_inr']/cr:.2f} Cr, pipeline {d['pipeline_inr']/cr:.2f} Cr")
    print(f"total: booked {booked/cr:.2f} Cr, pipeline {pipeline/cr:.2f} Cr, "
          f"gap {summary['gap_inr']/cr:.2f} Cr; rows {counts}; flags {len(flags)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
