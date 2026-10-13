"""Verify every link in data/links.tsv, and take its title from the source of truth.

Reddit cannot be checked by fetching it: reddit.com answers every scripted request with the
same JS shell, returning an identical HTTP 200 (and identical byte count) for a thread id that
does not exist. So Reddit links are checked against the arctic-shift archive of Reddit's own
data, which gives the stored title, the subreddit, and whether the post was removed.
Non-Reddit links are fetched normally and their <title> is read.

A link is kept only if it resolves, is not removed, and the module code or course name
actually appears in the post. Titles are overwritten with the authoritative ones.

Usage: python3 scripts/verify_links.py [--dry-run]
"""
import html, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / "data/links.tsv"
ARCTIC = "https://arctic-shift.photon-reddit.com/api/posts/ids?ids="
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
REDDIT_ID = re.compile(r"reddit\.com/r/(\w+)/comments/(\w+)")

names = {}
for f in (ROOT / "data/trees").glob("*.json"):
    def walk(n):
        if n["code"]: names.setdefault(n["code"], n["name"])
        for c in n["children"]: walk(c)
    for r in json.load(open(f))["roots"]: walk(r)

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,de"})
    with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode("utf-8", "replace")

def reddit_posts(ids):
    """id -> {title, text, subreddit, removed} for ids present in the archive."""
    out = {}
    for i in range(0, len(ids), 20):
        chunk = ids[i:i + 20]
        for p in json.loads(get(ARCTIC + ",".join(chunk))).get("data") or []:
            out[p["id"]] = {"title": p.get("title") or "", "text": str(p.get("selftext") or ""),
                            "sub": p.get("subreddit") or "", "removed": bool(p.get("removed_by_category"))}
        time.sleep(1)
    return out

head, rows = [], []
for raw in TSV.read_text().splitlines():
    (head if (not raw.strip() or raw.lstrip().startswith("#")) else rows).append(
        [x.strip() for x in raw.split("\t")] if raw.strip() and not raw.lstrip().startswith("#") else raw)

parsed = [r for r in rows if isinstance(r, list)]
posts = reddit_posts(sorted({m[2] for r in parsed if (m := REDDIT_ID.search(r[1]))}))

kept, problems = [], []
for r in parsed:
    code, url, date, src = r[0], r[1], (r[3] if len(r) > 3 else ""), (r[4] if len(r) > 4 else "")
    course = re.sub(r"\s*\([^)]*\)", "", names.get(code, "")).strip()
    m = REDDIT_ID.search(url)
    if m:
        p = posts.get(m[2])
        if not p: problems.append((code, url, "not in the Reddit archive")); continue
        if p["sub"].lower() != m[1].lower(): problems.append((code, url, f"archive says r/{p['sub']}")); continue
        if p["removed"]: problems.append((code, url, "removed from Reddit")); continue
        title, body = p["title"], p["title"] + " " + p["text"]
    else:
        try: page = get(url)
        except Exception as e: problems.append((code, url, f"fetch failed: {e}")); continue
        t = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
        title = html.unescape(re.sub(r"\s+", " ", t[1])).strip() if t else ""
        body = html.unescape(re.sub(r"<[^>]+>", " ", page))
        if not title: problems.append((code, url, "no title")); continue
    low = body.lower()
    if code.lower() not in low and not (len(course) > 12 and course.lower() in low):
        problems.append((code, url, f"neither {code} nor the course name appears in the post")); continue
    kept.append([code, url, re.sub(r"\s+", " ", title).strip()[:120], date, src])
    print(f"ok   {code:11} {title[:68]}")

if "--dry-run" not in sys.argv:
    TSV.write_text("\n".join([h for h in rows if isinstance(h, str)] + []) if False else
                   "\n".join(head + ["\t".join(k) for k in kept]) + "\n")
print(f"\nkept {len(kept)} of {len(parsed)}")
for c, u, why in problems: print(f"  drop {c:11} {why}  {u}", file=sys.stderr)
