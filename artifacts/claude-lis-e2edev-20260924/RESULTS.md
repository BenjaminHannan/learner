# lis-e2edev — listener stack on the month-end DEV bank (REPORT ONLY, no marks)

Bank: `artifacts/claude-e2e331-dev-20260924` (dev data, fine to read: 10 lives, 194 user turns, 131 truth facts).
Code: sealed scripts by the listener and month-end threads, run unedited from a combined tree
(fresh `git archive origin/builder-outbox` + fresh `git archive origin/main` overlay +
`artifacts/fable-self122-20260922/self122_head.pt` copied from the Mac repo).
Arms from `scripts/claude_lis_e2e_arms.py`, all with `--model ~/premonition-models/lis301-merged`
(those weights, threshold 0.995):
- lisC = 292t + lis-310 (ask-back base)
- lisS = 292t + 310 + 313 + 315 + 314
- lisG = 292t + 310 + 313 + 315 + 314 + 316 (full stack)

## Checks (all before running)

- `shasum -a 256 -c SEAL.sha256.txt` on the DEV bank: all 3 OK
  (turns.jsonl, truth.jsonl, README.md; seal lists bare filenames so it was run from inside the bank dir).
- `~/premonition-models/lis301-merged/model.safetensors` sha256:
  `b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890` — matches the required value.
- `uptime` at start: load averages ~15–25 (1-min), Mac shared but below the 60 stop line; no other reader job running
  (lis-314-panel had exited rc=0 before this task started).
- Disk: 64 GB free at start, 59 GB free at end — never near the 3 GB stop line.
- Env note (not a code edit): the first launch failed with `ModuleNotFoundError: No module named 'transformers'`
  from `scripts/claude_lis300_read.py`. The sealed COMMON RULES uv prefix lists only torch+numpy, but the reader
  needs transformers+safetensors; I added `--with transformers --with safetensors`, the same prefix lis-311b used
  for its real-reader run. Sealed code was never edited.

## Runs

Each arm: `python -B scripts/claude_e2e336_run.py --arm claude_lis_e2e_arms:build_<C|S|G> --name lis<C|S|G>
--model ~/premonition-models/lis301-merged --bank artifacts/claude-e2e331-dev-20260924
--out artifacts/claude-lis-e2edev-20260924/run`, one arm at a time.
Scorer: `python -B scripts/claude_e2e336_score.py --bank <bank> --runs run/arm_lisC.jsonl run/arm_lisS.jsonl
run/arm_lisG.jsonl --out artifacts/claude-lis-e2edev-20260924/scored` (exit 0).
Row counts: arm_lisC.jsonl 269 rows (194 user + 75 confirm_answer), arm_lisS.jsonl 227 rows (194 + 33),
arm_lisG.jsonl 227 rows (194 + 33). All 10 lives completed for every arm; no crash, no OOM.
Wall time: lisC ~25 min, lisS ~19 min, lisG ~19 min — inside the 150-minute cap.
No single turn exceeded 5 minutes (slowest turn anywhere: 76212.7 ms = 76 s).

Device: Mac arm64 (darwin), torch cuda=False, mps=True. The reader auto-selects MPS (float16);
the 292t loop runs on CPU. So per-turn ms below mix MPS reader inference + CPU loop on a shared Mac;
treat timings as noisy.

## Mechanical counts (verbatim from `scored/mechanical.json`)

### lisC

- user_rows 194, confirm_rows 75
- asks ALL: ABSTAIN 51, CONFIRM_OTHER 8, RIGHT 10, WRONG_CANDIDATE 2 (71 ask turns total)
- asks by type:
  - edit: ABSTAIN 7, CONFIRM_OTHER 2, WRONG_CANDIDATE 1
  - never_told: RIGHT 10
  - one_hop: ABSTAIN 14, CONFIRM_OTHER 1, WRONG_CANDIDATE 1
  - partial: ABSTAIN 4, CONFIRM_OTHER 1
  - reversal: ABSTAIN 8, CONFIRM_OTHER 2
  - two_hop: ABSTAIN 9, CONFIRM_OTHER 2
  - yesno: ABSTAIN 9
