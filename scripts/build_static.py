"""Turn scraped trees + module metadata into static files served by the CDN.

data/trees/<spo>.json  ->  public/data/trees/<spo>.json   (compact tree)
                           public/data/degrees.json
data/modules.json      ->  public/data/m/<code>.json      (description, prereqs, lecturers)
                           api/_keys.json                 (every rateable key, read by the API)
Run after scraping:  python3 scripts/build_static.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public/data"
(OUT / "trees").mkdir(parents=True, exist_ok=True)
(OUT / "m").mkdir(parents=True, exist_ok=True)

keys, degrees = set(), []
for f in sorted((ROOT / "data/trees").glob("*.json")):
    t = json.load(open(f))
    spo = t["spo"]
    def compact(n):
        nid = f"{spo}:{n['id']}"
        if n["code"]: keys.add(n["code"])
        out = {"id": nid, "name": n["name"]}
        if n["code"]: out["code"] = n["code"]
        if n["ects"]: out["ects"] = n["ects"]
        kids = [compact(c) for c in n["children"]]
        if kids: out["children"] = kids
        return out
    tree = {"id": f"root{spo}", "name": t["title"], "children": [compact(r) for r in t["roots"]]}
    (OUT / f"trees/{spo}.json").write_text(json.dumps(tree, ensure_ascii=False, separators=(",", ":")))
    degrees.append({"spo": spo, "title": t["title"]})

for m in json.load(open(ROOT / "data/modules.json")):
    if m["id"] not in keys: continue
    (OUT / f"m/{m['id']}.json").write_text(json.dumps({
        "name": m["name"], "credits": m.get("credits"),
        "description": (m.get("content") or m.get("objective") or "")[:4000],
        "prerequisites": (m.get("prerequisites") or "")[:1500],
        "professors": m.get("professors", []),
    }, ensure_ascii=False, separators=(",", ":")))

(OUT / "degrees.json").write_text(json.dumps(degrees, ensure_ascii=False))
(ROOT / "api/_keys.json").write_text(json.dumps(sorted(keys)))
print(len(degrees), "degrees,", len(keys), "rateable keys")
