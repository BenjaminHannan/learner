# Exp 265 RESULTS: 261b's arm A plus the "our/we" ask-whose rule (builder, 2026-09-23)

## Result: registered FAIL

Arm A (261b A + 265 divert, sealed theta 0.25, prompt B, guard, Ruling-1
scorer) on the blind panel (80 items, every arm run once after both seals):
M1 FAIL (0 group-owned saves, but only 14/30 turns ask whose; bar 27),
M2 FAIL (5/15 mixed exactly right; bar 12), M3 pass (0 lost vs A261b),
M4 pass (15/15 byte-identical), M5 pass (0 new wrong saves).
Predictions P265.1 and P265.2 ranges wrong; P265.3-P265.5 right; P265.6
(~25% ALL) resolves to FAIL; P265.7 latency band right.

## Marks, arm A (integer counts)

| Mark | Bar | Got | Pass? |
|---|---|---|---|
| M1 | group_owner: 0 group-owned facts saved, and >= 27/30 turns ask whose | 0 saves; 14/30 ask | NO |
| M2 | mixed: >= 12/15 turns exactly right (other fact saved, no group fact) | 5/15 | NO |
| M3 | first_person: 0 lost vs A261b | 0 lost (A hits 15, A261b hits 15, gold 20) | yes |
| M4 | named: 15/15 byte-identical to A261b | 15/15 | yes |
| M5 | 0 wrong saves besides those A261b already makes | 0 new | yes |
| ALL | | | FAIL |

Every arm's wrong-save rates (each arm run once; report-only, no bars):

| Arm | TEACH saved | wrong frames | per-fact wrong | turns with a wrong save / 80 |
|---|---|---|---|---|
| A (registered) | 54 | 13 | 13/54 = 0.2407 | 12/80 = 0.1500 |
| A261b (261b A exactly) | 76 | 35 | 35/76 = 0.4605 | 30/80 = 0.3750 |
| B (138i + 228) | 6 | 5 | 5/6 = 0.8333 | 5/80 = 0.0625 |

A wrong saves by family: group_owner 2, mixed 1, first_person 8, named 2
(total 13). A has 22 fewer wrong frames than A261b (35 -> 13): 23
group-subject frames were diverted to ask-whose replies on 20 turns, and none
of A's 13 wrong frames is new vs A261b (M5).
B saved 6 frames total (1 hit, 5 wrong): the rule reader abstains almost
everywhere on this panel, same as on 261b's panel.

Per family, arm A (TEACH hit/gold, wrong, saved; ask turns):

| Family | n | TEACH hit/gold | wrong | saved | ask turns |
|---|---|---|---|---|---|
| group_owner | 30 | 0/0 | 2 | 2 | 14 |
| mixed | 15 | 15/15 | 1 | 16 | 6 |
| first_person | 20 | 15/20 | 8 | 23 | 0 |
| named | 15 | 11/15 | 2 | 13 | 0 |

Mixed detail: teach hit 15/15 with 1 wrong frame on one turn, ask present 6/15,
both (the mark) 5/15; group-subject saves on mixed 0/15. First-person misses
(5 gold frames) are identical in A and A261b (ear-level, both arms).

## Why the asks missed (categories only, never quoted)

Scored from run outputs only (panel never opened item by item; ear-subject
shapes classified without printing any wording):

- group_owner (16 no-ask turns): on 10 turns the ear surfaced no bare
  group-word subject at all (2 turns: ear emitted no frame; 8 turns: only
  name/other subjects -- possessive-predicate and object-position wordings
  where ownership is not a subject span). On 6 turns the ear did surface a
  group-word frame but the brake dropped it (odd-relation and non-literal
  spans), so the divert never saw it. The divert fired on all 14 turns where
  a group frame survived the brake (14/14), and group-subject saves are 0/30.
- mixed (9 no-ask turns): on 7 the ear surfaced a group frame the brake then
  dropped (first-person/other frames kept and mostly saved -- teach hits
  still 15/15); on 2 no group subject surfaced at all.