- new_triples 50, new_triples_owner_value_unsupported 1, nosave_turns_with_writes 0
- facts_total 131, facts_saved 49, day1_saved_facts 27, day1_saved_facts_kept_at_end 27
- distinct_replies 93, most_common_reply_count 55, clarify_replies 103
- creative_turns 10, creative_turns_with_writes 0
- ms_median 2337.1, ms_p90 18121.8, ms_max 76212.7

### lisS

- user_rows 194, confirm_rows 33
- asks ALL: ABSTAIN 42, CONFIRM_OTHER 7, RIGHT 12, RIGHT_CONFIRM 3, WRONG_CANDIDATE 7 (71 ask turns total)
- asks by type:
  - edit: ABSTAIN 3, CONFIRM_OTHER 4, RIGHT 1, RIGHT_CONFIRM 1, WRONG_CANDIDATE 1
  - never_told: RIGHT 10
  - one_hop: ABSTAIN 12, RIGHT 1, RIGHT_CONFIRM 2, WRONG_CANDIDATE 1
  - partial: ABSTAIN 3, CONFIRM_OTHER 1, WRONG_CANDIDATE 1
  - reversal: ABSTAIN 9, CONFIRM_OTHER 1
  - two_hop: ABSTAIN 6, CONFIRM_OTHER 1, WRONG_CANDIDATE 4
  - yesno: ABSTAIN 9
- new_triples 35, new_triples_owner_value_unsupported 0, nosave_turns_with_writes 0
- facts_total 131, facts_saved 34, day1_saved_facts 19, day1_saved_facts_kept_at_end 19
- distinct_replies 70, most_common_reply_count 47, clarify_replies 95
- creative_turns 10, creative_turns_with_writes 0
- ms_median 2455.8, ms_p90 15024.8, ms_max 64918.3

### lisG

- user_rows 194, confirm_rows 33
- asks ALL: ABSTAIN 42, CONFIRM_OTHER 7, RIGHT 12, RIGHT_CONFIRM 3, WRONG_CANDIDATE 7 (71 ask turns total)
- asks by type:
  - edit: ABSTAIN 3, CONFIRM_OTHER 4, RIGHT 1, RIGHT_CONFIRM 1, WRONG_CANDIDATE 1
  - never_told: RIGHT 10
  - one_hop: ABSTAIN 12, RIGHT 1, RIGHT_CONFIRM 2, WRONG_CANDIDATE 1
  - partial: ABSTAIN 3, CONFIRM_OTHER 1, WRONG_CANDIDATE 1
  - reversal: ABSTAIN 9, CONFIRM_OTHER 1
  - two_hop: ABSTAIN 6, CONFIRM_OTHER 1, WRONG_CANDIDATE 4
  - yesno: ABSTAIN 9
- new_triples 35, new_triples_owner_value_unsupported 0, nosave_turns_with_writes 0
- facts_total 131, facts_saved 34, day1_saved_facts 19, day1_saved_facts_kept_at_end 19
- distinct_replies 70, most_common_reply_count 47, clarify_replies 95
- creative_turns 10, creative_turns_with_writes 0
- ms_median 2295.0, ms_p90 11787.2, ms_max 48063.6

## Read of the numbers (report only, no verdict)

- lisS and lisG are mechanically identical on every count except wall-clock ms (median/p90/max differ run to run).
  The +316 layer changed nothing on this DEV bank: same replies (grammar packets identical), same saves, same asks.
- lisC asks the user far more often (75 confirm rows vs 33) and saves more facts mechanically (49/131 vs 34/131,
  day-1 27 vs 19), with 50 new triples vs 35. Whether the extra saves are *right* is for the blind judges
  (judge_saves / judge_asks / grammar packets are in `scored/`).
- No arm wrote on a nosave turn (0) or on a creative turn (0) in any arm.
- All day-1 saved facts were still present at the end (lisC 27/27, lisS 19/19, lisG 19/19).

## Files

- `run/arm_lisC.jsonl`, `run/arm_lisS.jsonl`, `run/arm_lisG.jsonl` (runner outputs)
- `scored/mechanical.json` (counts above), `scored/judge_saves_<arm>.jsonl`,
  `scored/judge_asks_<arm>.jsonl`, `scored/grammar_<arm>.jsonl` (blind-grader packets)
