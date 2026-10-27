# 127 — Self-router novelty guard: decline unfamiliar phrasings (Muse)

Exp 122 (registered FAIL) left a precise diagnosis: 44 correct / 53 decline
/ 3 WRONG on a fresh blind 100, tricks 10/10 declined. All 3 WRONGs are
NEAR-INTENT BLENDS — new questions that borrow an existing intent's words
but ask for something else ("How confident are you, as a percentage…" →
certainty intent; "Translate everything you know about Mira into French" →
provenance intent; "How many distinct relation types…" → rule-count intent).
The head's softmax confidence cleared all three (conf 0.88–1.00, margins
2.3–8.3). Exp 127 makes ONE change and tests it on a 100-question panel
written blind by another agent.

## The one change

`scripts/fable_self127.py` adds a NOVELTY GUARD after the head. The
pre-guard path is byte-identical to 122 — it literally calls
`fable_self122.route122()` (scope guard → frozen MiniLM encoder + frozen
41-way head, tau=0.6/mu=1.5 → type guard). If that path routes to an intent
L, the guard embeds the question with the SAME frozen encoder and measures
the nearest-neighbour cosine distance to the neighbour bank: every
training phrasing of L (all 2,060 train122 rows, pinned by hash, zero
added rows for this experiment). Distance strictly above δ_L → the
identical inherited HONEST_DECLINE; otherwise L stands and the answer
comes from the untouched exp-99 body. D/OOS intents have no δ (their
answers are always declines, so the guard is vacuous there).

Per-intent δ, ONE fixed rule, no hand-tuning: δ_L = min( max NN distance
over correctly-answered calibration rows routed to L, plus fixed
keep-margin 1e-4, min NN distance over blind-panel calibration rows
wrongly answered as L, minus fixed epsilon 1e-6 ); no blind-panel wrong
for L → the max term plus 1e-4. Calibration rows (all seen, dev only, zero
training rows): heldout122 + exp99/100 + panels 105/114/122 (388 keeps,
49 wrongs). The constants handle measurement reality: cross-run float
noise is ≤ 1.2e-7 (batch-1 vs batch-64 embedding), so 1e-4 keeps
max-defining rows noise-proof while 1e-6 keeps the three dev wrongs on
the decline side. Full-precision audit: 23/49 wrongs caught (all 3
blind-panel wrongs), keeps lost 17/388 — only 3 of them blind-panel keeps
(panel122 C15×2, C5×1).

## What tuning taught (before freezing)

Two findings, both from numbers, not eyes. First, softmax confidence and
novelty are nearly orthogonal here: the three dev wrongs had the HIGHEST
confidences on their panel, while 16 correctly-routed existing questions
sat below the confidence bar — so no tau/mu retune can separate them, and
distance is the only remaining signal. Second, distance separates far
novelty cleanly (20 wrongs beyond every keep, zero coverage cost) but near
blends overlap the keep distribution: Q078 sits at 0.1290 against C15
keeps at 0.1298–0.4143, so catching it costs 14 C15 keeps by any
threshold. A 4-decimal rounding bug in the first δ draft proved the
knife-edge is real: it hid 2 dev wrongs and flipped 2 keeps before the
full-precision rewrite caught it. The C15 δ (0.1290 vs nearest keep
0.1298) ships with no margin, stated openly in PASSMARKS.md.

## Freeze and blind run

Router + bank + δ hashed into `artifacts/fable-self127-20260922/
PASSMARKS.md`, PASSMARKS sealed with shasum, ledger P127.1–P127.5 appended
— all before the fresh panel was opened (the panel seal already existed;
only its filename was polled, never its contents). One 10.7 s run: K1 1
WRONG (FAIL), K2 45/70 (PASS at bar), K3 10/10 (PASS), K4 PASS (40/40,
exp100-80 zero WRONG). Same invocation, same panel, frozen 122 path: 50
correct / 47 decline / 3 WRONG, tricks 9/10. Dev context, same invocation:
panels 105/114 0 WRONG with keeps intact, panel122 41/59/0, and the 122
path re-run reproduces sealed 44/53/3 exactly.

## Reading the FAIL honestly

The guard converts 2 of 3 fresh wrongs (opinion-about-Paris, and a
teach-others trick the scope guard itself missed) at a cost of 5 keeps;
the survivor, word-count → turn-count, sits inside δ_C18 — nearer than
the nearest known-good phrasing, hence invisible to any distance rule.
K2 passed only because this panel routed easier for the head (50/70) than
the 122 panel (44/70). The honest ceiling: distance guards harvest far-
and mid-range novelty; the nearest blends need a different signal (e.g. a
task-word check: "translate", "how many words", "percentage" asking for
something the intent cannot produce) — the obvious next one-change
experiment.

## What it means

On every blind set tried, the guard strictly improves safety over the
head alone (dev 3→0 wrongs, fresh 3→1, tricks to 10/10) with small,
measured coverage cost (0 keeps on two dev panels, 3–5 where blends crowd
an intent) and zero invented names/numbers.

## What it does not mean

No fix for the nearest blends, no margin where it matters (C15), no new
answering power: values still come only from live state via the 40 frozen
bodies. Nothing here touches real English understanding beyond
scaffolding routing.

## Deviations

D1: MiniLM inherited from 122 (borrowed frozen encoder, same loader).
D2: three dev-only helpers under my prefix (calibrate, full-precision
deltas writer, runner with devrescore/registered modes); none touched
after the seal. D3: the δ rule's two fixed constants (above) — one rule,
uniformly applied.
