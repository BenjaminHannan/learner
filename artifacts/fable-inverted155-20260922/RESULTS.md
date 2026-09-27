# Exp 155 RESULTS — inverted-frame teach stage (Muse)

Registered single change (scripts/fable_fix155_inverted.py +
scripts/fable_loop155_agent.py; loop150/loop135 read-only): "V is X's R." /
"V is the R of X." / "The R of X is V." saves (X, R, V) for the 42-key
table relation set (never the officeholder catch-all), via the canonical
path for one-word names and a bench-shaped screened action for longer
names. Two configs: loop155 (on loop150) and loop155x135 (with the 135
guard). Zero post-seal code edits.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar | result |
|---|---|---|
| I1 probe loop155 (47 cases) | 35 must-write >= 34 OK, 0 wrong writes | FAIL: 43 OK, 33/35 must-write OK (94.3 %), 2 WRONG-WRITE + 2 WRONG-REPLY |
| I2 probe loop155x135 (5 cases) | 3/3 mother saves + asks, 2/2 office byte-identical loop135 | PASS 5/5 |
| G1 bench 600 items | per-item verdict+reply identical loop150, 0 new wrong | PASS: 0/600 moves (edit200 150/50/0, old 157/43/0, new 136/63/1, all identical) |
| G2 marks123 vs marks150 | per-case identical | FAIL (registered): 8 rt110 case diffs (4 verdict-affecting) + 1 soak wrong + log noise; p2/p4/rt81/q4 per-case 0 moves |
| G3 sessions152 vs T-T | 0 reply moves, 0 new WRONG, 0 write moves | PASS: 6/6 sessions, 0/0/0 |
| G4 timing | every run < 1500 s Mac CPU | PASS: probes 3.5/2.9 s, bench 116 s, marks123 376 s, sessions 2.2 s |

## Diagnosis notes (one per FAIL, no silent re-runs)

- I1 (FAIL, case-authoring): all 4 non-OK cases are sealed-expectation
  errors, behaviour base-identical in each. W24/W27 ("Ovid/William Gibson
  is the author of Fasti"): base teaches author_of (pre-existing "X is the
  author of Y" pattern), the mixin returns base by design; my expectation
  wrongly assumed clarify+invert to (Fasti, author, V). Rewriting author_of
  would corrupt the sealed bench rev-* items, so the code is right and the
  cases were wrong. N06/N07 ("I think/Maybe Rita is Ann's mother"): parse
  fires, canonical twin SPLIT-refuses, verification fails, code returns the
  base clarify ("didn't understand"); I predicted the canonical SPLIT
  reply. No new wrong write anywhere: the 2 WRONG-WRITEs are byte-identical
  base teaches.
- G2 (FAIL registered, load-race): every verdict-affecting move is an
  "I didn't catch anything." empty inbox read (T2/T3/T5/D3 msg_00/01/02,
  soak turn 650) or empty `statuses` metadata with identical replies
  (N4/N6/D1/T6) — paths the change cannot touch (empty turn -> parse None
  -> base; "?" turns gated). The ref run itself contains the same artifact
  (D1 msg_00). Machine load was 218 during the registered run vs 133.5 s
  total for the ref. Open diagnostic re-run (reported, both on record) at
  load 84: rt110 62/62 verdict-identical PASS, soak wrong=0 PASS
  (marks155-rerun/); 2 remaining log-only diffs are the same empty-read
  signature with OK verdicts. Evidence favours no behaviour change, but the
  registered bar was missed: FAIL.

## What it means

Backwards sentences now teach: all 3 director probes save (Ann, mother,
Rita), office phrases stay exactly on base, bench/sessions/questions
unchanged.

## What it does not mean

F2 sentences with bench-pattern relations (author/founder) keep their
old author_of reading — the feature covers inversion, not re-ontologising.

## Deviations

None from the sealed plan except the recorded FAILs. No code edited after
the seal (seal abd5d62b… in SEAL.sha256.txt).

## Questions for Ben

Should "Ovid is the author of Fasti" mean (Fasti, author, Ovid) instead of
(Ovid, author_of, Fasti)? I kept the old reading; say the word and it
becomes the next experiment.

## Reproduce

See PASSMARKS.md Registered reproduce (probe x2, bench, marks123,
marks-diff, sessions). Diagnostic only:
marks155-rerun/rt110-report.json + soak-report.json (same commands with
--suite rt110/soak --out .../marks155-rerun).
