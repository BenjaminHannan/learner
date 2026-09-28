# Muse Spark 1.3 follow-up: up to 5 helpers (Thread manager, 2026-09-28T01:47Z)

Ben asked at 01:45:49 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEW3qJYQ2m8eDRYgFkFRidzCM): "give it a followup prompt that lets it run
up to 5 subagents". "It" is read as the Muse Spark chat running reviews/muse-spark-idea-harvest-2026-09-28.md (9f046992c).
Paste this into that same chat. If the chat has ended, paste the first prompt, then its last resume block, then this.
Effort: not an Opus 5.5 prompt. Everything below the line is the follow-up.

---

# Change from the next round: up to 5 helpers

Finish the round you are in, then switch to this. Everything else in my first message stays the same: the rules, the ledger, the idea card, the scores and the output rhythm, except where this message changes them.

**Helpers each round (up to 5, called at once):**
- **Explorers 1, 2 and 3** each get one angle and return 3 raw ideas. So you now cover 3 angles per round, and one pass through the 20 angles takes 7 rounds. The 7th round has only 2 angles left, so give the third explorer the best-scoring angle so far, to go deeper.
- **The skeptic** attacks the previous round's raw ideas, as before. There are now 9 per round, so one line is enough for a clear kill.
- **The deepener (new)** takes the highest-scoring kept idea that nobody has deepened yet and turns it into a plan someone could start building tomorrow:
  - the exact stored-weight count, shown line by line, within 2% of 1,645,726;
  - PyTorch-style pseudocode for the changed part and for how it decides to stop thinking;
  - the sealed test against the loop: the pass mark, the result that would prove it wrong, 2 seeds or more, and the cost;
  - the single most likely way it fails, and the cheapest check that would catch that first.
  If the deepener finds the idea can't meet the rules, it says so, and you lower its score or kill it.

Use fewer than 5 helpers when a round needs fewer, for example when no kept idea is left to deepen. Never give two explorers the same angle in one round.

**Output changes:**
- Round digest: at most 10 lines (kept, killed with the reason, deepened, and the current top 5 by name).
- Harvest report every 5 rounds: also include, in full and marked "deepened", every plan the deepener finished since the last report. When there are deepened ideas, take the top 3 sealed tests from them.
- Resume block: add a column saying whether each idea has been deepened.

Keep going until I type STOP.
