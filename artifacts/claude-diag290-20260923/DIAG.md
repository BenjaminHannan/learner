# DIAG 290 — why 138m says "I didn't understand that question" where 138k declined

Verdict: CAUSE FOUND. One stage does it: the exp-224 decline rewrite
(`install_decline224`), installed on every 138m build. It turns 138k's honest
"don't know" decline into 138m's "didn't understand" Q2 sentence on exactly
the turns the ears never parsed as questions (14 of 42 dev dialogs: all
"Does A have an R?" turns plus two inverted word orders). The question was
truly NOT parsed (no `ask` act, question branch never ran) — 138m did not
parse-it-and-find-nothing. But the Q2 wording is still misleading: it claims a
comprehension failure, while for the never-taught / taken-back arms the
notebook genuinely holds no such fact, so 138k's "I have no record of it" was
the true half of the old reply. 224c, 233, 234, 230c/219 and 227c are all
exonerated by direct test.

## Marks table (integer counts, all computed from rows.jsonl by script)

| # | Check | Count |
|---|-------|-------|
| M1 | Dev dialogs written (own wording, fictional names), each run fresh on 138k, 138l, 138m | 42 dialogs, 126 runs |
| M2 | 138k vs 138l full-matrix reply equality | 42 / 42 identical |
| M3 | Parsed turns (ears emitted `ask`) with byte-identical reply on k, l, m | 28 / 28 |
| M4 | Unparsed turns flipped glue -> Q2 from 138k to 138m | 14 / 14 |
| M5 | 224-alone stack (138l+224) reproduces 138m's Q2 on the 14 | 14 / 14 |
| M6 | 224c engagements anywhere (q1honest log entries, all stacks) | 0 |
| M7 | 138m-class stack WITHOUT wrappers serves the old glue on the 14 (class layers exonerated) | 14 / 14 |
| M8 | Question turns that wrote to the notebook | 0 / 180 |
| M9 | d224 log entries on 138m that are kind Q2 with qbranch=False and acts (clarify, clarify) | 14 / 14 |

## Shape x arm table (reply kind per agent; n = dialogs)

138k and 138l are identical on all 42 (M2), so one column covers both.

| Shape | Arm | n | 138k / 138l reply kind | 138m reply kind |
|-------|-----|---|------------------------|-----------------|
| What | taught | 2 | 2 answer | 2 answer (same text) |
| What | never | 5 | 5 decline-targeted ("I don't know Bex's father/hobby/...") | 5 decline-targeted (same text) |
| What | taken-back | 3 | 2 decline-targeted + 1 answer (replace-then-ask-new-value) | same 2 + 1 (same text) |
| Where | taught | 2 | 2 answer | 2 answer (same text) |
| Where | never | 4 | 4 decline-targeted | 4 decline-targeted (same text) |
| Where | taken-back | 2 | 2 decline-targeted | 2 decline-targeted (same text) |
| Who | taught | 2 | 2 answer | 2 answer (same text) |
| Who | never | 4 | 4 decline-targeted | 4 decline-targeted (same text) |
| Who | taken-back | 2 | 2 decline-targeted | 2 decline-targeted (same text) |
| Does | taught | 2 | 2 decline-glue | 2 didn't-understand (Q2) |
| Does | never | 4 | 4 decline-glue | 4 didn't-understand (Q2) |
| Does | taken-back | 4 | 4 decline-glue | 4 didn't-understand (Q2) |
| Does (boundary: "Has Bex a dog?", "Does Lena have mother?") | boundary | 2 | 2 decline-glue | 2 didn't-understand (Q2) |
| Does (boundary: "Is Bex's mother Talia?") | boundary | 1 | 1 answer ("Yes, ...") | 1 answer (same text) |
| What (boundary: "What is the city of Bex?") | boundary | 1 | 1 answer | 1 answer (same text) |
| Where (boundary: "Where lives Bex?") | boundary | 1 | 1 decline-glue | 1 didn't-understand (Q2) |
| Who (boundary: "Who is mother of Bex?") | boundary | 1 | 1 decline-glue | 1 didn't-understand (Q2) |

