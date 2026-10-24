# Sleep-B: brain-like sleep that moves recurring facts from the diary into the weights (pre-registration, 2026-10-24 ~04:05Z)

Labels used below: **shown** (a result on file), **suggested** (reasoning or literature), **untested**.
Not the village model, not the card experiments. This is the borrowed Qwen model on its own, like Sleep-1
(`backbone/PREREG-sleep1.md`, results in `backbone/RESULTS-sleep1.md`).

## Ben's design rules (2026-10-24, thread "Design sleep like the human brain")
1. Sleep moves knowledge from the notebook into the model's weights (notebook = hippocampus, weights = cortex).
2. Only things that keep coming up move into the weights. Raw chats stay as a searchable diary, never deleted.
3. Mimic real sleep as closely as possible.

## Question
Over a simulated week of raw chats, does a sleep that copies the brain's mechanisms (tagging, prioritized NREM replay
interleaved with old memories, REM remixing, synaptic downscaling, reconsolidation, cleanup) put the recurring facts into
the weights and make them more useful (chained, updated, generalised) than Sleep-1's flat recipe given the same compute?
Does weights + diary search beat diary search alone?

## World: "Week-1" (`week.py`, fixed seed 1, fictional names only)
The user is a fictional person, "Sam". Sam chats with an assistant over 7 days. Facts about Sam's contacts come up in
passing while Sam asks for help with ordinary tasks (emails, plans, recipes, shopping, homework).

- **Base facts:** the Sleep-1 generator (`facts.py` structure: 6 relations, chains mentor_of+lives_in,
  sibling+works_at, owns+born_in), rebuilt with seed 1 so every name is new. 120 facts.
- **Recurrence classes** (stratified by relation, assigned by seed): 40 facts come up on 1 day (C1), 40 on 2 distinct
  days (C2), 40 on 4 distinct days (C4).
- **Changing facts:** 20 extra people. Each has lives_in or works_at with an OLD value, mentioned on 2 distinct days in
  days 1-3, then a NEW value, mentioned on 2 distinct days in days 4-7 ("Drovak finally moved to Kelmira").
- **Routines (gist):** 12 routines "Sam has <activity> with <person> at <place>", each told as an episode on 3-4
  distinct days ("grabbing dinner with Kelvora at Zhoumira tonight"). Never stated as a habit.
- Each mention is one user turn that contains both names of its fact. Turns are written by Claude (Sonnet 5.5) from a
  per-session plan, about 9 mentions per session, 6 sessions per day. Code checks that every planned mention appears
  (both names in one user turn) and that no test wording appears. Sessions that fail are regenerated.
- Output: `week1.json` with the diary (day, session, turn, role, text), the ground-truth plan (which turn mentions
  which fact), and the tests. Frozen and hashed before any sleep run.

## Tests (asked at the end of day 7, after night 7)
All test wordings come from fixed templates that never appear in the diary or in any dream (leak filter as in Sleep-1).
Scoring: greedy answer, correct if it contains the target name.
- forward recall: 120 (by class C1/C2/C4); reverse recall: 120 (by class).
- two-hop: every chain whose two facts are both C2 or C4 (about 27). Reported split by whether REM dreamed that chain.
- changed: 20 questions asking for the current value. Report new-value rate and stale (old-value) rate.
- routine: 12 "usually" questions ("Where does Sam usually have dinner with Kelvora?").
- general skill: ARC-Easy test, first 500 (as Sleep-1). Morning gate uses a separate 100 ARC-Easy *validation* items.
- Each test is run two ways: weights only (no notes), and with diary search (BM25 over user turns of the whole diary,
  top 8 turns in context, labelled with their day).

## Arms (Qwen/Qwen3.5-2B, thinking off, LoRA rank 16, alpha 32, lr 2e-4, KL guard as Sleep-1)
- **A0** base, weights only. Floor.
- **AD** base + diary search. The baseline Ben's design already keeps.
- **AB** brain-like sleep, 7 nights (recipe below). Scored weights-only and with diary search.
- **AF** flat sleep, 7 nights: each night runs the Sleep-1 recipe on that day's user turns only (dream paraphrases and
  Q&A from each turn with that turn in context, verify, train the same cumulative LoRA with the KL guard). No recurrence
  rule, no priority, no REM, no downscaling, no reconsolidation, no rehearsal of earlier nights. **AF uses AB's realized
  per-night step counts**, so both get the same training compute.
