# y1d GPU results (Answering-from-memory thread, 2026-09-26)

Diagnosis on DEV data: plain MiniCPM5-1B answers the 71 DEV bank memory asks from raw chat
turns, three ways (gold / all / k20), ep-382 answer step (4 samples T 0.7 + guard) plus one
greedy answer per ask and condition. Code run unmodified (`scripts/claude_y1d_readchat.py`,
seed 4021, n=4). SEAL 8/8 OK, `--selftest` printed "selftest ok".

## Last printed JSON line

{"answerable_right": {"gold|p382": 3, "gold|greedy": 0, "all|p382": 13, "all|greedy": 5, "k20|p382": 9, "k20|greedy": 5}, "never_told_idk": {"all|p382": 5, "all|greedy": 9, "k20|p382": 8, "k20|greedy": 10}}

## Run facts

- GPU: NVIDIA GeForce RTX 5090 (rental 2, contract 52757085, offer 45043246, dph $0.469)
- MiniCPM5-1B commit: 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected value)
- all-MiniLM-L6-v2 commit: 1110a243fdf4706b3f48f1d95db1a4f5529b4d41
- torch 2.8.0+cu129 with CUDA True (image torch), transformers>=5 installed on box
- Wall minutes: ~2 (run launched 14:05:42Z, `gpu/` + `gpu_log.txt` written 14:07Z; 71 `[y1d]` lines, process exited on its own)
- Dollars: rental 1 (contract 52756144, offer 46753297, dph $0.406, ~6 min in loading with host docker-registry proxy error, destroyed) ~$0.04 + rental 2 (13:55:31Z-14:08:33Z, ~0.22 h x $0.469) ~$0.10 = task total ~$0.14 of $0.40 budget, 2 rentals of max 4
- Instance id: 52757085 (failed first rental 52756144 also recorded); post-destroy 0 claude-memory-y1d live
- Credit at gate: 5.499236376269863 (vast auto-refills; balance number only, no credit stop)
- Rows: `gpu/y1d_rows.jsonl` 203 lines (= 3 x 71 asks minus 10 never_told gold-skips), sha256-verified against the box before destroy
- No reader weights copied; nothing staged on the Mac (streamed `git archive` straight to the rental); run saved no weights

## Decision-rule readouts (PLAN.md rules, fixed before the run; G_nb = 5)

- D1 reading: A_gold (p382) = 3, below 20 -> the 1B's reading is the bottleneck; next change is reading, not routing.
- D2 finding: F = A_gold - A_all = 3 - 13 = -10 (<= 5) -> finding costs nothing here; whole-chat beats gold-only.
- D3 382b's input: A_k20 = 9 vs A_all - 3 = 10 -> 9 < 10, the store's ranking costs 4 here (just misses the bar).
- D4 guard cost (non-never_told asks right greedy but not right guarded): gold 1, all 1, k20 0.
- D5 honesty: never_told answered "don't know" (RIGHT): all 5 of 10 (p382), 9 of 10 (greedy); k20 8 of 10 (p382), 10 of 10 (greedy). Answerable WRONG_CANDIDATE under p382: all 12 (of 61 non-never_told; 11 of 56 value/yes/no), k20 7, gold 2.
- Routing: A_all = 13 < 25 -> routing condition not met (needs >= 25 with never_told-under-all >= 8 of 10; have 13 and 5 of 10).
- Proved-wrong clause: "Reading the user's own words beats the notebook on DEV" is wrong if A_all <= 10; A_all = 13, so NOT proved wrong (but only 13 of 56 vs notebook 5 of 56).

## counts block of gpu/y1d_summary.json (verbatim)

