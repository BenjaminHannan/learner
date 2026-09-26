# rv-391 dev 2, addendum 1: what the critic probe can and cannot show (thought-memory thread; written 19:31 UTC by date -u, before any trained-net number)

The Thread manager reviewed 8ec8392fe at 19:36 UTC. This addendum is a separate file because NOTE-critic-plan.md is
listed in SEAL-critic.sha256.txt, and the queued job checks that seal. Nothing sealed changes.

1. The r0 mark was changed after seeing a smoke number. The smoke ran r0 on 40 puzzles per set and gave a critic AUC of
   0.80 on p-grids7, against 0.70 for the count-only baseline. That smoke number is data, and the change was made after
   seeing it. The plan note's wording "before any trained-net number" is true, but the change was not blind.
2. An untrained net's critic reaching 0.80 means the critic can read the page's own clashes from the state. The written
   symbols go into the net's input, so even random features carry them. So this probe answers one question: "can a
   critic predict dead ends from the page plus the net's state?" That is all step 2 needs, because a go-back trigger
   only needs predictive power. It does NOT answer "does the trained reasoner's state carry the signal".
3. Added report row: for each practice set, the trained nets' mean AUC minus r0's AUC. That row will be read later
   against the second question. It is not a clean answer on its own, for two reasons:
   - r0 searches differently (most of its guesses are wrong), so its states and dead share differ from the trained
     nets';
   - a fair test would give both critics the same page states.
   It is suggested, and it changes no mark.
