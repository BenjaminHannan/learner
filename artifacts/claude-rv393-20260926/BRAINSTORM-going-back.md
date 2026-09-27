# Going back: what next? A brainstorm for Ben, through the Thread manager (thought-memory thread; 2026-09-27, after rv-393)

rv-393's plan (PLAN.md, "What would change the plan") said: if pencil marks are PROVED WRONG, going back goes to Ben
as a brainstorm, per the goals page ("when the ideas run out"). This note is that brainstorm. Nothing here is started.

## Where we are (plain words)
- The puzzle solver writes a guess when it is stuck. One wrong guess can ruin the puzzle.
- Going back means rubbing out a bad guess and trying another. To do that, something has to notice the bad guess.
- Five tries found nothing that notices it better than counting how many guesses are on the page:
  the solver's "am I done" value, its raw signals, a small checker net (twice), and now pencil-mark training.
- So for now going back is triggered by a timer: if the puzzle is not solved within 16 rounds of a guess, go back
  and try the next candidate. That timer is a hand-set rule, disclosed as scaffolding (Redirect, 16:04). rv-391
  will be registered on it, to test going back itself, once the re-run on the new nets lands (BensPC job 173;
  170 to 172 ran nothing).
- Side finding from rv-393: a short practice on 7x7 puzzles made the nets much better at 7x7 (173 to 241 of 300
  before, 285 to 291 after), so far fewer 7x7 puzzles are left for going back to rescue.

## Options (one change each; my pick first)
1. Keep the timer and run registered rv-391 on it (my pick for now). It is $0 and needs no architecture change.
   It answers the first question: does going back help at all, whatever triggers it? If going back itself does
   not help, a smarter trigger is not worth building.
2. Train on its own pencil marks, round after round. rv-393 trained on the untouched net's mistakes but was
   judged on its own. Repeat the fine-tune with traces from the fine-tuned net itself, a few times over (the field
   calls this expert iteration). $0 on BensPC, copies of nets, no architecture change. Risk: its own wrong guesses
   are its best beliefs, so it may still trust them.
3. Ask a second copy. Silicon can run copies: two nets trained from different starts that disagree on a cell
   are a doubt signal no single net has. $0 to measure on the four nets we already have, no new weights.
   Brain mapping (a guess): a second opinion, or checking your work a different way.
4. A learned "commit" output: the net itself says when to write a guess and when to rub one out, instead of the
   hand-written guess rule. This changes the reasoner's design, so it needs Ben's yes
   (design/v3/30-modes/ben-goals-2026-09-26.md:96).

## What I need from Ben
Nothing is blocked. Option 1 goes ahead on its own once job 173 lands. The question for Ben is whether
options 2 to 4 are worth trying after that, and whether he has another idea. If he wants an outside opinion, I can
write a prompt for Astra or GPT on why pencil training did not carry over to the net's own guesses.
