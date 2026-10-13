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

## Summaries of public discussion

`data/digests.tsv` holds short summaries, written in our own words, of what public threads say
about a course; `python3 scripts/build_digests.py` validates and builds them. They appear in
their own "Said elsewhere" block with a link to the source.

**They never touch the ratings.** A forum thread has no star value, so giving it one would make
the averages, the difficulty figures and the ranking fiction. The stars come only from people
who rated on this site. The build step rejects any summary containing a long verbatim quote,
so these stay summaries rather than reposted comments.

## Course discussions elsewhere

Every course page carries a r/tumunich search link as a fallback. Studydrive is linked at
university level, not per course: their search ignores the query (searching `IN2064` returns
"Finanzmathematik" and claims 1.6 M results), so a per-course search link there is a dead end.

`scripts/scan_reddit.py` pages the whole r/tumunich archive once (10,754 posts back to 2017,
cached in `data/vendor/`) and writes `data/links.tsv` from posts that actually mention a module
code. It matches on codes only: course names like "Machine Learning" also match "PhD in Machine
Learning" and tell a student nothing. Threads named after the module outrank passing mentions,
and posts with no replies are skipped because there is nothing to read.

`data/links.tsv` holds the resulting deep links to specific threads;
`python3 scripts/build_links.py` validates them into `public/data/links.json`, and
`scripts/verify_links.py` re-checks that each one still resolves. Note that Reddit cannot be
verified programmatically (it returns an identical HTTP 200 for a nonexistent thread id), so
threads must be eyeballed in a browser first. Candidates waiting for that:
`docs/reddit-link-candidates.md`.

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

## Exam pass rates

[stats.aamin.dev](https://stats.aamin.dev) publishes TUM exam statistics (registrations,
attempts, no-shows, pass rates) per module per semester. Each course links out to it. We do
not copy it: it is someone else's database, and their search backend is currently offline.
Worth approaching the author about combining forces.

See [SECURITY.md](SECURITY.md) for the abuse model.
