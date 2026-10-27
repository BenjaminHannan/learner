# 149 — Whole-word entity matching in questions (Muse, 2026-09-22)

For Ben in plain language: the assistant used to hear its own taught name
inside a longer word — taught "Norland", asked about "Norlandia", it
answered anyway. Now a name only counts when it appears as a whole word
("Norland's" and "Norland?" still count). One small change, tested on two
loop versions.

## The bug

Exp 143, class 5 (case O3): `compose_n_hop` asks the notebook about the
single mentioned taught entity. "Mentioned" meant `str.find` — a raw
substring test — so "norlandia" contains "norland" and the loop answered
"Aldport" with confidence.

## Substring-habit audit (every place found)

Question-side entity matching (all five patched, question behaviour only):
(1) `_entity_mentions92` (`fable_bench92_english_arm.py:145-173`) — the O3
cause, used by the N-hop composer every "?" turn takes; (2)
`_entity_mentions` (`fable_bench73_english_arm.py:215-237`) — same
`q.find` habit, used by the 2-hop composer on the loop102-fallback path;
(3) `_seed_subjects` (`fable_qrewrite132.py:496-519`) — `ql.find` over
notebook subjects when picking rewriter seeds; (4) `_span_of`
(`fable_qrewrite132.py:340-344`) — span accounting for seeds, compounds,
and walk nodes; (5) `_decomp_subjects` (`fable_qrewrite132.py:535`) —
` tgt.lower() in ql` containment for compound targets. Loop102's own
question lookup is (1)+(2) via the loop113b router and the bench73/FakeEars
fallback chain — FakeEars itself uses possessive-split + regex fullmatch,
not substring search, so it has no instance of this habit.

Deliberately NOT changed: relation-cue matching (`cue in ql` in both
`_relation_mentions*` and the rewriter's `_word_intervals`/`_evidence_ok`)
— cues are relation words, not entities, and widening them is a different
experiment; notebook-side containment (rewriter island step
`cur.lower() in s2.lower()`, loop113 `compound_subject_hit`) — the
notebook is trusted data, not user text; loop102 `_resolve_forget_name`
whole-word-prefix — teach-side forget aid, by design.

## The change

`scripts/fable_wordmatch149_core.py`: `(?<!\w)<entity>(possessive)?(?!\w)`,
case-insensitive; longest-match-first containment blocking kept, so longer
names still win. `apply_wordmatch()` rebinds the five sites process-wide
(no file edited — the loop134 `_APOS` precedent).
`scripts/fable_loop149_agent.py`: variant A `Loop149Ears` over loop134
ears; variant B `Qrewrite149Ears` over loop132 ears (composer + rewriter
seeds). Teach path untouched; a question that now matches zero entities
clarifies (MISSING_FACT), never guesses.

## Evidence

143 re-run: variant B moves exactly O3 (WRONG→abstain); variant A moves O3
plus F5/H4, which an unregistered loop134-base run proves are
rewriter-absence (identical moves, O3 still WRONG there) — recorded FAIL
per the sealed letter. New 33-dialogue probe: 6 affix pairs abstain taught
side answers; possessives, "??", quotes, hyphen/apostrophe names
("Notre-Dame", "O'Neill"), case variants, and longer-wins all correct, 0
wrong answers. Benches: 0 per-item diffs on bench121-new/old,
bench132-new, Fable-Edit-200 for both variants (1,400 item-runs).
marks123: all 10 suites identical to sealed loop134 (400/400 bench rows,
0 reply diffs). Slowest run 152.8 s.

## Limits

English only; single deterministic run per case; possessive forms beyond
"'s" (e.g. bare plural "Norlands'") were not probed; relation-cue
substring behaviour is unchanged and could still over-license a walked hop.

## What it means

Whole-word bounding removes the substring-entity wrong-answer class with
no measured cost anywhere else tried.

## What it does not mean

It does not touch the other four 143 wrong-answer classes, and it does
not give variant A the loop132 rewriter's island coverage.
