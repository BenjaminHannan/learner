# Fix sleep (problem 7) closes by design, not because a fix won
Fix-sleep thread, written 2026-09-27T13:30:12Z from `date -u`. Additive note; no sealed file is changed.

## Why it closes
Problem 7 was "sleep nights make the 1B forget general questions". Ben settled the question himself.

At 13:28:08 UTC he answered "yes" (cmsg_01FuvegZXjMmeUzStiEFVnEWF3UMqBUcaQoQMBxSh17FDr) to the Thread manager's
"Should sleep move to the reasoner?" (13:26:17). At 13:28:18 he added "can you make sure that happens all around".
Before that he had asked:
- 13:23:52: "isn't the 1b a reader? WHy does it matter if it forgets things"
- 13:25:42: "Why would the talker need to be trained at all? It just talks"

So nights train only the reasoner, and the reader and talker 1B stay frozen at night. A frozen model cannot forget
anything at night. **The problem is gone because of that decision, not because any of the fixes below won.**

The reader is still trained once, as a reader (lis-320). That training is not a night, and this note does not
touch it. Training the talker for talking itself, not for skills, is also outside this note.

## What the Fix-sleep tests showed
Every verdict stands as registered. A FAIL stays a FAIL.

| test | verdict | what it showed | verify |
|---|---|---|---|
| dl-1 | FAIL | Reward-style nights learned less than copy nights | 6e250996e |
| dl-2 | PASS (with forgetting) | Copy-practice nights raised puzzle luck a lot, but lost 26 of 200 base-right panel items by night 7 | a6cb00d26 |
| dl-3 | FAIL | Replaying the base's chat answers did not halve the forgetting (lost 20 and 36 vs 39 and 24) | fd2ff8daa |
| dl-4 | FAIL | A KL anchor on chat answers: lost 25 vs 33, needed 16.5 or less | 75f673fa5 |
| dl-5 | FAIL (finding only; Claude wording) | Grid nights learned in one night, then spilled their answer shape onto the panel (lost 98 and 61) | a5d779c29 |
| dl-6 | FAIL | Lighter nights (1 epoch) roughly halved both the forgetting and the learning | aba68565a |
| dl-7b | FAIL | An anchor on shaky facts cut forgetting from 26 to 7, but kept only 76% of the learning (F3) | a1ce6187b |
| dl-5s | finding only | A learned switch on the frozen base kept dl-5's grid add-ons off the panel (lost 98/61 to 0/0) | f0ae3bea6 |
| dl-9 | PASS | A separate add-on plus a learned on/off switch lost 0 of 300 panel items (always-on: 20 and 27) and kept all the puzzle learning | 1cb95fd69 |
| ip-1 / ip-1b | FAIL / PASS | A night can be stopped safely at any moment (11 of 11) | 0446319b2 / 50e216024 |

dl-9's PASS is scoped to its easy case: 2 seeds, one frozen 1B, number puzzles against quiz questions that look
nothing alike (the switch fit at 0.0 loss from night 2). It also threw away the always-on add-on's panel gains (55
and 49). It says nothing yet about look-alike requests, several parts, or the reasoner.

## Not run under Ben's 13:28:08 yes
- dl-8 (error-gated nights; sealed 1771eba18; handoff/held/300-fixsleep-dl8pc.md): held and marked DO NOT RUN
  (ad1c92b0d).
- dl-10 (replay plus switch; artifacts/claude-dl10-20260926/PLAN.md): plan only, never sealed.
- dl-11 (router over look-alike skills in the 1B; sealed 57f2bd620, ADDENDUM-1 56bd13490): the BensPC job
  handoff/held/301-fixsleep-dl11pc.md is held and marked DO NOT RUN. Its Luna data stage (queue
  300-fixsleep-dl11-luna) finishes as data only: no training run uses it for the 1B.

## What carries over
- ip-1b's rule (a night stops cleanly at any moment) still has to hold for the reasoner's nights. Fix sleep offers that check if Sleep research asks for it.
- dl-9's lesson, that a separate part plus a learned switch stopped the spill in the easy case, is input to the open experts card only. Nothing here decides that card.
- dl-12 (Thread manager OK, message queued 13:29:48 UTC) is a $0 measurement and builds nothing. It asks whether the frozen reader's state tells look-alike requests apart without a task label. Its result is report-only input to the experts card and bears on Ben's 11:34 "It should for each request be able to automatically decide what."
