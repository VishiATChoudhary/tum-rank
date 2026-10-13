"""Scan the whole r/tumunich archive for mentions of every TUM module, and emit only
links that really exist.

Reddit's own search page cannot be checked from a script, and Studydrive's search ignores
the query entirely, so guessing a search URL produces dead ends. Instead we page through the
arctic-shift archive of r/tumunich once, match module codes and distinctive course names
against each post, and write data/links.tsv from what is actually there.

Usage: python3 scripts/scan_reddit.py [--max-pages N]
"""
import datetime, json, re, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = set(json.load(open(ROOT / "api/_keys.json")))
API = "https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=tumunich&limit=100&sort=desc"
MAX = int(sys.argv[sys.argv.index("--max-pages") + 1]) if "--max-pages" in sys.argv else 200

names = {}
for f in (ROOT / "data/trees").glob("*.json"):
    def walk(n):
        if n["code"] in KEYS: names.setdefault(n["code"], n["name"])
        for c in n["children"]: walk(c)
    for r in json.load(open(f))["roots"]: walk(r)

def get(url):
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tum-rank"})
            return json.loads(urllib.request.urlopen(req, timeout=60).read())["data"]
        except Exception:
            time.sleep(3 * (attempt + 1))
    return []


def fetch_all():
  posts, before, seen = [], None, set()
  for page in range(MAX):
    batch = get(API + (f"&before={before}" if before else ""))
    batch = [p for p in batch if p["id"] not in seen]
    if not batch: break
    seen.update(p["id"] for p in batch)
    posts += batch
    before = min(p["created_utc"] for p in batch)
    print(f"\r{len(posts)} posts, back to {datetime.date.fromtimestamp(before)}", end="", flush=True)
    time.sleep(0.6)
  print()
  return posts

CACHE = ROOT / "data/vendor/reddit_tumunich.json"
if CACHE.exists() and "--refresh" not in sys.argv:
    posts = json.load(open(CACHE))
    print(f"{len(posts)} posts from cache (pass --refresh to re-fetch)")
else:
    posts = fetch_all()
    CACHE.write_text(json.dumps(posts, ensure_ascii=False))
    print(f"cached {len(posts)} posts")


# Match on module codes only. Course names generate far too much noise: "Machine Learning"
# also matches "PhD in Machine Learning" and "Tutoring Data Science/Machine Learning", which
# tell a student nothing about IN2064. A code is unambiguous.
CODE_IN = {code: re.compile(rf"\b{re.escape(code)}\b", re.I) for code in names}
hits = {}
for p in posts:
    if p.get("removed_by_category"): continue
    title, body = p.get("title") or "", p.get("selftext") or ""
    if (p.get("num_comments") or 0) < 1: continue       # no replies means nothing to read
    for code, rx in CODE_IN.items():
        in_title, in_body = rx.search(title), rx.search(body)
        if not (in_title or in_body): continue
        # a thread named after the module beats one that mentions it in a list of five
        hits.setdefault(code, []).append(((200 if in_title else 0) + min(p.get("num_comments") or 0, 40), p))

ADMIN = re.compile(r"\bpassword\b|\bpasswort\b|moodle access|anmeldung|registration (problem|issue)|how do i register", re.I)
lines = []
for code, scored in sorted(hits.items()):
    scored.sort(key=lambda sp: (-sp[0], -sp[1]["created_utc"]))
    ps = [p for _, p in scored]
    kept = 0
    for p in ps:
        if kept >= 3: break
        title = re.sub(r"\s+", " ", p.get("title") or "").strip()
        if not title or ADMIN.search(title): continue
        d = datetime.date.fromtimestamp(p["created_utc"])
        lines.append(f"{code}\thttps://www.reddit.com/r/tumunich/comments/{p['id']}\t{title[:120]}\t{d:%Y-%m}\tr/tumunich")
        kept += 1

head = (ROOT / "data/links.tsv").read_text().splitlines()
head = [l for l in head if l.lstrip().startswith("#") or not l.strip()]
(ROOT / "data/links.tsv").write_text("\n".join(head + lines) + "\n")
print(f"scanned {len(posts)} posts -> {len(lines)} links across {len({l.split(chr(9))[0] for l in lines})} courses")
