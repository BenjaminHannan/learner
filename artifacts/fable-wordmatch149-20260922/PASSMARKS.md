# PASSMARKS — Experiment 149: whole-word entity matching in questions (2026-09-22)

Single-change fix for exp-143 class 5 (O3): "What is the capital of
Norlandia?" matched taught "Norland" by substring (`str.find`) and answered
"Aldport". THE ONE CHANGE: an entity counts as mentioned only on word
boundaries (case-insensitive as today; trailing possessive "'s" and trailing
punctuation allowed); longer names still win over shorter ones. New files
only: `scripts/fable_wordmatch149_core.py` (matcher + process-wide
rebinding), `scripts/fable_loop149_agent.py` (variant A Loop149 over
loop134; variant B Qrewrite149 over loop132), drivers
`scripts/fable_wordmatch149_run143.py` / `_probe.py` / `_bench.py`, artifact
`artifacts/fable-wordmatch149-20260922/`, doc
`design/v3/30-modes/149-whole-word-entities-muse.md`. No existing file is
edited; sealed 143/bench/marks files are read-only.

Substring-habit audit (every place; only the five entity sites change):
patched: (1) `fable_bench92_english_arm.py:145-173` `_entity_mentions92`
(`q.find`, the O3 cause); (2) `fable_bench73_english_arm.py:215-237`
`_entity_mentions` (same habit, loop102-fallback path); (3)
`fable_qrewrite132.py:496-519` `_seed_subjects` (`ql.find`, rewriter seeds);
(4) `fable_qrewrite132.py:340-344` `_span_of` (span accounting);
(5) `fable_qrewrite132.py:535` `_decomp_subjects` target containment.
Listed, NOT changed (relation cues, not entities): `_relation_mentions92`,
`_relation_mentions` (bench73), `_word_intervals` / `_evidence_ok` cue
coverage in the rewriter. Listed, NOT changed (notebook-side, not question
matching): island containment `cur.lower() in s2.lower()` (qrewrite132),
`compound_subject_hit` containment (loop113), loop102 `_resolve_forget_name`
whole-word-prefix (teach-side forget, by design).

Pre-seal dev evidence (not registered): core `--selftest` 15/15; in-process
O3 shape abstains on both variants while "Norland?" and "Norland's capital?"
still answer.

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B ...`; every seed/case reported, never averaged):
  scripts/fable_wordmatch149_run143.py --variant 149 | qrewrite
    (sealed 143 runner imported; ART redirected here; daemon/config swapped)
  scripts/fable_wordmatch149_probe.py --variant 149 | qrewrite
    (33 sealed probe dialogues, fresh daemon dir each)
  scripts/fable_wordmatch149_bench.py --variant 149 | qrewrite
    (scorer v2 imported from bench132 runner; suites below)
  scripts/fable_marks123_all.py --agent scripts/fable_loop149_agent.py
    --config artifacts/fable-wordmatch149-20260922/loop149-config.json
    --out artifacts/fable-wordmatch149-20260922/marks149 --workers 4
    (variant A only; generic runner picks Loop149Daemon by name)

| Mark | Pass condition |
|---|---|
| W1 143 re-run, variant A (loop134+149) | O3 verdict OK-by-abstain (no longer answers); 0 of the other 123 cases worse than sealed 143 rows (worse = OK->non-OK or MISSED->WRONG-ANSWER; improvements allowed) |
| W1 143 re-run, variant B (loop132+149) | same bar vs sealed 143 rows |
| W2 new probe (33 dialogues, sealed pre-run) | 33/33 as sealed (untaught look-alikes abstain: w01 w03 w04 w06 w08 w10 w12 w14 w17 w19 w21 w26 w27; taught/possessive/punct/hyphen/apostrophe/case/longer-wins answer: all others); 0 WRONG-ANSWER on either variant |
| W3 benches per-item identical except predicted | predicted diffs: NONE on any suite/variant. Variant A vs sealed loop134 rows (bench121-new 136/63/1, bench121-old 157/43/0, fable_edit_200) + same-process loop134 baseline for bench132-new; variant B vs sealed loop132 rows (bench132-new) + same-process loop132 baseline for the other three suites |
| W4 marks123 vs loop134 | every suite verdict identical to sealed marks134 (p2, p3, p4, rt110, q1, bench, rt81, sleep, soak, q4); any reply diff outside predicted-none reported verbatim |
| W5 time + shape | each registered run < 25 min wall-clock Mac CPU; daemon wrappers accept idle_seconds (inherited) |

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.
