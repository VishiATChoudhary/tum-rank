"""Add lecturer names (from TUMonline lectureships) to data/modules.json."""
import json, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
mods = json.load(open(ROOT / "data/modules_src.json"))
def profs(m):
    if not m.get("source_course"): return []
    try:
        r = urllib.request.Request(f"https://campus.tum.de/tumonline/ee/rest/slc.tm.cp/student/courses/{m['source_course']}", headers={"Accept": "application/json"})
        c = json.load(urllib.request.urlopen(r, timeout=30))["resource"][0]["content"]["cpCourseDetailDto"]["cpCourseDto"]
        names = []
        for l in c.get("lectureships", []):
            i = l["identityLibDto"]; n = f"{i['firstName']} {i['lastName']}".strip()
            if l.get("teachingFunction", {}).get("key") == "L" and n not in names: names.append(n)
        return names
    except Exception: return []
with ThreadPoolExecutor(12) as ex: res = list(ex.map(profs, mods))
for m, p in zip(mods, res): m["professors"] = p
json.dump(mods, open(ROOT / "data/modules.json", "w"), ensure_ascii=False)
print(sum(1 for p in res if p), "modules with professors")
