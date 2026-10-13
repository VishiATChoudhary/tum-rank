"""Scrape a TUMonline curriculum (SPO) tree, no login needed.
Usage: python3 scripts/scrape_spo.py 4731 [5217 ...]  -> data/trees/<spo>.json
Also importable: scrape(spo) (used by the server for 'add degree').
"""
import html, json, re, sys, urllib.request
from pathlib import Path

URL = ("https://campus.tum.de/tumonline/wbstpcs.showSpoTree?pStpStpNr={}&pFilterType=20"
       "&pPageNr={}&pStpKnotenNr=&pStartSemester=W&pSjNr=1623")

def scrape(spo: int) -> dict:
    def page(n):
        r = urllib.request.Request(URL.format(int(spo), n), headers={"User-Agent": "tum-rank"})
        return urllib.request.urlopen(r, timeout=60).read().decode("utf-8", "replace")
    s = page(1)
    pages = max([int(x) for x in re.findall(r"von (\d+)", s)] or [1])
    for n in range(2, min(pages, 60) + 1): s += page(n)
    body_txt = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S | re.I))
    title = re.search(r"(\d+ [^()\n]{3,80}\(\d+, [^()]{3,60}\))", body_txt)
    nodes = {}
    for m in re.finditer(r'<tr class="coRow[^"]*?((?:kn\d+ )+)" id="kn(\d+)">(.*?)</tr>', s, re.S):
        classes, nid, body = m.groups()
        anc = [c[2:] for c in classes.split()]
        t = re.search(r'class="KnotenText[^"]*"[^>]*>(.*?)</span>', body, re.S)
        if not t: continue
        name = html.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip()
        nums = re.findall(r'<td class=" R"><div class="R ">\s*<span>([\d.,]*)</span>', body)
        ects = float(nums[0].replace(",", ".")) if nums and nums[0] else None
        code = re.match(r"\[([^\]]+)\]\s*(.*)", name)
        parent = anc[-2] if len(anc) > 1 and anc[-1] == nid else (anc[-1] if anc and anc[-1] != nid else None)
        nodes[nid] = {"id": nid, "parent": parent, "name": code.group(2) if code else name,
                      "code": code.group(1) if code else None, "ects": ects, "children": []}
    roots = []
    for n in nodes.values():
        (nodes[n["parent"]]["children"] if n["parent"] in nodes else roots).append(n)
    return {"spo": int(spo), "title": title.group(1) if title else str(spo), "roots": roots, "count": len(nodes)}

if __name__ == "__main__":
    for spo in sys.argv[1:]:
        t = scrape(spo)
        Path(__file__).resolve().parent.parent.joinpath(f"data/trees/{spo}.json").write_text(json.dumps(t, ensure_ascii=False))
        print(spo, t["title"], t["count"], "nodes")
