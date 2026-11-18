"""Done-check for task 1: sales tracker vs ₹25 Cr/month, ₹100 Cr Dec 2026–Mar 2027.

data/tracker.csv columns (exact):
  month,type,customer,product,qty_kg,value_inr,date,source
  month  : 2026-11 (baseline only), 2026-12, 2027-01, 2027-02, 2027-03
  type   : booked | pipeline | baseline   (baseline = Nov run-rate, not counted)
  source : Drive URL (https://docs.google.com/... or https://drive.google.com/...)
           or Gmail id written as gmail:<message-or-thread-id>
data/tracker_summary.json:
  {"target_inr": 1000000000, "months": {"2026-12": {"booked_inr":..,"pipeline_inr":..}, ...},
   "booked_inr":.., "pipeline_inr":.., "gap_inr":.., "flags":[...]}
The check recomputes every total from the CSV; the summary must match to the rupee.
"""
import csv
import json
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parent.parent
CR = 10_000_000
MONTHS = ["2026-12", "2027-01", "2027-02", "2027-03"]
MONTH_TARGET = 25 * CR
TARGET = 100 * CR
COLS = ["month", "type", "customer", "product", "qty_kg", "value_inr", "date", "source"]
SRC = re.compile(r"^(https://(docs|drive)\.google\.com/\S+|gmail:[A-Za-z0-9_-]+)$")
errors = []

csv_p, sum_p = root / "data/tracker.csv", root / "data/tracker_summary.json"
if not csv_p.exists() or not sum_p.exists():
    print("missing data/tracker.csv or data/tracker_summary.json")
    sys.exit(1)

assert MONTH_TARGET * len(MONTHS) == TARGET
with csv_p.open(newline="") as f:
    r = csv.DictReader(f)
    if r.fieldnames != COLS:
        errors.append(f"columns must be exactly {COLS}, got {r.fieldnames}")
    rows = list(r)

totals = {m: {"booked_inr": 0, "pipeline_inr": 0} for m in MONTHS}
counted = 0
for n, row in enumerate(rows, start=2):
    where = f"tracker.csv line {n}"
    t, m = row.get("type", ""), row.get("month", "")
    if t not in ("booked", "pipeline", "baseline"):
        errors.append(f"{where}: bad type {t!r}")
        continue
    if t == "baseline" and m != "2026-11":
        errors.append(f"{where}: baseline rows must be month 2026-11")
    if t != "baseline" and m not in MONTHS:
        errors.append(f"{where}: month {m!r} outside Dec 2026–Mar 2027")
    for k in ("customer", "product", "date"):
        if not row.get(k, "").strip():
            errors.append(f"{where}: empty {k}")
    if not SRC.match(row.get("source", "").strip()):
        errors.append(f"{where}: source must be a Drive URL or gmail:<id>, got {row.get('source')!r}")
    try:
        v = float(row["value_inr"])
        if v <= 0:
            raise ValueError
    except (ValueError, KeyError, TypeError):
        errors.append(f"{where}: value_inr must be a positive number")
        continue
    if t != "baseline" and m in totals:
        totals[m][f"{t}_inr"] += v
        counted += 1

if counted == 0:
    errors.append("no booked or pipeline rows for Dec–Mar; if none exist, report blocked, don't ship empty")

try:
    s = json.loads(sum_p.read_text())
except Exception as e:
    print(f"tracker_summary.json unreadable: {e}")
    sys.exit(1)

def close(a, b):
    return abs(float(a) - float(b)) < 1

booked = sum(t["booked_inr"] for t in totals.values())
pipeline = sum(t["pipeline_inr"] for t in totals.values())
gap = TARGET - booked - pipeline
if s.get("target_inr") != TARGET:
    errors.append(f"target_inr must be {TARGET}")
for key, val in (("booked_inr", booked), ("pipeline_inr", pipeline), ("gap_inr", gap)):
    if key not in s or not close(s[key], val):
        errors.append(f"summary {key}={s.get(key)} but CSV gives {val:.0f}")
for m in MONTHS:
    sm = s.get("months", {}).get(m, {})
    for key in ("booked_inr", "pipeline_inr"):
        if key not in sm or not close(sm[key], totals[m][key]):
            errors.append(f"summary months.{m}.{key}={sm.get(key)} but CSV gives {totals[m][key]:.0f}")
if not close(booked + pipeline + gap, TARGET):
    errors.append("booked + pipeline + gap != ₹100 Cr")
if not isinstance(s.get("flags"), list):
    errors.append("summary must carry a flags list (empty list if none)")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"tracker ok: booked ₹{booked/CR:.2f} Cr, pipeline ₹{pipeline/CR:.2f} Cr, gap ₹{gap/CR:.2f} Cr")
