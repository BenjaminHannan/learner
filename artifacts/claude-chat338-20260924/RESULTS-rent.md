# rent-338-chat RESULTS-rent (REGISTERED run exp 338, 2026-09-24)

Registered run of exp 338 (open conversation), rental GPU. Panel artifacts/claude-chatpanel338-20260924 is TEST-ONLY: run once, never read item by item, never quoted. No judge_*.jsonl or grammar_P.jsonl opened. No panel reply quoted.

## Step 1 seals (rental /root/tree)
- Panel SEAL (`artifacts/claude-chatpanel338-20260924/SEAL.sha256.txt`, `sha256sum -c` from inside panel folder): all OK (items.jsonl OK, README.md OK, no failures).
- `artifacts/claude-chat338-20260924/SEAL-code-rent.sha256.txt` written BEFORE running (10 scripts, sha256sum):
  - claude_chat338_agent.py, claude_chat338_run.py, claude_cre333_agent.py, claude_e2e330_arms.py, claude_lis_stackb.py, claude_lis_e2e_armsb.py, claude_e2e336_run.py, claude_e2e336_twin.py, claude_e2e336_score.py, claude_age334_agent.py (hashes in file).

## Step 2 panel runs (60 conversations, 400 turns/arm)
Commands (each its own process, full flags):
- `python -B scripts/claude_chat338_run.py --panel artifacts/claude-chatpanel338-20260924 --arm B --model /root/lis301-merged --gen-model /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc --out artifacts/claude-chat338-20260924/run`
- `python -B scripts/claude_chat338_run.py --panel artifacts/claude-chatpanel338-20260924 --arm P --model /root/lis301-merged --gen-model <same BASE> --out artifacts/claude-chat338-20260924/run`
- `python -B scripts/claude_chat338_run.py --panel artifacts/claude-chatpanel338-20260924 --arm T --gen-model <same BASE> --out artifacts/claude-chat338-20260924/run`
- `python -B scripts/claude_chat338_run.py --panel artifacts/claude-chatpanel338-20260924 --score artifacts/claude-chat338-20260924/run`

Summary (from `--score`, `run/summary.json`, counts only):
- B: turns 400, gave_up_or_canned 303, events_on_non_teach 3, ask_known_right 3/15, ask_unknown_dont_know 0/10, distinct_replies 46, most_common_reply_count 102, ms_median 441.2, ms_p90 614.6
- P: turns 400, gave_up_or_canned 3, events_on_non_teach 3, ask_known_right 3/15, ask_unknown_dont_know 8/10, distinct_replies 337, most_common_reply_count 26, ms_median 850.5, ms_p90 1217.8, chat338 {gave_up 302, replaced 300, kept_all_failed 2, G1 3, G3 9, G4 24, turns 400}
- T: turns 400, gave_up_or_canned 0, events_on_non_teach 0, ask_known_right 2/15, ask_unknown_dont_know 8/10, distinct_replies 398, most_common_reply_count 3, ms_median 967.6, ms_p90 1024.5
- conversations 60

Registered marks judged here (rest judged later by thread):
- P338.2 turns where P gives up or uses canned instruction line, bar ≤10% of turns: P 3/400 = 0.75% → PASS
- P338.6 notebook events on turns that are not `teach`, bar 0: P 3 → FAIL
- P338.1, P338.3, P338.4, P338.5: judged later by thread (blind graders/judges). Report only: P vs B pairwise packets built (judge_pair_B, 60 convs), P vs T packets built (judge_pair_T, 60 convs), ask_known right P 3 / B 3 / T 2 (of 15), ask_unknown dont-know P 8 / B 0 / T 8 (of 10), T invented-fact count: not scored here (thread judges), distinct replies P 337 / B 46 / T 398, most common reply count P 26 / B 102 / T 3, guard counts (P chat338): G1 3, G3 9, G4 24, ms median/p90 B 441.2/614.6, P 850.5/1217.8, T 967.6/1024.5.

## Step 3 DEV safety (readable bank artifacts/claude-e2e331-dev-20260924, report only)
- `python -B scripts/claude_e2e336_run.py --bank artifacts/claude-e2e331-dev-20260924 --out artifacts/claude-chat338-20260924/dev --arm claude_chat338_run:build_P --name P338 --model READER --gen-model BASE` → arm_P338.jsonl rows=248, lives=10
- `python -B scripts/claude_e2e336_score.py --bank artifacts/claude-e2e331-dev-20260924 --runs artifacts/claude-chat338-20260924/dev/arm_P338.jsonl --out artifacts/claude-chat338-20260924/dev/score`
- Score line: {"arm": "P338", "asks": {"ALL": {"ABSTAIN": 39, "CONFIRM_OTHER": 9, "RIGHT": 11, "RIGHT_CONFIRM": 5, "WRONG_CANDIDATE": 7}, "edit": {"ABSTAIN": 3, "CONFIRM_OTHER": 4, "RIGHT_CONFIRM": 3}, "never_told": {"RIGHT": 9, "WRONG_CANDIDATE": 1}, "one_hop": {"ABSTAIN": 10, "RIGHT": 1, "RIGHT_CONFIRM": 2, "WRONG_CANDIDATE": 3}, "partial": {"ABSTAIN": 4, "CONFIRM_OTHER": 1}, "reversal": {"ABSTAIN": 8, "CONFIRM_OTHER": 1, "WRONG_CANDIDATE": 1}, "two_hop": {"ABSTAIN": 7, "CONFIRM_OTHER": 2, "RIGHT": 1, "WRONG_CANDIDATE": 1}, "yesno": {"ABSTAIN": 7, "CONFIRM_OTHER": 1, "WRONG_CANDIDATE": 1}}, "clarify_replies": 13, "confirm_rows": 54, "creative_turns": 10, "creative_turns_with_writes": 0, "day1_saved_facts": 30, "day1_saved_facts_kept_at_end": 30, "distinct_replies": 145, "facts_saved": 49, "facts_total": 131, "most_common_reply_count": 27, "ms_median": 726.5, "ms_p90": 877.8, "new_triples": 53, "new_triples_owner_value_unsupported": 3, "nosave_turns_with_writes": 0, "user_rows": 194}

## Compute
- GPU: NVIDIA GeForce RTX 5090, 1x, vast.ai contract 52415371 (offer 44072609, 16 vCPU, 31 GB RAM, 80 GB disk, KR), image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, torch 2.8.0+cu128 CUDA True
- Failed first rental: contract 52415268 (offer 45669552), create success False, stuck loading/stopped, destroyed immediately, $0.00
- Hours (usable instance): rented ~2026-09-24T12:37Z, running 12:40:44Z–13:16:51Z ≈ 0.60 h; dph $0.55407407; dollars ≈ $0.33 (budget $3.00, spend well inside)
- Credit at start $9.97
- Model commit hash (BASE openbmb/MiniCPM5-1B): 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected); READER lis301-merged model.safetensors sha256 b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890; self122_head.pt 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25
- Wall time per arm (rental): B 210 s, P 361 s, T 369 s, score 0 s, DEV run P338 155 s
- All steps ran once, code unedited, TEST-ONLY panel never opened item by item, judge/grammar files never opened, no panel reply quoted. run/ and dev/ copied back before destroy, instance destroyed, 0 rent-338-chat instances live after.
