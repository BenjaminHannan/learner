# Exp 138e PASSMARKS — officeholder rewrite-chain guard, sealed before run

Agent: `scripts/fable_loop138e_agent.py` (Loop138eEars / Loop138eAgentLoop /
Loop138bMouth / Loop138eDaemon, build_agent138e, DEFAULT_CONFIG138E).
Config: `artifacts/fable-officechain138e-20260922/loop138e-config.json`.
Held-out cases: `artifacts/fable-officechain138e-20260922/heldout138e-sealed.json`
(32 fresh officeholder-chain questions with new names: 16 rewrite-right
138e-R01–R16, 16 would-be-wrong 138e-W01–W16; classes labeled by ONE open
run of the FROZEN base loop138b, never by 138e).
Sealed with `shasum -a 256` to SEAL.sha256.txt together with the agent file
and all `scripts/fable_fix138e_*.py` drivers. Ledger P138e.1–P138e.6
appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL.
No code edit after the seal; any edit is reported and the affected marks
re-run in the open. No rule changes after the seal.

## The sealed rule (one)

The rewriter's officeholder hop is used only when the session shows no
refused teach/correct mentioning the ask's entities, or when every
same-office sibling compound agrees on the holder. Veto (base 113c
clarify/abstain stands, stage `loop138e-veto-officeholder`) iff: (a) the
rewrite fires with `officeholder` in its rels; (b) a recorded refusal
(hear-side clarify on a non-"?" turn, or an _act teach/correct whose write
is not "Saved:"/duplicate) mentions a seed entity or a same-office sibling
target; (c) a same-office-prefix sibling compound with a different target
is unreachable from the seeds AND resolves to a different holder. STEP 1
diagnosis (dev only): 146 officeholder chains (140 correct, 3 wrong
025/073/149, 2 abstain off-path, 1 F5 fix); the veto fires on exactly the
3 wrongs and keeps all 140 corrects (full table + rejected features in
design/v3/30-modes/138e-officechain-muse.md).

## Marks

- T1: `… python -B scripts/fable_fix138e_heldrun.py` (32 sealed held-out
  cases, fresh Loop138eDaemon per item). Bar: 0 wrong over all 32;
  rewrite-right 16/16 still correct (bar floor: >= 13/16); would-be-wrong
  16/16 abstain, 0 wrong (predicted: veto returns the base clarify on each
  W case, stage `loop138e-veto-officeholder`; R cases take the unchanged
  rewrite path, stage `loop138b-rewrite`).
- T2: bench121-new items 025/073/149 (run inside G1). Bar: no longer
  wrong — predicted exactly wrong->abstain on all three (the base 113c
  abstain text, as loop138 gave); 174 stays wrong (113e OUT, unchanged).
- G1: `… python -B scripts/fable_fix138e_bench.py` (bench121-new +
  bench103-old-s2fresh + bench65-edit200 + bench132-4hop; reuses
  `artifacts/fable-agent138b-20260922/fable_loop138b_bench121.py` by
  import; per-item compare with the sealed
  `fable_bench121_loop138b_*_rows.jsonl` files). Bar: 0 new wrong on every
  split; exactly 3 per-item moves (025/073/149 wrong->abstain incl. reply
  and stage); every other item verdict-, reply- and stage-identical.
- G2: `… python -B scripts/fable_marks123_all.py --agent
  scripts/fable_loop138e_agent.py --config
  artifacts/fable-officechain138e-20260922/loop138e-config.json --out
  artifacts/fable-officechain138e-20260922/marks138e --workers 4`. Bar:
  every suite per-case verdict-identical to sealed marks138b; suite
  statuses identical (p2 PASS; p3 FAIL on l5z1 only; p4/rt110/q1/bench/q4/
  soak PASS; rt81 suite FAIL label inherited; sleep SKIP). Predicted
  cosmetic-only diffs: sleep reason names `fable_loop138e_agent.py`;
  rt110 M1 log statuses `["write"]` vs `[]` on the Saved teach (verdict OK
  both); l6 `replied_before_kill` timing counters may differ (all verdicts
  identical). Soak/rt110 flakes under heavy load are the known mailbox
  race: re-run that suite once in the open and report both.
- G3: `… python -B scripts/fable_fix138e_junk.py` (redteam136 145 cases;
  cases150 57; f1 46; cases139b 101; vs frozen 138b outputs) and
  `… python -B scripts/fable_fix138e_redteam.py` (143 cases vs
  redteam143-loop138b.json) plus `--only sessions` (sessions152 vs
  sessions152-loop138b.json; scripts/fable_loop138b_sessions.py pattern).
  Bar: 0 per-case moves everywhere; 0 new WRONG/WRONG-WRITE/junk writes;
  frozen tallies kept exactly (redteam136 135 OK/7 WW/3 MISSED; f1 45 OK +
  t14-only write; cases150 57/57; cases139b 101/101; 143 106 OK/7 MISSED/
  11 WRONG incl. H5 WRONG + F5 OK; sessions 129 OK/2 WRONG both arms, 0 new
  writes).
- G4: every registered run above < 25 min wall-clock Mac CPU
  (OMP_NUM_THREADS=1; daemon wrappers take explicit idle_seconds).

## Frozen references (read-only, never rewritten)

- Sealed loop138b rows/outputs: artifacts/fable-agent138b-20260922/
  (SEAL.sha256.txt); sealed marks138b therein.
- 143 cases: artifacts/fable-redteam143-20260922/;
  sessions: artifacts/fable-session152-20260922/sessions152.json.
- Junk cases + seals: artifacts/fable-redteam136-20260922/,
  fable-fix139b-20260922/, fable-fix150-20260922/, fable-fix144-20260922/.
