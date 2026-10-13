# Reddit links: how they are verified

The subreddit is **r/tumunich**. r/TUM does not exist.

Reddit cannot be verified by fetching it. `reddit.com` answers every scripted request with the
same JS shell: a real thread and the nonsense id `/comments/zzzzzzz` both return HTTP 200 and
the identical 8425 bytes, `old.reddit.com` redirects to a login wall, and headless Chrome gets
a 403 JS challenge. So a 200 proves nothing.

`scripts/verify_links.py` therefore checks every thread against the
[arctic-shift](https://arctic-shift.photon-reddit.com) archive of Reddit's own data, which
returns the stored title, the subreddit and whether the post was removed. A link is kept only
when the post exists, sits in the subreddit the URL claims, is not removed, and actually
mentions the module code or the course name. Titles in `data/links.tsv` are overwritten with
the archived ones, so nothing is typed by hand.

Last run: 36 of 37 candidates verified. One was dropped because it had been removed from
Reddit (`vha0fe`, IN2357). `build_links.py` then dropped 6 more whose module codes belong to
degrees this site has not imported: CIT513013, CIT5230000 (x2), IN2062, IN2073, IN2339.
**30 links across 24 courses are live.**

Deliberately excluded as purely administrative, since they don't help anyone choose a course:
exam-password threads for IN2067 (x3), attendance (IN0002), registration (IN0018),
prerequisites (CIT123001).

Re-run after editing `data/links.tsv`:

```bash
python3 scripts/verify_links.py   # checks against the archive, rewrites titles
python3 scripts/build_links.py    # writes public/data/links.json
```
