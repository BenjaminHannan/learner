# PASSMARKS — Exp 172b: bench protocol v3 ("confirming user") for the 172 copula-ask agent (Muse)

Sealed before any registered run. Agent code is 172's, UNCHANGED
(`scripts/fable_loop172_agent.py`; the ONE agent change versus loop154c:
non-allow-listed copula/verb-shape re-teach without an explicit
correction prefix asks the possessive change-prompt). Base for behaviour:
loop154c (`scripts/fable_loop154c_agent.py`). Every seed/case reported,
never averaged. One change only versus 172: NOTHING in the agent — the
bench driver adds the director-ruled confirm step (protocol v3).

Director ruling (08:20): the agent keeps asking. Bench protocol v3 =
"confirming user": after any bench edit turn whose reply is the agent's
change-prompt naming that edit's new value, the driver sends exactly one
extra turn "yes" and continues. No other extra turns, no other replies
accepted, the question turns are unchanged.

## Sealed reply forms (the whole spec)

- Copula re-teach, single-valued, no prefix: `I have Zilo's country of
  citizenship as Velmar. Do you want me to change it to Ostrin?`
  ("yes" -> `Saved: Zilo's country of citizenship is Ostrin.`;
  "no" -> `Okay, I left it as it was.`)
- Explicit correction (`Actually, ...`): silent correct as now
  (`Saved: Remy's country of citizenship is Ostrin.`)
- Allow-listed copula re-teach (`X is famous for Y` -> notable_work):
  byte-identical to loop154c (`Saved: Vex's notable work is Quux.
  (I also have Zoop.)`, ask lists oldest-first).
- Unanswered prompt + unrelated next turn: `(I dropped my earlier
  question.) ...` (inherited 154c/138b behaviour, unchanged).

## T marks (probes, sealed case files)

- T1: 154c's sealed T1 probe
  (`probe172b_t1_cases.jsonl`, byte copy of
  `artifacts/fable-multival154b-20260922/probe154b_cases.jsonl`, 81
  lines): 81/81 exact through loop172. Why identical: all its re-teaches
  are possessive shapes (act="teach", never the downgraded correct-route)
  or prefixed/allow-listed; 172's ears pass those through byte-identical.
- T1b: 154c's T1b probe turns with ONLY the copula silent-overwrite line
  changed to the change-prompt form (`probe172b_t1b_cases.jsonl`, 86
  lines / 83 turns in 3 reset-segments): 83/83 exact. Changed lines vs
  `artifacts/fable-multival154c-20260922/probe154c_cases.jsonl` (turns
  unchanged; expects/states regenerated open pre-seal from the 172 loop
  and reviewed):
  n=6 expect silent-`Saved: ... Portugal.` -> change-prompt
  (`I have Lionel Messi's country of citizenship as Argentina. Do you
  want me to change it to Portugal?`); n=7 expect `... is Portugal.` ->
  `... is Argentina.` (pending prompt kept; the ask path does not consume
  it); n=8 expect gains the `(I dropped my earlier question.)` prefix on
  the next teach; state maps at n=8/12/16/20/24/28 show
  `Lionel Messi|country_of_citizenship: ["Argentina"]` (kept) instead of
  `["Portugal"]`. No other line differs.
- T1c: NEW probe `probe172b_t1c_cases.jsonl` (99 lines / 92 turns in 7
  reset-segments, fictional names/persons only): 92/92 exact. Quotas:
  12 copula re-teaches of single-valued relations (citizen x2, capital
  x2, spouse x2, employer x2, occupation x2, language x1, place-of-death
  x1) -> change-prompt; 6 answered "yes" (state shows the NEW value, ask
  shows new), 6 answered "no" (state shows the OLD value, ask shows old),
  state pinned; 6 `Actually, X is ... Y.` -> silent correct as now (ask
  shows new); 6 allow-listed copula re-teaches (`famous for`) ->
  byte-identical to loop154c (asserted open pre-seal turn-by-turn,
  0 mismatches); 8 other (first-teach Saved, dup-ack, missing-ask,
  copula first-teach) -> byte-identical to loop154c (0 mismatches).
- T2: 0 wrong writes and 0 silent replacements of a taught value on every
  T case = T1+T1b+T1c all pass AND every pinned state map matches AND the
  final full_state matches. Every sealed re-teach of an occupied slot on
  a non-allow relation without a prefix expects the change-prompt, so a
  passing run proves no silent replace (a silent replace would mismatch
  both the prompt expect and the kept-state map).

## G marks

- G1 bench under v3, BOTH loop154c and loop172 (same driver
  `scripts/fable_fix172b_benchv3.py`, same run conditions, 4x200 items):
  loop172 per-item VERDICT identical to loop154c under v3 on 800/800
  items; 0 new wrong (no item where 172-v3 is wrong and 154c-v3 is not).
  Why: after each confirm the two agents hold the same value (154c
  prompts only on possessive re-teaches, of which bench has ~none, so its
  confirms ~= 0 and its v3 rows == its frozen old-driver rows; 172
  prompts on every copula edit and each "yes" lands the same edit 154c
  applied silently). Also predicted: 154c-v3 rows identical to frozen
  `fable_bench121_loop154c_*_rows.jsonl` with 0 confirms per split.
  Info (no bar): loop172 under the OLD driver reproduces 172's
  diagnostic — verdicts move exactly on the 681 scan-flagged items
  (191+197+99+194; stale kept-chain wrong/abstain), 0 confirms.
  Confirm counts reported per split for every arm.
