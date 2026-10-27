# RESULTS — Exp 138c: self serves only when grounded (Muse, 2026-09-22)

One change to loop138 (`scripts/fable_loop138c_agent.py`, imports loop138
read-only, nothing else touched): on a notebook-missed turn the self answer
is served ONLY on (router non-DECLINE AND grounded answer -- not FALLBACK,
no Self99 DECLINE_MARKERS); every other case serves the base loop's reply
verbatim. PASSMARKS sealed pre-run (`SEAL.sha256.txt`, 7 files OK), ledger
P138c.1–5 appended pre-run. Mac CPU, offline, OMP/MKL=1. No post-seal code
edits. Every seed/case reported.

## Marks (every seed/case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| B1 new121 (200) | identical to 134, 0 new wrong | 135/63/2; 1 move: 174 correct→wrong; 165 back to abstain; 0 reply-moves | FAIL (1 move) |
| B1 old_s2fresh (200) | identical to 134 | 157/43/0; 0 moves, 0 reply-moves | PASS |
| B1 edit200 (200) | identical to 138 rows (=134 verdicts) | 150/50/0; 0 moves, 0 reply-moves | PASS |
| B2 p2/p3/p4/q1/q4/bench/sleep | verdict-equal 134 (L1 moves exempt) | p2 0/0 (=138 rows; L1 fixes B7/C2/C5/D8 vs 134); p3 L1-L6 PASS; p4 0/0; q1 F5+M5; q4 0 leaks; bench 150/50/0+157/43/0; sleep SKIP | PASS |
| B2 rt110 (62) | equal 134, S1 back | OK→BUG 3 (S1 + P4 + U1), still-BUG 7 | FAIL (3 moves) |
| B2 rt81 (74) | verdict-equal 134 | 61 OK / 0 BUG / 13 UNCLEAR, per-case verdicts = 134 | PASS |
| B2 soak (2000, 3 kills) | 0 lost/wrong/doubled | 0/3/0, audit pairs 0/0/0 | FAIL (3 wrong) |
| B3 panel (100, turn path) | ≤ 6 wrong | 20 wrong (same 6 as 138 + 14 flips) | FAIL |
| B3 bench routing | informational | served_self 0 / served_base 62 (165 no longer served) | — |
| B4 probe (4) | 4/4 base-verbatim, 0 mashed markers | 4/4 OK, all DECLINE→base | PASS |
| B5 time | each run < 25 min | probe 2.6 s, bench 24.1 s, panel 7.1 s, marks 423.5 s | PASS |

## Why each FAIL happened (one diagnosis note each)

- B1-174: the frozen 113c gate misjudged a full N-hop frame as partial, so
  the notebook itself answered short (records: answer/OK, never routed). The
  self rule is never consulted on notebook-won turns -- unfixable by this
  change, by construction.
- B2-S1: redteam count-probe ("how many facts…also Mira's pet is a cat")
  misses the notebook, router fires C1, and the C1 answer is genuinely
  grounded state content ("I know 0 facts…"), so the rule serves it -- S1
  stays BUG by design. P4/U1 are load flakes, not the rule: loop-level
  repro serves both correctly, and a solo open rt110 re-run gives
  OK→BUG [S1] only, exactly loop138's pattern (registered rt110 took 423 s
  vs 120 s for 138 -- machine heavily loaded by parallel agents).
- B2-soak: 3 wrongs, all bare "I didn't catch anything." empty-read
  clarifies on scattered turns (202/567/1712), audit pairs 0/0/0 -- the
  known mailbox-race signature under load (cf. exps 155/158), same family
  as the P4/U1 flakes; base-loop text, never self content.
- B3: 14 C-intent paraphrases the frozen router declines (novelty guard)
  flip DECLINE→WRONG. Loop138's mashed decline carried scorer markers
  (filed DECLINE, neutral); 138c's honest base clarify ("…Could you say it
  another way?") carries none, so the unchanged scorer files it WRONG on
  "Could". The sealed accept rule covers only decline-expected items, so
  these stay WRONG. No new content anywhere: bench-new served_self = 0.

## Deviations

None post-seal (no code edits after `SEAL.sha256.txt`; solo rt110 re-run
was diagnostic only, output to scratch, registered artifact untouched).
Pre-seal extension stated in PASSMARKS: grounded = FALLBACK + marker
clause (brief named FALLBACK only; 165's hijack text "I have no opinions…"
is a decline body, so the marker clause does the work).

## What it means

The mashed decline is gone everywhere: probe 4/4 base-verbatim, 165 back
to abstain, zero self content served on 200 bench items, panel declines
served as honest base clarifies (39 accept-rule hits).

## What it does not mean

Not a superset of loop134: grounded self content still fires on
redteam-shaped misses (S1-class) by design; the 113c gate over-fire
(174-class) is untouched; and honest base clarifies score WRONG under the
unchanged panel scorer on router-declined C-intent paraphrases (14 flips).

## Reproduce

Seal: `shasum -c artifacts/fable-self138c-20260922/SEAL.sha256.txt`. B4:
`… python -B scripts/fable_loop138c_probe.py`. B1:
`… python -B scripts/fable_loop138c_bench121.py`. B3:
`… python -B scripts/fable_loop138c_selfcheck.py`. B2:
`… python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop138c_agent.py --config
artifacts/fable-self138c-20260922/loop138c-config.json --out
artifacts/fable-self138c-20260922/marks138c --workers 4`.
Questions for Ben: none.
