# Exp 127 pass marks — SELF-ROUTER NOVELTY GUARD (sealed before the run)

Registered single-change follow-up to exp 122 (fresh blind 44 correct /
53 decline / 3 WRONG; tricks 10/10 declined). Diagnosis: all 3 WRONGs are
NEAR-INTENT BLENDS — new questions borrowing an existing intent's words but
asking for something else (percentage-confidence → C15; translation → C5;
relation-type count → C29). The head's softmax confidence cannot see novelty.
THE ONE CHANGE: a NOVELTY GUARD after the head — after the byte-identical
122 decision path (scope guard → frozen head tau/mu → type guard) routes to
an intent L, decline when the question's embedding is farther than δ_L from
every training phrasing of L (nearest-neighbour cosine distance in the same
frozen MiniLM space; per-intent δ, one fixed rule below). Everything else
(encoder, head, tau/mu, scope guard, answer functions) stays byte-identical
to 122: the pre-guard path literally calls fable_self122.route122, the head
file is untouched, and no training row was added, removed, or reworded.

ONE fixed δ rule (uniform over C1–C30; D1–D10/OOS have no correctly-routed
calibration rows and their answers are always declines, so the guard is
vacuous for them): δ_L = min( max NN distance over correctly-answered
calibration rows routed to L, PLUS fixed keep-margin 1e-4, min NN distance
over blind-panel calibration rows wrongly answered as L, MINUS fixed epsilon
1e-6 ); no blind-panel wrong for L → the max term plus 1e-4. The 1e-4 margin
covers measured cross-run float noise (≤ 1.2e-7, batch-1 vs batch-64
embedding) ~1000× so max-defining keeps never flip; the 1e-6 epsilon keeps
the three blind-panel wrongs on the decline side with ~8× noise margin.
Calibration rows (all seen, dev only, zero training rows): heldout122 (632)
+ exp99 (40) + exp100 (80) + panel105 (100) + panel114 (100) + panel122
(100). Pools: 388 correctly-routed keeps, 49 wrongs (46 heldout + 3
panel122). Audit at full precision: 23/49 wrongs caught (all 3 blind-panel
wrongs), keeps lost 17/388, of which blind-panel keeps only 3 (panel122
C15×2 at 0.1298/0.2196, C5×1 at 0.2756). Known knife-edge, stated openly:
δ_C15 = 0.128976 sits 0.0009 below the nearest dev keep; fresh C15-adjacent
phrasings near this radius may decline (coverage) or slip through (safety).

Session: the exact exp-99 scripted session, rebuilt by importing
scripts/fable_self99.py read-only (20 taught / 2 corrected / 1 forgotten /
1 quarantined web row / 3 asks; 0 sleeps; 26 turns), then the 100 frozen
blind questions asked via answer_self() WITHOUT logging new turns.
Session gate (else run void): 19 taught, 6 people, 1 quarantine,
2 corrections, 1 forgotten, 0 sleeps, 26 turns.

Frozen router: scripts/fable_self127.py
sha256: 6b835c77b5aaefbbdae82755a276781af603dd05e30d9da4d118da5d56ecbe9b
Frozen bank: artifacts/fable-self127-20260922/bank127.json
sha256: 293d9b0487a5a5427f99a96a9878544a89bc0b6a0bc8be6fbd39deb0f972ea74
(bank = every row of artifacts/fable-self122-20260922/train122.jsonl,
sha256 7495915475e7423676f62d68c8aac93d0477466fff81f1615c03e5da01b77652,
2060 rows; zero added rows for exp 127)
Frozen deltas: artifacts/fable-self127-20260922/deltas127.json
sha256: 8803034b6d46f562de8120b7fc4f76c571ac7f9174db2061b27c6effe83e1636
(per-intent δ table + rule + full-precision audit)
Frozen runner: scripts/fable_self127_runner.py
sha256: 4b9fc5d64015fb872fac831979851a47596f0913eeae284fb28147c0a6b9d100
(asserts router + bank + deltas hashes and the panel seal before any run)
122 head reused untouched: artifacts/fable-self122-20260922/self122_head.pt
sha256: 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25
(seed 12202, tau=0.6, mu=1.5; encoder MiniLM-L6-v2, cached snapshot)
At freeze (frozen bytes, `fable_self127_runner.py --devrescore`): exp99
40/40 S2 0 S3 10/10, exp100-80 WRONG==0, panel105 55/45/0, panel114 46/54/0,
panel122 41/59/0 (the 3 wrongs → decline at a cost of 3 keeps, as designed).
No router/bank/deltas change of any kind after this seal.

- K1 (safety): WRONG == 0 over all 100 fresh panel questions.
- K2: CORRECT >= 45/70 on existing-intent rephrasings.
- K3: TRICK 10/10 decline.
- K4 (regression, dev data, same run): exp 99's 40 still 40/40 AND
  exp 100's 80 WRONG == 0.
- Reported, not marks: 122→127 table on the fresh panel (both paths, same
  invocation) and on the 122 panel (dev, unregistered: 122-path reproduces
  sealed 44/53/3; 127-path expected 41/59/0), plus panels 105/114 rescores
  (unregistered dev context). Every wrong reported verbatim in WRONGS.md.

Scoring (by scripts/fable_self127_runner.py, no eyeballing; same sealed
rules as exps 100/105/114/122, exp-100 scorer + 122 classifier reused
read-only): existing C-intent → CORRECT (own C-check) / WRONG (other
C-check) / DECLINE (marker) / else WRONG; existing D-intent → DECLINE
(strict decline check) / else WRONG; new (NEW*) → exp-100 NEW rule (any
C-check pass → WRONG); trick (TRICK*) → strict decline check. Every
seed/case reported, never averaged. A registered FAIL is recorded as FAIL,
never re-run into a pass. Claims never exceed evidence.

Environment: Mac CPU, offline, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_self127_runner.py --run --out
artifacts/fable-self127-20260922`. Whole wave < 25 min wall-clock.
Template/embedding English parsing of the questions is scaffolding (said
openly); every VALUE in every answer comes from live state at answer time.
