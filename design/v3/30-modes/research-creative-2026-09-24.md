# Creative writing research (2026-09-24, creative research thread)

Ben asked (18:41 UTC) for research on how Premonition could be creative (stories, poems, plans, ideas).
One workflow ran: 4 web researchers (small-model writing, brain creativity, picking and judging, grounded personal
creativity), 1 code reader (code only, never the TEST-ONLY 333 panel or its run outputs), and 1 skeptic per research
report who re-opened the cited papers. Raw output: artifacts/claude-cre-research-20260924/workflow-result.json.
Nothing here was trained or run on a GPU. This thread changed no code and no sealed build.

Labels: **shown** = in the code or the paper's full text; **suggested** = a reasonable reading, not measured;
**untested** = an idea. "Checked" means a skeptic agent opened the source and it held up.

## Plain version for Ben

The creative helper loses to the plain 1B mostly because of plumbing, not because the 1B is too dumb:
1. **The front door misses requests.** The keyword detector only notices a few wordings. On the panel it sent 25 of
   the 40 creative requests to the creative path. I tested 8 requests I wrote myself and it missed 6, e.g.
   "Write my sister a birthday card", "Help me word an apology to Sol", "What could I cook for Sam on Friday?".
2. **It never sees the conversation.** It gets one instruction, the notebook facts, and your last message. The plain
   model it lost to sees the whole chat, so it can use details the notebook didn't save ("she's into pottery",
   "I'm broke this month").
3. **It doesn't pick its best try.** It keeps the first of 4 drafts that passes the safety filters. A tidy-up step
   also chops the last item off numbered lists, and the "no refusals" filter throws away useful hedged answers.

The research says: tweaking how the model picks words barely helps at 1B; asking a 1B model to plan or critique its
own writing mostly doesn't work; what does work is (a) practice on a few thousand good examples and (b) a separately
trained small judge that picks the best draft, if it's kept from simply rewarding longer answers.

The brain-like and new ideas, for later: give each draft a different mix of true notebook facts (recombining
memories, as the hippocampus does when you imagine), and during sleep train a small detector of invented facts
about people, using the notebook as the answer key. We found no published version of the second one.

## What the code shows (all shown, file:line; checked by this thread)

| # | Finding | Where |
|---|---|---|
| C1 | Router = cue AND request form AND NOT recall. No cue for cook/make/bring, card, message/note/text, word(ing), draft, weekend/trip, speech; "write" needs "me/us a"; "plan" needs an article. This thread's check: 6 of 8 hand-written requests missed. Panel: 25/40 routed (VERIFY-333.md). | scripts/claude_cre333_agent.py:29-34; scripts/claude_cre333b_agent.py:45-59 |
| C2 | The panel's P arm is 292t + 333d only, so the 15 unrouted items got 292t's ordinary reply: P333.3 was capped at 25/40. P's 8 useful = 8 of the 25 routed. | scripts/claude_cre333_run.py:53-55 |
| C3 | 333d sends the 1B [system + notebook facts, current message]; no chat history. 338 sends the last 12 messages; twin b sends the whole chat. | scripts/claude_cre333d_agent.py:60-65; scripts/claude_chat338_agent.py:155-158; scripts/claude_e2e336_twin.py:53,64 |
| C4 | Sampling T 0.7, top_p 0.9, 200 tokens, 4 samples, keep the first that passes the guards. No ranking. Twin is greedy. | scripts/claude_chat338_agent.py:188-212; scripts/claude_cre333d_agent.py:65-70 |
| C5 | trim() cuts to the last [.!?]: a numbered list without a final period loses its last item and keeps a bare "3.". | scripts/claude_chat338_agent.py:76-84 |
| C6 | G5 (refusal filter) also matches "without knowing ...", "could you tell me ..." inside otherwise useful answers, while SYSTEM333D tells the model to stay general about untaught people, which invites exactly those hedges. | scripts/claude_cre333d_agent.py:23-27,30-33 |
| C7 | context_facts: every user fact + anything named + one hop, up to 40, in notebook order (no relevance ranking). | scripts/claude_cre333_agent.py:53-63 |
| C8 | Only 2 of 25 routed turns fell back, so the filters mostly decide *which* weak draft wins, not *whether* one does. | VERIFY-333.md (333d section) |
| C9 | The sealed 330c puts 338b outside 333d, so an unrouted creative request in the sealed build may get a 338b chat reply, not 292t's. The panel didn't measure that stack. **Suggested** (read from the layer order; not run). | scripts/claude_e2e330c.py:4-13 |

The DEV bank has only 10 creative turns, all routed: too few to set pass marks. A blind-written DEV creative set
is needed before any experiment below.

## What the research says (checked unless marked)

Small models (0.5B-3B):
- Sampler changes are a weak lever at 1B. The min-p paper's only 1B creative test used 3 prompts (2407.01082 App.
  C.3.6, checked); a reanalysis found no reliable min-p gain (2506.13681, checked; it did not re-test the 1B table).
- Self-critique and plan-first help big models, not small ones (reported by the researcher; **not re-checked**).
- Cheap supervised training works on short creative replies: on a 7B, SFT raised "acceptable" greetings from 53.8%
  to 86.2%, RL added about 5 points (2508.21476, checked; the label is binary "acceptable", not "excellent").
  Plain SFT on long stories collapsed a 9B (2606.04095, checked).
