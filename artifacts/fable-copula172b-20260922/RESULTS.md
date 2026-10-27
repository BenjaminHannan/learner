# RESULTS — Exp 172b: 172's copula-ask agent under bench protocol v3 (Muse)

Agent code is 172's, unchanged (sha 665177a8…). Base behaviour: loop154c.
Director ruling: the agent keeps asking; bench protocol v3 = "confirming
user" (one extra "yes" after any bench edit turn answered by the
change-prompt naming that edit's new value; nothing else extra).
Status: REGISTERED PASS with one noted deviation (P172b.5 subclause).

## Marks table (integer counts, every case reported)

| mark | bar | number | verdict |
|---|---|---|---|
| T1 (81-line 154b probe via 172) | 81/81 byte-identical | 81/81, 0.2 s | PASS |
| T1b (83 turns, copula line -> prompt) | 83/83, only sealed lines differ | 86/86 lines, states match | PASS |
| T1c (new, 92 turns fictional) | 92/92 (12 prompts 6 yes/6 no + states, 6 Actually, 6 allow, 8 other) | 99/99 lines | PASS |
| T2 | 0 wrong writes, 0 silent replaces, all T | 0 / 0 over 272 turns | PASS |
| G1 bench v3 (4x200, both agents) | 172-v3 verdict == 154c-v3, 0 new wrong | 800/800 identical verdict+reply, 0 new wrong, 44.8 s | PASS |
| G1 info: 172 old driver | (no bar) | 678 moves, all inside the 681 flagged | info |
| G1 info: 154c v3 vs frozen | predicted identical | 2 diffs (see deviation) | DEVIATION |
| G2 marks123 per-case vs marks154c | identical except predicted | 0 unpredicted moves, 0 new WRONG, 344.8 s | PASS |
| G3 rt136/rt143/sessions152 | 0 moves, 0 new wrong/write | 0/0/0 moves, 8.7 s | PASS |
| G4 | every run < 1500 s | max 344.8 s | PASS |

Confirms per split (v3): loop172 — new_121 208, s2fresh 213, edit200 99,
bench132 201 (721 total); loop154c — 0/0/0/2. Teach-reject items track the
same counts (prompts); the 5 non-prompt rejects (multi-fact/single-name
limits) took no confirm, per the ruling.

## G1 detail

Under v3 every 172 prompt is confirmed and lands the same edit 154c
applies silently, so final states match: 800/800 identical verdict AND
final reply, 0 new wrong. Under the OLD driver 172 prompts go
unanswered: 678 items move (stale kept-chain wrong/abstain), every one on
172's pre-written scan list of 681 (3 flagged items keep verdict+reply).

## G2 detail

p2: B1/B2/B3/B7/B8/F2 move OK->BUG with EXACTLY the predicted kept-chain
finals (Spanish/English/USA); B6 keeps final Warsaw (prompt + dup-ack
mid-replies as predicted); prompt turns write 0 facts. rt110 F2/F6/D5
byte-identical as predicted (forget empties the slot so the re-teach is a
first-teach; the vanish never processes). marks-bench: 300 verdict moves
+ 2 prompt-form-only, all on scan-flagged ids. p3/p4/q1/q4/rt81/sleep/
soak per-case identical (sleep SKIP reason names the agent file by
construction). Nothing the agent wrote or answered is false: finals are
taught-kept values or abstains.

## Deviation (reported, no re-run hidden)

P172b.5's "154c-v3 == frozen 154c rows" subclause is FALSE on 2 items:
bench132-4hop-105 (correct->correct, reply now uses the confirmed chain)
and bench132-4hop-162 (wrong->abstain: the confirmed chain breaks on a
pre-existing multi-fact reject, so the agent abstains instead of guessing
stale). Cause: bench132 contains 2 possessive re-teaches that prompt even
under 154c; v3 confirms them. No new wrong (wrong count fell). The main
G1 bar (172-v3 == 154c-v3, 0 new wrong) holds 800/800.

## Post-seal edit (reported, re-run in the open)

`scripts/fable_fix172b_markscmp.py` EDIT 1: normalize volatile fields in
the identical-suites check (per-suite seconds; the agent filename inside
the sleep SKIP reason). No case/suite input touched, no agent/driver
change; the FAST deterministic compare was re-run in the open on the
sealed registered outputs (failures 2 -> 0, both diffs volatile-only).

## Deviations from plan

None besides the two notes above. No silent re-runs (one registered run
per suite; T probes one registered run each). No other agent's file
touched; no repo-root notebook writes. Scratch: work-t1/t1b/t1c,
scratch-bench dirs, marks172b, g3 — all inside
`artifacts/fable-copula172b-20260922/`.

## Reproduce (Mac CPU, offline; after seal 572a95dc…)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix172b_probe.py --cases artifacts/fable-copula172b-20260922/probe172b_t1c_cases.jsonl --out <out> --tag probe172b_t1c
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix172b_benchv3.py --arm loop172 --proto v3
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop172_agent.py --config artifacts/fable-copula172b-20260922/loop172b-config.json --out <out> --suites p2,p3,p4,rt110,q1,bench,rt81,sleep,soak --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix172b_g3.py
```

## What it means

Asking first and meaning "yes" compose: a confirming user gets exactly
the old bench behaviour (800/800), while an unconfirmed re-teach keeps
the taught value and says something true.

## What it does not mean

It does not mean bench edits auto-apply anymore — under v3 every one of
the 721 copula/possessive edit-prompts needs its "yes"; without it the
bench scores stale (678 moves), which is the designed ask-first price.
