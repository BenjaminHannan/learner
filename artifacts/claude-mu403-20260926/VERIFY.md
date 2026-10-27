# mu-404 and mu-403 verify: mu-404 INCONCLUSIVE, mu-403 FAIL (proved wrong)

"Making things up about you" thread. Written 2026-09-26 18:22 UTC (`date -u`). DEV only. Marks: PASSMARKS.md here,
sealed acf79fc43 before the run. Run: rent-mu404b (RESULTS-rent.md; 4 arms x 446 replies, reader sha e688e1b2...6a76
matched, no adapter; ~$0.67). Run files committed 19ca69669. Counts: scripts/claude_mu404_judge.py count (marks.json in
judge/). Blind recount (separate agent, own script, recount/ here): every count, p and mark matches marks.json; 0 differences.

## Counts (made-up claims about the user; C = flags summed over two blind judges, 446 replies per arm)
| arm | what | C | flagged by both | by either | think turns | non-think |
|---|---|---|---|---|---|---|
| R | 0.2c stack, right reader, no adapter (control) | 64 | 29 | 35 | 2 | 62 |
| F | R, no notebook facts in 1B prompts (mu-404) | 59 | 24 | 35 | 2 | 57 |
| P | R + one system-prompt line (mu-403) | 69 | 32 | 37 | 2 | 67 |
| T | plain MiniCPM5-1B | 139 | 62 | 77 | 37 | 102 |
Every (arm, conversation) had exactly two judgements; 0 bad packets.

## mu-404: INCONCLUSIVE (validity mark V404 failed)
- V404: R's log shows 34 chat prompts with at least one notebook fact (of 318 context_facts calls; bar 40). F's
  replies differ from R's on 24 of 446. The panel did not put the thing being tested in front of the 1B.
- Report only (not a verdict): N1 C_R 64 vs C_F 59 (bar: cut by 10 and to 0.67x); N2 R more in 6 conversations,
  fewer in 4, p 0.377.
- Why it could not pass, found after the run: devchat has 0 of 446 turns that teach a fact (it was built for chat
  quality, like mu-402's panel), so facts reached the 1B only when the reader happened to save a passing detail. The
  panel labels alone would have shown this at $0 before renting. The next test builds facts in by construction and
  counts them before any spend (NEXT below).

## mu-403 (the one line): FAIL, proved wrong
- V403 valid: P's reply differs from R's on 253 of 446 (bar 149).
- M1 fail: C_R 64, C_P 69 (the line added claims instead of cutting them). Proved wrong: C_P >= C_R.
- M2 fail: R more flags than P in 11 conversations, fewer in 15, p 0.837.
- M3 fail: over both pair judges P won 55, lost 93, tied 12 (bar: losses - wins <= 16; here 38). Each judge alone
  preferred R (29-46 and 26-47). One-sided sign p 0.001 on 93 of 148: shown on DEV that the line makes chat worse.
- M4 pass: C_P 69 <= C_T 139.
- Suggested, not tested: the line changed wording without making the 1B more careful; replies stayed the same length
  (median 46 words on the 253 differing turns in both arms) with slightly more questions (25 vs 17). Why judges
  preferred R was not examined further.

## Predictions (PASSMARKS, before the run)
- P404.1 mu-404 PASS 45%: not decided (INCONCLUSIVE).
- P404.2 C_R > C_T 50%: wrong (64 vs 139).
- P403.1 mu-403 PASS 35%: wrong.
- P403.2 M3 fails 30%: right.

## What this means
- Shown (DEV): the prompt line is not a fix for made-up claims and it hurts chat. It does not go to 0.2d.
- Shown (DEV): with the right reader and no adapter, the 0.2c stack made up far fewer claims than the plain 1B (64
  vs 139). Much of that gap comes from hand-written parts 0.2d drops: on the 46 sum questions ("think" turns) R's
  hand-written think layer (think299b) answered in a fixed "How I worked it out" form or said "I'm not sure", while
  the plain 1B often restated the user's numbers wrongly (2 vs 37 flags); outside those turns 62 vs 102.
  So 0.2d's plain-1B talker is expected to start near the plain 1B on made-up claims unless its learned reasoner takes
  the sums (suggested, untested). This matters for 0.2d's S1 win row (ADDENDUM-15).
- Not shown: whether stored facts in the prompt cause made-up claims. That needs NEXT.

## Next (replaces NEXT-draft.md's branches; sealed in its own folder before any spend)
mu-405, the plain MiniCPM5-1B talker as 0.2d uses it (no rule layers), fresh DEV panel of two-session chats: session 1
teaches 2-4 code-chosen facts, session 2 has feelings/advice/followup turns near those topics plus one ask of a stored
fact. Arms: N = session 2 only; K = + the facts as bare notebook triples (0.2c's line); W = + session 1's user turns
as 'User said, "..."' lines (0.2d's W input). Facts come from the panel's labels, so "facts in the prompt" is 100% by
construction and is counted on CPU at $0 before sealing. K vs N asks whether stored facts cause made-up claims; W vs K
asks whether keeping the user's own words (source monitoring) cuts them.
