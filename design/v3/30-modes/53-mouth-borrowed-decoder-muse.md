# 53 — Mouth: borrowed decoder, our head, our brake

The mouth turns a RESULT RECORD from the reasoner into one plain English
sentence. Records look like `{"kind": "answer", "status": OK | MISSING_FACT |
BROKEN_CHAIN | AMBIGUOUS | UNKNOWN_ENTITY | BAD_REQUEST, "name": ...,
"relations": [...], "fields": {...}}` (reasoner50 / wire51 adapters;
TemplateMouth is the current placeholder). Ben's rulings for this part: the
decoder is a borrowed small open-weight model with OUR head and format on top,
fine-tuned records → English (same approach as the ears), never Qwen; it must
never state a fact not in the record; MISSING_FACT must say it does not know
and name what is missing.

## What is borrowed, what is ours

Borrowed: HuggingFaceTB/SmolLM2-360M-Instruct (Apache-2.0), all 32 transformer
blocks frozen. Nothing from the web or from pre-training is trusted: every
content word the mouth emits is checked against the record before Ben sees it.

Ours, three pieces. (1) The record format: a tagged prompt
`<REC> <ST> status <NM> name <RL> rel1 rel2 <AN>/<SB>/<FD>/<HP>/<SC> field
values </REC>` using 10 new special tokens. (2) The record adapter, trained:
the 10 new input-embedding rows (9,600 params) + the last transformer block
(9,832,320) + the lm_head (47,195,520) = 57,037,440 trainable parameters. The
head is untied (cloned off SmolLM2's tied embeddings) so training it never
moves old input rows — the body is bit-identical before and after. (3) The
FAITHFULNESS BRAKE in plain software (`brake_check`): every entity/relation
string in the output must already appear in the record or in a fixed
function-word list; OK outputs must contain the answer verbatim; empty outputs
are rejected. Anything else falls back to TemplateMouth and is counted.

Protocol match: `Mouth.say(record) -> str` satisfies `fable_agent_loop.Mouth`.
Write/clarify/note records pass through untouched; only answer records go
through the decoder. The mouth can never cause a wrong write: it returns
strings, and all writes go through LISTENING, which never sees mouth output.

## Training data

`fable_mouth53_data.py` generates synthetic records → sentences with plain
templates: 3,000 train pairs (seed 5301) covering all six statuses, 1–3 hop
paths, the 8 village relations (mother, father, child, sibling, spouse,
employer, hometown, school) plus 30 open relations, 6 templates per status.
Held-out: 500 fresh records (250 OK, 80 MISSING_FACT, 60 BROKEN_CHAIN, 40
AMBIGUOUS, 40 UNKNOWN_ENTITY, 30 BAD_REQUEST). Every template carries a status
anchor ("don't know", "not someone I can look up", "more than one", "don't
know anyone", "could not use that"), so a rule-based classifier can read the
status back. Machine-check: all 3,500 template sentences pass the brake and
classify correctly, and every OK sentence contains its answer.

## What the run showed (see RESULTS.md for integers)

Trained 1,200 single-pair steps at lr 1e-4 on Mac CPU (12.7 min; lr chosen by
pre-registered pilots after 2e-5 stalled). Train loss 0.03 — near-memorization
of seen pairs. On held-out: the brake held (0 violations after it, every OK
answer exact), but the raw decoder passed it only 204/500 times and 74 of those
carried a wrong or missing status anchor (loops, truncated entity ids,
invented relations). So status recovery reached 426/500 (bar 480: FAIL) and one
anchorless BROKEN sentence cost a live-loop abstention in the wire51 replay
(wrong 1, correct 11, abstentions 2 vs 0/12/3: FAIL; the other two gaps are
ears-caused — the Qwen bridge was down and the TemplateMouth control shows the
same gaps). Training + scoring took 19.8 min (bar 25: PASS).

## Why this shape

The adapter is deliberately LoRA-free and small-scope: new rows for the record
tokens (the only new vocabulary), the last block (to re-route record features
to words), and our own untied head. Everything else frozen means the borrowed
model cannot smuggle new facts into old words — the only path to Ben's eyes is
through the brake, which reads the record, not the model. The fallback design
makes safety the default: an untrained or confused decoder produces silence or
gibberish, the brake rejects it, and Ben hears the deterministic template.

## Limits and next steps

Single-pair SGD memorized more than it generalized; the copy circuit for unseen
name/relation combos needs more steps or batched updates, still within the CPU
budget (only ~20 of 25 min used). The brake is lexical: it catches invented
words but not a fluent sentence with the wrong status anchor — that is exactly
the measured O2/O5 gap, and closing it in plain software (e.g. requiring the
record's anchor per status) is a design change for Ben, not a tuning tweak.

## What it means / What it does not mean

What it means: Ben can already talk through this mouth safely — the brake
guarantees every sentence repeats only record facts, says "I don't know" with
the missing piece named, and the wire51 loop runs end to end with it. What it
does not mean: the borrowed decoder itself is not yet trustworthy — unassisted
it fails more than half the held-out panel, so the brake (plain software, not
the model) is doing the real safety work, and removing it would let loops and
inventions reach Ben today.
