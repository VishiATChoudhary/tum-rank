"""TUM Rank API. One Vercel Python function behind /api/*.

Env: DATABASE_URL (Postgres), ADMIN_TOKEN (>= 24 chars), IP_SALT (random secret),
     optional GH_TOKEN + GH_REPO to trigger the degree-import workflow on approval.
"""
import hashlib, hmac, json, os, re, secrets, unicodedata, urllib.request
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import psycopg
from psycopg.rows import dict_row

HERE = Path(__file__).resolve().parent
KEYS = set(json.load(open(HERE / "_keys.json")))
ADMIN = os.environ.get("ADMIN_TOKEN", "")
SALT = os.environ.get("IP_SALT", "dev-salt").encode()
LOCAL = os.environ.get("TUMRANK_LOCAL") == "1"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ratings(
  id SERIAL PRIMARY KEY, key TEXT NOT NULL, token TEXT NOT NULL, iph TEXT NOT NULL,
  course_stars SMALLINT NOT NULL CHECK (course_stars BETWEEN 1 AND 5),
  prof_name TEXT, prof_stars SMALLINT CHECK (prof_stars BETWEEN 1 AND 5),
  comment TEXT NOT NULL DEFAULT '', created TIMESTAMPTZ NOT NULL DEFAULT now(),
  status TEXT NOT NULL DEFAULT 'live', reports INT NOT NULL DEFAULT 0, UNIQUE(key, token));
