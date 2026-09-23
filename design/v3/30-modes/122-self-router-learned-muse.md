# 122 — Self-router with a learned intent classifier (Muse)

Exp 114 (registered FAIL) left a precise diagnosis: 17 correct / 79 decline /
4 WRONG on a fresh blind 100, tricks 10/10 declined. The scope guard works;
the ceiling is VOCABULARY — the keyword scorer cannot recognise oblique
phrasings (46 margin declines on existing intents, plus synonym misfires like
"tally" and "cite its origin"). Exp 122 makes ONE change and tests it on a
100-question panel written blind by another agent.

## The one change

`scripts/fable_self122.py` replaces the keyword scorer with a LEARNED intent
classifier. Everything else is inherited untouched: the exp-114 scope guard
runs first, the exp-105 question-type guard restricts candidates, the
margin/confidence decline converts doubt into the identical HONEST_DECLINE
sentence, and every answer comes from the untouched exp-99 bodies by calling
the grandparent `Self99Agent.answer_self()` on the predicted intent's
canonical question (the keyword router is bypassed, never edited).

The classifier is a frozen borrowed MiniLM-L6-v2 encoder (22.6M params,
sentence-transformers/all-MiniLM-L6-v2, cached on the Mac) through OUR
plain-PyTorch loader (`fable_bert_loader`: `read_safetensors`, `Bert`,
`WordPiece`; D1 below), mean-pooled and L2-normalised to 384 dims, plus a
trained 41-way linear head (40 intents C1–C30/D1–D10 + OOS). Why borrowed
rather than from-scratch: oblique phrasings ("tally", "individuals", "cite
its origin") need semantic similarity a from-scratch model on ~2k rows cannot
supply; the borrowed encoder supplies it with zero new pretraining, and only
~16k head weights are learned, so the whole train embeds + fits in ~10 s on
Mac CPU (budget < 15 min). Why MiniLM over SciBERT/ModernBERT: same loader
family and already verified in-repo (the loader's own `--check` reference
model), at ~5x lower CPU cost per embed.

## Training data (mine, checked against dev)

`scripts/fable_self122_data.py` holds 11 hand-written bases per intent (casual,
formal, typo'd, very short, long-winded) plus 138 + 40 OOS/new-intent negative
bases, expanded x4 by a seeded style augmenter (filler wrap, typo injection,
case/punct variant): 44 rows/intent (≥ 40), 672 OOS rows (≥ 300), 2,692 total
(2,060 train / 632 held-out, split by base). `build()` loads the exp-99
canonicals, exp-100 blind set, and panels 105/114 read-only and FAILS on any
verbatim (normalised) overlap — the dev sets were used for validation and
threshold choice only. Three tuning rounds on dev misfires added fresh
neighbourhood rows (C24 can/do anchors, trust-comparison and list-not-count
OOS neighbours, C9/C10 contrastive splits, near-canonical anchors for
C5/C11/C12/C13/C15); each round's rows are fresh wording, never dev copies.

## Threshold and freeze evidence

Head trained full-batch AdamW (600 epochs, inverse-sqrt class weights),
seeds 12201–12203 — all three reported in `train122_report.json`, never
averaged. Grid over (tau, mu) on held-out + all four dev sets: frozen
operating point is seed 12202, tau=0.6, mu=1.5, with 0 WRONG on exp99-40,
exp100-80, panel105-100, and panel114-100, exp99 canonicals 40/40, and 99/120
existing-C correct across the two panels. The identical decision code in
`fable_self122.py --devcheck` reproduces this exactly (DEVCHECK PASS).

## Freeze and blind run

Router + head weights hashed into `artifacts/fable-self122-20260922/
PASSMARKS.md`, PASSMARKS sealed with shasum, ledger P122.1–P122.5 appended —
all before the panel was opened. The runner aborts unless router hash, head
hash, and panel seal verify. Marks: K1 0 WRONG of 100; K2 ≥ 45/70
existing-intent correct; K3 10/10 tricks decline; K4 exp99 40/40 and exp100 0
wrong; exp-105/114 rescores reported as unregistered dev context. Every seed
and case reported, never averaged.

## What it means

If K1–K4 pass, a learned scorer on a frozen borrowed encoder lifts the
vocabulary ceiling while keeping every safety property (guard-first declines,
zero hallucinated names/numbers, honest "I do not know" fallbacks).

## What it does not mean

No new answering power: values still come only from live state via the 40
frozen bodies; the classifier only points. Nothing here touches real English
understanding beyond scaffolding routing.

## Deviations

D1: MiniLM-L6-v2 instead of SciBERT/ModernBERT (same loader, verified
in-repo, ~5x cheaper; stated in the brief's spirit as a frozen borrowed
encoder), with `WordPiece(lowercase=True)` because MiniLM's config carries
`do_lower_case=None` for an uncased vocab. D2: `fable_self122_diag.py`, a
dev-only per-case printer (never touches the blind panel). D3: the exp-105
type-guard is kept as a candidate restrictor on top of classifier outputs
(conservative; part of the decline machinery, not the scorer).
