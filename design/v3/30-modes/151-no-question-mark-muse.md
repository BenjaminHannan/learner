# 151 — No-question-mark fix (Muse, 2026-09-22)

## Problem

Director probe: after "The capital of Peru is Lima", the "?" question
answers but five no-"?" variants ("What is the capital of Peru", lower-case,
"who is jo ng married to", "whats ...", "Where is Jo Ng a citizen of") all
clarify. Phone typists skip "?". Red-team 143 J5/J10 (sealed, read-only)
are the same bug class: "?"-free questions judged MISSED.

## Where the loop decides question vs statement

`scripts/fable_loop121_agent.py:175` (`Loop121Ears.hear`): ends in "?" ->
question side (exact loop113b); anything else -> teach path. Supporting
gates: `fable_loop113b_agent.py:70` (N-hop router only on "?"),
`fable_loop132_agent.py:83` (rewriter only on clarified "?"),
`fable_loop102_agent.py:290` (qualifier strip never on "?").

## The one change

A message containing NO "?" at all is fed through the exact base path as
its byte-exact "?" twin (whitespace collapsed, trailing "." / "!" stripped,
"?" appended) iff (a) its first word after repeated openers
hey/hi/ok/so/and/um is in the sealed list — what, whats, what's, who,
whos, who's, whose, where, wheres, where's, which, when, how, is, are, was,
does, do, did, can, could, tell me, do you know — and (b) both teach
parsers (`hear_teach_template`, `hear_teach_extra`) reject the collapsed
text and its qualifier-stripped form. Messages containing "?" are untouched;
teaches ("The capital of Peru is Lima" parses, so condition (b) blocks),
forgets, hearsay, and corrections never trigger. A rewrite can only turn a
clarify/teach-path miss into the twin reply, never alter a "?" reply.

## Build (additive only)

`scripts/fable_qmark151_core.py`: sealed list + pure `should_rewrite_151` /
`with_question_mark_151`. `scripts/fable_loop151_agent.py`: `QMarkMixin151`
(MRO-first `hear`, tags stage `loop151-qmark+...`) over `Loop134Ears`
(variant A) and over `Loop132Ears` + 149 wordmatch re-applied at bind
(variant B, loop132+149 shape). Variant-B names avoid Loop\*/DEFAULT_\*/
build_agent\* so generic runners pick A. Configs
`artifacts/fable-qmark151-20260922/loop151(-qrewrite)-config.json`.

## Evidence and marks

Q1: 32 sealed pairs (frames, lower-case, whats/tell-me/do-you-know, 1-/2-hop,
4 untaught) 32/32 byte-equal per variant; 22 non-questions 22/22 marked
clarifies, 0 writes. Q2: J5/J10 MISSED->OK, 0/122 worse vs sealed
qrewrite149. Q3: 0 diffs, 4 suites x 2 variants (all 800 questions end in
"?"; 0 bench teaches trigger with both parsers rejecting). Q4: 10/10 suite
verdicts identical to sealed marks134 (p2 FAIL-status and rt81 61/13 match
base exactly); one predicted reply-text allowance unused (0 text diffs).
Slowest run 135.0 s. SCORE PASS.

## What it means / does not mean

Skipped "?" no longer costs the answer on question-shaped non-teaches. It
teaches nothing new: untaught questions still abstain, non-questions still
clarify, and "?" replies are untouched by construction.
