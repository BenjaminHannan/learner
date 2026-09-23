# Exp 230b-r RESULTS — same 230b code, fresh blind panel, M1(c) re-defined

**Verdict: FAIL (registered).** M1(a) false "Yes" = 1 (bar 0) and M1(b) NO fixed = 13/14.
Both come from one item: r230b-038. After "My name is Wystane Morrick.", the question
"Is it Wystane Borrick, my name?" still gets "Yes. Your name is Wystane Morrick.".
Diagnosis: 230 answers this word order with "Yes. Your name is …", but asked_name has no
"Is it X, my name?" pattern. The asked name is never extracted, so no comparison happens.
This is the risk named in PASSMARKS: a phrasing the patterns miss, not a comparison error.
The re-defined M1(c) passed at 11/11.

Code SHAs matched the 230b seal before and after the run, 7/7 OK. Nothing was edited
after the seal. The panel seal was checked from the repo root: 2/2 OK. 230 and 230b ran once
each, per item, in fresh temp workdirs (the unchanged 230b driver with --panel-dir).

## Marks table (M1, 48-item fresh blind panel)

| mark | bar | result |
|---|---|---|
| (a) false "Yes" | 0 | **1 — FAIL** (r230b-038) |
| (b) NO items with base "Yes. Your name is …" now exactly "No. Your name is <stored>." | 14/14 | **13/14 — FAIL** (r230b-038) |
| (c) YES items with base_yes true still start "Yes" | 11/11 | 11/11 — pass |
| (c) YES items with base_yes false (reported, not scored) | — | 3: r230b-018, 020, 032, all unchanged from 230 ("I do not know that …") |
| (d) UNCHANGED items byte-identical to base230 | 10/10 | 10/10 — pass |
| (e) question writes | 0 | 0 — pass |
| every turn follows the sealed expected() rule; base230.jsonl = live 230 | — | 48/48; 0 mismatches |
| M2-M5 (reused from 230b, SHAs match) | as 230b | dev 31/31; 0 suite moves; smoke identical; +0.035 ms |

## Every move (13, all predicted by class: NO item with base "Yes. Your name is …")
r230b-001, 004, 006, 007, 008, 009, 010, 011, 012, 013, 014, 035, 037.
Each went from "Yes. Your name is S." to "No. Your name is S.".

## Every miss / unmoved item
- r230b-038 (NO): "Is it Wystane Borrick, my name?" is still "Yes. Your name is Wystane Morrick.".
  This is the one FALSE YES.
- NO items that did not move and are not false yeses, because 230 already refused
  ("I do not know that …"): r230b-002, 003, 005, 036.
- YES items with base_yes false: 018 "IS MY NAME PRYSELLE?", 020 "is my name grendaline oskov?",
  032 "Is it Sorvane?". All get "I do not know that …" on 230 and on 230b. Reported, not scored.
- NOT_TOLD items 025-030: unchanged, none say "Yes".
- Seen in passing (not a mark, and not caused by 230b): r230b-044 "What is your name?" after
  "My name is Castrevel." gets "Your name is Castrevel." on both 230 and 230b. The question asks
  for the assistant's name, but the reply gives the user's name.

## Deviations
- None to the protocol. The marks driver is the sealed 230b one; its --panel-dir option was
  written before the 230b seal.

## What it means
With the same code, most wrong-name checks are now fixed. On a new blind panel, 13 of 14
"Is my name X?"-style questions with the wrong name now answer "No. Your name is …". Every
correct-name question that said "Yes" before still says "Yes". Nothing was written, and no
other reply changed.

## What it doesn't mean
It is not reliable yet. One word order, "Is it X, my name?", still gets a false "Yes", because
the name finder is a short list of sentence patterns and that shape is not on it. A more general
extractor would fix this, but that is a code change and needs its own registered run. Some
correct-name questions ("IS MY NAME PRYSELLE?", "Is it Sorvane?") still get "I do not know",
exactly as on 230.
