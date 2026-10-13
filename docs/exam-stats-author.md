# Note to the author of stats.aamin.dev

Not sent. TUM Rank cites exam outcome figures from https://stats.aamin.dev on course pages,
with attribution and a link back on every figure. The underlying numbers are TUM's exam
statistics, but the compilation is theirs, so they should be told, and asked.

If they object, delete `data/vendor/exam_stats.json`, re-run `scripts/build_exams.py`,
and the feature disappears.

---

Subject: TUM Rank cites your exam stats — happy to change or remove anything

Hi,

I found stats.aamin.dev through an r/tumunich thread where someone recommended it, and it's
the most useful TUM dataset I've come across.

I've built https://tum-rank-one.vercel.app, an anonymous course rating site for TUM
(open source: https://github.com/VishiATChoudhary/tum-rank, MIT). It has the same goal as your
site from the other direction: you have the objective exam outcomes, I'm trying to collect
subjective student ratings.

On each course page I now show the failure rate, number of candidates and average grade for
that module, credited to TUM Exam Stats with a link back to you, and there's a "Hardest exam"
ordering built from it. I parse the sample data your front page serves. Three things I want
to be straight about:

1. If you'd rather I didn't, say so and I'll remove it the same day. No argument.
2. If you'd prefer a different wording, attribution or link placement, tell me what you want.
3. If you have an API or a dump, I'd much rather pull from that than parse your HTML.

Honestly, the better outcome might be combining these. You have the data students need;
I have a rating interface and a course tree from TUMonline. Happy to contribute to yours
instead, or hand mine over, whatever is more useful.

Either way, thanks for building it.
