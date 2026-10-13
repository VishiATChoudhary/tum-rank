"""data/digests.tsv -> public/data/digests.json

Short summaries, in our own words, of what public discussion says about a course.
They are shown in their own labelled block and never contribute to the ratings,
the difficulty average or the ranking: those come only from people who rated here.
"""
import json, re, sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
KEYS = set(json.load(open(ROOT / "api/_keys.json")))
SRC = ROOT / "data/digests.tsv"

out, bad = {}, []
for ln, raw in enumerate(SRC.read_text().splitlines(), 1):
    if not raw.strip() or raw.lstrip().startswith("#"): continue
    p = [x.strip() for x in raw.split("\t")]
    if len(p) < 3: bad.append((ln, "need code, summary, url")); continue
    code, summary, url, date = p[0], p[1], p[2], (p[3] if len(p) > 3 else "")
    if code not in KEYS: bad.append((ln, f"unknown module {code}")); continue
    if urlparse(url).scheme != "https": bad.append((ln, f"bad url {url}")); continue
    if len(summary) > 600: bad.append((ln, "summary over 600 chars")); continue
    # a summary must be ours, not a pasted comment: no long verbatim runs in quotes
    for q in re.findall(r'"([^"]+)"', summary):
        if len(q.split()) > 12: bad.append((ln, f"quoted run too long: {q[:40]}…")); break
    out.setdefault(code, []).append({"summary": summary, "url": url, "date": date,
                                     "src": urlparse(url).netloc.replace("www.", "")})

(ROOT / "public/data/digests.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(f"{sum(len(v) for v in out.values())} summaries across {len(out)} courses")
for ln, why in bad: print(f"  line {ln}: {why}", file=sys.stderr)
sys.exit(1 if bad else 0)
