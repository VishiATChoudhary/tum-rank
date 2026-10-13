# Candidate Reddit threads, UNVERIFIED

A research agent reported these r/tumunich threads as discussing specific TUM modules.
**None of them has been verified**, and they are deliberately not shipped on the site.

Reddit cannot be checked programmatically: it answers every scripted request with the same
JS shell, and a deliberately nonsensical thread id (`/comments/zzzzzzz`) returns the identical
HTTP 200 and the identical 8425 bytes as a real one. Headless Chrome gets a 403 JS challenge.
So a 200 proves nothing, and an agent-reported URL could be a hallucination.

To ship any of these: open it in a normal logged-in browser, confirm the thread exists and is
about that module, then add a line to `data/links.tsv` and run `python3 scripts/build_links.py`.
The live site already links to a Reddit *search* per course, which needs no verification.

Note: the subreddit is **r/tumunich**. r/TUM does not exist.

| Module | Thread | Reported title | Date |
| --- | --- | --- | --- |
| IN2064 | https://www.reddit.com/r/tumunich/comments/1n29yxt | Is Machine Learning (IN2064) at TUM worth it? | 2025-08 |
| IN2064 | https://www.reddit.com/r/tumunich/comments/1qa1c9n | Points needed for Machine Learning (IN2064)? | 2026-01 |
| IN0015 | https://www.reddit.com/r/tumunich/comments/1wm9yu7 | Did anyone take Discrete Structures (IN0015) last year? | 2026-09 |
| IN2007, IN2055 | https://www.reddit.com/r/tumunich/comments/1flbkoy | Classes reviews / groupchat [informatics] | 2024-09 |
| IN2041 | https://www.reddit.com/r/tumunich/comments/1jf3tm1 | Is TUM really that difficult? (Erasmus CS student) | 2025-03 |
| IN2041, IN2062 | https://www.reddit.com/r/tumunich/comments/1sxhd5x | Applying for an Exchange Semester | 2026-04 |
| CIT5130002, IN0018 | https://www.reddit.com/r/tumunich/comments/1k27smj | Diskrete Wahrscheinlichkeitstheorie oder Intro to Data Science? | 2025-04 |
| CIT5230000 | https://www.reddit.com/r/tumunich/comments/170oqyi | Introduction to Programming (CIT5230000) | 2023-10 |
| CIT5230000 | https://www.reddit.com/r/tumunich/comments/1o5lpvt | Introduction to Programming (CIT5230000) | 2025-10 |
| CIT413048, IN0006, IN0012, IN2073 | https://www.reddit.com/r/tumunich/comments/1of03m7 | Joining TUM informatics as an exchange student | 2025-10 |
| IN0015 | https://www.reddit.com/r/tumunich/comments/1alcyne | Can I study Quantum Science & Technology with an Informatik bachelor? | 2024-02 |
| CIT513013 | https://www.reddit.com/r/tumunich/comments/1nh2koi | Ersti Help Aero BSc | 2025-09 |
| IN2067 | https://www.reddit.com/r/tumunich/comments/1rqspft | Informatics SS26 - Robotic courses | 2026-03 |

Dropped as purely administrative (registration passwords, prerequisites, attendance rules —
no help to someone choosing a course): IN2067 x3 password threads, IN0002 attendance,
IN0018 registration, CIT123001 prerequisites.