CREATE INDEX IF NOT EXISTS ratings_key ON ratings(key) WHERE status = 'live';
CREATE TABLE IF NOT EXISTS reports(rating_id INT NOT NULL, iph TEXT NOT NULL, PRIMARY KEY(rating_id, iph));
CREATE TABLE IF NOT EXISTS suggestions(
  id SERIAL PRIMARY KEY, kind TEXT NOT NULL, spo INT NOT NULL, parent TEXT, name TEXT,
  iph TEXT NOT NULL, created TIMESTAMPTZ NOT NULL DEFAULT now(), status TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS hits(iph TEXT NOT NULL, kind TEXT NOT NULL, ts TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS hits_lookup ON hits(iph, kind, ts);
"""
_conn = None
def db():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True, row_factory=dict_row, prepare_threshold=None)
        _conn.execute(SCHEMA)
    return _conn

# ---------------- anti-abuse ----------------
LIMITS = {  # kind: (max, window)
    "rate": (12, "1 hour"), "rate_day": (40, "1 day"), "suggest": (3, "1 hour"), "suggest_day": (8, "1 day"),
    "report": (20, "1 hour"), "admin_fail": (5, "15 minutes"), "global_write": (3000, "1 hour"),
}
BAD = re.compile(
    r"https?:|www\.|\b[\w-]+\.(com|net|org|de|io|ru|xyz|cn|me|ly|gg|co|app|link)\b|@[\w-]+\.|\bt\.me\b|"
    r"whatsapp|telegram|discord\.gg|onlyfans|\bcrypto\b|\bviagra\b|\bcasino\b|\bbtc\b|\busdt\b|\+?\d[\d\s/().-]{8,}", re.I)
SLURS = re.compile(r"\b(n[i1]gg|f[a@]gg?ot|k[i1]ke|retard|hure|schlampe|fotze|wichser|hurensohn|spast|neger)\w*", re.I)

def clean(s, mx, minlen=1):
    if not isinstance(s, str): raise ValueError("Text required.")
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\ufff9-\ufffb]", " ", s)  # control, zero-width, bidi
    if sum(unicodedata.combining(c) > 0 for c in s) > 3: raise ValueError("Please write plain text.")  # zalgo
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) < minlen: raise ValueError("Too short.")
    if len(s) > mx: raise ValueError(f"Max {mx} characters.")
    if re.search(r"[<>{}\[\]\\`]", s): raise ValueError("Plain text only, no markup.")
    if BAD.search(s): raise ValueError("No links, contact details or ads.")
    if SLURS.search(s): raise ValueError("Keep it civil.")
    if re.search(r"(.)\1{5,}", s) or re.search(r"(\b\w+\b)(\W+\1\b){3,}", s, re.I): raise ValueError("Too repetitive.")
    letters = sum(c.isalpha() for c in s)
    if len(s) >= 6 and letters / len(s) < 0.55: raise ValueError("Text only, please.")
    if len(s) > 20 and sum(c.isupper() for c in s) / max(letters, 1) > 0.6: raise ValueError("Please don't shout.")
    return s

def limited(iph, kind):
    n, win = LIMITS[kind]
    c = db().execute("SELECT count(*) c FROM hits WHERE iph=%s AND kind=%s AND ts > now() - %s::interval", (iph, kind, win)).fetchone()["c"]
    return c >= n

def hit(iph, *kinds):
    for k in kinds: db().execute("INSERT INTO hits(iph, kind) VALUES (%s, %s)", (iph, k))
    if secrets.randbelow(200) == 0: db().execute("DELETE FROM hits WHERE ts < now() - interval '2 days'")

# ---------------- handler ----------------
class handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def ip(self):
        if LOCAL: return self.client_address[0]
        # Vercel sets these; client-supplied X-Forwarded-For is overwritten by the edge
        return (self.headers.get("x-real-ip") or self.headers.get("x-vercel-forwarded-for", "").split(",")[0] or "0").strip()
    def iph(self): return hmac.new(SALT, self.ip().encode(), hashlib.sha256).hexdigest()[:32]
    def token(self):
        c = SimpleCookie(self.headers.get("Cookie", ""))
        v = c["tr"].value if "tr" in c else ""
        return (v, False) if re.fullmatch(r"[0-9a-f]{32}", v) else (secrets.token_hex(16), True)

    def send(self, obj, code=200, cookie=None, cache=None):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", cache or "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cookie: self.send_header("Set-Cookie", f"tr={cookie}; Max-Age=63072000; Path=/; HttpOnly; SameSite=Lax" + ("" if LOCAL else "; Secure"))
        self.end_headers(); self.wfile.write(b)

    def is_admin(self):
        t = self.headers.get("X-Admin-Token", "")
        if not ADMIN or len(ADMIN) < 24: return False
        iph = self.iph()
        if limited(iph, "admin_fail"): return False
        if hmac.compare_digest(t.encode(), ADMIN.encode()): return True
        hit(iph, "admin_fail"); return False

    # ---- GET ----
    def do_GET(self):
        try:
            u = urlparse(self.path); p = unquote(u.path); q = parse_qs(u.query)
            if p == "/api/stats":
                rows = db().execute("""SELECT key, avg(course_stars)::float a, count(*) n, avg(prof_stars)::float p,
                    count(*) FILTER (WHERE course_stars=1) d1, count(*) FILTER (WHERE course_stars=2) d2, count(*) FILTER (WHERE course_stars=3) d3,
                    count(*) FILTER (WHERE course_stars=4) d4, count(*) FILTER (WHERE course_stars=5) d5
                    FROM ratings WHERE status='live' GROUP BY key""").fetchall()
                return self.send({r["key"]: [round(r["a"], 3), r["n"], r["p"] and round(r["p"], 2), r["d1"], r["d2"], r["d3"], r["d4"], r["d5"]] for r in rows},
                                 cache="public, s-maxage=20, stale-while-revalidate=60")
            if p == "/api/extra":
                spo = int(q.get("spo", ["0"])[0])
                rows = db().execute("SELECT id, parent, name FROM suggestions WHERE kind='course' AND status='approved' AND spo=%s", (spo,)).fetchall()
                return self.send([{"key": f"s:{r['id']}", "parent": r["parent"], "name": r["name"]} for r in rows], cache="public, s-maxage=60")
            if m := re.fullmatch(r"/api/module/([\w:.-]{1,40})", p):
                key = m[1]; tok, new = self.token()
                rs = db().execute("""SELECT id, course_stars, prof_name, prof_stars, comment FROM ratings
                                     WHERE key=%s AND status='live' ORDER BY created DESC LIMIT 200""", (key,)).fetchall()
                profs = {}
                for r in rs:
                    if r["prof_name"] and r["prof_stars"]: profs.setdefault(r["prof_name"], []).append(r["prof_stars"])
                mine = db().execute("SELECT course_stars, prof_name, prof_stars, comment FROM ratings WHERE key=%s AND token=%s", (key, tok)).fetchone()
                return self.send({
                    "avg": round(sum(r["course_stars"] for r in rs) / len(rs), 2) if rs else None, "n": len(rs),
                    # a lecturer only shows up once two different people rated them (limits one-person smear/boost)
                    "prof_avgs": [{"name": k, "avg": round(sum(v) / len(v), 2), "n": len(v)} for k, v in profs.items() if len(v) >= 2],
                    "ratings": [{"id": r["id"], "course": r["course_stars"], "prof": r["prof_name"], "prof_stars": r["prof_stars"], "comment": r["comment"]} for r in rs],
                    "mine": mine}, cookie=tok if new else None)
            if p == "/api/admin/queue":
                if not self.is_admin(): return self.send({"error": "Forbidden"}, 403)
                sug = db().execute("SELECT id, kind, spo, parent, name, created::text FROM suggestions WHERE status='pending' ORDER BY created").fetchall()
                flagged = db().execute("SELECT id, key, course_stars, prof_name, prof_stars, comment, reports, created::text FROM ratings WHERE status='flagged' ORDER BY created").fetchall()
                return self.send({"suggestions": sug, "flagged": flagged})
            return self.send({"error": "Not found"}, 404)
        except Exception as e:
            print("GET error", repr(e)); return self.send({"error": "Server error"}, 500)

    # ---- POST ----
    def do_POST(self):
        try:
            # CSRF: JSON only (forces a CORS preflight cross-site) and same-origin when the browser says where it came from
            if not self.headers.get("Content-Type", "").startswith("application/json"): return self.send({"error": "JSON only"}, 415)
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).netloc != self.headers.get("Host"): return self.send({"error": "Bad origin"}, 403)
            n = int(self.headers.get("Content-Length") or 0)
            if n > 4096: return self.send({"error": "Too large"}, 413)
            body = json.loads(self.rfile.read(n) or b"{}")
            if not isinstance(body, dict): raise ValueError("Bad request.")
            tok, new = self.token()
            if body.get("website"):  # honeypot: bots fill every field; pretend it worked
                return self.send({"ok": True, "message": "Thanks!"}, cookie=tok if new else None)
            out = self.route(urlparse(self.path).path, body, tok, self.iph())
            return self.send(out, cookie=tok if new else None)
        except ValueError as e: return self.send({"error": str(e)}, 400)
        except PermissionError as e: return self.send({"error": str(e)}, 403)
        except Exception as e:
            print("POST error", repr(e)); return self.send({"error": "Server error"}, 500)

    def route(self, p, b, tok, iph):
        if p.startswith("/api/admin/"): return self.admin(p, b)
        if limited("*", "global_write"): raise ValueError("The site is busy, try again later.")

        if p == "/api/rate":
            key = str(b.get("key", ""))
            ok = key in KEYS or (re.fullmatch(r"s:\d{1,9}", key) and db().execute(
                "SELECT 1 FROM suggestions WHERE id=%s AND kind='course' AND status='approved'", (int(key[2:]),)).fetchone())
            if not ok: raise ValueError("Unknown course.")
            cs = b.get("course_stars")
            if type(cs) is not int or not 1 <= cs <= 5: raise ValueError("Rate the course from 1 to 5.")
            pn, ps = (b.get("prof_name") or "").strip(), b.get("prof_stars")
            if ps is not None:
                if type(ps) is not int or not 1 <= ps <= 5: raise ValueError("Rate the professor from 1 to 5.")
                pn = clean(pn, 60, 3)
                if not re.fullmatch(r"(?:Prof\. |Dr\. )*[^\W\d_][^\W\d_'\u2019.-]*(?:[ '\u2019.-]+[^\W\d_]+)+\.?", pn): raise ValueError("Professor: first and last name.")
            else: pn = None
            com = clean(b["comment"], 200, 3) if (b.get("comment") or "").strip() else ""
            if com and db().execute("SELECT 1 FROM ratings WHERE lower(comment)=lower(%s) AND token<>%s", (com, tok)).fetchone(): raise ValueError("Someone already wrote exactly that.")
            # cookie clearing: at most 4 different ratings per course from one network per day
            same_net = db().execute("SELECT count(*) c FROM ratings WHERE key=%s AND iph=%s AND token<>%s AND created > now() - interval '1 day'", (key, iph, tok)).fetchone()["c"]
            if same_net >= 4: raise ValueError("Too many ratings for this course from your network today.")
            if limited(iph, "rate") or limited(iph, "rate_day"): raise ValueError("Slow down, try again later.")
            hit(iph, "rate", "rate_day"); hit("*", "global_write")
            db().execute("""INSERT INTO ratings(key, token, iph, course_stars, prof_name, prof_stars, comment) VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (key, token) DO UPDATE SET course_stars=EXCLUDED.course_stars, prof_name=EXCLUDED.prof_name,
                prof_stars=EXCLUDED.prof_stars, comment=EXCLUDED.comment, iph=EXCLUDED.iph, created=now(),
                status=CASE WHEN ratings.status='removed' THEN 'removed' ELSE 'live' END, reports=0""",
                (key, tok, iph, cs, pn, ps, com))
            return {"ok": True}

        if p == "/api/report":
            rid = b.get("id")
            if type(rid) is not int: raise ValueError("Bad request.")
            if limited(iph, "report"): raise ValueError("Slow down.")
            hit(iph, "report")
            if db().execute("INSERT INTO reports VALUES (%s, %s) ON CONFLICT DO NOTHING", (rid, iph)).rowcount:
                # 3 reports from 3 different networks hide it until a moderator looks (not deleted, so mass-reporting can be undone)
                db().execute("""UPDATE ratings SET reports = (SELECT count(*) FROM reports WHERE rating_id=%s),
                    status = CASE WHEN status='live' AND (SELECT count(*) FROM reports WHERE rating_id=%s) >= 3 THEN 'flagged' ELSE status END
                    WHERE id=%s""", (rid, rid, rid))
            return {"ok": True}

        if p == "/api/suggest":
            kind = b.get("kind")
            if limited(iph, "suggest") or limited(iph, "suggest_day"): raise ValueError("You've sent a lot of suggestions, try tomorrow.")
            if kind == "course":
                spo, parent = b.get("spo"), str(b.get("parent", ""))
                if type(spo) is not int or not re.fullmatch(rf"{spo}:\d{{1,12}}", parent): raise ValueError("Pick an area first.")
                name = clean(b.get("name"), 80, 4)
                if db().execute("SELECT 1 FROM suggestions WHERE kind='course' AND spo=%s AND lower(name)=lower(%s) AND status<>'rejected'", (spo, name)).fetchone():
                    raise ValueError("Already suggested.")
                db().execute("INSERT INTO suggestions(kind, spo, parent, name, iph) VALUES ('course', %s, %s, %s, %s)", (spo, parent, name, iph))
            elif kind == "degree":
                spo = b.get("spo")
                if type(spo) is not int or not 1 <= spo <= 99999: raise ValueError("Enter the TUMonline SPO number (digits only).")
                if db().execute("SELECT 1 FROM suggestions WHERE kind='degree' AND spo=%s AND status<>'rejected'", (spo,)).fetchone(): raise ValueError("Already requested.")
                db().execute("INSERT INTO suggestions(kind, spo, iph) VALUES ('degree', %s, %s)", (spo, iph))
            else: raise ValueError("Bad request.")
            hit(iph, "suggest", "suggest_day"); hit("*", "global_write")
            return {"ok": True, "message": "Thanks! A moderator will review it."}
        raise ValueError("Unknown endpoint.")

    def admin(self, p, b):
        if not self.is_admin(): raise PermissionError("Forbidden")
        if p == "/api/admin/act":
            what, i, action = b.get("type"), b.get("id"), b.get("action")
            if type(i) is not int: raise ValueError("Bad id.")
            if what == "suggestion" and action in ("approve", "reject"):
                row = db().execute("UPDATE suggestions SET status=%s WHERE id=%s RETURNING kind, spo", ("approved" if action == "approve" else "rejected", i)).fetchone()
                msg = "Done."
                if row and row["kind"] == "degree" and action == "approve": msg = dispatch_import(row["spo"])
                return {"ok": True, "message": msg}
            if what == "rating" and action in ("restore", "remove"):
                db().execute("UPDATE ratings SET status=%s WHERE id=%s", ("live" if action == "restore" else "removed", i))
                if action == "restore": db().execute("DELETE FROM reports WHERE rating_id=%s", (i,))
                return {"ok": True, "message": "Done."}
        raise ValueError("Bad action.")

def dispatch_import(spo):
    tok, repo = os.environ.get("GH_TOKEN"), os.environ.get("GH_REPO")
    if not tok or not repo: return f"Approved. Run: gh workflow run import-degree.yml -f spo={spo}"
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/import-degree.yml/dispatches", method="POST",
        data=json.dumps({"ref": "main", "inputs": {"spo": str(spo)}}).encode(),
        headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json", "User-Agent": "tum-rank"})
    try: urllib.request.urlopen(req, timeout=10); return "Approved. Import workflow started, the site redeploys in ~10 minutes."
    except Exception as e: return f"Approved, but starting the workflow failed ({e}). Run: gh workflow run import-degree.yml -f spo={spo}"
