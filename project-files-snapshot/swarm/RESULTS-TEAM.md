# Swarm idea: results (2026-10-05)

Ben asked (2:35 PM ET) about a swarm of small models trained to work together and to learn in different ways, then
(3:01 PM ET) to "see if they can be trained together". Three checks, all on the from-scratch 3.3M models (Experiment B),
plus one free check on the real model (Experiment A). Marks for each were fixed before its run.

**Bottom line (shown, two seeds; a screen, not a confirm):** no form of teaming tried here helps on the twisted questions
(`variant`). Different recipes miss the same twisted questions that a second copy of B2 misses; a coach that decides who
practises what stopped routing anything once the members fit their practice questions; a coach that sees the members'
answers picks better on familiar questions (+2.5 points over B2 on `in_dist`) but not on twisted ones (-0.6). The swarm is
parked. The lever is the shared failure itself: questions every member gets wrong.

## 1. Free checks (no training)

Experiment A, the real model (CRDC, PR #38), 6 seeds voting: `in_dist` 89.7 alone, 93.9 as a vote; `variant` 49.2 alone,
53.7 as a vote; all six miss the same 95 of 280 (few-shot number rules 39 of 40).

Experiment B, all 7 small recipes (seeds 100/101, re-scored on CPU): on `variant`, "both wrong / geometric mean of errors"
is 92.0 for same-recipe pairs and 88.4 for different-recipe pairs (mark was 15 points apart: missed). Of the better
model's mistakes, the other model shares 93.3 (same recipe) vs 92.7 (different recipe). The three-member team B2 +
plain_tf_steps + plain_tf has a union of 42.2 / 41.9 against B2 alone 32.3 / 34.6, but majority vote gets 32.7 / 29.4.

## 2. Team screen: coach decides who practises what (`team.py`, marks `TEAM-PASS-MARKS.md`), BensPC

Seed 100 only (both runs 24k steps, about 218 min each on the RTX 5070 Ti):

| arm | team vote variant | team vote in_dist | B2 member variant | tfsteps | tf |
|---|---|---|---|---|---|
| ON (coach routes practice) | 31.2 | 90.1 | 33.8 | 29.0 | 20.1 |
| OFF (independent) | 31.4 | 90.7 | 36.4 | 28.8 | 20.5 |

**VOID** by the rule amended before any result: the final coach moved 1.0% of each member's sampling (mean TV 0.010;
void below 0.05; OFF 0.003). Why: early on the coach favoured B2 overall (share 0.70 at step 1,000), which by itself does
not change allocation; as the members fit their practice rows (98-99% right by the end) the coach's targets became uniform
and it drifted back to equal shares (final coach loss 1.093, close to ln 3 = 1.099, the loss of a uniform guess). Its largest effect: B2 got 1.37x the `cipher_map` practice.
The seed-101 pair was stopped part-way (it could not change a void screen) to free the GPU. Also noted: the coach-weighted
team vote (31.2 / 31.4) is below its own B2 member on `variant`.

## 3. Selector: a coach that sees the answers (`selector.py`, marks `SELECTOR-PASS-MARKS.md`), cloud CPU

Frozen solo members, 16k fresh labelled practice questions, aware (sees the three answers) vs blind (same layout, masked).

| team | split | aware | blind | B2 | union | aware rescues / harmful overrides (% of rows) |
|---|---|---|---|---|---|---|
| s100 | variant | 33.3 | 32.1 | 32.3 | 42.2 | 2.5 / 1.4 |
| s101 | variant | 32.4 | 33.5 | 34.6 | 41.9 | 1.6 / 3.8 |
| s100 | in_dist | 91.4 | 90.7 | 89.0 | 95.3 | 3.5 / 1.2 |
| s101 | in_dist | 92.8 | 92.1 | 90.1 | 96.0 | 3.3 / 0.6 |

`variant`: aware - blind = +1.21 / -1.06 (mean +0.08); aware - B2 = +1.06 / -2.20 (mean -0.57). **STOP** by the marks
(mean gain under 1.0 against both references, and behind both on s101). On `in_dist` and `frame` both selectors beat B2
(aware +2.4 / +2.7 on `in_dist`): picking among members works on familiar questions, and seeing the answers adds about
0.7 points there, but on twisted questions the selector overrides B2 wrongly about as often as it rescues it.

## What this does and does not show

- Shown: at 3.3M, with these three recipes, neither practice routing (as built) nor answer-aware selection turns the
  team's extra right answers on twisted questions into a better team answer.
- Not shown: that teams can never help. Untested: members trained to disagree on unlabelled inputs (DivDis / D-BAT),
  members that exchange messages while thinking, routing that stays alive after the members fit their practice.
- Any team claim would also have to beat a single ~10M B2 (not trained).
