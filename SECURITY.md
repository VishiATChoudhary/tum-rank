# Security and abuse model

Report vulnerabilities privately via GitHub's "Report a vulnerability" (Security tab), not in public issues.

| Attack | Defence |
| --- | --- |
| Spam / ads in comments | Plain text only, 200 chars; links, domains, emails, phone numbers, ad words rejected; repeated characters/words and shouting rejected; duplicate comments rejected |
| Hate speech | Slur blocklist (EN/DE) + community reports + moderator removal |
| Unicode tricks (zalgo, bidi override, zero-width) | NFKC normalisation, control/bidi/zero-width characters stripped, combining-mark limit |
| XSS | Server rejects markup characters; client renders all user text via `textContent`; strict CSP (`script-src 'self'`, no inline script) |
| Ballot stuffing (clearing cookies, many tabs) | One rating per course per browser (edits replace it); max 4 ratings per course per network per day; per-network hourly/daily limits; global write ceiling |
| One rating dominating the ranking | Ranking uses a Bayesian average (3 virtual ratings at 3.0), so a single 5★ can't top the table |
| Smearing or boosting a professor | Professor score only shown once two different ratings exist; name must be a real first + last name |
| Mass-reporting legit comments | Reports deduplicated per network; 3 networks needed to hide; hidden comments go to the moderation queue, not deleted, and can be restored |
| Fake courses / degrees | Suggestions are queued until a moderator approves them; degrees are imported only from TUMonline by a GitHub Action |
| SSRF via degree import | The API never fetches URLs; it only stores an integer SPO number |
| CSRF | POST requires `application/json` (forces CORS preflight) and same-origin `Origin`; cookie is `SameSite=Lax`, `HttpOnly`, `Secure` |
| SQL injection | Parameterised queries only; inputs type-checked |
| Admin token brute force | Header-only token, constant-time compare, 5 failures per 15 min per network lock out |
| Clickjacking | `frame-ancestors 'none'` |
| Oversized requests | 4 KB body limit, 10 s function timeout |
| Bots filling forms | Hidden honeypot field; bot submissions get a fake success |
| IP spoofing | IP read from Vercel's edge headers (client `X-Forwarded-For` is overwritten) |
| Privacy | IPs stored only as salted HMAC hashes; no accounts, no analytics |

Known limits: a determined attacker with many IPs (VPNs, botnets) can still add ratings slowly. Next step if that happens: verify TUM email addresses before a rating counts.
