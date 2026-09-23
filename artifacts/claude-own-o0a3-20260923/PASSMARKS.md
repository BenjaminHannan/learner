# own-O0a3 PERMISSION AUDIT — pass marks (sealed BEFORE the registered run)

Question (Ben-approved 2026-09-23): own-O0a/O0a2 asked "can every TRUE fact
get through?" This asks the other side: "can a WRONG reading get through?"
Coverage bought by loosening safety (v0 -> v1 -> learned-licensed) must show
up here as wrong readings let through.

Inputs (read-only dev sets, not panels — quoting allowed):
- artifacts/claude-own-o0a-20260923/turns.jsonl + gold.jsonl (300 turns,
  272 ASSERT/CORRECT/DENY + 76 no-save gold facts)
- artifacts/claude-own-o0a2-20260923/turns.jsonl + gold.jsonl (300 turns,
  281 ASSERT/CORRECT/DENY + 114 no-save gold facts)
- relation table artifacts/claude-smolear257-20260922/relation_table_v2.json
- compilers scripts/claude_own_o0a_compiler.py (v0) and
  scripts/claude_own_o0a2_compiler.py (v1 + learned-licensed), imported
  read-only (toks, has_span, plural/template extras reused; main() never run)

Generator: scripts/claude_own_o0a3_mutate.py (piloted to /tmp, 0 crashes).
From every gold ASSERT/CORRECT/DENY fact (553), every applicable one-change
WRONG reading: m1 owner->another name span in turn (capitalized, len>=2,
non-stopword); m2 value->another such word span; m3 owner/value reversed
(name owners only); m4 relation->another table relation whose v0 cue IS in
the turn; m5 relation->table relation whose cue is NOT in the turn (absent
under both v0 and v1 expressions, first 3 alphabetically); m6 owner
ME->WE / WE->ME / name->ME; m7 value trimmed (multi-word) or extended by one
adjacent turn word. From every gold no-save fact (190): m8 mode->ASSERT.
Fixed made-counts (deterministic generator): m1 813, m2 1639, m3 353,
m4 137, m5 1659, m6 553 (180 me2we + 353 name2me + 20 we2me), m7 542, m8 190;
total 5886 wrong readings. Each is judged under v0, v1, learned-licensed with
WE_ALLOWED=False throughout (Ben's 2026-09-23 ruling: WE is never saved as
the speaker; it asks).

Measures per (kind x rule): made / blocked / through (raw), plus the CLEAN
subset (mutants whose gold fact is itself writable under that rule: the rule
had every chance to save the truth, so blocking the mutant is a genuine
safety win and letting it through is a genuine hole). No-save golds are never
writable (mode gate), so m8 uses a REST partition instead: mutants with empty
value (55, incl. 7 that are also OTHER), OTHER-valued (1), WE-owned valued
(9) vs rest (125, full spans + table relation).

## Marks

- **Pown0a3.1**: every prediction P1..P8 below stated before the run; hits and
  misses reported honestly in RESULTS.md. No pass bar on the counts (this is
  a measurement).
- **Pown0a3.2**: 0 crashes during the registered run.
- **Pown0a3.3**: the table is complete — every kind (m1..m8, m6 in 3 subs,
  m7 in 3 subs) x every rule (v0, v1, licensed) filled with integer counts.

## Predictions (numbered, BEFORE the registered run)

Design expectation: the compiler trusts the reader's choice of span, relation
and mode, so most wrong readings sail through; only a missing cue (m5 under
v0/v1), a WE owner (m6-me2we), an empty value / OTHER relation / WE owner
(m8 structural), or a no-save mode ever blocks.

- P1 (m1 owner-swap): clean-through >= 95% under all three rules (~100%
  expected: the swapped owner is a span by construction).
- P2 (m2 value-swap): clean-through >= 95% under all three rules (~100%).
- P3 (m3 reversed): clean-through >= 95% under all three rules (~100%: both
  spans present, cue unchanged).
- P4 (m4 cued-relation-swap): clean-through >= 90% under all three rules
  (n small: only turns naming two relations; ~109-132 clean per rule).
- P5 (m5 uncued-relation-swap): clean-blocked 100% under v0 and 100% under
  v1 (no-relation-cue by construction); clean-through 100% under
  learned-licensed (cue dropped, spans/mode unchanged).
- P6a (m6 ME->WE): clean-blocked 100% under all three rules (WE-owner under
  Ben's ruling).
- P6b (m6 name->ME): clean-through >= 95% under all three rules (ME needs
  no span).
- P6c (m6 WE->ME): clean base is EMPTY by construction (no WE-owned gold is
  writable while WE_ALLOWED=False), so no clean prediction is possible;
  raw through >= 70% under each rule (ME needs no span; blocks only from
  inherited gold defects such as missing cues).
- P7 (m7 value +-1 word, trim/extend-next/extend-prev): clean-through >= 90%
  under all three rules (trimmed head and adjacent-word extensions remain
  whole-word spans by construction).
- P8 (m8 no-save->ASSERT): empty-value mutants (55) blocked 100% under all
  rules; OTHER-valued (1) blocked 100%; WE-owned valued (9) blocked 100%;
  rest (125): licensed 100% through, v1 75-95%, v0 40-65%, ordered
  licensed >= v1 >= v0 (rule nesting guarantees the ordering).

Run (CPU only, no model, no downloads, deterministic — no randomness):
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/claude_own_o0a3_mutate.py artifacts/claude-own-o0a3-20260923`
Output: mutations.jsonl + summary.json + RESULTS.md. Registered summary must
be identical to the pilot summary (determinism check); any diff is reported.
