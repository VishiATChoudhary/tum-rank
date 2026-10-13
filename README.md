# TUM Rank

Course ratings for TU Munich, by students. Pick your degree, see every course grouped by area, rate the course and the professor (1 to 5 stars), and leave a short text comment.

**Live:** https://tum-rank-one.vercel.app · **Contribute:** see [CONTRIBUTING.md](CONTRIBUTING.md)

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

## Offering history

`data/vendor/all_offered_courses_*.json` come from
[Vuenc/TUM-Master-Informatics-Offered-Lectures](https://github.com/Vuenc/TUM-Master-Informatics-Offered-Lectures)
(MIT, Vincent Bürgin), scraped from TUMonline. `scripts/build_offerings.py` reduces them to
per-module facts: how many semesters a module ran, and the first and last one. Courses that
have not run for about two years are flagged, which saves students planning around a dead
module. Covers 299 of 803 lecture-type courses.

## Course discussions elsewhere

`data/links.tsv` holds deep links to places where a course is discussed (Reddit threads, blog posts).
`python3 scripts/build_links.py` validates them and writes `public/data/links.json`.

**We link, we never copy.** Review text from other sites is copyrighted by its authors, and
republishing criticism of a named lecturer would make this site the publisher under German
personality rights. Third-party opinions are never imported as ratings: the stars and the
difficulty averages come only from people who rated here.

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
