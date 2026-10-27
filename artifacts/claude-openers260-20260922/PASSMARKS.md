# Exp 260 — PASSMARKS (registered before the seal; the panel folder has not been opened)

Arm under test: **260** = `scripts/claude_loop260_agent.py` + `artifacts/claude-openers260-20260922/loop260-config.json`
(138m + `scripts/claude_fix260_openers.py`, outermost; SrcGuardMixin228 first in the daemon MRO).
Base arm: **138m** = `scripts/claude_loop138m_agent.py` + `artifacts/claude-merge138m-20260922/loop138m-config.json`.
Design note: `design/v3/30-modes/260-openers-opus.md`. Predicted moves (machine-readable): `predicted_moves260.json`.

The verdict is PASS only if M1–M6 all pass. Any change to a sealed file after the seal = FAIL. No re-seal.
No silent re-runs: each registered command runs once; a driver-only fix after the seal is reported with its diff.

## Commands (from the repo root)

- M2–M6: `bash scripts/claude_260_runall.sh artifacts/claude-openers260-20260922/run` (checks `uptime` before
  every step; scorer `scripts/claude_openers260_regscore.py` writes `run/regscore260.json`).
- M1: after the panel writer's `artifacts/claude-openpanel260-20260922/SEAL.sha256.txt` checks OK:
  `bash scripts/claude_260_panel.sh artifacts/claude-openers260-20260922/run` — seal check, then schema check
  (`claude_openers260_score.py schema`; SCHEMA-MISMATCH → exit 3 → the run is VOID, reported, never scored by
  hand), then the panel once on 138m and once on 260 (`claude_openers260_run.py panel`), then the scorer.
- If the panel is not sealed 40 minutes after this seal: report and stop.

## M1 — blind openpanel260 (80 items), 138m's number reported next to every figure

Scored exactly per `openpanel260-spec.txt` (normalise = lowercase + strip edge punctuation/spaces; junk = any
triple stored after the turn or followup that is in neither stored_after_setup nor expect_store; store_ok =
expect_store ⊆ stored_after_turn and nothing else added; question_write = a question turn or the followup changes
the store; reply_ok = gold "" or gold ⊆ scored reply (followup reply for teaches, turn reply for question turns)).

| bar | pass if |
|---|---|
| opener_teach | ≥ 16/20 right |
| opener_question | ≥ 10/12 right |
| greeting_question | ≥ 7/8 right |
| bare_greeting | ≥ 5/6 right |
| junk_guard | 8/8 right and 0 junk items |
| name_trap | no item right on 138m and wrong on 260 |
| junk writes | 0 items with junk over all 80 |
| question writes | 0 |
| control | 16/16 right and every reply byte-identical to base138m.jsonl |

Also reported (not a bar): fidelity of my 138m arm vs the writer's base138m.jsonl (setup/turn/followup replies and
stores), and every miss on both arms.

## M2 — frozen suites vs 138m's registered rows (0 flips toward an abstain)

Suites: rt136, rt143, sessions152, bench (4 files). Rows are compared directly with 138m's saved rows, every field
except wall-clock timing (`seconds`/`sec`). Method notes (deviations from the brief's command line, same method 138m
used): rt136 labels come from `fable_suitediff218 --base-dir artifacts/fable-agent138j-20260922` (the sealed base
format suitediff needs) and must equal 138m's own labels plus the predicted one below; rt143 is run with
`scripts/claude_138l_rt143nogate.py` because 138m registered no suitediff rt143 rows (its saved row file is
`run/rt143nogate-m.json`); sessions152 + bench use `--base-dir artifacts/claude-merge138m-20260922/run/sd` and must
show 0 moves.

**Predicted moves (exactly this list):**
- **rt136 C122** "Hi. Tom's boss is Ann." — reply `Saved: Tom's boss is Ann.`, stored [[Tom, boss, Ann]]
  (138m: `Saved: Hi. Tom's boss is Ann.`, stored [[Hi. Tom, boss, Ann]]). rt136 expects no write for this
  multi-sentence turn, so the verdict is WRONG-WRITE on both arms; suitediff218 labels the changed write
  **"new junk write"**. Registered reading: this one predicted label is the stated fact saved without the greeting
  (the same exemption M4 grants), not a new junk subject; any other new WRONG / WRONG-WRITE / junk / lost-OK label,
  any other moved unit, or any rt143 verdict flip fails M2. (A reader who does not accept the exemption should read
  M2 as FAIL on C122 alone; the final report states this.)
