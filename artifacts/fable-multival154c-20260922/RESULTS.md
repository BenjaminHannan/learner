# RESULTS — Exp 154c: multi-valued relations as an allow-list (Muse)

Base: loop154b (`scripts/fable_loop154b_agent.py`), subclassed read-only;
no base file edited. Agent: `Loop154cAgentLoop`
(`scripts/fable_loop154c_agent.py`). Step 1 answer: 154b's multi-valued
test is `scripts/fable_fix154b_multival.py:39-41` (`is_single154b` -- every
key outside the 11-entry SINGLE_VALUED_154 table takes the add path);
154c replaces it with `is_multi154c`
(`scripts/fable_fix154c_allowlist.py`) -- ONLY the 22 allow-listed keys
take the add path, all others take the loop138b path byte-identically.
Full design: `design/v3/30-modes/154c-multival-allowlist-muse.md`.

## The one change versus loop154b (sealed forms)

Allow-listed teach of a new different value ADDS (`Saved: Omar's sister
is Lena. (I also have Priya.)`); allow asks list oldest-first; 2-hop
through a 2-valued allow hop clarifies; correct-not / forget-one-value on
allow as 154b. Deny-listed re-teaches (citizenship, language, occupation,
employer, team, country, ...) keep loop138b's change-prompt
byte-identical -- including copula shapes (`Lionel Messi is a citizen of
Y` maps to country_of_citizenship) and multi-word subjects.

## Marks table (integer counts, every seed/case reported)

| mark | bar (sealed) | number | status | secs |
|---|---|---|---|---|
| T1 probe (81) | 81/81 exact (154b probe reused unchanged) | 81/81 | PASS | 0.2 |
| T1b probe (83 turns) | 83/83 exact (28 deny =138b, 12 allow adds +5 clarifies =154b forms) | 86/86 lines | PASS | 0.2 |
| T2 writes | 0 wrong, 0 lost | 0 wrong; 21 state maps + full_state exact | PASS | — |
| G1 bench 4x200 | moves only on 16 allow-dup items; 0 new wrong | 15 moves, all correct->abstain clarifies on allow-dup items, 0 elsewhere, 0 new wrong | PASS | 43.3 |
| G2 marks123 | per-case identical to marks138b except predicted | p2 identical PASS (B1/B2/B3/B5/B8/F2 fixed); l5z2 1 predicted move; rest identical (see note) | FAIL | 497.0 |
| G3 junk/redteam/sessions | 0 moves, 0 new wrong/write | rt136 145/145, rt143 124/124, sessions152 6/6: 0 moves | PASS | 7.5 |
| G4 clock | every run < 1500 s | max 245.8 (soak); bench 43.3, rt110 151.4, p3 60.9 | PASS | — |
| soak | 2000 turns 3 kill-9, 0 lost/wrong/doubled | 2000/3/0/0/0 identical to 138b | PASS | 245.8 |

Predictions: P154c.1 TRUE | P154c.2 TRUE | P154c.3 TRUE | P154c.4 TRUE |
P154c.5 TRUE | P154c.6 TRUE. 6/6.

## G2 FAIL — one diagnosis note

FAIL (recorded, not re-run) for exactly the ONE predicted allow-list
move: l5z2 bench65-mquake-033 (`William Gibson is famous for
Neuromancer/Little Busters!`) goes correct->MISS, asking `William
Gibson's notable work is Neuromancer and Little Busters. Which one do you
mean?` -- notable_work is allow-listed, so 154c behaves as 154b here, by
design. Marks-bench moves exactly on the 4 predicted allow-dup items
(mquake-033, s2fresh-031/125/200, all correct->abstain). Everything else
is per-case identical: p2 64/64 (the 154b B/F fact-edit failures are
fixed), l1/l2/l3/l4/l6 PASS identical, l5z1 FAIL identical (58/60
per-turn both, pre-existing), p4 30/30 identical, rt110 62/62
verdict+reply identical, q1/q4 PASS, rt81 74/74 identical (60/0/14 both,
suite bar pre-existing), sleep SKIP both, soak identical. No soak/rt110
flakes observed (no open re-runs).

## Deviations / notes

1. Open pre-seal helper `scripts/fable_fix154c_buildprobe.py` (un-sealed)
   generated the T1b case file from reference-arm runs; expects reviewed
   turn by turn. Sealed files untouched (`shasum -c SEAL.sha256.txt`
   passes post-run).
2. rt110 case M1: verdict/reply/fact-writes identical; one harness log
   metadata field differs (`statuses []` frozen on 138b vs `["write"]` on
   154b AND 154c -- allow-path consistent, judge "all sealed checks
   held" on all three). Not counted as a move.
3. T1b runs in 3 reset-segments (sealed design): segments isolate the
   yes/no pending state, which legitimately evolves per-arm.

## Questions for Ben

None -- the p2 replace-vs-add question from 154b is resolved by the
allow-list (family words add; citizenship/language/etc. replace).

## Reproduce (Mac CPU, offline)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154c_probe.py --cases artifacts/fable-multival154b-20260922/probe154b_cases.jsonl --out artifacts/fable-multival154c-20260922/probe154b --state-dir <fresh-dir>
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154c_probe.py --cases artifacts/fable-multival154c-20260922/probe154c_cases.jsonl --out artifacts/fable-multival154c-20260922/probe154c --state-dir <fresh-dir>
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154c_regress.py --bench
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154c_g3.py
```

## What it means

Sisters, friends, children, pets and 8 more family/work relations keep
every value taught and clarify before reasoning through one, while
re-teaches of citizenship, language, occupation, employer, team and
country replace exactly as before -- the 154b fact-edit failures are
fixed (p2 B/F back to identical, 6/6 predictions true).

## What it does not mean

It does not keep second values for deny-listed relations (one l5z2
mquake item still clarifies instead of answering), and it does not merge
values or guess which sister you meant.
