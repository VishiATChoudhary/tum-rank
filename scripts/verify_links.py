"""Check every link in data/links.tsv actually resolves, and take its title from the live page.

Agent- or human-supplied titles are not trusted: we fetch each URL, read the real <title>,
and (for Reddit) confirm the thread body mentions the module code or the course name.
Rewrites data/links.tsv in place with verified titles, dropping anything that fails.

Usage: python3 scripts/verify_links.py [--keep-unverified]
"""
import html, json, re, sys, time, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "data/links.tsv"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
names = {}
for f in (ROOT / "data/trees").glob("*.json"):
    def walk(n):
        if n["code"]: names.setdefault(n["code"], n["name"])
        for c in n["children"]: walk(c)
    for r in json.load(open(f))["roots"]: walk(r)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,de"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

head, rows = [], []
for raw in TSV.read_text().splitlines():
    (head if (not raw.strip() or raw.lstrip().startswith("#")) else rows).append(raw)

out, dropped = [], []
for raw in rows:
    p = [x.strip() for x in raw.split("\t")]
    code, url, date, src = p[0], p[1], (p[3] if len(p) > 3 else ""), (p[4] if len(p) > 4 else "")
    try:
        page = fetch(url)
    except Exception as e:
        dropped.append((code, url, f"fetch failed: {e}")); continue
    m = re.search(r'<title[^>]*>(.*?)</title>', page, re.S | re.I)
    title = html.unescape(re.sub(r"\s+", " ", m[1])).strip() if m else ""
    title = re.sub(r"\s*:\s*r/\w+$", "", title)                      # reddit suffix
    if not title or "page not found" in title.lower():
        dropped.append((code, url, "no usable title")); continue
    text = html.unescape(re.sub(r"<[^>]+>", " ", page)).lower()
    course = names.get(code, "")
    key = re.sub(r"\s*\([^)]*\)", "", course).lower().strip()
    mentions = code.lower() in text or (len(key) > 10 and key in text)
    out.append((code, url, title, date, src, mentions))
    print(f"{'ok ' if mentions else 'WEAK'} {code:11} {title[:62]}")
    time.sleep(1.5)

keep = [o for o in out if o[5] or "--keep-unverified" in sys.argv]
TSV.write_text("\n".join(head + ["\t".join(o[:5]) for o in keep]) + "\n")
print(f"\nkept {len(keep)} of {len(rows)}")
for c, u, why in dropped: print(f"  dropped {c}: {why}", file=sys.stderr)
for o in out:
    if not o[5]: print(f"  weak (code/name not found on page) {o[0]} {o[1]}", file=sys.stderr)
