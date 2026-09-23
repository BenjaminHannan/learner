Starting your scorer-consistency audit — checking runners and scorers across every verdict.
I've mapped all 15 verdicts — now digging into the runners and scorers behind each one.
The 138n mismatch is confirmed as the reference case — now auditing the other 14 experiments for the same issue.
Every panel uses one shared scorer for all arms — now verifying the saved rows to finalize the verdict table.
Audit complete — writing the verdict table to your output file.
Verdict: only 1 scorer mismatch in all 15 experiments — 138n M7/tablepanel221 (the known one). Every other verdict compared arms with the same runner+scorer and cannot flip on these grounds.

Marks table (integer counts from saved rows only, flags+ids, no item text):

| experiment | panel/comparison | base scorer | new-arm scorer | same? | could flip? |
|---|---|---|---|---|---|
| 138n | tablepanel221 (M7) | fable_fix221_panelmap.py (splits "A; B", ALL parts) | fable_fix221_panel.py (plain, literal match) | n | y — p221-059#2, p221-066#2, p221-070#2. Registered 66 right/0 wrong; 138n-as-scored 77/3 (lost_to_wrong 2, new_wrong 3). Consistent-scorer recount: 138n 79/0, bars 2,3 → 0,0 |
| 138n | tablepanel221b (M7) | claude_qnorm221c_run.py arm 221c | same script arms n/m | y | n (54/0 → 85/0, 0 new wrong) |
| 138n | teachpanel229 (M7) | claude_teach229_run.py score reg col 229 | same script+base | y | n (reg wrong 7, 138n 6 subset, 0 new) |
| 138n | namepanel232c (M7) | claude_fullname232c_score.py reg | same script+base | y | n (80/80 both, 0 moves) |
| 138n | firstnamepanel236 (M7) | claude_firstname236_score.py reg | same script+base | y | n (60/60 both, 0 moves) |
| 138n | aliaspanel237 (M7) | claude_table237_score.py reg 65/1 | same runner+scorer+fieldmap | y | n (138n 68/1, same 1 wrong, +3 gained) |
| 138k | suites vs 138j | suitediff218+merge138k score | same tools | y | n (0 moves all suites, bench×3 4/4 identical) |
| 138l | cases+suites vs 138k | claude_138l_l1/score all arms + suitediff | same | y | n (76 predicted exact; exceptions 13/13+25/25 identical) |
| 138m | cases+suites vs 138l | claude_138m_l1/score + suitediff | same | y | n (208 exact, 990/990 reproduced; exceptions 63/63 identical) |
| 252c | corrtail258+corrpanel252 | claude_merge252c_score.py all arms | same | y | n (0 lost, 54 total; M4 1 move c252-022 per rule) |
| 258 | corrtail258 80 | claude_comment258_score.py both arms | same | y | n (16 became right, keep 8/8, control 16/16) |
| 259 | corrtail258 80 | claude_bound259_score.py both arms | same | y | n (newly right 002/010/011/035, 0 newly wrong) |
| 260 | openpanel260 80 | claude_260_panel.sh+openers260_score | same | y | n (80/80 vs 38/80, 42 moves all →right, fidelity 80/80) |
| 237 | aliaspanel 80 | claude_table237_run+score+fieldmap | same | y | n (base copies byte-identical sealed shas) |
| 237b | aliaspanel237b 80 | 237 runner reused+237b score | same | y | n (221 arm reproduces base221 80/80) |
| 236 | firstnamepanel 60 | fullname232_run+firstname236_score | same | y | n (fresh 221 agrees 60/60) |
| 232c | namepanel232c 84 | fullname232_run+232c_score | same | y | n (36/36 multi vs 0/36; reruns 0 diffs; M3 same suitediff, 0 moves vs 232 rows) |
| 229 | teachpanel229 100 | claude_teach229_run run+score | same | y | n (23 newly RIGHT; 2 direction WRONG 009/011 declared) |
| 221b | panel221b 120 | claude_221b_run.py one scorer 3 arms | same | y | n (+23: 62 vs 39, 0 wrong/writes/lost; 1 flake move bench132-4hop-160, 5/5 correct rerun) |
| 221c | panel221b 120 | claude_qnorm221c_run.py one scorer | same | y | n (7 fires, 0 wrong/writes/lost; suites 0 moves; copies sha-equal) |

Every move that matters: the 3 tablepanel221 ids above (wrong→right under consistent key); 138n gained 21 on tablepanel221, 31 on 221b, 8 on 229, 3 on 237 (all miss→right, per m7-compare). Every miss: 8 right→miss on tablepanel221 are real behaviour gaps (4 inverse missing the label, 4 self changed by identity layer), not grading errors.

Deviations: (1) PUSH not done — OPUS-RULES forbids commits/pushes, so AUDIT.md is left uncommitted in artifacts/claude-scoreraudit-20260923. (2) Additive-only kept, 1 new dir + 1 new file. (3) Load ~56, disk 16–17 GB free; read-only work only. (4) Worktree had others' uncommitted changes; untouched. (5) No panel items opened/quoted; flags+counts only; no runs.

What it means (high-school English): 14 of 15 comparisons graded old and new with the same answer key, so those scores are fair. Only 138n's tablepanel221 used two different keys, marking 3 right answers wrong. With one key, that FAIL becomes a PASS on its bars (official FAIL stays on record with this note).

What it doesn't mean: it doesn't mean 138n is perfect (8 right→silent items are real gaps for 138nb), doesn't mean any other verdict flips, and doesn't mean anything was re-run or re-read — this audit only counted saved flags.

Output: artifacts/claude-scoreraudit-20260923/AUDIT.md (uncommitted, unpushed per rules).