Kind key: decline-glue = full 138k double decline ("I do not know that from
what you taught me. ..."); decline-targeted = parsed lookup miss ("I don't
know Bex's father.", "I don't know anyone called Zane."); didn't-understand =
224 Q2 ("I didn't understand that question — could you say it another way?").

## Which change caused it (exact file:line)

`scripts/fable_loop224_agent.py:113-137`, function `turn224`, installed on
every 138m build by `scripts/claude_loop138m_agent.py:210-215`
(`_build138j_plus224c` calls `L224.install_decline224(loop)` at :213, then
`L224C.install_q1honest224c(loop)` at :214). The kind decision is :121-127:

- no `ask` act in the tapped ears acts -> not Q1;
- `state["qbranch"]` is False on all 14 turns, but `_pipeline_question(text)`
  (`:73-81`) returns True for any text ending in "?" -> kind Q2;
- Q2 sentence served from `scripts/fable_decline224.py` (`Q2_SENTENCE`).

Bisect proof: 138l + `install_decline224` alone flips 14/14 to the exact 138m
Q2 text with parsed controls unchanged (M5); adding 224c changes nothing
(q1c log 0 entries everywhere, M6); the full 138m class stack (233 rewrite,
234 small talk, 230c/219 name line, 227c identity gate) with the two wrappers
omitted serves the byte-identical 138k glue on 14/14 (M7).

## Was the question parsed? (honesty test)

No — genuinely not parsed, on all 14 turns, on every agent. Evidence per turn
(recorded in rows.jsonl): ears acts = `[clarify]` only (heard twice: the 154d
peek re-hear plus the real hear), `has_ask` = False, outer ears
`last_stage` = "none", `last_routed.intent` = "DECLINE", notebook events
unchanged (0 writes, M8). So 138m did NOT parse the question and find
nothing; its pipeline never recognized these turns as questions at all.

Two honesty caveats, both in 138m's disfavor:
1. The Q2 verdict did not come from the pipeline treating the turn as a
   question (`qbranch` False 14/14). It came from the text-shape fallback
   ("ends with ?"), so the reply says "that question" about a turn the
   pipeline itself only ever `clarify`-ed.
2. For the never-taught (4 Does) and taken-back (4 Does) arms the notebook
   truly holds no such fact, so the discarded knowledge-half of the old glue
   ("I have no record of it, so I will not guess") was TRUE. 138m keeps only
   the comprehension-half, misattributing a knowledge gap to a hearing gap.

## Smallest single change restoring the honest decline

One new guard condition in the 224 swap (new wrapper file; no frozen file
touched, additive-only): when the tapped acts contain no `ask`, the question
branch never ran, and the acts are `clarify`-only, pass the turn through with
the original glue instead of serving Q2. That restores the byte-identical
138k reply on exactly these 14 turns; parsed turns never reach the glue, and
the Q1/S1 paths are untouched, so no other reply changes. (Diagnosis only —
not implemented here.)

## Every move, miss, deviation

- Moves (k -> m reply changes): 14, all glue -> Q2, all on unparsed turns
  (12 Does-shape + "Where lives Bex?" + "Who is mother of Bex?"). 0 moves on
  the other 28 dialogs.
- Misses (both agents wrong): `t-does-dog`, `t-does-mother` — fact TAUGHT and
  stored, yet 138k serves the glue and 138m serves Q2 (2/2 taught-Does).
  Pre-existing 138k limitation (Does-questions never parse), not caused by
  the 138m change; the kind still flips there.
- Correct controls: all 6 taught What/Where/Who answer on all agents;
  `b-what-replace` answers the new value on all agents; "Is Bex's mother
  Talia?" answers "Yes, ..." on all agents (yes/no path needs no `ask`).
- Deviation (method): first bisect stack labeled `138m-no224` leaked the
  wrappers (its build path re-entered the 224-installing builder;
  `has224=True`), so its 18 rows are VOID. They match full-138m 18/18
  (consistency check) and are superseded by `138m-no224v2` (asserted
  wrapper-free, M7). Rows kept, relabeled, nothing deleted.
- Env: load 36-51 (bar 60), disk 14 GB free (bar 3 GB), 1 process, CPU only,
  no panels opened, no model changes.

## What it means / what it doesn't mean

- Means: if a user asks "Does A have an R?" (or an inverted "Where lives A?"),
  138m will say it didn't understand even when the real problem is just that
  nobody taught it that fact. The old "I have no record of it" told the truth;
  the new sentence hides it. Any scorer or user reading "didn't understand" as
  a hearing failure will misdiagnose a knowledge gap.
- Doesn't mean: 138m is lying about parsing — it really didn't parse these.
  It also doesn't mean What/Where/Who answers moved: all 28 parsed turns are
  byte-identical across 138k, 138l and 138m, and 138m never invents facts here
  (0 question-turn writes). The damage is exactly 14 turns wide and one
  wrapper deep.

## Repro

- `scripts/claude_diag290_run.py` — 42 dialogs x 138k/138l/138m -> rows.jsonl
- `scripts/claude_diag290_bisect.py` — S1/S2/void-S3 (18-dialog subset)
- `scripts/claude_diag290_bisect2.py` — corrected S3 (`138m-no224v2`)
- `scripts/claude_diag290_summary.py` — every count in the marks table
- `scripts/claude_diag290_pilot.py`, `scripts/claude_diag290_probe.py`,
  `scripts/claude_diag290_probe2.py` — pilots/probes (superset exploration)
- Raw data: `artifacts/claude-diag290-20260923/rows.jsonl` (198 rows; 18
  labeled `138m-no224` are VOID per above)
- Runner: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B <script>`
