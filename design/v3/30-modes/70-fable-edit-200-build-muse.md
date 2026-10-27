# 70 — Fable-Edit-200 build (experiment 65, 2026-09-22)

How the 200-item benchmark was built, what the notebook arm does with it,
and what passed. Written for Ben in plain language.

## The idea in five lines

Public benchmarks already test what our design claims to be good at:
installing a corrected fact without breaking everything else (MQuAKE),
answering a fact backwards as well as forwards (the reversal curse), and
saying "I don't know" instead of guessing (abstention). Fable-Edit-200
packs all three into 200 fixed items: 100 real two-hop edit questions, 50
forward/backward pairs we invented, 50 questions that must be refused. The
notebook arm answers from taught triples — not English — because the ears
are still in training. Result: 200/200, zero wrong answers, 0.2 seconds.

## Data (open licences only)

- **MQuAKE-Remastered** (CC-BY-4.0, https://huggingface.co/datasets/henryzhongsc/MQuAKE-Remastered):
  `data/CF3k-00000-of-00001.parquet`, sha256
  `12c8bc1f…cf9eee0`, 1,405,488 bytes. The CF-3k fixed subset.
- **TwoHopFact** (CC-BY-4.0, https://huggingface.co/datasets/soheeyang/TwoHopFact):
  `TwoHopFact.csv`, sha256 `522d3764…e605e338`, 94,576,306 bytes.
  Downloaded and hash-recorded for licence verification; not sampled in
  this 200-item run.
- **Not downloaded:** CounterFact, zsRE, Reversal-Curse data — no licence
  found for any of them. Full per-file record in
  `data/open/bench65/LICENCES.md`.

## The 200 items (seed 6500, builder `scripts/fable_bench65_build.py`)

1. **100 MQuAKE two-hop, single-edit** (`bench65-mquake-001…100`). Eligible
   cases have exactly one edit triple pair forming a two-hop chain
   (bridge entity shared). Each item teaches the two ORIGINAL facts first,
   then the two counterfactual replacements, and asks the dataset's
   question (gold = new answer + aliases).
2. **50 reversal** (`bench65-rev-f00…24-fwd/rev`, 25 fictitious facts × both
   directions). Invented people and works (e.g. "Uriah Hawthorne is the
   composer of Abyssal Melodies"), stored with both templates
   (`{A} is the {R} {B}.` / `{B} was {Ri} {A}.`) and five relation pairs
   (composer/author/discoverer/founder/inventor of + inverse). No real
   person or fact appears.
3. **50 abstention** (`bench65-abs-absent-…`, `bench65-abs-broken-…`). 25
   absent (notebook holds filler facts; the asked subject or relation is
   never taught), 25 broken chains (first hop taught, second hop uses a
   `never_taught_rel` relation). Gold is "abstain".

Every item stores `id, source, type, taught[]` (subject/relation/object
triples plus the ORIGINAL English sentence alongside), `question, gold[],
expected`. Manifest with hashes:
`data/open/bench65/fable_bench65_build_manifest.json`.

## The notebook arm (`scripts/fable_bench65_notebook_arm.py`)

For each item, independently: open a FRESH notebook, declare the item's
relations, teach originals (`correction=False`) then the edit
(`correction=True`, so the edit supersedes — never overwrites weights,
because there are no weights), then ask the item's frame through the
qual56 wrapper over the reasoner50 (which replays the contract's hop loop;
agreement with `Notebook.ask` was 200/200). Scoring is exact match after
normalisation; abstain = any non-OK status; WRONG = OK with a value outside
the gold set. Additive: imports the notebook contract and qual56 reasoner
read-only, never edits them.

## What passed (sealed marks N1–N4, ledger P65.1–P65.4, 4/4 TRUE)

N1: 100/100 MQuAKE (0 wrong) — the edit superseded the original through
the bridge entity every time. N2: 50/50 reversal — symmetric lookup shows
no curse. N3: 50/50 abstain, 0 wrong — absent items surfaced as
MISSING_FACT/UNKNOWN_ENTITY, broken chains as MISSING_FACT at hop 2 (never
BROKEN_CHAIN; see RESULTS.md note). N4: 0.2 s on Mac CPU, one thread.

## Limits and next steps

Structured input only — English sentences ride along as metadata but are
never parsed; the English-input arm awaits ears rung 2. No baseline model
was run here (experiment 66 covers SmolLM2-360M). A future bar could demand
the exact BROKEN_CHAIN label on broken chains.

## What it means

The notebook + reasoner can install one corrected fact, follow it across
two hops, answer it backwards, and refuse what it was never taught — all
without touching any weights, in a fraction of a second.

## What it does not mean

It does not mean the assistant understands English yet, beats any other
system, or handles paraphrase, ambiguity, or time-changing facts — none of
those were tested here.
