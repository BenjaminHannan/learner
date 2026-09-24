# lis-314b / lis-315 / lis-316 RESULTS (builder, sealed confirm panel)

## VERDICT: MIXED — P314 5/5 PASS, P316 3/3 PASS, P315 2/3 (P315.3 FAIL)

P314.1–5 all PASS. P316.1–3 all PASS. P315.1 PASS, P315.2 PASS (+21 facts),
P315.3 FAIL (P asks 61 questions vs C 59; bar P ≤ C, miss by 2).
Neither registered idea-killer fired: lis-314 is not proved wrong
(P314.1 PASS, saved-or-pending 96.6% ≥ 75%, ask_right 60 ≥ C 51);
lis-315 is not proved wrong (P315.1 PASS, +21 points ≥ +2).

## Marks (integer counts)

| Mark | Bar | Result | Counts | PASS/FAIL |
|---|---|---|---|---|
| P315.1 wrong-save turns | P ≤ C + 1 | P 0, C 0 | 0 ≤ 1 | PASS |
| P315.2 taught facts saved at dialog end | P ≥ C + 5 points | P 165/175, C 144/175 | +21 | PASS |
| P315.3 questions to the user | P ≤ C | P 61, C 59 | +2 over | FAIL |
| P314.1 wrong-save turns | K ≤ C + 1 and K ≤ 2 | K 0, C 0 | 0 ≤ 1, 0 ≤ 2 | PASS |
| P314.2 taught facts saved or correctly pending | K ≥ 85% | K 169/175 = 96.6% | ≥ 85 | PASS |
| P314.3 turns per question to the user | K ≥ 8 | K 354/32 = 11.06 | ≥ 8 | PASS |
| P314.4 asks answered right (told asks) | K ≥ C + 5 | K 60, C 51 | +9 | PASS |
| P314.5 never-told asks answered with a value | K ≤ C | K 0, C 0 | 0 ≤ 0 | PASS |
| P316.1 wrong-save turns | G ≤ S | G 0, S 0 | 0 ≤ 0 | PASS |
| P316.2 taught facts saved or correctly pending | G ≥ S − 2 points | G 170, S 170 | +0 | PASS |
| P316.3 questions to the user | G ≤ S + 3 | G 32, S 32 | +0 | PASS |

Supporting counts: K never-told asks 20/20 abstained (ask_untold_abstain 20,
ask_untold_stated 0); C identical (20/20 abstained, stated 0). K told asks:
60 right / 42 abstain / 7 wrong of 109. S told asks: 88 right / 13 abstain /
8 wrong of 109. G told asks: same as S (88 / 13 / 8).

## Every summary.json count, all six arms (40 dialogs, 354 turns each)

Arm A (292t alone, reference only): turns 354, kind_smalltalk 72,
kind_teach 135, kind_ask 129, kind_correct 10, kind_other 8,
questions_to_user 0, ask 129, ask_right 17, ask_abstain 83, ask_wrong 9,
ask_untold 20, ask_untold_abstain 20, wrong_save_turns 15,
wrong_saved_facts 15, final_facts 175, final_facts_saved 41,
final_facts_saved_or_pending 41, final_pending 0, facts_saved_pct 23.4,
facts_saved_or_pending_pct 23.4, asks_told 109, turns_per_question 354.0,
ms_median 4.2, ms_p90 9.5, ms_max 2794.3.

Arm C (+310, current wrapper): turns 354, kind_smalltalk 72, kind_teach 135,
kind_ask 129, kind_correct 10, kind_other 8, questions_to_user 59,
q_askback_yes 53, q_askback_no 6, ask 129, ask_right 51, ask_abstain 55,
ask_wrong 3, ask_untold 20, ask_untold_abstain 20, wrong_save_turns 0,
wrong_saved_facts 0, final_facts 175, final_facts_saved 144,
final_facts_saved_or_pending 144, final_pending 0, facts_saved_pct 82.3,
facts_saved_or_pending_pct 82.3, asks_told 109, turns_per_question 6.0,
ms_median 1227.2, ms_p90 2000.9, ms_max 3233.1.

Arm P (+310+315, per-fact release): turns 354, kind_smalltalk 72,
kind_teach 135, kind_ask 129, kind_correct 10, kind_other 8,
questions_to_user 61, q_askback_yes 57, q_askback_no 4, ask 129,
ask_right 55, ask_abstain 52, ask_wrong 2, ask_untold 20,
ask_untold_abstain 20, wrong_save_turns 0, wrong_saved_facts 0,
final_facts 175, final_facts_saved 165,
final_facts_saved_or_pending 165, final_pending 0, facts_saved_pct 94.3,
facts_saved_or_pending_pct 94.3, asks_told 109, turns_per_question 5.8,
ms_median 1228.1, ms_p90 2000.7, ms_max 3237.0.

