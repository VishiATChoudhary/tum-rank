# r/tumunich launch post

Post from your own account. Best timing: the first two weeks of a semester (course
planning) or the week after exams (opinions are fresh). Flair it as a project/tool if
the subreddit has one, and reply to every comment for the first day.

---

**Title:** I built a course rating site for TUM because I was tired of asking Reddit which electives are worth it

**Body:**

Every semester the same threads show up here: is IN2064 worth it, is Automata too hard for an
exchange, which electives should I take. The answers are good but they scroll away, and the
next person asks again.

So I built https://tum-rank-one.vercel.app

- Every course in B.Sc. and M.Sc. Informatics, Information Systems and DEA, straight from TUMonline
- Rate a course and the lecturer 1 to 5, plus a difficulty score, and leave one sentence
- Anonymous: no account, no email, no login. IPs are only ever stored as a salted hash
- Open source: https://github.com/VishiATChoudhary/tum-rank

Two things on it already, before anyone has rated:

- **Which courses are actually still running.** 75 modules have not been offered for about two
  years. Planning around a dead module is a waste of a semester.
- **Links to the old threads here** that discussed a given course, so the answers stop scrolling away.

It is empty of ratings right now, which is the honest state of a site on day one. If you have
taken anything this year, one rating takes about ten seconds and makes it useful for whoever
asks next semester.

Issues and pull requests welcome, and if you contribute a few I will add you as a collaborator.

---

## Variants

**Shorter, for a comment reply in an existing "which course" thread:**

> I built https://tum-rank-one.vercel.app for exactly this. Anonymous, no login, covers every
> Informatics course from TUMonline, and flags the modules that have not run in two years.
> Still empty of ratings, so it only gets useful if people add theirs.

**For the Fachschaft channels (German):**

> Ich habe eine anonyme Kursbewertungsseite für TUM gebaut: https://tum-rank-one.vercel.app
> Kein Login, keine Accounts, Open Source. Alle Module aus TUMonline, plus die Info, welche
> Module seit zwei Jahren nicht mehr angeboten wurden. Feedback und PRs gerne.
