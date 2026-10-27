# PASSMARKS — Exp 154c: multi-valued relations as an allow-list (Muse)

Sealed before any registered run. Base: loop138b frozen rows in
`artifacts/fable-agent138b-20260922/` (+ 154b's frozen rows for
differential prediction). Every seed/case reported, never averaged. One
change only versus loop154b: the add-a-second-value path fires ONLY for
`MULTI_VALUED_154C` (allow-list); all other relations take the loop138b
path byte-identically.

## Sealed reply forms (the whole spec)

- Allow-listed add: `Saved: Omar's sister is Lena. (I also have Priya.)`
- Allow ask, oldest first: `Omar's sister is Priya and Lena.`
  (3+: `Priya, Lena and Ana.` — no Oxford comma)
- 2-hop through a non-final ALLOW hop with 2+ values:
  `Omar's sister is Priya and Lena. Which one do you mean?` (never a guess)
- Correct-not on allow: `Saved: Omar's sister is Lena.` (+ remainers /
  `(I didn't have {old}.)` as 154b)
- Forget-one on allow: `Forgotten: Omar's sister Priya.` /
  miss: `I don't have Omar's sister Priya.`
- Every deny-listed relation (citizenship, language, occupation, employer,
  team, country, ... and all SINGLE_VALUED_154): today's loop138b
  change-prompt / replace, byte-identical (e.g. `I have Omar's
  citizenship as Spain. Do you want me to change it to Portugal?`).

## T marks (probes, sealed case files)

- T1: 154b's sealed probe
  (`artifacts/fable-multival154b-20260922/probe154b_cases.jsonl`, reused
  UNCHANGED): 81/81 exact through 154c. STOP-check done pre-seal: its
  relations are boss/brother/child/city/friend/mother/pet/sister/spouse/
  teacher; every multi one (brother/child/friend/pet/sister) is
  allow-listed, every single one is deny (138b == 154b path). No STOP.
- T1b: NEW probe `probe154c_cases.jsonl` (83 turns in 3 reset-segments,
  86 lines): 83/83 exact. Quotas: 28 deny re-teach/edit turns (citizenship
  x5 incl. multi-word "Lionel Messi" + copula "is a citizen of" both
  mapping to country_of_citizenship, language/occupation/employer/team/
  country re-teaches each declined with "no", deny correct-not, deny
  forget) byte-identical to loop138b; 12 allow second-adds (sister,
  brother, sibling, friend, child, son, daughter, pet, dog, cat, cousin,
  notable_work, each with list-ask) in 154b's sealed forms; 5 two-hop
  clarifies through 2-valued sister/brother/friend hops; 8 first-teach
  setups (plain Saved in both arms). Segments isolate the yes/no pending
  state; segment-C setups reference 154b (pending-clean first-teach
  Saved). Expects generated open pre-seal from the reference arms and
  reviewed turn by turn.
- T2: 0 wrong writes, 0 lost values = T1b 83/83 AND every pinned state
  map (21) matches AND the final full_state map matches exactly.

## G marks (regressions vs loop138b frozen rows)

- G1 bench (4x200 vs `fable_bench121_loop138b_*_rows.jsonl`): every
  per-item move (verdict or reply) lands on one of the 16 pre-sealed
  allow-dup items (child/notable_work double-teaches, enumerated in
  `trigger_scan154c.json` and below); 0 moves on the other 784 items.
  Predicted moves (from 154b's frozen diff on the same items): the same
  15 correct->abstain mid-chain clarifies, bench132-4hop-112 no-move.
  New wrongs: 0 (154b's 55 new wrongs were all final-hop list forms on
  deny relations, which revert under 154c).
  Allow-dup ids: bench121-4hop-069/079/110/137/162/195,
  bench103-s2fresh-4hop-031/125/200, bench65-mquake-033,
  bench132-4hop-022/045/112/113/142/179.
- G2 marks123 (per-case verdict+reply vs `marks138b`, every suite):
  p2 per-case identical (B1/B2/B3/B5/B8/F2 return to identical -- the
  fix); p3 identical EXCEPT l5z2 bench65-mquake-033 correct->MISS
  (`William Gibson's notable work is Neuromancer and Little Busters.
  Which one do you mean?`, same as 154b); marks-bench suite moves exactly
  on bench65-mquake-033 + bench103-s2fresh-4hop-031/125/200 (all
  correct->abstain clarifies, same replies as 154b); p4/rt110/q1/q4/rt81/
  sleep/soak per-case identical. Pre-seal scan (`trigger_scan154c.json`,
  REAL loop138b ears hear() over every suite input -- copula shapes and
  multi-word subjects parsed natively): 0 allow triggers in p2 (64),
  rt110 (62), rt81 (17 seqs), q1 (7), p4 (30), p3 literals, redteam136
  (145), redteam143 (124), sessions152 (6); bench flags exactly the 16
  allow-dup items above. Soak teaches only city (deny).
- G3 sessions152 + redteam136/143: 0 moves, 0 new WRONG/WRONG-WRITE, 0 new
  writes (scan: 0 allow triggers in all three input sets; 154b already
  0 moves there).
- G4: every registered run < 1500 s wall-clock Mac CPU with
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; daemon wrappers take
  idle_seconds (G3 30 s; marks123 internal 3600 s).

Predictions ledger: P154c.1..P154c.6 (appended before any registered run).

## Sealed files (hashes in SEAL.sha256.txt)

- `artifacts/fable-multival154c-20260922/probe154c_cases.jsonl`
- `artifacts/fable-multival154c-20260922/loop154c-config.json`
- `artifacts/fable-multival154c-20260922/trigger_scan154c.json`
- `scripts/fable_loop154c_agent.py`
- `scripts/fable_fix154c_allowlist.py`
- `scripts/fable_fix154c_probe.py`
- `scripts/fable_fix154c_regress.py`
- `scripts/fable_fix154c_g3.py`
- `scripts/fable_fix154c_scan.py`

Open pre-seal helpers (NOT sealed, NOT registered): `scripts/
fable_fix154c_buildprobe.py` (wrote the T1b case file from reference-arm
runs). Any code edit after the seal (including scorer/driver/case files)
is reported and the affected marks re-run in the open. A FAIL is recorded
as FAIL with one diagnosis note; no silent re-runs. Soak/rt110 flakes
under heavy load are a known mailbox race: re-run that suite once in the
open and report both.
