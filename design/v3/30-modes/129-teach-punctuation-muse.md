# 129 — Teach-punctuation strip (Muse, 2026-09-22)

## Problem

Red team 124 bug 4: bench73-style teaches (`X is a citizen of Y.`,
`Actually, …`, capital/official-language sentences) store the
sentence-final period in the value (`Italy.`), print it back (`…is
Italy..`), and break every chain through that value (`Portugal. ≠
Portugal`). Step-0 probe confirmed the leak on every teach path except
FakeEars-with-plain-period and the explicit-dot bench73 patterns.

## Design: one mixin, two applications

`scripts/fable_fix129_punct.py` — pure functions, no state:

- `strip_sentence_punct(span)`: strip-then-restore. (1) Drop wrapping
  quotes. (2) Greedily drop trailing `. ! ? ; :` runs (plus unmatched
  closers). (3) If a `.` was dropped and the stem's last token is
  abbreviation-shaped, restore one `.`. Abbreviation-shaped = contains an
  internal `.` (`D.C`, `U.S.S.R`), is a single initial (`J`), or is on the
  corporate/title/short-form list (Inc Corp Ltd St Mr Dr Ave Mt Jr …).
  Rationale: a sentence period can only be last, so interior periods are
  content; after an abbreviation token the trailing dot is ambiguous and
  keeping it is the conservative choice (dropping corrupts a name;
  keeping only risks junk on abbreviation tokens). Matched brackets and
  wrapping quotes are content and pass through byte-identical.
- `sanitize_triple` / `sanitize_action(s)`: strip subject+value spans;
  relation keys, forget/ask/clarify actions untouched; empty results
  left for downstream guards.

Applied subclass-only at two levels (defence in depth): ears `hear()`
sanitizes outgoing teach/correct actions (covers the F3-correction and
121-extra paths); loop `_act()` sanitizes again pre-write (covers the
inner-chain Bench73Stage/FakeStage delegate path). `loop129a` wraps
loop117, `loop129b` wraps loop121; question sides, mouths (modulo 117's),
guards, and sleep paths are untouched.

## Why two levels

The outer ears see correction/extra actions directly, but delegate-path
actions are built inside the wrapped chain (their correct/teach flag is
computed on the raw span — a re-teach of `Italy.` still flags `correct`,
harmless: the stored value is clean either way). `_act` is the single
funnel every write passes through, so no teach path can bypass the strip.

## Evidence (registered)

F1 45-case probe: 0 failures both loops. F2: 0 punct-caused wrong writes
of 124 turns; 129b R1/V6 BUG→OK with full 3-hop chains restored; all
other diffs confined to rendering/punct rows. F3a: identical to loop117
(Q2 per-case `diff=[]`; P2 G8 `Albany..`→`Albany.`). F3b: identical to
loop121 (`new_moves=[]`). F4: old 157/43/0, new 136/63/1 (bars met);
edit200 literal 200/200 unmet for structural reasons (50
expected-abstain items; 150/150 answers + 50/50 abstains, 0 wrong).

## Limits and follow-ups

- `?`-valued teaches still clarify via the old exp-91 screen (safe, kept).
- Title-bangs (`Help!`) are stripped like sentence-bangs: shape alone
  cannot distinguish them; scorer-v2 norm forgives, chains stay consistent
  because every teach position strips identically.
- Over-keep residual: a sentence period after a ≤ list-token word (e.g. a
  name ending `Al`) is kept. Extending the list is cheap if evidence
  appears.
- Not fixed here: all question-side composer bugs (prefix answers,
  wrong-question answers), tracked by exps 124/117.
