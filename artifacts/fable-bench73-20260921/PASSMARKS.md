# Experiment 73 — PASSMARKS (Fable-Edit-200, ENGLISH-INPUT arm, pluggable ears)

Sealed before the registered run. Data
`data/open/bench65/fable_edit_200.jsonl` (200 items: 100 MQuAKE-Remastered
CF-3k two-hop single-edit, 50 reversal ours-fictitious, 25 abstain-absent +
25 abstain-broken ours-fictitious) plus 5 hand-made garbled items in
`fable_bench73_garbled.jsonl` (this folder). The arm feeds ONLY English
strings (taught `sentence_en`, then `question`) through an Ears object, then
the same notebook + QualifierAwareReasoner + scoring as exp 65. Wald-clock on
Mac CPU, `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`. Single deterministic run
(seed-free templates); every item reported, nothing averaged.

Reference: the structured-arm table is recomputed in-memory during the run
(exp-65 code imported read-only; no other agent's files touched) and must
match exactly (exp 65 sealed: 100/100 two-hop, 50/50 reversal, 50/50 abstain,
0 wrong).

| Mark | Bar (integer counts) |
|------|----------------------|
| T1 template parity | template-arm table identical to the structured reference: mquake-twohop 100/100 correct, reversal 50/50 correct, abstain-absent 25/25 abstain, abstain-broken 25/25 abstain, 0 WRONG overall |
| T2 garbled abstention | 5/5 garbled items yield MISSING/abstain, 0 WRONG (unparseable input is never written and never guessed) |
| T3 wall-clock | whole 200-item template run < 5 min on Mac CPU |

Scoring: identical to exp 65 (exact match after normalisation; abstain = any
non-OK status; WRONG = OK with a value outside the gold set). A registered
FAIL stays a FAIL. ears47 choice is smoke-test grade only (import + CPU
forward on 3 sentences, or a documented skip while exp 47 trains).

## What it means

If all three marks pass, English teaching sentences install the same facts as
hand-fed triples (template ears parses every sentence pattern in the file),
the question composer resolves every English question to the right query, the
notebook + reasoner behave identically on English-derived input, and anything
the ears cannot parse becomes a structural abstention instead of a guess.

## What it does not mean

It does not show general English understanding: the template ears covers only
the sentence patterns enumerated in the design doc (dev-checked 575/575 on
this file, gold-free at run time), and multi-hop query order comes from the
taught chain structure with a mention-coverage gate, not from parsing question
paraphrases. The real (neural) ears is exp 47, still training.
