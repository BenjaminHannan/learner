# g406-2 and g406b: can GLM 5.3 Flash, at reasoning effort "low", spot made-up claims about the user the way the blind judges do?

"Making things up about you" thread. Written 2026-09-26 23:44 UTC (date -u). DRAFT for the Thread manager's review. It will be sealed
before any GLM call, and nothing below changes after an answer has been seen. DEV data only. Nothing is trained.
Cost: $0 (Mac CPU, GLM through Ben's opencode subscription, this thread's share of 3 calls at a time).

## Why a new gate, not g406's resume
g406 (sealed 79032cbd8) got 80 of 560 answers before stopping, with 57 of them unusable (VERIFY-run1.md 81be47cc3,
INCONCLUSIVE on the route). Its resume (handoff/held/claude-madeup-g406r-mac.md) was held until the reading thread's
opencode diagnosis came back. The diagnosis (lis-320 ADDENDUM-6) found:
- opencode's default reasoning effort makes a call take 88-460 s (ocdiag, ocdiag2).
- With `--variant low` the same prompts parsed 4 of 4 in 5-15 s (ocdiag3).
- Pilot 4 on low made 60 calls with 0 failed calls, 58 parsed, in 3.1 minutes.

g406's ADDENDUM-3 said a change to how GLM is called makes a new gate, not a resume. The reasoning effort is part of
the marker, so this is g406-2. Its only change against g406 is the call: scripts/claude_lis320_glm_oclow.call_low.
That is helper v1.1's call with "--variant low" on the run line; the helper file is unedited. Run 1's 80 rows, which
used the default effort, are not merged in. The held resume job will not run.

## Why g406b now, alongside it
mu-405b (VERIFY.md 00816bdbe) showed that the made-up claims mu-406 must remove appear when the talker reads its memory.
- With the memory block in the user message: U 166 flags vs 31 for W.
- A code check for invented slot values catches almost none of them. 1 of U's 300 replies names a slot value the user
  never gave. That is a post-hoc count, so suggested only.
- So mu-406's labels must come from GLM, and must be checked on transcripts where the talker has the memory. g406's
  PASSMARKS already named that check (g406b, "two-session rubric on mu-405's judged packets, before any training").
- mu-405b's 240 packets now have two blind judges each, so g406b can run in the same job. It has its own verdict.

## Setup
- Script: scripts/claude_g406_2_glm.py.
  - `--mode one` (g406-2) uses g406's build_prompt, parse and packets unchanged: mu-402 and mu-403/404, 560 transcripts,
    2,990 replies.
  - `--mode two` (g406b) uses mu-405's two-session rubric: JUDGE-claims405.md from "For EVERY assistant reply" through
    "If yes, flag it.", unchanged. It runs on mu-405b's 240 judged packets (N, W, U and H arms mixed, 1,200 replies).
    The framing lists the user's earlier messages under the name the rubric uses (`earlier_user_messages`).
  - One call per transcript. A packet counts as done only when a usable row exists, and later batches retry failed
    packets. Each row keeps its error text; no reply text is kept.
- Truth: the two blind Opus judges' flags per reply. g406-2 uses the mu-402/403 judge folders. g406b uses mu-405b's
  judge/out, whose blind recount matched.
  - "either" = at least one judge flagged the reply; "both" = both did.
  - Base either-rates, counted at $0 before any call: g406-2 0.1124 (336 of 2,990); g406b 0.14 (168 of 1,200,
    131 flagged by both).
- Count: scripts/claude_g406_count.py (sealed, unchanged). It runs on the one-row-per-packet file
  (`--best-to`), once per gate.

## Marks (g406's, unchanged, applied to each gate separately)
- V (validity): usable answers on at least 95% of packets: g406-2 at least 532 of 560, g406b at least 228 of 240.
  Otherwise INCONCLUSIVE.
- G1: of the replies both judges flagged, GLM flags at least 70%.
- G2: among replies GLM calls clean, the either-rate is at most half the base: g406-2 at most 0.0562, g406b at most
  0.07.
- G3: GLM calls at least 50% of replies clean.
- PASS = V, G1, G2 and G3.
- Proved wrong (GLM's marks carry no signal): among replies GLM flags, the either-rate is at or below the base.
- G1's meaning, from g406 ADDENDUM-1: GLM catches about as much as one judge catches of the other's flags. It does
  not mean GLM is as good as the judges.

## What each result means for mu-406
- g406b PASS: mu-406 picks its training replies with GLM's two-session marks, at reasoning effort low, in this
  prompt form. This holds whatever g406-2 says, because g406b is the form mu-406 will use.
- g406b FAIL or INCONCLUSIVE: no GLM marks for mu-406. The prompt is not reworded to chase a pass. mu-406 then moves
  to its named fallback (PLAN-draft-2.md).
- g406-2 is reported with its own verdict. If g406-2 passes and g406b fails, the two-session reading is where GLM
  fails. If both fail, low effort may be the cause; that is suggested only, since g406 at default effort never
  finished.

## Report only
- Per arm for g406b (--arm-report): GLM flags, judges' either and both, and GLM's catches of both-flagged replies for
  N, W, U and H. The question is whether GLM sees U's extra claims.
- Hard cases: GLM's flag rate on replies only one judge flagged.
- Per source for g406-2.
- Call seconds, error prefixes, and parsed share.

## Predictions (before any call)
- P406-2.1: g406-2 PASS, 30% (g406's 35%, lowered because low effort may read less carefully).
- P406b.1: g406b PASS, 30%.
