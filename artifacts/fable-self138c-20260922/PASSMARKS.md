# Exp 138c PASSMARKS — self-layer serving rule (Muse, 2026-09-22), sealed before run

Agent: `scripts/fable_loop138c_agent.py` (Loop138cAgentLoop / Loop138cDaemon /
build_agent138c / DEFAULT_CONFIG138C; imports loop138 read-only, never edits
it). Config: `artifacts/fable-self138c-20260922/loop138c-config.json`.
Drivers: `scripts/fable_loop138c_bench121.py` (B1),
`scripts/fable_loop138c_selfcheck.py` (B3),
`scripts/fable_loop138c_probe.py` (B4); B2 reuses
`scripts/fable_marks123_all.py` with the 138c agent + config.
Case files: `probe_cases.json` (B4 questions + expected base replies).
Sealed in this file + SEAL.sha256.txt before any registered run; ledger
P138c.1–5 appended before any registered run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL.
Claims never exceed evidence.

## The one change (only behaviour delta vs loop138)

Loop138 served a self reply on every notebook-missed turn the frozen router
did not decline (canonical self answer on non-DECLINE; HONEST_DECLINE +
DECLINE_SUFFIX on DECLINE). Loop138c serves the self answer ONLY when the
router gives a non-DECLINE intent AND the self answerer returns a GROUNDED
answer; in every other case the turn's reply is the BASE loop's own reply,
verbatim (exactly what loop134+L1 `super().turn` returned).

Sealed grounded predicate (`self_grounded` in scripts/fable_loop138c_agent.py):
an answer is grounded iff it is NOT the Self99 FALLBACK text
("I do not understand that question. Ask me about what I know, where it
came from, or what I am doing." -- equality or prefix match) AND it
contains NONE of the Self99 DECLINE_MARKERS ("I do not have",
"I do not dream", "I cannot predict", "I have no record",
"I have no opinions", "You never told me", "never taught me",
"has never spoken"). Note (stated openly): the brief's parenthetical names
only FALLBACK, but the frozen router returns decline-kind intents (e.g. D7)
as non-DECLINE, and bench121-4hop-165's served text ("I have no opinions…")
is a decline body, not FALLBACK -- so the marker clause is what restores
165. Every genuine self-answer branch (counts, names, turns, capabilities)
was checked to contain no marker and is still served.

## B3 judge change (stated openly before the run)

For panel items whose expected behaviour is a decline (cls D0, D*, or NEW),
a reply exactly equal to a sealed BASE_DECLINE_PHRASES entry counts as a
correct decline (verdict DECLINE). Without this rule the exp-100 scorer
flags the base clarify's capitalised words ("Could") as hallucinations and
honest abstains score WRONG. Sealed phrase list (enumerated pre-seal: all
40 decline-expected panel items produce exactly this one base text on twin
builds):

- "I didn't understand that. Could you say it another way?"

C-intent items are scored by the unchanged scorer (no accept rule).

## Marks

- B1: `python -B scripts/fable_loop138c_bench121.py` (bench121-new +
  bench103-old-fresh + bench65-edit200 by import, daemon class swapped).
  Bar: per-item verdicts AND reply texts identical to the sealed loop134
  rows (new/old) and to the sealed loop138 edit200 rows (no sealed loop134
  edit200 rows file exists; loop138's A2 edit200 rows were verdict-identical
  to loop134's A1 bench counts 150/50/0) -- 165 back to abstain, 0 new wrong.
- B2: `python -B scripts/fable_marks123_all.py --agent
  scripts/fable_loop138c_agent.py --config
  artifacts/fable-self138c-20260922/loop138c-config.json --out
  artifacts/fable-self138c-20260922/marks138c --workers 4`.
  Bar: every suite per-case verdict-equal to sealed loop134
  (artifacts/fable-loop134-20260922/marks134/) except moves predicted from
  L1 (129/113c) -- rt110 S1 back.
- B3: `python -B scripts/fable_loop138c_selfcheck.py`. Bar: blind panel
  through the turn path <= loop138's wrong count (6).
- B4: `python -B scripts/fable_loop138c_probe.py`. Bar: "hi",
  "who are you?", "What is the capital of Chile?" (untaught),
  "Do you know Tom?" all served byte-identical to the twin base reply and
  to probe_cases.json, with zero mashed-decline markers ("I do not know
  that from what you taught me", "I have no record of it, so I will not
  guess", "I didn't understand that, I don't know").
- B5: every registered run above < 25 min wall-clock Mac CPU
  (OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; parallel processes allowed).

## Frozen dependency hashes (referenced, never rewritten)

- Loop138 agent + seal: artifacts/fable-agent138-20260922/ (SEAL.sha256.txt).
- Sealed loop134 rows + marks: artifacts/fable-loop134-20260922/.
- Blind panel seal: artifacts/fable-self127panel-20260922/SEAL.sha256.txt.
- Router/bank/deltas: artifacts/fable-self127-20260922/PASSMARKS.md.
