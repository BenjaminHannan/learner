# Exp F1 PASSMARKS: 241b's sealed reply rewriter as the outermost layer on 292t

Written by the F1 builder on 2026-09-23 before the seal. Task: F1 section of
design/v3/30-modes/talk-fluency-plan.md ("F1: 241b's rewriter on 292t",
registered 18:38 UTC). Rules: COMMON RULES in the task message (OPUS-RULES.txt
was absent at its stated path -- see D8). CPU only. At most 4 parallel
processes; `uptime` / `df -g /` checked before heavy steps.

## 0. What is being tested

- **Base arm 292t:** scripts/claude_loop292t_agent.py with
  artifacts/claude-join292t-20260923/loop292t-config.json (registered PASS).
- **F1 arm:** scripts/claude_loopf1_agent.py (LoopF1Daemon) with
  artifacts/claude-f1-20260923/loopf1-config.json (new, sealed here).
  The ONE change: 241b's sealed reply rewriter run outermost over 292t's
  turn282b chain. Per reply line, scripts/claude_loop241b_agent.render_line
  is imported unchanged (parse back to frame, stage-A candidates, first one
  passing brake v2; else the 292t line kept byte-identical, sev-1 logged).
  Stats keys (mouth241b_stats) and log schema (mouth241b_log, MOUTH241B_LOG
  env) are identical to 241b's. The mouth cannot write (read-only entity
  names for brake rule 3 only).
- **No existing file is edited.** Piece files
  (scripts/claude_mouth241b_*.py, scripts/claude_loop241b_agent.py,
  scripts/claude_loop292t_agent.py and everything else) are imported
  read-only and unchanged.
