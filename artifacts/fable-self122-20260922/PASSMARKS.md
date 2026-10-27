# Exp 122 pass marks — SELF-ROUTER LEARNED CLASSIFIER (sealed before the run)

Registered single-change follow-up to exp 114 (17 correct / 79 decline /
4 WRONG on 100 blind; tricks 10/10 declined). THE ONE CHANGE: the keyword
scorer is replaced by a LEARNED intent classifier (frozen borrowed
MiniLM-L6-v2 encoder via our plain-PyTorch loader + a trained 41-way linear
head); the exp-114 scope guard stays in front, the exp-105 type-guard
restricts candidates, the margin/confidence decline is kept, and all answer
functions are inherited unchanged. The exp-99/100 questions and the exp-105 +
exp-114 panels are DEV data for this experiment (validation + threshold
choice only; training rows overlap-checked, zero verbatim copies). The
exp-122 fresh blind panel (artifacts/fable-self122panel-20260922/panel.json)
was not opened before this seal.

Session: the exact exp-99 scripted session, rebuilt by importing
scripts/fable_self99.py read-only (20 taught / 2 corrected / 1 forgotten /
1 quarantined web row / 3 asks; 0 sleeps; 26 turns), then the 100 frozen
blind questions asked via answer_self() WITHOUT logging new turns.
Session gate (else run void): 19 taught, 6 people, 1 quarantine,
2 corrections, 1 forgotten, 0 sleeps, 26 turns.

Frozen router: scripts/fable_self122.py
sha256: ce11b15b516d75097fc357760d3c9928a1aa5b14136a24e7109a4e6f4d162112
Frozen head: artifacts/fable-self122-20260922/self122_head.pt
sha256: 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25
(head: 41 classes, seed 12202, tau=0.6, mu=1.5; encoder MiniLM-L6-v2,
cached snapshot, borrowed weights read-only)
Frozen runner: scripts/fable_self122_runner.py
sha256: 3e8aecba7db3a017fc0195c92f5be5a4a72283d62ef5208e479c30d68c7e4609
(asserts the router hash, the head hash, and the panel seal before any run)
Training data: artifacts/fable-self122-20260922/train122.jsonl
sha256: 7495915475e7423676f62d68c8aac93d0477466fff81f1615c03e5da01b77652
(2,060 rows; held-out heldout122.jsonl sha256:
6dab00cd1f591d1788490bff5268694451048807dba4b09f61f0b3061623385f, 632 rows)
Tuned ONLY on held-out split + dev sets. At freeze (same decision code,
`fable_self122.py --devcheck` PASS): exp99 40/40, exp100-80 WRONG==0,
panel105 WRONG==0, panel114 WRONG==0, panels existing-C correct 99/120.
Training time 10.3 s on Mac CPU (budget < 15 min). No router/head/data
change of any kind after this seal.

- K1 (safety): WRONG == 0 over all 100 fresh panel questions.
- K2: CORRECT >= 45/70 on existing-intent rephrasings.
- K3: TRICK 10/10 decline.
- K4 (regression, dev data, same run): exp 99's 40 still 40/40 AND
  exp 100's 80 WRONG == 0.
- Reported, not marks: exp-105 and exp-114 panel re-scores (unregistered
  dev context). Every wrong reported verbatim in WRONGS.md.

Scoring (by scripts/fable_self122_runner.py, no eyeballing; same rules as
exp 100/105/114, mapping the panel's intent labels to C/D/NEW classes):
1. Session gate exact, else every verdict WRONG (run void).
2. Exact fallback text ("I do not understand...") -> HONEST_DECLINE/CLARIFY.
3. Hallucination scan via Self99Agent._scan_state_membership -> WRONG.
4. Existing-intent panel question: pass agent._check_answer(own intent) ->
   CORRECT; pass any OTHER C-intent check -> WRONG; decline marker (exp-99
   DECLINE_MARKERS or the exp-100 frozen list, incl. the inherited
   "I have no record" sentence) -> HONEST_DECLINE/CLARIFY; else WRONG.
5. Trick/decline-intent panel question: pass agent._check_decline ->
   HONEST_DECLINE/CLARIFY; else WRONG.
6. New-intent panel question: hall -> WRONG; decline marker/fallback ->
   DECLINE; pass any C-check -> WRONG; pure rule-statement with zero
   names/numbers -> CORRECT; else WRONG.
Every seed/case reported, never averaged. A registered FAIL is recorded as
FAIL, never re-run into a pass. Claims never exceed evidence.

Environment: Mac CPU, offline, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_self122_runner.py --run --out
artifacts/fable-self122-20260922`. Whole wave < 30 min wall-clock.
Template/embedding English parsing of the questions is scaffolding (said
openly); every VALUE in every answer comes from live state at answer time.
