# Exp 168 PASSMARKS — self-grounded canned replies (sealed before run)

Agent: `scripts/fable_loop168_agent.py` (Loop168AgentLoop /
Loop168Daemon, build_agent168, DEFAULT_CONFIG168) — subclasses loop138b
(read-only, never edited). THE ONE CHANGE lives in
`scripts/fable_fix168_ground.py`: the L2 self path serves
`grounded_self_answer` instead of loop138's `self_answer_from_live_state`.
Rule: a canned self reply naming an entity/value is emitted ONLY if the
notebook currently holds exactly that fact; otherwise the fact clause is
stripped (`I do not have favourites.` / `I have no opinions.` /
`I cannot predict.` / `You never taught me their age, ...`); replies
depending on a web filing / forgotten fact / taught rows with empty state
say so plainly (`I haven't filed anything from the web.`) instead of
crashing. All other replies byte-identical (base answerer called intact).
Config: `artifacts/fable-selfground168-20260922/loop168-config.json`
(same plug points as loop138b-config.json).
Drivers (new, sealed): `scripts/fable_fix168_probe.py` (T1/T2),
`scripts/fable_fix168_bench.py` (G1), `scripts/fable_fix168_regress.py`
(G3); G2 runs `scripts/fable_marks123_all.py` with the 168 agent.
Cases (sealed): `artifacts/fable-selfground168-20260922/
fable_fix168_probe_cases.json` (61 turns: A25 fresh self-Qs with fictional
names, B3 teaches + 10 asks with Mira-green/Paris + Oslo taught, C5 empty +
3 with-state web/sleep/proposal Qs, D15 ordinary teach/ask turns).

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1`, `uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B ...`. Every seed/case reported, never
averaged. A registered FAIL stays FAIL. No code edit after the seal
except as reported in RESULTS.md (affected marks re-run in the open).

## Marks

- T1: `... python -B scripts/fable_fix168_probe.py --out
  artifacts/fable-selfground168-20260922/probe168`. Bar: part A 25/25
  with 0 crashes and 0 replies naming a check-name not in the notebook;
  part B 10/10 byte-identical to loop138b; part C 5/5 empty-state plain +
  honest with 0 crashes and 3/3 with-state byte-identical; part D 15/15
  byte-identical (reply + write flag).
- T2: same run. Bar: 0 FACT/RETRACT events added by any of the 43
  self-question turns on loop168.
- G1: `... python -B scripts/fable_fix168_bench.py` (reuses sealed
  `fable_loop138b_bench121.py` split table + `fable_bench121_run` scorer
  by import; loop168 arm only). Bar: per-item verdict AND reply identical
  to `fable_bench121_loop138b_*_rows.jsonl` on all 4 splits — 0 moves,
  0 new wrong expected.
- G2: `... python -B scripts/fable_marks123_all.py --agent
  scripts/fable_loop168_agent.py --config .../loop168-config.json --out
  .../marks168 --workers 4`. Bar: every suite per-case identical to
  sealed `marks138b` (seconds/tmp-path/agent-name/sleep-SKIP-reason
  scrubbed) EXCEPT 4 predicted reply-only moves, verdicts identical:
  rt81 `O_user-03` + `I_edges-03` and p3-l2 `O_user-03` + `I_edges-03`
  (`I have no opinions. Oslo and Paris...` -> `I have no opinions.`;
  `I cannot predict. Nothing you taught me...` -> `I cannot predict.`,
  notebook holds neither Oslo/Paris nor Mira there). No other move.
- G3: `... python -B scripts/fable_fix168_regress.py` (sessions152 +
  redteam136 + redteam143 patterns by import, loop168 only, vs loop138b
  frozen JSONs). Bar: 0 new WRONG / 0 new junk writes; every move
  predicted: redteam143 `J8`, `K9`, `O5` reply-only moves
  (`I have no opinions. Oslo and Paris...` -> `I have no opinions.`,
  verdicts stay WRONG-ANSWER — no abstain marker in either string);
  sessions152 0 moves; redteam136 0 moves.
- G4: every registered run above < 25 min wall-clock Mac CPU
  (OMP_NUM_THREADS=1; one heavy suite at a time; daemon wrappers take
  idle_seconds, default 30.0).

## Frozen references (read-only)

- Sealed loop138b rows: artifacts/fable-agent138b-20260922/
  (SEAL.sha256.txt): `fable_bench121_loop138b_*_rows.jsonl`,
  `sessions152-loop138b.json`, `redteam143-loop138b.json`,
  `redteam136-loop138b.json`, `marks138b/`.
- Ledger P168.1–P168.7 appended pre-run.