- Stage 2 (only after stage 1, each one change from AB): AB-noREM (REM steps go to NREM), AB-noSHY (no downscaling),
  AB-flatpriority (uniform replay over eligible items), AB-all (every item eligible, i.e. Ben's rule switched off).

## AB recipe: each brain mechanism and its copy
| Brain (status of the brain claim) | Sleep-B step |
|---|---|
| Hippocampus encodes each episode once, fast (well established) | Diary: every turn stored raw, append-only, never deleted. |
| Tagging at encoding: novelty, reward, "you'll need this" boost later consolidation (suggested; Wilhelm 2011, tagging-and-capture) | After each session the model extracts facts from each user turn as short sentences (JSON, at most 5 per turn). Tags per item: days_seen, importance (turn says remember / important / don't forget), correction (actually / correction / no, it's). |
| Pattern completion: a new episode reactivates similar old ones (established) | days_seen = distinct days with a user turn containing the item's names (string search over the diary; invented names are unique). |
| Ben's rule | Eligible to move into the weights only if days_seen >= 2, or flagged important or correction. |
| Sleep pressure grows with the day's load (Process S, established) | Night steps = min(300, 40 + 4 x eligible items not yet consolidated). |
| 4-5 cycles; deep NREM early, REM grows toward morning (established) | 4 cycles. NREM share of each cycle's steps: 80%, 65%, 50%, 35%. |
| NREM replay: hippocampus reinstates episodes and teaches the cortex, compressed (established in rodents) | Dreams: for each eligible item, the diary turns containing its names (up to 4, labelled by day) go in context; the model writes 4 paraphrases and 4 Q&A in both directions stating the CURRENT fact; each Q&A is re-answered with the same turns in context and kept only if it matches. Dreams are regenerated when an item gets new mentions, else reused. |
| Replay is prioritized (suggested; weak or salient traces favoured) | Sampling weight = days_seen x (1 + importance + correction) x (1 + surprise) x (0.25 if consolidated). surprise = 1 if the weights-only model got the item's probe wrong this morning. |
| Interleaving new with old protects old memories (complementary learning systems, suggested/established in models) | Every NREM batch: about 75% new-item dreams by weight, 25% rehearsal of consolidated items. KL guard on generic prompts every step, as Sleep-1. |
| Reconsolidation: a recalled memory becomes changeable and is re-stored with updates (shown in animals, debated in humans) | When the diary holds two values for the same person and relation (the model judges "changed / same / unrelated" for item pairs that share a name across days), the item's dreams use the newest value and add "now" questions; if the weights-only model gives the old value on its probe, the item's weight doubles. |
| REM: cortex recombines memories with little hippocampal input; links, schemas, insight (suggested; Wagner 2004) | REM dreams use the updated weights and only short extracted fact sentences (no raw turns). (a) chains: two eligible items that share a name -> a question that needs both, with answer; (b) gist: items seen on 3+ days -> one "usually" question. Then the diary checks each dream (deliberate departure from the brain, to avoid false memories) and only verified ones train. |
| Synaptic downscaling and pruning after sleep (SHY; ~18% synapse shrink in mice, de Vivo 2017) | End of each night, per LoRA module: SVD of the update, singular values x 0.85, drop those below 5% of the module's largest, refactor into the same rank. Things replayed across nights survive; one-night changes fade. |
| Systems consolidation: the cortex copy becomes independent, the hippocampal tag fades (established for gist; detail stays hippocampal) | An item is "consolidated" after its weights-only probe is right on 2 mornings in a row; its replay weight drops to 0.25. Raw turns stay in the diary. |
| Glymphatic cleanup (debated) | Nightly index cleanup: merge duplicate items, drop items whose dreams failed verification on 2 nights, mark superseded values. |
| (no brain analogue; safety) | Morning gate: if ARC-Easy validation (100) drops more than 3 points below base, or consolidated-probe recall drops more than 10 points, revert that night's update. Reverted nights are reported. |

Probes are dreamed questions held back from training (one per item), never test wordings.

## Pass marks (fixed now, before any data exists)
- **P1 transfer:** AB weights-only forward recall >= 70% on C4 and >= 50% on C2.
- **P2 brain features help:** AB >= AF + 10 points on the integration score = mean of two-hop, routine and changed-new
  (weights only), AND AB forward recall on C2+C4 >= AF - 5.
- **P3 old skills:** AB ARC-Easy (500) >= base - 2.
- **P4 system:** AB + diary search >= AD + 5 on the pooled test (forward, reverse, two-hop, changed, routine), and >= AD + 10 on two-hop.
- **P5 updates:** AB changed-new >= 60% and stale <= 20% (weights only).
- C1 recall is reported, not marked. By Ben's rule it should stay low in the weights and be answered by diary search.

**Wrong if** AB <= AF on the integration score (the brain mechanisms add nothing over flat sleep at equal compute),
or AB + diary <= AD on the pooled test (sleep adds nothing over search), or AB loses more than 5 ARC-Easy points.

Learning curves: forward recall on eligible items after nights 2, 4 and 7 (weights only).
One seed in stage 1. Compute: one Vast A100, hard cap $3 (coordinator, 03:55Z). Chat writing: Claude API, cap $3.