{
 "all|greedy|ALL": {"ABSTAIN": 52, "WRONG_CANDIDATE": 5, "RIGHT": 14},
 "all|greedy|ANSWERABLE": {"ABSTAIN": 47, "WRONG_CANDIDATE": 4, "RIGHT": 5},
 "all|greedy|edit": {"ABSTAIN": 10},
 "all|greedy|never_told": {"RIGHT": 9, "WRONG_CANDIDATE": 1},
 "all|greedy|one_hop": {"ABSTAIN": 12, "WRONG_CANDIDATE": 2, "RIGHT": 2},
 "all|greedy|partial": {"ABSTAIN": 5},
 "all|greedy|reversal": {"ABSTAIN": 10},
 "all|greedy|two_hop": {"ABSTAIN": 11},
 "all|greedy|yesno": {"RIGHT": 3, "ABSTAIN": 4, "WRONG_CANDIDATE": 2},
 "all|p382|ALL": {"RIGHT": 18, "WRONG_CANDIDATE": 17, "ABSTAIN": 36},
 "all|p382|ANSWERABLE": {"RIGHT": 13, "WRONG_CANDIDATE": 11, "ABSTAIN": 32},
 "all|p382|edit": {"ABSTAIN": 9, "RIGHT": 1},
 "all|p382|never_told": {"WRONG_CANDIDATE": 5, "RIGHT": 5},
 "all|p382|one_hop": {"RIGHT": 7, "WRONG_CANDIDATE": 4, "ABSTAIN": 5},
 "all|p382|partial": {"WRONG_CANDIDATE": 1, "ABSTAIN": 4},
 "all|p382|reversal": {"ABSTAIN": 8, "RIGHT": 2},
 "all|p382|two_hop": {"ABSTAIN": 9, "RIGHT": 1, "WRONG_CANDIDATE": 1},
 "all|p382|yesno": {"RIGHT": 2, "ABSTAIN": 1, "WRONG_CANDIDATE": 6},
 "gold|greedy|ALL": {"ABSTAIN": 60, "RIGHT": 1},
 "gold|greedy|ANSWERABLE": {"ABSTAIN": 56},
 "gold|greedy|edit": {"ABSTAIN": 10},
 "gold|greedy|one_hop": {"ABSTAIN": 16},
 "gold|greedy|partial": {"ABSTAIN": 4, "RIGHT": 1},
 "gold|greedy|reversal": {"ABSTAIN": 10},
 "gold|greedy|two_hop": {"ABSTAIN": 11},
 "gold|greedy|yesno": {"ABSTAIN": 9},
 "gold|p382|ALL": {"ABSTAIN": 56, "RIGHT": 3, "WRONG_CANDIDATE": 2},
 "gold|p382|ANSWERABLE": {"ABSTAIN": 51, "RIGHT": 3, "WRONG_CANDIDATE": 2},
 "gold|p382|edit": {"ABSTAIN": 10},
 "gold|p382|one_hop": {"ABSTAIN": 15, "RIGHT": 1},
 "gold|p382|partial": {"ABSTAIN": 5},
 "gold|p382|reversal": {"ABSTAIN": 10},
 "gold|p382|two_hop": {"ABSTAIN": 11},
 "gold|p382|yesno": {"RIGHT": 2, "ABSTAIN": 5, "WRONG_CANDIDATE": 2},
 "k20|greedy|ALL": {"ABSTAIN": 54, "RIGHT": 15, "WRONG_CANDIDATE": 2},
 "k20|greedy|ANSWERABLE": {"ABSTAIN": 49, "RIGHT": 5, "WRONG_CANDIDATE": 2},
 "k20|greedy|edit": {"ABSTAIN": 10},
 "k20|greedy|never_told": {"RIGHT": 10},
 "k20|greedy|one_hop": {"ABSTAIN": 13, "WRONG_CANDIDATE": 1, "RIGHT": 2},
 "k20|greedy|partial": {"ABSTAIN": 5},
 "k20|greedy|reversal": {"ABSTAIN": 10},
 "k20|greedy|two_hop": {"ABSTAIN": 10, "RIGHT": 1},
 "k20|greedy|yesno": {"RIGHT": 2, "ABSTAIN": 6, "WRONG_CANDIDATE": 1},
 "k20|p382|ALL": {"ABSTAIN": 45, "WRONG_CANDIDATE": 9, "RIGHT": 17},
 "k20|p382|ANSWERABLE": {"ABSTAIN": 40, "WRONG_CANDIDATE": 7, "RIGHT": 9},
 "k20|p382|edit": {"ABSTAIN": 9, "WRONG_CANDIDATE": 1},
 "k20|p382|never_told": {"RIGHT": 8, "WRONG_CANDIDATE": 2},
 "k20|p382|one_hop": {"ABSTAIN": 12, "WRONG_CANDIDATE": 2, "RIGHT": 2},
 "k20|p382|partial": {"ABSTAIN": 5},
 "k20|p382|reversal": {"ABSTAIN": 9, "RIGHT": 1},
 "k20|p382|two_hop": {"ABSTAIN": 8, "RIGHT": 3},
 "k20|p382|yesno": {"RIGHT": 3, "ABSTAIN": 2, "WRONG_CANDIDATE": 4}
}

## Deviations (2)

1. Rent-kit section C's `fable_self122` route122 smoke check raises FileNotFoundError on the box (self122_head.pt absent). Expected: this task streams code only and forbids reader weights, so the check does not apply; SEAL and selftest (the task's stop gates) both passed.
2. First ssh launch command's trailing `tail`/`ps` printed nothing (shell `&` precedence), but the follow-up check showed the run healthy and it completed on its own; no action taken.
