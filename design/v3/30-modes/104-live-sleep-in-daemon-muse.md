# 104 — Live sleep inside the daemon (Muse, 2026-09-22)

## Problem

Exp 90/96 left the loop96 daemon with sleep armed but forever idle: loop90
constructs `HardGate46Sleeper(state_dir, reasoner=None, ...)`, and the live
reasoner (`QualifierAwareReasoner77`) has no episode feed — its `words`
table starts empty and nothing ever fills it. Exp 57 proved the install
recipe works on 20 episodes, but outside any daemon, driven by direct
`loop.submit` calls. Exp 104 fires a real install inside the running
loop96 daemon, end to end, through its mailbox only.

## Design (additive only; no existing file touched)

`scripts/fable_sleep104_agent.py` holds three new pieces; everything else
is imported read-only and wrapped:

- **Sleep104Reasoner** wraps the loop's own reasoner77 instance. On a bare
  learned-word question (`relations == ["maternal_grandmother"]`) it
  resolves the start entity and walks mother+mother through the live
  notebook; when the chain resolves it appends one episode
  `(start, word 0, answer)` — the exact wire57 `_queue_word_episode` rule,
  with the word index fixed by `R44.WORD_NAMES`. Pre-install the inner
  reasoner answers MISSING_FACT (the word is unknown: no facts, not in
  `functional`), and the episode is still queued. Post-install the inner
  hop loop answers OK through the installed logits; the wrapper then
  rewrites the record's source to `sleep-derived` and heads the trail with
  the install report row. The hop rows stay the taught FACTs they are —
  the mark names the routing, which is what sleep installed.
- **Sleep104Sleeper** subclasses wire57's `SparseVillageSleeper` (the
  exp-46 recipe and unchanged 4-fold gate, same sparse-village probe
  builders). After an install it (1) loads the hardened `[3][9]` logits
  from the recipe's own checkpoint file (the outcome dict does not carry
  them), audits the skill stages (non-keep stages must read mother,
  mother — keep padding may sit in any row), (2) bridges them into the
  live reasoner's `words` table, (3) appends one `sleep-derived` report
  row (actor `sleep`, relation `sleep_report`, exp-52 convention), and
  (4) persists the word atomically (tmp + fsync + os.replace). Serving
  state is that JSON file only: valid on boot means installed, anything
  else means cleanly absent. A `sleep104-SLEEPING` marker brackets the
  recipe for the kill-9 arm. The HardGate audit already tolerates a
  sleep-derived row (no supersede, not a quarantined source).
- **Sleep104Daemon** = `Loop96Daemon` + a retrofit (swap reasoner/sleeper
  in the built loop, clean stale tmps, boot-load the word) + per-turn
  sleep logging (turn seconds, recipe seconds, outcome, bridge). A SLEEP
  tick fires inside ordinary `turn()` processing because `run_until_idle`
  keeps stepping while the log is full — no manual call exists anywhere.

`scripts/fable_sleep104_drive.py` is the mailbox-only wave driver: family
world (20 K/M/G + 5 T/N/H chains), 80 turns at threshold 75, Z4 kill
(during t075's SLEEP, marker-gated) + restart + 200 taught asks + a
restore check (completed install rebooted), Z5 noisy arms (post-ask wrong
corrections: 4 → correct-or-refused, 8 → refused; pre-ask wrong teaches
are gate-invisible because episodes derive from the notebook — found in
trial, documented in the driver).

## Evidence (sealed wave, all PASS)

Z1: seeds 1/2/3 each entered SLEEP unprompted during t075 and installed
with 20/20 episodes (OOF 1.00, agreement 1.00; 71–77 s each). Z2: 5/5
NEW-people probes correct via mailbox, 5/5 records plus the notebook row
sleep-derived. Z3: 0 wrong installs, 0 taught overwrites, taught 50/50
with 0 dupes, per seed. Z4: kill landed mid-SLEEP; restart clean
(absent install, 5/5 abstain, 0 wrong, 200/200 taught, 0 dupes);
completed-install copy rebooted to 5/5. Z5: noise4 installed correctly
(5/5); noise8 refused (5/5 abstain); 0 wrong installs. Wave 414 s.

## Limits

One word (`maternal_grandmother` = mother+mother), one family pattern,
hand-set size threshold (sleep fires on fullness, never need); the 60 s+
fit dominates turn latency during install; ears/mouth remain template
stand-ins; the episode feed covers only the one word slot (other chains
are refused, never forced). Kill timing between report-row write and
word-file commit is milliseconds wide and was not hit; either order
degrades to honest abstain-or-serve, never a half skill.

## What it means / does not mean

Means: the running daemon teaches itself a genuinely new relation
overnight and proves it on strangers, crash-safely. Does not mean it
knows when to sleep, what to dream about, or any second word: the schedule
is a counter and the slots are still hand-made.
