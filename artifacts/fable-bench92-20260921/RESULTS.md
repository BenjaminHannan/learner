# RESULTS — Experiment 92: Fable-Edit-SCALE (2026-09-22)

Registered verdict: **FAIL** (B2 breaks on S4-batch and the English arm;
see marks table). The notebook itself scales cleanly to 3–4 hops,
same-chain multi-edits, overrides and 3-hop reversal: 1,000/1,000
correct, 0 wrong across S1/S2/S3/S5/S6.

## Marks table (sealed `PASSMARKS.md`, sha `4a28607a…e00aaa50`)

| Mark | Result |
|---|---|
| B1 per-split correct/wrong/miss | notebook — S1 200/0/0, S2 200/0/0, S3 200/0/0, S4 973/25/2, S5 200/0/0, S6 200/0/0; English — S1 195/1/4, S2 142/32/26, S3 181/8/11; nothing averaged |
| B2 wrong = 0 every split | **FAIL**: S4 25, EN-S1 1, EN-S2 32, EN-S3 8; holds on S1/S2/S3/S5/S6 notebook |
| B3 first split < 95% + 5 verbatim fails | no notebook split below 95% (S4 = 97.3%); the breaking split is S4 via B2 — 5 items below |
| B4 S4 latency + size | p50 2.365 ms, p99 5.789 ms (mean 2.804, max 16.649); notebook 4,517 events / 1,472,262 bytes / 1,914 entities / 35 relations / 4,000 teaches / 0 teach-CONFLICTs |

Ledger P92.1–P92.8: P92.1 TRUE, P92.2 TRUE, P92.3 TRUE (200/200),
P92.4 FALSE on the letter (predicted <95%: got 97.3%; the wrong>0 half
was right — 25 confident wrongs), P92.5 TRUE, P92.6 TRUE, P92.7 FALSE
(S2-English did break <95% as predicted, but the 0-wrong half was wrong:
1/32/8 wrongs), P92.8 TRUE (notebook wave 7.3 s, English wave 2.7 s).

## Where it breaks, exactly

**S4 batch interference (notebook, 25 WRONG + 2 MISS).** 1,000 cases
share bridge entities (Nigeria, USA, UK, Poland…). Originals never
collide (0 CONFLICTs — case subjects are unique), but edits use
`correction=True`, so the LAST case in case_id order to edit a shared
bridge slot wins and earlier cases answer with its value — confidently.
Reasoner and contract agree on all 27 (contract_disagree 0): the bug is
in the teaching regime (no case isolation), not the hop loop.

**English arm (41 WRONG total, all one cause).** Exp-73's generic
`The <X> is <Y>` → officeholder pattern SHADOWS the three new specific
patterns: `The director of The Beatles is Gilad Erdan` parses as
(`director of The Beatles`, officeholder, …) instead of
(`The Beatles`, director_manager, …) — same for head_coach and
original_broadcaster (typo `origianl` included). The corrupted subject
truncates the N-hop walk (e.g. 006 walks 1 hop from `With the Beatles`
and answers `The Beatles`), producing confident wrongs. All 41 wrongs
(1 + 32 + 8) involve a shadowed relation; statement-parse failures were
0. The fix (try specific patterns before the generic one) is future
work — the registered numbers stand.

## B3: five S4 failures verbatim (question | gold | taught → answer)

1. `bench92-s4-batch-018`: "Who is the head of the government in the
   country that Ahmadu Bello is a citizen of?" | gold Karl Döhler |
   taught (Ahmadu Bello, citizenship, Nigeria), (Nigeria, head_gov,
   Buhari), edits (…, Nigeria), (Nigeria, head_gov, Karl Döhler) →
   answered **Muhammadu Buhari** (later case's bridge edit won).
2. `-023`: "…country that Frank R. Strayer is a citizen of?" | gold
   Justin Trudeau | bridge USA→Canada/Trudeau edit → answered
   **Abd El Azim Wazir**.
3. `-043`: "…head of state in the country of origin of Fairport
   Convention?" | gold Alexander Van der Bellen | bridge UK→Austria
   edit → answered **Klaus Iohannis**.
4. `-044`: "Which continent is home to the country where Sigur Rós was
   developed?" | gold Africa | bridge Iceland→Cape Verde/Africa edit →
   answered **North America**.
5. `-134`: "What is the capital of the nation that Tomasz Gollob is a
   citizen of?" | gold St. Marys | bridge Poland capital Warsaw→St.
   Marys edit → answered **Warsaw**.

## What it means

Hop depth (3–4), multi-edit chains, overrides and reversal need no new
machinery: isolated notebooks are perfect. Sharing one notebook across
1,000 cases breaks the zero-wrong property through bridge collisions,
and English template parsing breaks it through pattern shadowing.

## What it does not mean

It does not mean the reasoner is at fault (contract agrees everywhere),
that batch teaching is unfixable (case isolation / namespacing was not
tested), or that English needs a neural net (pattern ORDER, not model
size, caused all 41 wrongs).

## Deviations / reproduce

Deviation 1: notebook-arm script crashed after S1–S3 on a missing
`contract_status` key in S4 rows (pre-results, pre-completion); fixed by
adding a real `nb.ask` contract check, full wave re-run deterministically.
No other agent's files touched; nothing committed. Reproduce:
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_bench92_notebook_arm.py --run` (then `…_english_arm.py
--run`). Data: `data/open/bench92/` (manifest
`fable_bench92_build_manifest.json`). Questions for Ben: none.
