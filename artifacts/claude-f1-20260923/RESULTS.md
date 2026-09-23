# Exp F1 RESULTS: 241b's sealed reply rewriter as the outermost layer on 292t

## Result first

F1 (292t + 241b render_line outermost) is built, sealed (41 files), and
registered once per arm. Mechanical marks: M2 PASS (0 unfaithful lines,
0 store/event changes everywhere), M3 PASS (every move reply-only, every
one a 241b route-A rewrite, every gate clean), joinpanel regression PASS
(90/90 byte-identical, 0 store diffs), convbench-f0 286/286 turns with
13 changed lines, all route A, 0 store diffs, M5 wall PASS (ratio 0.994).
M1/M4 are director-graded (not run here).

This does NOT mean F1 talks conversationally yet: only 13 of 286 everyday
turns visibly change, because most 292t replies are clarify/fixed lines the
mouth passes through untouched, and many understood-turn replies already
match stage-A surface forms. It DOES mean the rewriter installs cleanly on
292t: wording-only changes, nothing else moves.

## Integer counts

Build + dev pilot (own 73 turns, fictional names):
- dev turns 73; changed turns 28; changed lines 29 (all route A);
  legacy 1 (long "I can: ..." fixed text, byte-identical); passthrough 38;
  store-diff turns 0; crash turns 0.
- Route-A-with-identical-text exists (dev 8, joinpanel 24): 292t lines
  already in stage-A form parse and re-render verbatim. Counts as route A,
  changes nothing.

M3 registered (F1 vs 292t rows, run/ once):
- sessions152: 57 moves, 57 reply-only, 0 other.
- bench (NEW-1, D2): 648 moves, 648 reply-only, 0 other. GATE clean.
- bench frozen-harness (pilot, for the record): 649 moves = 639 reply-only
  + 10 new WRONG; all 10 are missing driver "yes" turns (frozen verbatim
  confirm needle vs 241b's sealed articles: "the United Kingdom",
  "a basketball coach", "an association football referee",
  "the Dominican Republic"); confirms 2->1 once and 1->0 nine times;
  NEW-1 matches all 10; 10/10 resolved with base-identical confirms.
- rt136: 145 rows; 52 reply-only, 0 other-field diffs; run gate clean.
- rt143nogate: 124 rows; 0 triples diffs; 0 expected diffs; reply text
  diffs 34 turns; teach-reply text-only diffs (triples identical).
- verifier vp: 98 rows, 63 reply-only, 0 other; vs: 12 rows, 11 reply-only,
  0 other. 0 stored/ev diffs anywhere.
- regscore problems 0. VERDICT PASS.
- S1 anchor: NEW-1 == frozen confirm on 721/721 saved 292t conflicts.

Joinpanel292t regression (sealed runner, once per arm; panel seal 2/2 OK;
78 dialogs, 90 turns):
- 90/90 turns 0 store/ev diffs; reply diffs 0 (byte-identical arms);
  unattributed 0; probes 0 reply diffs, 0 store diffs. VERDICT PASS.
- Mouth routes on the panel: A 24 (all A-identical), legacy 20 (ANSWER
  act, byte-identical fallbacks), passthrough 50.

Convbench-f0 (both arms, once; 40 dialogs, 286 turns, join_miss 0):
- changed lines 13 of 286 (prediction was 50-130: MISS, fewer than
  expected); all 13 route-A attributed (SAVED 9, ANSWER 2,
  ABSTAIN_MISSING 2); store-diff turns 0; event-count diff turns 0.
- Mouth routes: A 65 (13 visible + 52 A-identical), passthrough 223,
  legacy 0. changed-lines.jsonl holds every changed line
  (armA = 292t text, armB = F1 text, dialog/turn id).
- No grammar grading and no judge run here (director queues blind
  graders for M1/M4).

M5 wall (3 alternated suite runs per arm, load1 < 40 before each run):
- F1 runs 44.0/50.1/60.4 s; 292t runs 44.1/50.4/61.2 s; every run started
  with load1 below 40 (22.5/33.9/39.8/20.5/21.6/39.3).
- median292t 50.42 s, medianf1 50.12 s, ratio 0.994 <= 1.05. VERDICT PASS.

## Every move, every miss, every deviation

Moves: all suite/probe/convbench moves are reply-text-only; every checked
one is a 241b route-A rewrite (mouth log: suite 7590 A / 247 passthrough /
5 legacy; conv 65 A / 223 passthrough / 0 legacy; joinpanel 24 A / 50
passthrough / 20 legacy). Legacy fallbacks keep 292t text byte-identical.
Misses: (1) PF1.3 count prediction missed (13 vs 50-130) -- directionally
fewer visible changes; (2) PF1.4 expected some panel reply diffs, got 0
(byte-identical -- stronger); (3) frozen-harness bench shows 10 new WRONG,
all needle artifacts per D2 (resolved under NEW-1).
Deviations: D1-D8 in PASSMARKS.md (instance install; NEW-1 bench; gate
semantics; rt143 teach text; mouth logging; M5 block definition; conv
runner copy; setup deviations incl. missing OPUS-RULES path, one early
`git log`, dir-name listings only, config descriptive-only diff).
No sealed file changed after the seal (41/41 OK re-checked post-run).
No panel or benchmark user turn is quoted in this file.

## What it means / doesn't mean (plain high-school English)

F1 takes the better sentence-writer from the older model and bolts it onto
the newer model as the last step before answering. It only rewords -- it
never changes saved facts, answers, or decisions, and the numbers above
prove that (zero store changes, zero verdict changes). But rewording alone
barely shows: on everyday chat only 13 of 286 replies look different,
because most replies are "I don't understand" lines no rewording can fix.
The understanding problem belongs to a different work line.
