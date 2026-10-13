"""Offering history per module -> public/data/offerings.json

Source: data/vendor/all_offered_courses_*.json, from
Vuenc/TUM-Master-Informatics-Offered-Lectures (MIT, Vincent Bürgin), scraped from TUMonline.
Each record is one course instance in one semester, with the module code inside the title,
e.g. "Machine Learning (IN2064)". We keep facts only: which semesters a module ran.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = set(json.load(open(ROOT / "api/_keys.json")))
CODE = re.compile(r"\(([A-Z]{2,4}\d{3,}\w*)\)")
TERM = re.compile(r"^(SS|WS)(\d{2})")

def term_key(t):
    m = TERM.match(t)
    if not m: return (0, 0)
    year = 2000 + int(m[2])
    return (year, 1 if m[1] == "SS" else 2)   # SS comes before WS within a year

def pretty(t):
    m = TERM.match(t)
    return f"{m[1]} {2000 + int(m[2])}" if m else t

# titles carry the module code only 45% of the time; fall back to an exact
# normalised title match against the curriculum trees, skipping ambiguous titles
def norm(s): return re.sub(r"[^a-z0-9]", "", re.sub(r"\([^)]*\)", "", s.lower()))

by_title = {}
for f in sorted((ROOT / "data/trees").glob("*.json")):
    def walk(n):
        if n["code"] in KEYS: by_title.setdefault(norm(n["name"]), set()).add(n["code"])
        for c in n["children"]: walk(c)
    for r in json.load(open(f))["roots"]: walk(r)

hist = {}
for f in sorted((ROOT / "data/vendor").glob("all_offered_courses_*.json")):
    for c in json.load(open(f))["courses"]:
        term, title = c.get("termName") or "", c.get("title") or ""
        if not TERM.match(term): continue
        codes = [x for x in CODE.findall(title) if x in KEYS]
        if not codes:
            match = by_title.get(norm(title), ())
            if len(match) == 1: codes = list(match)
        for code in codes: hist.setdefault(code, set()).add(term)

out = {}
for code, terms in hist.items():
    ts = sorted(terms, key=term_key)
    out[code] = {"n": len(ts), "first": pretty(ts[0]), "last": pretty(ts[-1]), "lastKey": term_key(ts[-1])[0] * 10 + term_key(ts[-1])[1]}

(ROOT / "public/data/offerings.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
newest = max((v["lastKey"] for v in out.values()), default=0)
recent = sum(1 for v in out.values() if v["lastKey"] >= newest - 20)   # within ~2 years
print(f"{len(out)} modules with offering history ({len(out) / len(KEYS):.0%} of {len(KEYS)} keys)")
print(f"  offered in the last ~2 years: {recent}")
print(f"  median semesters offered: {sorted(v['n'] for v in out.values())[len(out)//2]}")
