# TUM Rank

Course ratings for TU Munich, by students. Pick your degree, see every course grouped by area, rate the course and the professor (1 to 5 stars), and leave a short text comment.

**Live:** https://tum-rank.vercel.app · **Contribute:** see [CONTRIBUTING.md](CONTRIBUTING.md)

## How it works

- `public/` is a static site (no framework, no build step). Course trees and descriptions are static JSON in `public/data/`, served from the CDN.
- `api/index.py` is one Python serverless function on Vercel, backed by Postgres (Neon). It stores ratings, reports and suggestions.
- Course data is scraped from TUMonline's public curriculum trees (`scripts/scrape_spo.py`), no login needed.
- New courses and degrees suggested by students wait for a moderator (`/admin.html`). Approving a degree starts the `Import degree` GitHub Action, which scrapes the tree, commits it and triggers a redeploy.

## Run locally

```bash
brew services start postgresql@17 && createdb tumrank
pip install -r requirements.txt
DATABASE_URL=postgresql:///tumrank ADMIN_TOKEN=$(openssl rand -hex 16) python3 server.py
# open http://localhost:8090
```

## Data

```bash
python3 scripts/scrape_spo.py 5217      # scrape a curriculum tree (≈5 min, 14 pages)
python3 scripts/build_static.py         # regenerate public/data and api/_keys.json
```

## Environment (Vercel)

| Variable | What |
| --- | --- |
| `DATABASE_URL` | Postgres connection string (set by the Neon integration) |
| `ADMIN_TOKEN` | Moderator token, 24+ random characters |
| `IP_SALT` | Random secret used to hash IP addresses (raw IPs are never stored) |
| `GH_TOKEN`, `GH_REPO` | Optional. Fine-grained token with Actions: write, so approving a degree starts the import |

See [SECURITY.md](SECURITY.md) for the abuse model.
