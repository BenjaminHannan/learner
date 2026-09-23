# PASSMARKS — Exp 154b: second values for multi-valued relations (Muse)

Sealed before any registered run. Base: loop138b frozen rows in
`artifacts/fable-agent138b-20260922/`. Every seed/case reported, never
averaged. One change only (multi-valued add, never replace).

## Sealed reply forms (the whole spec)

- Multi add: `Saved: Omar's sister is Lena. (I also have Priya.)`
- Multi ask, oldest first: `Omar's sister is Priya and Lena.`
  (3+: `Priya, Lena and Ana.` — no Oxford comma)
- 2-hop through a non-final multi hop with 2+ values:
  `Omar's sister is Priya and Lena. Which one do you mean?` (never a guess)
- Correct-not: `Saved: Omar's sister is Lena.` (+ `(I also have ….)`
  when values remain; + `(I didn't have {old}.)` when old was not current)
- Forget-one: `Forgotten: Omar's sister Priya.` /
  miss: `I don't have Omar's sister Priya.`
- Single-valued relations (SINGLE_VALUED_154): today's change-prompt,
  byte-identical to loop138b.

## T marks (new probe, `probe154b_cases.jsonl`, 81 cases, sealed)

- T1: 81/81 exact replies. Quotas inside: 17 add-second-value cases
  across sister/friend/brother/child/pet (n=2,5,8,11,14,16,19,22,52,59,
  62,67,70,73,76 +3rd values) each with a list-ask after; 17
  single-valued turns (n=24–40) string-identical to loop138b on fresh
  loops; 8 named-value corrections/forgets (n=41,43,44,46,48,49,56,78);
  7 two-hop clarifies (n=55,60,65,68,71,74,77); plus a single-chain
  contrast (n=80–81, chains to Oslo, no clarify).
- T2: 0 wrong writes, 0 lost values = T1 81/81 AND every pinned state
  map matches AND the final full_state map matches exactly.

## G marks (regressions vs loop138b frozen rows)

- G1 bench (4x200 vs `fable_bench121_loop138b_*_rows.jsonl`): every
  per-item move (verdict or reply) lands on a multi-dup item — an item
  teaching 2+ objects for one non-single (subject, relation)
  (pre-seal scan counts: new_121_4hop 190, old_s2fresh_4hop 197,
  edit200 93, bench132_4hop 186). All no-dup items byte-identical.
  Direction: non-final-hop dups clarify (`Which one do you mean?` is a
  bench abstain phrase) so correct/wrong->abstain; final-hop dups list
  both values so exact-match fails -> wrong (new wrongs only by this
  list form, only on multi-dup items). Teach-reject counts drop on
  multi-dup items (both Saved). 0 moves on no-dup items.
- G2 marks123 (`scripts/fable_marks123_all.py` suites, per-case verdict
  +reply identical to `marks138b`): predicted moves: none. Pre-seal
  scans: p2 64/64 clean, rt110 62/62 clean (T4 hearsay-pet turn
  reviewed: hearsay screen fires before any teach on both arms),
  multi-turn trigger shapes absent by construction of those suites.
- G3 sessions152 + redteam136/143: 0 new WRONG/WRONG-WRITE, 0 moves.
  Pre-seal scans: redteam136 145/145 clean, redteam143 124/124 inputs
  clean, sessions152 6/6 sessions clean.
- G4: every registered run < 1500 s wall-clock Mac CPU with
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; daemon wrappers take
  idle_seconds.

## Sealed files (hashes in SEAL.sha256.txt)

- `artifacts/fable-multival154b-20260922/probe154b_cases.jsonl`
- `scripts/fable_loop154b_agent.py`
- `scripts/fable_fix154b_multival.py`
- `scripts/fable_fix154b_probe.py`
- `scripts/fable_fix154b_regress.py`
- `artifacts/fable-multival154b-20260922/loop154b-config.json`

Any code edit after the seal (including scorer/driver scripts) is
reported and the affected marks re-run in the open. A FAIL is recorded
as FAIL with one diagnosis note; no silent re-runs.