- **Code, all new (sealed, 9 scripts + this note + config + devcases +
  pilot record + predicted moves):**
  - scripts/claude_loopf1_agent.py (F1 agent + LoopF1Daemon)
  - scripts/claude_f1_pilot.py (dev pilot driver, builder's own turns only)
  - scripts/claude_f1_runall.sh (registered M2+probes; bench via NEW-1, D2)
  - scripts/claude_f1_suites.py (NEW-1 bench swap, mirrors 241b --scorer241b)
  - scripts/claude_f1_regscore.py (F1-vs-292t scorer: reply-only bars)
  - scripts/claude_f1_convrun.py (convbench-f0 both arms; mirrors convf0)
  - scripts/claude_f1_convscore.py (mechanical compare + changed-lines)
  - scripts/claude_f1_joinscore.py (joinpanel regression scorer, no text)
  - scripts/claude_f1_wall.py (M5 alternating wall, load-gated)
  - artifacts/claude-f1-20260923/loopf1-config.json (from --write-config)
  - artifacts/claude-f1-20260923/devcasesf1.json (73 own dev turns)
  - artifacts/claude-f1-20260923/pilot/pilot.json (dev pilot record)
  - artifacts/claude-f1-20260923/predicted_movesf1.json (machine predictions)

## 1. Marks (fixed now, from the F1 section)

- **M1:** grammar of every changed convbench line >= 99%, two blind graders,
  each valid only with >= 36/40 planted errors caught. Director-graded.
- **M2:** 0 unfaithful lines (route-A lines pass brake v2 rules 1-8;
  legacy fallback is byte-identical). 0 notebook-event or store changes vs
  292t on the suites, the verifier probes, joinpanel292t (regression only)
  and convbench-f0.
- **M3:** frozen suites (fable_suitediff218 --only rt136,rt143,sessions152,
  bench) vs 292t's rows: reply-only moves, every one a 241b rewrite
  (route A in the mouth log), GATE clean on the F1-vs-292t comparison.
  Bench v3 splits of the F1 run use 241b's sealed NEW-1 confirm (D2).
- **M4:** blind pairwise judge on the changed convbench lines, 292t vs F1,
  sides randomised. Pass: >= 70% of non-ties won, <= 10% lost.
  Director-queued; not run here.
- **M5:** suite wall within +5% of 292t: medians of 3 alternated runs each
  (M2 suite block: sessions152+bench, rt136, rt143nogate), load1 < 40
  before every run, waiting up to 6 hours. Never quiet => VOID, re-run.
- **Wrong if:** any unfaithful line, any store change, or <= 60% judge wins.

## 2. Pilot basis (dev material + frozen harness, pre-seal)

Dev pilot (73 own turns, fictional names): 28 changed turns / 29 changed
lines, every changed line route A; legacy 1 (the long "I can: ..." fixed
text, kept byte-identical); passthrough 38; 0 store-diff turns; 0 crashes.
Suites pilot vs 292t's rows (frozen harness): sessions152 57 moves, all
reply-only; bench 649 moves = 639 reply-only + 10 new WRONG; rt136 52
reply-only, 0 other-field diffs, run gate clean; rt143 triples+expected
identical, reply/teach-reply text diffs only; verifier vp 63 reply-only,
vs 11 reply-only, 0 stored/ev diffs anywhere.
Root cause of the 10 (D2): every one is a missing driver "yes" -- 241b's
sealed CONFLICT rendering adds an article ("the United Kingdom", "a
basketball coach", "an association football referee") so the frozen
byte-verbatim confirm needle (`new_val in sent`) misses; confirms 2->1 or
1->0; stale fact; wrong final answer. NEW-1 (confirm_match) matches all 10
and agrees with the frozen needle on 721/721 of 292t's saved conflict
replies (S1 anchor). NEW-1 bench pilot: 648 moves, all reply-only, GATE
clean, 10/10 flips resolved with base-identical confirm counts.

## 3. Predictions (also appended to the ledger as PF1.n)

- **PF1.1:** M2: 0 unfaithful lines and 0 store/event changes on suites,
  probes, joinpanel regression, and convbench-f0.
- **PF1.2:** M3 registered: sessions152 exactly 57 reply-only moves;
  bench (NEW-1) exactly 648 reply-only moves; rt136 exactly 52 reply-only,
  0 other-field diffs; rt143 0 triples/expected diffs; vp exactly 63 and
  vs exactly 11 reply-only diffs; every gate clean; every reply diff
  route A in the mouth log; sev-1 only the "I can: ..." line class.
- **PF1.3:** convbench-f0: 50-130 changed turns of 286, every changed line
  route A, 0 store/event diffs; changed-lines.jsonl complete.
- **PF1.4:** joinpanel292t regression (once per arm, sealed runner):
  90/90 turns 0 store/ev diffs, every reply diff route-A attributed,
  0 probe store diffs.
- **PF1.5:** M5 wall PASS with margin (ratio ~1.00-1.03; in-suite mouth
  mean ~0.24 ms/line).
- **PF1.6:** M1 grader bar passes (p ~ 0.6, same basis as 241b P241b.5);
  riskiest: CONFLICT article rendering, "Saved: Your ..." capital, "a red"
  class adjectives. M4 passes (p ~ 0.65, same basis as 241b P241b.6).
- **PF1.7:** S1 anchor: NEW-1 == frozen on 721/721 saved 292t conflicts.

## 4. Declared interpretations and deviations (fixed before the seal)

- **D1, instance install:** 292t installs its stack as instance attributes
  (loop.turn = turn282b closure), which shadow any class-level turn --
  verified: 241b's mixin class alone on a 292t loop never runs (0 mouth
  stats over 4 probe turns). F1 therefore installs the mouth the way
  292t's own layers install (outermost, instance): loop.turnf1_inner
  captures the turn282b chain; the outermost turn runs 241b's exact
  per-line render_line. The mixin class still fronts the loop class.
  Per-line code path is 241b's, unchanged.
- **D2, NEW-1 bench:** the F1 bench splits run with 241b's sealed NEW-1
  confirm (claude_fix172b241b_benchv3 via claude_f1_suites.py, mirroring
  241b's sealed --scorer241b); 292t base rows stay frozen; S1 anchor
  721/721 in S2. Without this, the frozen verbatim needle fails 10
  confirmations on sealed 241b wording (pilot proof above). Both numbers
  (frozen pilot 10 flips; NEW-1 0 flips) are reported.
- **D3, gate semantics:** bars compare F1 vs 292t rows, so the run's own
  gate must read "GATE: clean". 292t's sealed gate vs ITS base (138j) is a
  different comparison and is not re-compared.
- **D4, rt143 teach_replies:** teach-turn reply text diffs with identical
  triples+expected are reply-only moves (SAVED etc. are rewritten).
- **D5, mouth logging:** registered runs set MOUTH241B_LOG to a run-dir
  file (behavior-neutral logging for M2b route evidence).
- **D6, M5 suite block:** sessions152+bench, rt136, rt143nogate per arm
  (verifier probes excluded -- not suites).
- **D7, convbench runner:** claude_convf0_run.py hardcodes the 292 arm, so
  F1 uses scripts/claude_f1_convrun.py, a faithful copy with an arm table
  (same per-dialog loop, fresh agent per dialog, same output schema).
  No grading, no judge here; the director queues blind graders.
- **D8, setup deviations:** (a) OPUS-RULES.txt was absent at its stated
  /private/tmp path (no such file/dir); the COMMON RULES in the task
  message were followed. (b) `git log --oneline -5` ran once during setup
  before the "never git log" line was fully noted; no older file version
  was used (plan via git show origin/main; 292t files exist only in the
  worktree and were read read-only). (c) Panel/bench dir filenames were
  listed during setup (ls); no panel or benchmark item was ever read,
  quoted, or tuned on. (d) loopf1-config.json differs from
  loop292t-config.json only in descriptive strings (daemon module, self
  rulef1, expf1 block) -- verified behaviorally identical.
- **Verdict:** PASS iff M1, M2, M3, M4, M5 all pass (M5 VOID => re-run).
  M1/M4 unscorable => VOID.
