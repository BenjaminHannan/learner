# 120 — Talker mouth fine-tune PREP: our talker learns to SAY answers (Muse)

PREP only. Exp 101's from-scratch talker (28.85M decoder + pointer-generator
copy head, SimpleStories-EN) is pretraining on the BensPC GPU right now
(ends ~04:00; step ~1670, loss ~2.2, ~49k tok/s, measured 2026-09-22 — that
throughput number is the basis of the time estimate below). This experiment
is its second stage: fine-tuning that talker to turn notebook-answer RECORDS
into one faithful plain-English sentence each. The director launches the GPU
fine-tune after the pretraining run exits; nothing here starts a GPU job.

## The one change vs exp 53

Exp 53 (borrowed SmolLM2-360M decoder + our head/format/brake) reached O1/O3/O4
but FAILED O2 (status recovery 426/500, bar 480) and O5 (one anchorless BROKEN
sentence cost a live-loop abstention): unassisted, the borrowed decoder failed
296/500 records (59 %) before the plain-software brake caught them. The brake
did the real safety work. Exp 120 keeps the record shape, the brake design,
the rule-based status read-back and the O1–O5 bars, and swaps ONLY the decoder:
our own pretrained talker. New mark O6 caps raw-decoder unfaithfulness at
10 % (≤ 50/500) — the number that says the model itself learned the job,
not just the brake.

## Records, templates, anchors

Records keep exp-53 keys (`kind/status/name/relations/fields`) with the
notebook-answer status set: OK / UNKNOWN / ABSTAIN / CLARIFY / SAVED / FORGOT
plus provenance (`taught | inferred | sleep-derived | web-verified`).
`fable_talker120_data.py` generates 3,000 train + 500 held-out pairs
(250 OK + 50×5) from templates written for this experiment: ≥ 30 surface
forms per status (machine-counted after blanking slot strings), one status
anchor per sentence (`don't know`, `can't answer that`, `do you mean` /
`which one`, `saved`, `forgotten`; OK carries its answer verbatim).
Train and test names/values come from disjoint synthetic pools (asserted).
Machine-checks fail loudly: pools disjoint, all 3,500 sentences pass the
brake, every sentence classifies to its own status, every OK/SAVED sentence
contains its answer.

## Fine-tune: prefix in, sentence out, copy head earns its keep

`fable_talker120_train.py` resumes from the finished exp-101 checkpoint and
fine-tunes the FULL model (ours — nothing frozen) with the pointer-generator
mixture NLL masked to the target span: predicting each sentence token mixes
the vocab softmax with copy attention over the serialized-record prefix, so
names/values are copied from the record, never recalled. Recipe (registered):
5 epochs, bs 32, ctx 256, lr 1e-4 cosine+warmup, bf16. Data ≈ 0.23M
tokens/epoch → ~1.15M tokens ≈ 25 s at the measured 49k tok/s; scoring
(500 greedy mixture decodes, ≤ 32 new tokens) plus the wire51 replay fit in
minutes. Total ≈ 5 min wall-clock, bar < 25 (O4).

## Codec honesty

`fable_talker120_mouth.py` carries a small pure-Python reader of the
talker101 tokenizer.json (GPT-2-style ByteLevel; stdlib + torch only, per Mac
compute rules) plus `serialize / brake_check / classify / TalkerMouth`
(the brake is exp 53's design; its word list is exp 53's verbatim plus
`forgotten/forgot`). The codec is validated by round-trip and by the CPU
smoke, NOT claimed bit-identical to the Rust encoder — any segmentation drift
is absorbed by fine-tuning in the shared id space, and is stated as such.

## Smoke (Mac CPU, prep, seeds reported, no marks scored)

From the latest STABLE talker101 checkpoint: 100 fine-tune steps (S1: loss
falls) + 20 held-out greedy decodes (S2: pipeline runs). The live
`full_run/ckpt_last.pt` was deliberately NOT copied: the trainer rewrites it
every step (~3/s), so any copy risks a torn file, and the GPU run must not be
disturbed. The registered GPU run resumes from the finished full-run
checkpoint instead; the smoke proves the pipeline, not the data.

## What it means / What it does not mean

What it means: everything the GPU fine-tune needs exists and is proven on
the CPU path; O6 will say whether OUR talker learned faithful speech or just
hides behind the brake. What it does not mean: no fine-tuning has happened —
O1–O6 are predictions (ledger P120), and a FAIL stays a FAIL.
