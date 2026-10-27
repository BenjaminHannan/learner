# rd-378g: a note writer with no Claude in its training (registered 2026-09-26 16:58 UTC)

Thread "Trustworthy notes". Written before any GLM note, grade or training row for it exists.

## Why
Ben's 16:39 rule (goals page 5f38f110e): nothing a model trains on is written or judged by Claude. Thread manager ruling
16:53 (after Ben's "Retrain first" for the reader, 16:46): the rule covers trained models that could join a build.
The rd-378 note writer learned from 7,650 rows of Opus-written dialogs and notes, kept only where an Opus judge found
every note ok (artifacts/claude-rd378-20260925/data/README.md). It stays out of every build. rd-378L's PASS (notes
help search, 274fae558) stands as a finding about that writer; the writer that could ship has to earn it again.

## The one change
The training rows' author. G = MiniCPM5-1B (commit 87179e5c1f455ef22e6223592d2d61351b525bfc) + LoRA, trained exactly
as the rd-378 writer was (scripts/claude_rd378_data.py: a turn is kept only if every note on it is graded "ok" and
nothing was missed; repeat 3; scripts/claude_lis300_train.py epochs 2, lr 2e-4, rank 32, batch 16, max-len 512,
seed 300, --merge), but on GLM rows:
- dialogs and notes: GLM 5.3 Flash writes 240 dialogs with notes (scripts/claude_rd378g_teacher.py writenotes, the rd-378
  writer brief's note rules; structure and note form checked in code);
- grades: GLM grades every note with the judge brief's verdict words (scripts/claude_rd378k_teacher.py label).
Used only if the label gate passes (artifacts/claude-rd378k-20260926/PASSMARKS.md and PASSMARKS-B.md, both rows).
No panel, bank, LoCoMo or LongMemEval text, and no Claude-written or Claude-judged row.

## Registered test (real chats decide)
LoCoMo conversations 5-9 (PRACTICE: "after using LoCoMo for development"; never trained on; no question, answer, turn or
note text printed or pushed), through the store the build would use: scripts/claude_rd378u_confirm.py score with G's
greedy notes (scripts/claude_rd378_write.py over claude_rd378L_recall.py dialogs --convs 5-9), exactly as rd-378u
scored the rd-378 writer. A = heard rows only (store v3); G = store v4 with G's notes.
R = the rd-378 writer's figure from rd-378u's verified notes_confirm.json (same questions; the A rows must match).

## Marks (any@10, categories 1-4)
| Mark | Bar |
|---|---|
| G1 notes still help | G any@10 >= A any@10 + 5 points |
| G2 as good a search aid as the Claude-trained writer | G any@10 >= R any@10 - 2 points |
| G3 no category left behind | no category (1, 2, 3, 4) more than 3 points below A |
| G4 notes parse | unparsed turns <= 2% |
PASS = G1-G4. Proved wrong: G any@10 <= A any@10 + 1 point.
Runs only if rd-378u is a verified PASS; otherwise notes are out of search and this test is not run.
Report only: @5, @20, all@k, lines reached through a note, notes per turn, median and p90 write ms, dev loss, the GLM
grade counts, teacher cost.

## What happens next (fixed now)
PASS: G is the Claude-free note writer. It is offered to Month-end for 0.2d's notes slot (store v4), and rd-378k (the
cut-only step) runs with A = G, as PASSMARKS-B of rd-378k says.
FAIL: the Claude-free writer is not yet as good a search aid. First ask how the brain does it. Brain-first next step,
one change: in the brain an episode's index binds who, what and when together (episodic binding in the hippocampus;
textbook level, the mapping is a guess), so the teacher is asked to name every person and resolve every "that" and "she"
inside each note, with the same marks on fresh GLM chats.

## Seal
SEAL.sha256.txt (this file and the scripts named here) is written before any GLM note for rd-378g exists; SEAL-B adds
the GLM dialogs, grades and rows before training.
