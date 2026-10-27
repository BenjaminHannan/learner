# Exp 193 — missing-apostrophe possessives on loop138h — PASSMARKS (sealed BEFORE any registered run)

Base: loop138h (`scripts/fable_loop138h_agent.py`, sealed rows in
`artifacts/fable-agent138h-20260922/`). One change, ears only, outermost:
`scripts/fable_loop193_agent.py` (`Loop193Ears(Apos193Mixin,
Loop138hEars)` over the unchanged 138h stack; `Loop193AgentLoop`,
daemon, config identical in shape to 138h). Rule body:
`scripts/fable_fix193_apos.py` (read-only imports only).

## The repair rule (closed)

`rewrite_apos193(turn, nb)`: a word token that equals, ignoring case, a
name ALREADY IN THE NOTEBOOK plus a trailing "s" (`kofis`, `Kofis`,
`toms`, `Juans`; also "s'" forms such as `Kofis'`), immediately followed
(whitespace-adjacent) by a relation word the base can already parse, is
replaced by the notebook-canonical `Name's` form; the rewritten turn is
then parsed by the unchanged base, silently (no confirm; the reply shows
the reading, exactly like the apostrophe twin's). ALL must hold per
token, else the token (and, if no token qualifies, the whole turn) is
untouched and the base owns it byte-identical:

- (a) the candidate token itself carries no apostrophe except one
  trailing "s'" (`Kofi's`-style tokens never match);
- (b) the stem matches the DISPLAY name of exactly one known notebook
  entity case-insensitively, and that display is a single word
  (alias-only matches never fire);
- (c) the full token is not itself a known entity nor the final word of
  a known multi-word entity (plurals `cats`/`bus`, `Wills` with Will
  unknown, stay untouched); an "s'" token preceded by `the` is declined
  (162b owns `The Xs' ...` plural teaches);
- (d) the next word is a known relation: a person relation (the base's
  PERSON_RELATIONS), `city` (sealed 138h rows show the base saves and
  answers it, G3h-5a/b), a relation key already taught into the
  notebook, or the possessive-stripped form of one of those (`boss's`
  counts as `boss`, so 2-hop `Kofis boss's city` and of-chain `city of
  Kofis boss` work).

Out of scope by construction (traps): unknown stems, real plurals,
known stems followed by a non-relation, opinion questions (`What is
your favourite city?`), every already-parsing turn.

## A1 — sealed case file `case193.json` (40 turns)

- 6 cap setup teaches S1-S6 (apostrophe forms, identical on both loops).
- 14 asks Q01-Q14 (missing apostrophe on a known name; what/who/where;
  lowercase + capitalised; 1-hop x8 incl. the director probe shapes,
  2-hop x5 `Kofis boss's city` / `Kofis boss's boss` / `Juans mother's
  boss`, of-chain x1): PASS iff loop193 reply(turn) == loop138h
  reply(twin) with 0 notebook writes on either loop.
- 6 teaches E1-E6 (`kofis mother is Efua.`, `Toms city is Oslo.`,
  `juans boss is Pablo.`, s'-form `Nadias' mother is Sara.`, `amas
  father is Kofi.`, `toms mother is Ana.`): PASS iff loop193
  reply(turn) == loop138h reply(twin) AND the fact delta == twin's delta
  (silent repair: no confirm, twin events).
- 14 traps X01-X14 (unknown stems ask+teach, real plurals `cats`,
  `bus`, `Wills` with Will unknown, `cats mother` with stem unknown,
  known stem + non-relation `kofis favourite colour`, opinion `What is
  your favourite city?`, already-parsing ask/teach/reteach, yes/no
  shape, me-route `My boss is Lee.`, 162b-territory `The Zibs'
  captain is Rex.`): PASS iff same turn byte-identical 193 vs 138h in
  reply AND fact delta.
- A1 PASS = 40/40 step checks (every turn reported, never averaged).
  Driver: `scripts/fable_fix193_probe.py`.

## A2 — frozen suites vs sealed loop138h rows + live base

- redteam136 (145 cases), redteam143 (124), sessions152 (180 turns):
  verdict+reply (+stored/writes) per case identical to the sealed
  `*-loop138h.json` rows; 0 new WRONG/WRONG-WRITE/junk writes vs base.
- bench121 4 splits (`new_121_4hop`, `old_s2fresh_4hop`, `edit200`,
  `bench132_4hop`, stock `scripts/fable_bench121_run.py`): per-item
  verdict identical to sealed 138h rows, 0 new wrong.
  Driver: `scripts/fable_fix193_suites.py` (same sealed judges, loop193
  swapped in; suites run one at a time).
- marks123 (`scripts/fable_marks123_all.py --agent
  scripts/fable_loop193_agent.py --config
  artifacts/fable-apos193-20260922/loop193-config.json --out
  artifacts/fable-apos193-20260922/marks193 --workers 4`): every suite
  per-case identical to `artifacts/fable-agent138h-20260922/marks138h/`
  EXCEPT the predicted set below; 0 case-moves, 0 new
  WRONG/WRONG-WRITE/junk writes. Compare:
  `scripts/fable_fix193_comparem.py` (read-only scrub-compare).
- A2 PASS = all identical-except-predicted (0 unpredicted moves).

## Predicted volatile / rename-only (part of the seal)

- V1: rt110 harness `statuses` log-metadata may vary run-to-run under
  parallel-agent load (daemon.log.jsonl harvest race; pilot: M1
  `[]` vs `["OK"]` and M3 msg_00 `[]` vs `["write"]` with identical
  verdict+reply+fact_writes on both cases; M1 re-ran 3/3 `["OK"]` on
  loop193). Verdict+reply+fact_writes per case must still match exactly
  (enforced semantically by the compare driver).
- V2: sleep SKIP reason names the new agent file
  (`fable_loop193_agent.py`); `fable_marks123_summary.json`
  `total_seconds` is timing-volatile. Nothing else in the summary may
  differ (`suites` block identical).
- V3: suite-level FAIL bars inherited from 138h stay as on 138h
  (marks123 p3 l5z1:F, p4 1 nonpass, rt81 bug-1/unclear-14, sleep SKIP;
  rt136 136/6/3; rt143 107/7/10 by counter).

## G4 + etiquette

- Each registered run < 1500 s wall-clock Mac CPU,
  `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, offline; daemon wrappers take
  `idle_seconds`. Heavy suites run one at a time. Never write to the
  repo-root notebook. Fictional names only. 0 new WRONG / WRONG-WRITE /
  junk writes anywhere vs loop138h.
- Sealed files hashed to SEAL.sha256.txt: this file, `case193.json`,
  `scripts/fable_loop193_agent.py`, `scripts/fable_fix193_apos.py`,
  `scripts/fable_fix193_probe.py`, `scripts/fable_fix193_suites.py`,
  `scripts/fable_fix193_comparem.py`,
  `artifacts/fable-apos193-20260922/loop193-config.json`.
- Any edit to the agent code, config, or case files after the seal
  makes the registered verdict FAIL, whatever the re-run shows. A
  driver/scorer-only fix after the seal is reported with the diff and
  the affected marks re-run in the open. A FAIL is recorded as FAIL
  with one diagnosis note; no silent re-runs.
- Open pilots (same drivers, same paths) before the seal: A1 40/40;
  rt136/rt143/sessions/bench 0 moves; marks123 per-case identical
  except V1 (M1+M3 statuses-only) + V2 (sleep rename, summary timing);
  M1 statuses re-ran 3/3 `["OK"]` on loop193.

## Predictions pointer

Ledger block `## 2026-09-22 — Experiment 193 ...` with P193.1-P193.7 is
appended to `artifacts/fable-predictions-ledger.md` BEFORE the runs.
