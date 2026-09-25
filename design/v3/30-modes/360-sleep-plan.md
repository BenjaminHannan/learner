# 360 — What sleep does every night (Fix-sleep thread, 2026-09-25)

Owner: Fix-sleep thread (cmsg_01FuvegZXjMmeUzStiEFVnEWDjPgDy9L2RU9kjo7B9cnHs). Numbers 360-369.
Ben, 00:32 UTC 09-25: while the model isn't in use it should be doing something, and sleep is where it
improves itself over time, like a brain. This thread owns that.
Sources: sleep-research-2026-09-24.md (jobs A, B, C), VERIFY-336.md.

## Division of work
- This thread: the sleep cycle (when it runs, what jobs it runs, commit/undo), the scrap layer, the
  chat re-read job, the self-check gate, and the harness that runs reasoner training as a nightly job.
- Sleep research thread: the loop reasoner's training recipe, its size, the 3x goal, the teacher model.
  Sleep calls that recipe; it does not change it. Coordination goes through the coordinator.
- Reading thread: the live reader and lis-314 confirm rules. Sleep never changes the live reader.

## The nightly program (after 0.1; 0.1 stays sealed)
Sleep runs at night and also whenever the model has been idle for a while with unreplayed turns
("sleep pressure", job E from the research note). Every job writes only into a staged copy; the night
is kept only if the self-check at the end passes. Nothing guessed ever reaches the main notebook.

1. **Replay the day (job A).** Re-read every turn in the nb-323 turn log with a slower, careful read
   (full chat context, more compute than the live reply allows). Find teachings the live reader missed
   or misread, and re-check readings still waiting for a yes. Missed teachings become candidates in the
   scrap layer; weak pending readings are dropped. The morning agenda asks about the best candidates
   (small daily limit); only the user's yes saves. Aim: raise the 57% saved rate without adding wrong
   saves (in 336, all 33 wrong saves followed a confirm question, so fewer, better questions matter).
2. **Practice school (job C).** Build practice puzzles from facts the user actually taught: recombined
   chains of 2, then 3, then 4 steps, plus questions whose answer is missing (right answer: "I don't
   know"). Exact code checks every answer. The notebook rows are always in the input, so no fact is
   learned closed-book. Train the loop reasoner on them with the sleep research thread's recipe, mixed
   with replay of older practice so old skills aren't lost.
   **Second input: checked creative wins** (Ben, 00:51 UTC 09-25, creative thread). The reasoner should
   handle most things; the creative generator is for what it usually can't. When a creative idea solves
   such a problem and an exact checker (or the user) confirms it, the creative line writes it to
   `<state_dir>/wins/wins.jsonl` (one record: problem, the notebook rows it used, the solution steps, who or
   what checked it). Sleep turns each win into reasoner training episodes (the solved problem plus
   recombined variants built from the same kind of rows), so next time the reasoner solves it without the
   creative detour. Wins train the reasoner only; they never enter the notebook as facts. They are capped
   in the mix (model-made data at most 40%, CAIRN #47), and the gain must show on fresh blind problems
   made after the recipe is frozen, never on the wins themselves.
3. **Self-check before keeping the night (job B).** Re-ask the day's questions plus trick questions
   about things never taught. If the new reasoner states a made-up answer, loses a taught answer, or
   does worse than yesterday's, undo the whole night (weights, scrap layer, agenda).

## Build order (one change each, marks registered before any run)
- 360 scrap layer: sleep-derived and inferred rows go to a separate disposable notebook and never answer
  from the main one. Card test, $0.
- 361 staged commit + undo: a rejected sleep leaves notebook, routes and weights byte-identical. $0.
- 362 idle-time scheduler + day replay (job 1), candidates only. Dev on bank DEV 331; registered on a
  fresh blind bank. Banks A and B stay untouched.
- 363 practice school (job 2). First as a card test on the loop reasoner, then inside the agent. The
  claim to test: after several nights on its own taught facts, the reasoner does better on FRESH blind
  questions about new facts than (a) a twin that never sleeps and (b) a twin trained on the same amount
  of generic practice. (b) is what separates self-improvement from extra practice.
- 364 self-check gate (job 3), tested on a blind set of faulty and clean nights.

## Honest limits
- The loop reasoner is not in 0.1 yet (0.1 answers with the hand-written reasoner plus 298 and
  think299b). Until the loop reasoner beats that, sleep trains it on the side and its gains are
  measured separately; it is swapped in only after a registered PASS.
- Every learned reasoner so far has failed its bar (294-299, rsn-350). 363 may fail too.
- Training needs a GPU: rented 5090, at most $4 per job, $30 total cap.
