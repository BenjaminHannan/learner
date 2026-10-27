---
name: creative-egg-search-design
description: Ben's 09-25 afternoon creative design talk: Bayesian "egg" search, what he liked and rejected (no number-distance warmth)
metadata:
  type: project
  modified: 2026-09-25T16:11:45.603Z
---
Creative thread brainstorm, 2026-09-25 15:21-16:15 UTC. Page: https://claude.ai/artifact/5o6qUhdK53hmkUMwHCFWf8 (source was the creative session's scratchpad egg-search.html).
- Idea: a net predicts where answers probably are (a belief with several lobes, the "egg"). It samples guesses (Thompson-style) and updates the belief from what it finds. There are two speeds: in-context during a puzzle, and sleep writing the update into the weights.
- Ben 16:11: LIKES the sleep belief update. He REJECTED "warmth = numeric closeness": 22 vs 24 says little, and hard math has no distance-to-answer.
- My recommendation to him: do the sleep belief update first, then aim with checkable progress (can the leftover numbers still reach 24; lemmas and special cases in math) or learned warmth (a value net over past searches). Drop number-distance warmth. When the budget runs out, say "I don't know" and save the puzzle for sleep.
- The first test (plain circle / grow faster / aim with feedback) is NOT approved or built.
Related: [[creative-line-333e]], [[brain-emulation-goal]].
- 16:25 UTC Ben asked for evidence and a real-world scaling plan. Delivered design/v3/30-modes/creative-scaling-plan-2026-09-25.md (main ee8688ee9). Research notes with fetched quotes, 122 sources, are in reviews/creative-research-2026-09-25/. The ladder climbs by how exact the check is: rung 1 = reachability judge + hindsight relabel (22 counts as a hit for "make 22"); rung 2 = easier self-made variants; rung 3 = transfer to a second family; rung 4 = partial checkers; rung 5 = ideas, where the model sleeps only on ideas a person confirmed. Nothing is registered or approved yet.
- 16:55 UTC: Ben wants real-world practice (coding) and wants the model to learn to ASK when something isn't solvable. Delivered design/v3/30-modes/assistant-practice-plan-2026-09-25.md (main 355a9a6ae). Licence-checked ladder: Reasoning Gym (Apache; exclude gsm_symbolic) -> own Wordle / units / JSON -> Lichess CC0 -> xLAM calls -> MBPP / APPS / TACO -> contests -> Spider -> SWE-Gym. Excluded: allenai RLVR-IFeval and IF_multi (they contain GSM8K). First test proposed, not yet approved: "can't" on 458 provably unsolvable 24 hands, with solvable twins.
