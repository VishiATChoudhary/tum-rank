"""Fetch and parse TUM Exam Stats into data/vendor/exam_stats.json.

https://stats.aamin.dev publishes TUM exam statistics per module per sitting. We parse the
factual figures only and always cite and link the source in the UI. If the site's author
asks us to stop, delete data/vendor/exam_stats.json and re-run build_exams.py.
"""
import html, json, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "tum-rank (https://github.com/VishiATChoudhary/tum-rank)"}
page = urllib.request.urlopen(urllib.request.Request("https://stats.aamin.dev", headers=UA), timeout=90).read().decode("utf-8", "replace")
txt = re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", "\n", html.unescape(page)))
txt = re.sub(r"\n+", " ", txt)

recs = []
for m in re.finditer(r"Date:\s*(\d{4}-\d{2}-\d{2})\s*Module Number:\s*([A-Z0-9_]+)\s*Name:\s*(.*?)\s*"
                     r"Registered:\s*(\d+)\s*Attempt made:\s*(\d+)\s*Not present:\s*(\d+)(.*?)"
                     r"(?=Date:\s*\d{4}-\d{2}-\d{2}|\Z)", txt, re.S):
    date, code, name, reg, att, absent, rest = m.groups()
    fail = re.search(r"failed:\s*([\d.]+)%", rest)
    avg = re.search(r"Average total:\s*([\d.]+)", rest)
    # The distribution reads "<pct>% <count> K. <grade>": the grade label comes AFTER its
    # own figures. The final entry is "<pct>% <count> K. 5.0 X Nicht erschienen", which is
    # the no-show count rather than a grade, so the lookahead drops it.
    dist = {}
    for pct, cnt, grade in re.findall(r"([\d.]+)%\s*(\d+)\s*K\.\s*([1-5]\.\d)(?!\s*X)", rest):
        dist[grade] = dist.get(grade, 0) + int(cnt)
    recs.append({"date": date, "code": code, "name": name.strip()[:80], "reg": int(reg), "att": int(att),
                 "absent": int(absent), "fail": float(fail[1]) if fail else None,
                 "avg": float(avg[1]) if avg else None, "dist": dist})

(ROOT / "data/vendor/exam_stats.json").write_text(json.dumps(recs, ensure_ascii=False))
print(f"{len(recs)} exam sittings from stats.aamin.dev")
