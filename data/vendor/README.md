# Vendored third-party data

`all_offered_courses_*.json` come from
[Vuenc/TUM-Master-Informatics-Offered-Lectures](https://github.com/Vuenc/TUM-Master-Informatics-Offered-Lectures)
by Vincent Bürgin, used under the MIT licence (see `LICENSE.vuenc`). They are scraped from
TUMonline and record which courses were actually offered in which semester, SS10 onwards.

We use them for one thing: offering history per module (how often, first, last). Facts only.
`scripts/build_offerings.py` turns them into `public/data/offerings.json`.
