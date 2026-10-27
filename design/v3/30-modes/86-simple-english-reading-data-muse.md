# 86 — Simple English reading data (Muse)

A licence-clean reading corpus for the reading ladder. Later, the model
reads simple English pages and turns sentences into notebook rows. This
doc covers data only: no notebook writes, no weight updates, no truth
claims about the sentences.

## Source (open data only)

Simple English Wikipedia, official Wikimedia dump (no mirrors):
`https://dumps.wikimedia.org/simplewiki/20260901/simplewiki-20260901-pages-articles-multistream.xml.bz2`
— dump 2026-09-01, 385,846,687 bytes, published SHA-1 `50152ec5…`.
Licence: CC BY-SA 4.0 + GFDL (dual, per Wikimedia Terms of Use and
`Wikipedia:Copyrights`). Full provenance + licence text in
`data/open/simplewiki86/LICENCE.md`; every sentence carries its page for
credit. Streamed over HTTPS on 2026-09-22; stopped after 45,088,768 bytes
once the 200,000 target was met (sha256 of the consumed prefix in
`counts.json`).

## Method (`scripts/fable_simplewiki86_extract.py`, stdlib + numpy)

Stream chunks through a fresh `bz2.BZ2Decompressor` per multistream chunk
(a smoke test caught that one shared decompressor stalls after the header
stream), split `<page>` blocks, keep namespace 0, drop redirects. Plain
wikitext stripper: comments, refs, templates (innermost-first), tables,
File/Category links dropped, `[[a|b]]→b`, external-link text kept, HTML
tags/unescapes/bold removed. Split into sections on `==` headings, then
sentences on `.?!` + capital. Keep a sentence iff: ends with `.`, starts
with a capital letter, 4–30 words, contains a fact cue (`is/was/are/were/
has/had/born/died/located/capital` or `member of`), and has none of
`{{ }} [[ ]] < >`, `http`, `=`. Exact dedup on lowercased text; stable id
`sw86_` + sha1-12. Held-out 2,000: deterministic round-robin over pages
sorted + shuffled with seed 86 (one sentence from each of 2,000 pages).
Checks: 1,000-sample residue scan (seed 86), full-file dupe audit, numpy
ranking of 50 relation-ish verbs, vocab list.

## Results

200,000 kept from 43,925 pages in 20.5 s wall on Mac CPU. 570,093
candidates; biggest drops: no-cue 160,097, not-capital 84,522,
non-declarative end 46,499, markup 42,353. Residue 0/1,000, dupes 0,
vocab 86,035. Top verbs: is 87,206, was 47,999, are 38,026. 20-sentence
sample and full counts in `artifacts/fable-simplewiki86-20260921/RESULTS.md`.

## Limits (claims never exceed evidence)

Cue-word filtering is a heuristic, not a truth or grammar check — sample
rows include clumsy but declarative lines (e.g. the Mafia row). Some rows
need surrounding context (`It has not changed much since then`). Sentences
are verbatim CC BY-SA excerpts: reusers must credit pages, link the
licence, share alike. Held-out is a subset of the main file (flagged for
the later labelling step), not a disjoint split. Nothing here was
human-labelled; the 2,000 held-out rows exist for exactly that next step.

What it means: the ladder's raw reading material exists, clean and counted.
What it does not mean: the model knows any of it — web text is data, never
a taught fact.
