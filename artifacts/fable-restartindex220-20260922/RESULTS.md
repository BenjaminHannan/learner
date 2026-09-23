# Exp 220 RESULTS — restart must not double the fast index (PASS)

One change on loop138i: after a load, every event is indexed exactly once.
`FixedIndexedContractNotebook._load` calls `C.Notebook._load(self)` (whose loop
already indexes each line via `self._apply`) and drops the second
`for ev in self.events: self._index_event(ev)` pass. New files only:
`scripts/fable_fix220_restartindex.py`, `scripts/fable_loop220_agent.py`,
`scripts/fable_fix220_marks.py` (scorer), config + cases + PASSMARKS sealed in
`artifacts/fable-restartindex220-20260922/` (SEAL 6/6 OK post-runs, no post-seal edits).

## Marks (registered; integer counts)

| mark | fixed (loop220) | base (138i) | bar | verdict |
|---|---|---|---|---|
| R1 index equality, 60 comparisons | 60/60 equal | 20/60 (only determinism) | 60/60 | PASS |
| R2 ghost cases, 11 histories | 11/11 clean | 0/11 (reverse serves ghost) | 11/11 | PASS |
| R3 answers, 20 histories x 10 q x 3 arms | 20/20 identical | — | 20/20 | PASS |
| R4 rt136 / rt143 / sessions152 / bench(800) | 0/0/0/0 moves | — (sealed rows) | 0 moves | PASS |
| R5 sleep smoke | = 138i on every mark | reference | equal | PASS |
| R6 load, 6002 events, 5 reps | wall max 0.073 mean 0.064 | wall max 0.082 mean 0.072 | <= +10% | PASS* |

R2 detail: after restart + "Forget Lee's city.", base answers "Oslo is the city
of Lee." and still lists ('Lee','city','Oslo'); fixed answers "I don't know
anyone whose city is Oslo." / "I don't know Lee's city." with clean triples on
all 11 cases (forward, reverse, and boss-chain probes all abstain).
R5 detail (both arms): sleeps=1, installed=1, episodes=20, probes 5/5 right,
0 wrong, broken-chain abstains, taught 50/50 dupes 0, overwrites 0.

## Sleep-path question
The sleep path does NOT read the index-backed triples. Episode replay
(`Sleep130Reasoner._queue130`, `Sleep145Reasoner.answer`) reads only
`notebook.current()` (facts + the log-derived `active()` flag), never
`_triples/_sro/_rev`. A forgotten fact is inactive, so it cannot be queued or
replayed into weights: R2 probes show `current()` empty after forget on both
arms, and smoke shows 0 taught overwrites on both. The ghost lived only in the
duplicated triple/reverse indexes that serve reverse questions and the
170-cached `notebook_triples`.

## What it means
Restarting no longer corrupts the index: forgets fully forget, and every reply
is restart-independent.

## What it does not mean
It does not change any fresh-session behaviour (R4: 0 moves on 800+ frozen
cases) and does not touch sleep learning (R5 identical); it only removes the
stale second copy.

## Deviations / notes
* R2 pass = all three probes abstain + triple gone (abstain templates echo the
  question's value, e.g. "…whose city is Oslo." — correct, not a leak).
* *R6 note: strict per-rep wall pairing missed once (rep3: fixed 0.069 vs base
  0.061, +13%, 8 ms over the paired bound under concurrent-machine noise);
  process-time fixed <= base on all 5 reps, and wall aggregates pass
  (max 0.073 vs 0.082; mean 0.064 vs 0.072).
* One pilot-only bench132 reply-only flake (item 103, correct->abstain) never
  reproduced: 0 moves in the registered bench run, 0 moves in 10 seeded
  bench132 runs (seeds 0-9, both agents), 0 same-process base-vs-fixed moves
  over all 200 items — cross-process seed flake, agent-independent.
* One suite at a time; every run < 25 min (max 107.5 s); isolated scratch dirs
  only; fictional names only; ledger P220.1-7 appended pre-run, outcomes post-run.

## Reproduce (each: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B …`)
* R1/R2/R3: `scripts/fable_fix220_marks.py --mode r1|r2|r3 --agent fixed
  --cases artifacts/fable-restartindex220-20260922/cases220.json --out <dir>`
* R4: `scripts/fable_suitediff.py --agent scripts/fable_loop220_agent.py
  --config artifacts/fable-restartindex220-20260922/loop220-config.json
  --base 138i --out <dir> --only rt136|rt143|sessions152|bench`
* R5: `scripts/fable_sleepsmoke206.py --agent scripts/fable_loop220_agent.py
  --config artifacts/fable-restartindex220-20260922/loop220-config.json
  --root <dir> --report <f> --label fixed220 --idle-seconds 5.0`
* R6: `scripts/fable_fix220_marks.py --mode r6 --agent both --out <dir>`

No questions for Ben. Verdict: PASS.
