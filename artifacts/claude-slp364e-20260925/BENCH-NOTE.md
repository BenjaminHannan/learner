# slp-364e bench note (written at seal, before the run)

Fifth bench by a separate agent (58 min check run): 20/20 clean, 20/20 faults, 17 fault categories; 12 of 20 faults
show only in questions other than "Who is X's R?" or about people the day barely mentions.
Blindness: the author opened no gate, runner, earlier bench or result. Slip: a few recursive `grep -rn` searches over
scripts/ (for loop class names) scanned the forbidden files too; the author reports that no line from them matched or
was shown.
Author's notes, relevant to reading the result:
- Three notebook faults write through an `_append` captured before the runner installs slp-368, so the lock does not
  block them (it models a sleep step holding an old writer). slp-369 and the gate must catch them.
- The loop answers every yes/no word question "I don't know" before and after the night (the bench does not grade them).
- A word question on an incomplete chain can get a first-hop answer instead of "I don't know" (loop behaviour, both arms).