- G2 marks123 (`scripts/fable_marks123_all.py` via subprocess, agent
  `scripts/fable_loop172_agent.py`, config `loop172b-config.json`):
  per-case identical to loop154c's frozen `marks154c` EXCEPT the cases
  below (scan `artifacts/fable-copula172-20260922/trigger_scan172.json`,
  written before any run). A case whose sealed expectation was the silent
  replace NEVER counts as a new WRONG unless the agent writes or answers
  something false (prompt turns must write 0 facts; finals must be
  taught-kept values or abstains).
  p2 (predicted finals; asking is the correct behaviour, the kept chain
  answers a taught value):
  B1 final `Roberto Merhi's country of citizenship's official language is
  Spanish.` (Arabic re-teach unconfirmed; was Arabic);
  B2 final `... is Spanish.` (Portugal unconfirmed; was Portuguese);
  B3 final `CM Punk's spouse's languages spoken written or signed is
  English.` (Russian unconfirmed; was Russian);
  B6 final `Poland's capital is Warsaw.` (same final as sealed; Krakow
  unconfirmed so step-2 reply is the prompt and step-3 is the dup-ack);
  B7 final `... is Spanish.` (Atlantis unconfirmed; was don't-know);
  B8 final `Twitter's chief executive officer's country of citizenship is
  United States of America.` (Latvia unconfirmed; was Latvia);
  F2 final `... is Spanish.` (restart clears the unanswered prompt; was
  Arabic). Each re-teach turn's reply is the change-prompt naming old->new
  (Spain->Arabic, Spain->Portugal, English->Russian, Warsaw->Krakow,
  Spain->Atlantis, USA->Latvia).
  rt110 (predicted IDENTICAL — scan false positives from static tracking
  that ignores forget/vanish):
  F2 turn-3 `Saved: Poland's capital is Krakow.` (forget emptied the slot;
  the re-teach is a first-teach, no prompt — correct);
  F6 turn-4 `Saved: Roberto Merhi's country of citizenship is Portugal.`
  (forget cleared citizenship; re-teach lands; final Portuguese —
  correct); D5 identical (the Krakow turn vanishes mid-read, never
  processed; final Warsaw, Krakow absent everywhere — correct).
  marks-bench suite (old driver, 400 items): verdict/reply moves ONLY on
  scan-flagged ids in fable_edit_200 (99) + s2fresh_4hop (197); prompt-form
  teach-reply diffs only on flagged ids; 0 new wrong on unflagged ids.
  p3/p4/q1/q4/rt81/sleep/soak: per-case identical (semantic fields;
  seconds volatile).
- G3 sessions152 + redteam136/143 (`scripts/fable_fix172b_g3.py`,
  idle_seconds=30.0): 0 moves vs frozen loop138b rows, 0 new
  WRONG/WRONG-WRITE, 0 new writes (scan: 0 triggers in all three sets).
- G4: every registered run < 1500 s wall-clock Mac CPU with
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; daemon wrappers take idle_seconds
  (benchv3 30.0 s; G3 30.0 s; marks123 internal 3600 s). Heavy suites run
  one at a time.

Predictions ledger: P172b.1..P172b.8 (appended before any registered run).

## Sealed files (hashes in SEAL.sha256.txt)

- `artifacts/fable-copula172b-20260922/PASSMARKS.md`
- `artifacts/fable-copula172b-20260922/probe172b_t1_cases.jsonl`
- `artifacts/fable-copula172b-20260922/probe172b_t1b_cases.jsonl`
- `artifacts/fable-copula172b-20260922/probe172b_t1c_cases.jsonl`
- `artifacts/fable-copula172b-20260922/loop172b-config.json`
- `scripts/fable_fix172b_probe.py`
- `scripts/fable_fix172b_benchv3.py`
- `scripts/fable_fix172b_g3.py`
- `scripts/fable_fix172b_markscmp.py`

Open pre-seal helpers (NOT sealed, NOT registered):
`scripts/fable_fix172b_buildcases.py` (wrote the T1b/T1c case files from
open reference-arm runs; reviewed turn by turn). Agent code
`scripts/fable_loop172_agent.py` is 172's (read-only; sha recorded below,
unchanged by 172b). Shared infra read-only: `scripts/fable_bench121_run.py`,
`scripts/fable_marks123_all.py`, `scripts/fable_loop154c_agent.py`,
`scripts/fable_fix154c_probe.py`, `scripts/fable_fix154c_allowlist.py`,
`scripts/fable_loop102_agent.py`, scan
`artifacts/fable-copula172-20260922/trigger_scan172.json`.

Any code edit after the seal (including driver/scorer/case files) is
reported and the affected marks re-run in the open. No rule changes after
the seal. A FAIL is recorded as FAIL with one diagnosis note; no silent
re-runs.
