# rd-378k: the cut-only note writer (371c step 4b) (registered 2026-09-26 16:49 UTC)

Thread "Trustworthy notes". Written before any rd-378k training row, teacher label, panel note or judge verdict exists.
Plan: design/v3/30-modes/371c-note-and-save-plan.md, step 4b; its marks (drop >= 15 points, missed rise <= 10%, proved
wrong < 5 points) are kept here.

## Why
The rd-378 note writer (MiniCPM5-1B + LoRA, merged sha256 dbcc8db5...8510) writes notes that are often untrue: 113 of
360 unsupported on notepanel378, 145 of 277 key notes on notepanel371b, 539 of 1,257 greedy notes on rd-371b's training
dialogs. rd-378L showed the notes help search (PASS, 274fae558), so an untrue note can pull a wrong line into view.
Ben chose "Cut only" (12:02 UTC): a correction may only delete the untrue part of the writer's own note, never add words.
Ben's "Use GLM" (16:39 UTC, goals page 5f38f110e): nothing a model trains on is written or judged by Claude. So the
practice dialogs are written by the GLM teacher and the writer's notes are graded by the GLM teacher; Claude only
writes the sealed test panel and judges it blind (allowed for tests).

Brain picture (textbook level; the mapping is a guess): during consolidation the brain replays the day's traces, and
the ones that were checked against where they came from (reality monitoring) are kept and strengthened, while unchecked
ones fade. Here the replayed traces are the writer's own notes, the check is the teacher's reading of the cited turns,
and consolidation is training on what survived. Nothing new is learned from outside the writer's own words.

## The one change
A = the rd-378 writer, unchanged. B = the same writer trained once more on its own notes with every note the teacher
did not mark "ok" deleted. Only the training rows differ from A's recipe.
- Dialogs: 160 practice dialogs written by GLM 5.3 Flash (scripts/claude_rd378k_teacher.py write: 20 calls of 4 chat +
  4 overheard, 12-16 turns, structure checked in code). No panel, bank, LoCoMo or LongMemEval text.
- Drafts: A writes a greedy draft and one sample at temperature 0.8 per turn (scripts/claude_rd371b_sample.py
  --samples 1 --temp 0.8 --seed 371), as rd-371b did.
- Grades: the teacher grades every distinct note of a turn with the judge brief's own verdict words
  (claude_rd378k_teacher.py label over claude_rd378k_data.py judgein; artifacts/claude-rd378-20260925/data/JUDGE_NOTES.md).
- Rows (scripts/claude_rd378k_data.py): target = the turn's distinct notes graded "ok", word for word, first-seen order;
  a turn left with no note is kept only if the teacher found nothing missed there. 10% of dialogs to dev. Repeat 3.
- Training: scripts/claude_lis300_train.py from A's merged weights: epochs 2, lr 2e-4, rank 32, batch 16, max-len 512,
  seed 300, --merge (A's own settings).

## Label gate (before any training)
The teacher grades the rd-371b training drafts of the dialogs with sha256(id) % 3 == 0 (claude_rd378k_teacher.py label
--only-hash 3 on artifacts/claude-rd371b-20260926/data/judge_train_in.jsonl), compared, ok vs not ok, with the blind
judges' verdicts on the same notes (judge_train_out.jsonl; used only to measure the teacher, never trained on).
Rule (the creative thread's rule for a label source, k1e): agreement >= 85% and kappa >= 0.5. If it fails, nothing is
trained: one change to the teacher (two teacher passes, a note kept only if both say ok) is measured by the same rule on
the dialogs with sha256(id) % 3 == 1, and only a passing teacher grades the training drafts.

## Registered test
artifacts/claude-notepanel378k-20260926 (TEST-ONLY; 30 fresh dialogs, 15 chat + 15 overheard, 12-16 turns, written blind
by a separate Claude agent from BRIEF.md; sealed before any rd-378k training). A and B each write greedy notes over it
once (scripts/claude_rd378_write.py). Each writer's notes become one unnamed set, P or Q, by a coin flip recorded in
map.json, which the judges never open. Four blind Claude judge runs with the judge brief JUDGE_NOTES.md, two per set,
each run seeing one set only. Scored by scripts/claude_rd378k_score.py score (a writer's figure = the mean of its two runs).

## Marks
| Mark | Bar |
|---|---|
| K1 untrue notes | B's unsupported share of its notes <= A's - 15 points |
| K2 true notes kept | B's ok-note count >= 85% of A's |
| K3 memorable things missed | B's missed total <= 1.10 x A's |
| K4 notes parse | B's unparsed turns <= 2% |
| K5 search not hurt (only if rd-378u is a verified PASS) | LoCoMo conversations 5-9 through store v4 (claude_rd378u_confirm.py): B's any@10 >= A's any@10 - 2 points |
PASS = K1-K4, and K5 where it applies. Proved wrong: B's unsupported share is less than 5 points below A's.
K5 uses rd-378u's own notes for A (kept on the Mac, never pushed) and B's notes over the same dialogs; LoCoMo is
practice, never trained on, and no LoCoMo text is printed or pushed. If rd-378u is not a verified PASS, K5 is not run.
Report only: every verdict count per run, both-runs-agree counts, notes per turn, bad_when / bad_cite / bad_form shares,
dev loss, median write ms, teacher cost.

## What happens next (fixed now)
PASS: B replaces A as the note writer offered to Month-end (with store v4 if rd-378u passed). The next round repeats the
same loop with B's drafts on new teacher dialogs (graded, cut, trained once more) until notes reach rd-378's own bar of
<= 5% unsupported.
FAIL or proved wrong: first ask how the brain does it. Brain-first fallback, one change: learn from the cut notes too,
not only from what survived (error-driven learning: a prediction that turns out wrong weakens the path that made it;
the mapping is a guess). Same rows, each cut note's full draft added as the rejected side of a preference pair (DPO),
so the kept side is still cut-only and no word is added. Judged on a fresh blind panel with these marks.

## Seal
SEAL.sha256.txt (this file, the scripts named here and JUDGE_NOTES.md) is written before any teacher label exists. The
panel carries its own seal, written before any rd-378k training. SEAL-B.sha256.txt adds the teacher's dialogs, the
drafts, the labels, the rows and the panel's seal before training.
