# RESULTS — Experiment 111: Loop102 end-to-end through the real doorway (2026-09-22)

Registered FAIL overall (E1, E2 fail; E3, E4 pass). The loop is healthy at
the notebook level; the failures are two doorway framing gaps plus one
scorer mismatch, all mechanistically identified. FAIL stands, never re-run.

## Marks table (sealed `PASSMARKS.md`, sha `e3a3b757…`)

| Mark | Result |
|---|---|
| E1 Fable-Edit-200: right behaviour ≥ 195/200 AND wrong ≤ 2 | **FAIL**: right behaviour 50/200 (0 exact-correct + 50 abstain), wrong 150 |
| E2 fresh-200: wrong ≤ 2 | **FAIL**: wrong 131/200 (correct 0, abstain 69) |
| E3 abstain items: 0 confident wrong | **PASS**: wrong 0/50 (abstain 50/50) |
| E4 whole wave < 25 min Mac CPU | **PASS**: 6.9 s |

Ledger P111.1–P111.5: TRUE, FALSE, TRUE, TRUE, TRUE (4/5; P111.2 predicted 0
teach rejects, got 22 on the fresh split).

## Per-type tables (correct / abstain / wrong), doorway vs baselines

Exp-111 doorway, Fable-Edit-200 (fresh daemon per item, outbox reply scored
with the verbatim exp-66 `classify`):

| type | n | correct | abstain | wrong | contains_gold |
|---|---|---|---|---|---|
| mquake-twohop | 100 | 0 | 0 | 100 | 100 |
| reversal | 50 | 0 | 0 | 50 | 50 |
| abstain-absent | 25 | 0 | 25 | 0 | 0 |
| abstain-broken | 25 | 0 | 25 | 0 | 0 |

Exp-66 SmolLM2-360M in-context baseline (same scorer, short-phrase answers):

| type | n | correct | abstain | wrong |
|---|---|---|---|---|
| mquake2hop | 100 | 34 | 3 | 63 |
| reversal | 50 | 18 | 1 | 31 |
| abstain_* | 50 | 0 | 7 | 43 |

Exp-111 doorway, fresh-200 (exp-103 4-hop split):

| type | n | correct | abstain | wrong | contains_gold | teach rejects |
|---|---|---|---|---|---|---|
| mquake-s2fresh-4hop | 200 | 0 | 69 | 131 | 5 | 22 (12 items) |

Exp-103 English arm on the same fresh-200 (direct notebook, N-hop composer):
193 correct / 0 wrong / 7 miss. The doorway loses all of that (see mechanism).

## Mechanism (why)

1. **Mouth framing vs exact-match scorer (all 150 split-A "wrongs").** The
loop knew every answer (contains_gold 150/150) but FakeMouth speaks full
sentences ("Twitter's chief executive officer's country of citizenship is
Latvia."), which never exact-match gold. Registered wrong; diagnostically
right.
2. **2-hop question composer truncates 4-hop chains (fresh ~127 wrongs).**
The ears chain asks via bench73's 2-hop `compose_question`; exp-103's N-hop
`compose_n_hop` was never wired into loop102. Replies are correct 2-hop
prefixes ("Derek Shepherd's spouse's creator is Frank Herbert.", gold
Arabic) — confident wrongs.
3. **Fresh-split templates the doorway cannot hear (22 rejects, 12 items).**
"X works in the field of Y", "X is employed by Y", "X's child is Y" match no
bench73 pattern; "…citizen of United Kingdom of Great Britain **and**
Ireland" trips the doorway's one-fact-at-a-time guard on "and". Split-A
templates: 0 rejects in 800 teaches. Sentences were NOT rewritten.
4. **Scorer artifact disclosed:** "not" ⊂ "notable" buckets 3 confident
fresh-split wrongs ("…author's notable work is The Railway Children.") as
abstain. E3 (split-A abstains) is unaffected: all 50 are genuine
"I don't know…" replies.

## 5 most instructive failures (verbatim)

1. `Q: What is the country of citizenship of the chief executive officer of
Twitter? → Twitter's chief executive officer's country of citizenship is
Latvia.` (gold Latvia; framing-only wrong)
2. `Q: What language is officially spoken in the country where the creator
of the spouse of Derek Shepherd is a citizen? → Derek Shepherd's spouse's
creator is Frank Herbert.` (gold Arabic; 2-hop truncation)
3. `Alberto Zaccheroni works in the field of association football manager →
I didn't understand that. Could you say it another way?` (teach reject)
4. `Diana Gabaldon is a citizen of United Kingdom of Great Britain and
Ireland → I can take one fact at a time — could you split that?` (teach
reject via "and" guard)
5. `Q: Which continent is home to the country where the notable work
associated with the author of Troilus and Criseyde was developed? →
Troilus and Criseyde's author's notable work is The Railway Children.`
(gold Asia; confident wrong, scorer-bucketed abstain)

## What it means

The joined-up loop teaches, edits, abstains and answers correctly through
its real mailbox on known templates; end-to-end testing caught a real
integration gap (N-hop composer never wired into the loop) plus three
unheard fresh-split phrasings.

## What it does not mean

It does not mean the notebook/reasoner regressed (split-A answers all
present; exp-103's 193/200 notebook result is untouched), nor that the
mouth is wrong (full sentences are correct English — the registered scorer
demands short phrases).

## Deviations / reproduce

Deviation: a 5-item pre-seal smoke probe (2 answer + 3 abstain) informed
predictions P111.1–P111.5; it wrote only to temp dirs, never to the
artifact folder. No other deviation; no other agent's files touched;
nothing committed. Reproduce: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1;
uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/fable_bench111_run.py --run` (6.9 s). Rows:
`artifacts/fable-bench111-20260921/fable_bench111_*_rows.jsonl`.
Questions for Ben: none.
