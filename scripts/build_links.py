"""Build public/data/links.json from data/links.tsv.

links.tsv is tab-separated, one discussion per line, '#' starts a comment:
    MODULE_CODE <TAB> URL <TAB> TITLE <TAB> YYYY-MM <TAB> SOURCE

Only links are stored. Never copy review text from a source we do not own or
that is not openly licensed: see SECURITY.md and the note in README.
"""
import json, re, sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
KEYS = set(json.load(open(ROOT / "api/_keys.json")))
SRC = ROOT / "data/links.tsv"
OK_SCHEME = {"https"}

out, bad = {}, []
for ln, raw in enumerate(SRC.read_text().splitlines() if SRC.exists() else [], 1):
    if not raw.strip() or raw.lstrip().startswith("#"): continue
    parts = [p.strip() for p in raw.split("\t") if p.strip() != ""]
    if len(parts) < 3: bad.append((ln, "need at least code, url, title")); continue
    code, url, title = parts[0], parts[1], parts[2]
    date = parts[3] if len(parts) > 3 else ""
    u = urlparse(url)
    if code not in KEYS: bad.append((ln, f"unknown module code {code}")); continue
    if u.scheme not in OK_SCHEME or not u.netloc: bad.append((ln, f"bad url {url}")); continue
    if date and not re.fullmatch(r"\d{4}(-\d{2})?", date): bad.append((ln, f"bad date {date}")); continue
    if len(title) > 120: title = title[:117] + "…"
    src = parts[4] if len(parts) > 4 else u.netloc.replace("www.", "")
    out.setdefault(code, []).append({"url": url, "title": title, "date": date, "src": src})

for v in out.values(): v.sort(key=lambda d: d["date"], reverse=True)
(ROOT / "public/data/links.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(f"{sum(len(v) for v in out.values())} links across {len(out)} courses")
for ln, why in bad: print(f"  line {ln}: {why}", file=sys.stderr)
sys.exit(1 if bad else 0)
