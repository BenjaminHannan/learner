# Exp 86 — Simple English reading data (Muse) — PASSMARKS (sealed BEFORE the run)

Source: Simple English Wikipedia official dump
(multi-stream pages-articles), CC BY-SA 4.0 + GFDL. Raw data only —
never enters the notebook or weights.

| mark | bar (all integer counts) |
|---|---|
| W1 | >= 100,000 kept sentences in data/open/simplewiki86/sentences.jsonl |
| W2 | 0 sentences with markup residue (any of `{{`, `[[`, `<`, `]]`, `}}`) in a deterministic 1,000-sentence check (seed 86) |
| W3 | 0 exact-duplicate sentences in sentences.jsonl (normalised exact dedup) |
| W4 | whole extraction wall-clock < 25 min on Mac CPU (stream the bz2, stop early once targets are met) |

Sentence contract: declarative (ends with `.`, starts with capital),
4–30 words, one fact-like statement each (cue token or phrase:
is/was/are/were/has/had/born/died/located/capital/"member of"),
with page title, section, stable id. Held-out: 2,000 sentences
stratified by page (seed 86). Report: every seed/case reported, never averaged.