- rt143 (124 rows): 0 moved. sessions152 (180 units): 0 moved. bench132_4hop, edit200, new_121_4hop,
  old_s2fresh_4hop (200 each): 0 moved.

## M3 — sleep smoke

`fable_sleepsmoke206.py --idle-seconds 5.0` on 260 must equal 138m's saved `run/smoke-m.json` in every field
except `.agent`, `.config`, `.label`, `.seconds`, `.root`, `.report`. Pilot: only `.agent .config .label .seconds` differ.

## M4 — 138m verifier probes (`artifacts/claude-verify-20260922/138m/probes.json`, `probes-supp.json`)

Compared with 138m's saved `rows-138m.json` / `supp-rows-138m.json` (a pilot re-run of 138m matched them 0 diffs).
Every changed row must be one of these, with exactly this reply/ev/triples; 0 new writes except B15:t0 (a save of
the stated fact without the opener); stored-set changes exactly B15 and D10:
- **B15:t0** "Please call me Fenna." → `Saved: your name is Fenna.` (ev 3; 138m: save-failure reply, ev 0).
- **B15:t1** "What's my name?" → `Your name is Fenna.` (138m: `I don't know your name yet.`).
- **D08:t1** "Please, who is Tomas's boss?" → `Tomas's boss is Mirela.` (138m: didn't-understand-question).
- **D10:t0** "Please, Kestrel's job is fisher." → `Saved: Kestrel's job is fisher.`, stores Kestrel (138m stored "Please, Kestrel").
- **D10:t1** "could you tell me Kestrel's job please?" → reply unchanged; only the triples column differs (Kestrel).
- **E06:t0** "hello there" → `Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?"`.
- **E10:t0** "Hi! What's your name?" → `My name is Premonition.` (138m: `You never told me your name, so I do not know it.`).
- probes-supp: 0 changes.

## M5 — restart dialogs (138m's M6 files: 138j p3-dialogs, p3c-restart2, p3d-ghost; 138k v-dialogs, v-supp)

Compared with 138m's saved `run/probe/m-*.json`: **predicted reply changes: none.** Pass = 0 reply changes,
equal event counts and stored sets, 0 ghost answers (138m scorer's rule), 0 failed duplicate checks, audits present.

## M6 — latency

`claude_merge138k_latency.py`, 2 reps, alternating processes 138m,260 ×3 in the same session, on the p3 dialog files.
Pass = median(260) − median(138m) ≤ **+3 ms** per turn. Pilot: +0.43 ms and +0.15 ms.

## Abstain flips

Any unpredicted flip toward an abstain counts against its mark; that item is then run alone 5 times and reported,
with whether the 228 guard was installed (the agent refuses to build without it).

## Dev set (not a mark; tuned on)

`devcases260.json` (109 dialogs, from `scripts/claude_openers260_devcases.py`), scored by
`claude_openers260_score.py dev`. Pilot: **260 109/109, 138m 45/109** (`pilot/dev-score.json`).
Families: opener_comma 17, opener_plain 8, opener_nocomma 12, greeting_question 8, identity_greeting 5,
bare_greeting 8, junk_shape 8, junk_guardonly 3, name_trap 10, title_cant_tell 4, question_trap 7, restart 5,
fallback 5, control 6, username 3.

## Known limits (predicted, not hidden)

- "Hey Pell's boss is Rhoda." (greeting + one capitalised word, no punctuation) keeps 138m's junk "Hey Pell";
  it cannot be told apart from the title "Hey Jude's writer is Fenn.".
- "So Bram Kite's boss is Rhoda." (no-comma opener before a 2+-word name) keeps 138m's junk "So Bram Kite".
- "X is a Y." after an opener only saves if the plain shape saves on 138m (it does not for "Tamsin is a baker.").