Arm K (+310+314, confirm-at-use): turns 354, kind_smalltalk 72,
kind_teach 135, kind_ask 129, kind_correct 10, kind_other 8,
questions_to_user 32, q_confirm_yes 25, q_askback_yes 3, q_askback_no 4,
ask 129, ask_right 60, ask_abstain 42, ask_wrong 7, ask_untold 20,
ask_untold_abstain 20, wrong_save_turns 0, wrong_saved_facts 0,
final_facts 175, final_facts_saved 142,
final_facts_saved_or_pending 169, final_pending 29, facts_saved_pct 81.1,
facts_saved_or_pending_pct 96.6, asks_told 109, turns_per_question 11.06,
ms_median 1388.4, ms_p90 2064.1, ms_max 3340.8.

Arm S (+310+313+315+314, stack without guards): turns 354,
kind_smalltalk 72, kind_teach 135, kind_ask 129, kind_correct 10,
kind_other 8, questions_to_user 32, q_confirm_yes 25, q_askback_yes 3,
q_askback_no 4, ask 129, ask_right 88, ask_abstain 13, ask_wrong 8,
ask_untold 20, ask_untold_abstain 20, wrong_save_turns 0,
wrong_saved_facts 0, final_facts 175, final_facts_saved 142,
final_facts_saved_or_pending 170, final_pending 30, facts_saved_pct 81.1,
facts_saved_or_pending_pct 97.1, asks_told 109, turns_per_question 11.06,
ms_median 1361.8, ms_p90 2207.6, ms_max 3426.8.

Arm G (S + 316 code guards, deliverable): turns 354, kind_smalltalk 72,
kind_teach 135, kind_ask 129, kind_correct 10, kind_other 8,
questions_to_user 32, q_confirm_yes 25, q_askback_yes 3, q_askback_no 4,
ask 129, ask_right 88, ask_abstain 13, ask_wrong 8, ask_untold 20,
ask_untold_abstain 20, wrong_save_turns 0, wrong_saved_facts 0,
final_facts 175, final_facts_saved 142,
final_facts_saved_or_pending 170, final_pending 30, facts_saved_pct 81.1,
facts_saved_or_pending_pct 97.1, asks_told 109, turns_per_question 11.06,
ms_median 1255.2, ms_p90 2022.5, ms_max 3257.0.

## Device and timing

Reader (lis-301 merged, T = 0.995) on MPS (torch mps available True; Reader
default device resolves to mps on this Mac, no CUDA). Base 292t alone
(arm A) CPU-only, ms_median 4.2. Reader arms ms_median 1227–1388 per turn,
ms_p90 2000–2208, ms_max 3233–3427. No MPS out-of-memory crash in any of the
six arms (the lis-314-panel BLOCKED cause is fixed).

## Wrong saved facts, arms K, S, G (stored triple + turn kind)

None. wrong_saved_facts = 0 in all three arms, so there is no stored triple
to list. (Reference: arm A has 15 wrong-save turns / 15 wrong saved facts;
no mark uses arm A.)

## Checks (all before the run)

- Panel seal: `shasum -a 256 -c SEAL.sha256.txt` inside
  artifacts/claude-lispanel314-20260924/ → 6/6 OK (panel.jsonl, key.jsonl,
  label_B.jsonl, key_v2.jsonl, README.md, ADJUDICATION.md). Panel items never
  opened, printed or quoted; only the seal and the runner touched them.
- Code seal: `shasum -a 256 -c
  artifacts/claude-lis314b-20260924/SEAL.sha256.txt` from tree root → 9/9 OK.
- lis301-merged model.safetensors sha256 =
  b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 (match).
- `python -B scripts/claude_lis314b_test.py` → 16/16 passed.
- uptime at start: up 21 hrs, load ~60–165; disk 57 GB free (well above 3 GB).
- Sealed code never edited. Tree = fresh `git archive origin/builder-outbox`
  overlaid with fresh `git archive origin/main`, plus
  artifacts/fable-self122-20260922/self122_head.pt copied from the Mac repo.
- Ordering deviation (logged, no effect on numbers): arm A (reader-free,
  CPU-only) ran while lis-313b-f0 was on its arm A; all five reader arms
  started only after lis-313b-f0's last reader arm wrote its rows (one reader
  job on the Mac at a time). Time used ≈ 60 min of the 240 min cap.

## What this means in plain high-school English

The crash fix works: all six arms finished, zero out-of-memory crashes.
Confirm-at-use (lis-314) does what it promised: it asks half as often as the
current wrapper (32 questions vs 59 over 354 turns, one per 11 turns), keeps
97% of taught facts either saved or safely parked (169/175), answers 9 more
told questions right (60 vs 51), and never invents an answer for something it
was never told (0/20 both arms) with zero wrong saves. Per-fact release
(lis-315) saves 21 more facts than the current wrapper (165 vs 144) with zero
wrong saves, but asks 2 MORE questions (61 vs 59), which fails its P315.3 bar
by 2. The safety guards (lis-316) cost nothing measurable: G matches S on
every count (170 saved-or-pending, 32 questions, 0 wrong saves). The full
stack G is the month-end join deliverable: 97.1% kept, 88/109 told asks
right, 0 wrong saves, 32 questions per 354 turns.