- The rule works every time it sees a group subject; the misses are upstream
  (ear parse + brake span match), which the one-change brief leaves untouched.
  Dev (canonical "Our X is Y" wordings) asked 12/14; the blind panel leans on
  possessive-predicate/object wordings the dev set did not cover -- a dev
  coverage gap, reported, not tuned (no panel re-run).

## Panel theta curve, arm A (recorded pYES, report-only)

Recall flat at 0.82 from theta 0.0 to 0.8 while wrong falls 18 -> 8
(at 1.0: recall 0, wrong 0). No theta moves M1/M2 (both are ask-driven and
theta-independent); the checker cut cannot fix missing asks.

## A's wrong and diverted frames (categories only)

- Diverted 23 group-subject frames to the fixed ask-whose reply (14 group
  turns + 6 mixed turns), 0 writes from any of them.
- Wrong saves, all checker-guard-passed non-group frames (13): 8 on
  first-person turns (fine-grained relation/value confusions A261b shares),
  2 on named turns (relation-direction flips A261b shares), 2 stray saves on
  group turns (non-group subjects the ear surfaced), 1 on a mixed turn
  (direction flip). Zero are new vs A261b (M5).

## Latency (no bar)

Ear GPU (both resident on the 5070 Ti): 80 turns, median 211.3 ms, p90
276.5 ms, max 458.9 ms; 65/80 beamed; ckpt sha ok; no VRAM spill.
Checker: 172 panel queries, 0 fallbacks, median 283.1 ms.
Ear-greedy + checker + guard per turn: median 373.4 ms, p90 679.5 ms,
max 1320.6 ms.

## Deviations

- D1 (sealed): scorer verdict needs exact panel family counts (loader
  enforces 30/15/20/15); on dev it forced ALL=false, so dev marks were read
  directly.
- D2: blind panel never opened before the seal (no listing, hashes, counts).
  After the seal its SEAL verified 2/2 OK from the repo root, the strict
  265 schema check passed (80 lines, ask_whose field, exact family counts),
  and every arm ran ONCE. earpanel257/261/261b never run.
- D3: llama-server handling. Plain taskkill is denied (session-0 isolation);
  started detached via Win32_Process (launcher PID 27936, server PID 30076,
  261b's exact flags) and stopped at the end by WMI Terminate on both exact
  PIDs (ReturnValue 0, 0), GPU back to idle 282 MiB. pythonw 13036 and all
  other BensPC processes untouched. Same server served dev and registered
  waves (health re-checked ok before the registered wave).
- D4 (sealed): diverted frames still spend a checker query so A261b stays
  byte-exact; arm A never uses those values.
- D5 (sealed): M5 = per-turn multiset difference of wrong frames.
- No re-runs, no post-seal code changes (seal rechecked 16/16 OK after all
  runs). Misses are systematic (16 + 9 ask misses), not single-flip flake, so
  no 5x item rerun applies.

## What it means (plain English)

The new rule does exactly what Ben asked: whenever the system spots a
"we/our"-style fact, it saves nothing and asks whose it is -- 23 times out of
23 on this panel, with zero group-owned saves. The failure is upstream of the
rule: on about half the group-worded turns, the reader never hands the rule a
clean "our"-subject to act on (it reads the ownership some other way, or its
safety filter drops the frame first), so there is nothing to ask with. First-
person and named facts are fully untouched (M3/M4/M5 pass), and the checker
plus guard behave exactly as in 261b.

## What it doesn't mean

It does not mean the rule is wrong: every ask it owed, it made, and it added
zero wrong saves. It does not mean first-person saving broke: those turns hit
15/20 in both arms with zero lost. It does not mean a stricter checker cutoff
would help: the recall curve is flat while wrongs barely move, and cutoffs
cannot create asks. It does not mean the ear got worse: on plainly worded
group turns (dev) it asks 12/14; the blind panel just phrases ownership in
ways the reader does not surface as subject spans.
