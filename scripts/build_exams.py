"""Exam outcomes per module -> public/data/exams.json

Source: TUM Exam Stats (https://stats.aamin.dev), which publishes TUM exam statistics
per module per sitting. We take only the factual outcome figures (how many sat, what
share failed, average grade), cite the source on every figure and link back.

These are exam facts, not opinions. They are kept strictly apart from the student
ratings: they never touch the stars, the student difficulty votes, or the "Top rated"
ranking. They power their own "Hardest exam" ordering, which is clearly labelled.

Usage: python3 scripts/fetch_exams.py && python3 scripts/build_exams.py
"""
import json, re, statistics, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = set(json.load(open(ROOT / "api/_keys.json")))
SRC = ROOT / "data/vendor/exam_stats.json"
if not SRC.exists():
    sys.exit("run scripts/fetch_exams.py first")

by_code = {}
for r in json.load(open(SRC)):
    if r["code"] not in KEYS or r.get("fail") is None or not r.get("att"): continue
    by_code.setdefault(r["code"], []).append(r)

out = {}
for code, rs in by_code.items():
    rs.sort(key=lambda r: r["date"])
    sat = sum(r["att"] for r in rs)
    if sat < 10: continue                      # too few candidates to mean anything
    fail = sum(r["fail"] * r["att"] for r in rs) / sat      # weighted by candidates
    grades = [r["avg"] for r in rs if r.get("avg")]
    out[code] = {
        "fail": round(fail, 1), "sat": sat, "sittings": len(rs),
        "avg": round(statistics.fmean(grades), 2) if grades else None,
        "first": rs[0]["date"][:7], "last": rs[-1]["date"][:7],
    }

(ROOT / "public/data/exams.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
hard = sorted(out.items(), key=lambda kv: -kv[1]["fail"])
print(f"{len(out)} modules with exam outcomes")
for c, v in hard[:5]: print(f"  {c:11} {v['fail']:5.1f}% failed, {v['sat']} sat, {v['sittings']} sittings")