- TinyStories-style seeding (random words + features) is how synthetic data stays varied (2305.07759, checked; it
  was used to pretrain tiny models, not to tune a 1B chat model).

Picking and judging:
- Trained scorers beat zero-shot judges on creative writing: 78% agreement with humans for a trained 8B reward model,
  56-60% for zero-shot 7-8B judges (LitBench 2507.00769, checked). **Correction:** the 78% model is 8B, not small.
- Length bias is the main trap: a 1B reward model trained on unfiltered pairs "strongly preferred the longer story";
  length-balanced data fixed that (2507.00769, checked).
- Ready-made small reward models exist (Skywork-Reward-V2 0.6B and Llama-3.2-1B, 2507.01352, checked), but the 1B
  is weak on factuality (60.9) and hard style-vs-substance cases (57.8). The claim that it matches frontier judges on
  personalisation was **wrong**: that benchmark hid the user profile from the reward model (2604.07343 Sec. 4.1).
- Likelihood-based picking favours bland, safe replies (Li et al. 2016, 1510.03055, checked). That matches 333b/c.
- Judges drift with answer order and length; report length-controlled preference (2404.04475, checked).
- Measure variety only among on-task replies; distinct-n and type/token ratios mostly track length (2403.00553;
  NoveltyBench 2504.05228, checked: Llama-3.2-1B was very varied but low in usefulness).

Brain:
- Creativity looks like a loose generator (default mode network + hippocampal recombination) checked by a controller
  (executive network), with switching between them. In N=2433, more switching went with more divergent thinking,
  but the effects are small (g=0.17) and correlational (Chen et al. 2025, checked).
- Almost every piece already has an ML version (ReMIND 2601.07121, QDAIF 2310.13032, DivPO 2501.18101, DDPO
  2503.17126, dream/sleep phases 2606.03979 and 2607.16256). Dream-style LoRA consolidation was null at matched
  settings on three base models (2607.16256, checked). So novelty has to come from the combination.
- Generative "cortex" recall drifts toward the typical case (schema distortion), which in an assistant shows up as
  invented facts. The fix those models point to is Premonition's design: exact specifics in the notebook, generic
  structure from the generator (suggested reading of GENESIS 2510.15828 and Spens & Burgess 2024).

Grounding in taught facts:
- A few relevant facts beat many loosely related ones (LoCoMo 2402.17753, checked; the effect is small and was
  measured on QA, not creative writing).
- Telling a model to "use the user's preferences" can make it invent preferences or refuse (PrefEval 2502.09597,
  checked; the mapping to 333d is suggested).
- Small trained classifiers or read-outs of a model's own hidden state beat hand rules for intent detection
  (2410.01627, checked; rejecting out-of-scope requests stayed hard and cost in-scope recall).
- Hidden-state probes can flag invented entities (2509.03531, checked: linear probe AUC 0.85-0.87 on 8B-70B, with
  web-search labels).

## Recommended order (one change each; DEV only, never the 333 panel)

0. **DEV creative set + judge audit** (untested; $0-0.2). A blind writer makes 40 creative requests + 30 look-alikes
   (including recall questions about taught people, which must route 0), fictional names outside A-M. Audit the
   judge: padded-copy probe and both answer orders. Measure the judge's own repeat noise (8 vs 10 on 40 is noise).
1. **Oracle routing check** (untested; under $1). Force every DEV creative item down the creative path vs the
   ordinary path. If the creative path doesn't win there, a better router can't help. Then:
   **Learned request detector** (untested; $0 CPU): logistic head on sentence embeddings or the 1B's hidden state,
   trained on DEV. Pass (fixed now): routes at least 36/40 held-out creative, at most 1/30 look-alikes, 0 recall
   questions. Proved wrong if it routes under 30/40 or does no better than the regex.
2. **Give the creative path the last 12 chat messages**, as 338 does (untested; under $1). Pass: useful at least
   333d + 5 of 40 on DEV and invented person facts at most 2/40. Proved wrong if the gain is under +3 or invented facts
   rise. Free first check on CPU: share of taught seed facts that reach context_facts; if at least 90%, skip it.
3. **Fix trim and narrow G5** (untested; under $0.50). Pass: 0 replies ending in a bare list number, useful not lower,
   fallbacks and invented facts not higher.
4. **A real picker**: 8 drafts, choose with a length-matched trained scorer (a small head on MiniCPM5-1B, trained on
   teacher-labelled pairs of its own replies) or Skywork-Reward-V2-1B (a new download: needs Ben's yes). Always report
   a "pick the longest" control on the same drafts. About $1-2.

After 09-30 (research line, brain-like):
5. **Recombination cues** (partly published; untested): each of the 4 drafts gets a different near + remote notebook
   fact about the same person, so drafts differ without inventing anything.
6. **Sleep-trained invented-fact probe** (no published version found; untested): in sleep, generate drafts about
   notebook people, label each person-claim as supported or not from the notebook, train a probe on the 1B's hidden
   states, and use it to pick among drafts. Pass: AUC at least 0.85 on held-out drafts and better than regex G2.
7. **Creative skill LoRA from seeded teacher replies with fact slots**, trained in sleep (skill only, never facts).
   About $1-3 plus a teacher model download (needs Ben's yes). Risk: copies the teacher's samey style.

Skeptics' main cautions: no experiment should use "beats the twin" on 40 items without a paired test and a judge
repeat; pass marks need a declared gray zone; and every generation result is confounded by C1-C3 until those are
fixed or held equal.
