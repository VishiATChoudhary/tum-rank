#!/usr/bin/env python3
"""Local dev server: serves public/ and routes /api/* to the same handler Vercel runs.
Usage: DATABASE_URL=postgresql:///tumrank ADMIN_TOKEN=<24+ chars> python3 server.py [port]
"""
import os, sys
os.environ.setdefault("TUMRANK_LOCAL", "1")
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "api"))
from index import handler as Api  # noqa: E402

PUBLIC = Path(__file__).parent / "public"

class Dev(Api, SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): SimpleHTTPRequestHandler.__init__(self, *a, directory=str(PUBLIC), **k)
    def do_GET(self):
        return Api.do_GET(self) if self.path.startswith("/api/") else SimpleHTTPRequestHandler.do_GET(self)
    def end_headers(self):
        if not self.path.startswith("/api/"): self.send_header("Cache-Control", "no-cache")
        super().end_headers()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8090
    print(f"http://localhost:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Dev).serve_forever()
