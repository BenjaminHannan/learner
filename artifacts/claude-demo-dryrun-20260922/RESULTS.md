# Demo dry-run: loop138i base agent vs SmolLM2-360M-Instruct (2026-09-22)

One script (32 turns, including 1 restart and 5 visitor-improvised turns), one run per system. Measurement only: no agent code was changed.

- Script: `script.json`. Side-by-side replies: `transcript.md`. Raw replies, notebook triples after every turn, and SmolLM prompts: `raw.json`.
- Driver: `scripts/claude_demo_dryrun.py`. Transcript renderer: `scripts/claude_demo_transcript.py`.
- Diagnosis probes (not graded, alternate wordings on fresh temp state): `scripts/claude_demo_variant_probe.py`, `scripts/claude_demo_restart_probe.py`, `scripts/claude_demo_reload_probe.py`, `scripts/claude_demo_values_probe.py`.
- Agent: loop138i with `artifacts/fable-agent138i-20260922/loop138i-config.json`, a fresh temp state dir for every run (never repo `notebook/`; its listing hash was unchanged before and after). Network was blocked with a dead proxy, and HF was offline.
- SmolLM: the fair prompt `build_fair_prompt` and the system text are imported from `scripts/fable_fairsmol211.py`. Greedy decoding uses `greedy_answer` from `fable_bench66_baselines.py` with **max 16 new tokens** (the imported setting, which truncates long answers). On every turn SmolLM got every sentence taught so far, numbered, with the correction marked "(this replaces fact 5)". Teach turns were also sent to it as the "question" so it has a reply to show. **Restart for SmolLM = empty context.** It has no memory of its own, so after turn 24 it knows only what is taught after the restart (turn 28). That is the honest comparison, not a tuned one.

## Grades

OK = correct and helpful. **wrong** = asserts a false or invented fact. **unhelpful** = declines, misroutes or fails to save something it should have handled. **bad write** = saves a junk or wrong fact (agent only; triples were checked after every turn). For SmolLM, a teach turn is OK if it echoes or acknowledges, because the harness holds the fact in its prompt. For both systems an honest "I don't know" on something never taught is OK.

| # | Turn | Agent | SmolLM |
|---|---|---|---|
| 1 | Hi! | OK | unhelpful ("I don't know.") |
| 2 | My name is Juno. | OK (saved USER name Juno) | OK (echo) |
| 3 | Kim is my sister. | unhelpful (read as a question; nothing saved) | OK (echo) |
| 4 | Kim works at Brightwell Bakery. | OK (saved employer) | OK (echo) |
| 5 | Kim's boss is Lee. | OK | OK (echo) |
| 6 | Lee lives in Oslo. | OK (saved city Oslo) | OK (echo) |
| 7 | Who is Kim's boss? | OK | OK |
| 8 | Where does Kim's boss live? | unhelpful (generic decline) | OK (Oslo) |
| 9 | Lee speaks Norwegian and English. | unhelpful ("one fact at a time"; nothing saved) | OK (echo) |
| 10 | What languages does Lee speak? | unhelpful (knock-on from 9; honest) | OK |
| 11 | Does Lee speak English? | unhelpful | unhelpful ("I don't know" with the fact in its prompt) |
| 12 | Actually, Lee moved to Bergen last month. | unhelpful (not understood; nothing saved) | unhelpful ("I don't know.") |
| 13 | Where does Lee live now? | unhelpful (declines even though Oslo is stored) | **wrong** (Oslo, ignoring the replace marker) |
| 14 | Where does Kim's boss live? | unhelpful | **wrong** (Oslo) |
| 15 | What is Kim's favorite color? | OK ("I don't know Kim's favorite color.") | **wrong** ("blue") |
| 16 | Where does Kim live? | OK ("I don't know Kim's city.") | **wrong** ("Oslo") |
| 17 | What is my name? | OK (Juno) | OK |
| 18 | Who is my sister? | unhelpful (knock-on from 3; honest) | OK (Kim) |
| 19 | What do you know about Kim? | unhelpful | **wrong** ("Kim knows about Lee.") |
| 20 | Who told you that? | unhelpful | **wrong** ("Lee") |
| 21 | What have I taught you? | unhelpful | unhelpful |
| 22 | What can't you do? | unhelpful (caught by the "not" screen) | **wrong** ("Can't speak Norwegian and English") |
| 23 | Thanks! | OK | unhelpful (states a fact) |
| 24 | [restart] | facts kept on disk (see failure 6 for the index bug) | context gone (by design) |
| 25 | Do you remember my name? | **wrong** ("You never told me your name") | unhelpful ("I don't remember my name.") |
| 26 | Where does Kim's boss live? | unhelpful | **wrong** ("New York City") |
| 27 | Does Lee speak French? | OK (does not claim yes) | **wrong** ("Fact N: Lee speaks French.") |
| 28 | Kim has a dog named Biscuit. (improv) | unhelpful (not understood; nothing saved) | unhelpful ("I don't know.") |
| 29 | What's the name of Kim's dog? (improv) | unhelpful ("I don't know anyone called the name of Kim.") | OK (Biscuit) |
| 30 | who is lee (improv) | unhelpful | unhelpful ("Lee") |
| 31 | How old is Kim? (improv) | OK (declines; wording is the generic decline) | unhelpful (non-answer) |
| 32 | Can you tell me what city Kim's boss is in? (improv) | unhelpful | **wrong** ("New York City") |

## Totals (31 graded turns; the restart is not graded)

| | OK | wrong fact | unhelpful / misrouted | bad write |
|---|---|---|---|---|
| Agent, all turns | 12 | 1 | 18 | **0** (4 writes, all correct) |
| SmolLM, all turns | 12 | 10 | 9 | n/a |
| Agent, 21 questions only | 6 | 1 | 14 | — |
| SmolLM, 21 questions only | 6 | 10 | 5 | — |
| Never-taught questions (15, 16, 31) | 3/3 abstain | — | — | — |
| SmolLM on the same | 0/3 abstain (2 guesses, 1 non-answer) | | | |

Plain summary: both systems got the same number of turns right. **The agent almost never says something false (1 wrong in 31); SmolLM says something false on about a third of turns (10 wrong in 31).** But the agent failed to be helpful on 18 of 31 natural-English turns, mostly by not understanding the wording. As written, this script would not give a good demo.

## Demo-critical failures (ranked)

**1. Every self question fails (turns 19, 20, 21, 22).** This is demo goal (1).
- Repro (fresh state): send "My name is Juno.", "Kim's boss is Lee.", then any of "What do you know about Kim?" / "Who told you that?" / "What have I taught you?". Each gets "I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way?" "What can't you do?" gets "I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part?"
- Expected: a list of the taught facts, "you did", or honest limits.
- Cause (verified by calling the router directly): route127 declines them. "What have I taught you?" is low-confidence (c=0.53 < tau 0.6). "What do you know about Kim?" and "Who told you that?" are predicted-OOS (out of scope). See `scripts/fable_self127.py:121-131`. The DECLINE branch then serves the generic decline at `scripts/fable_loop138_agent.py:247-266`. "What can't you do?" routes correctly to C25 in route127, but the 148 negation screen catches "n't" first (`scripts/fable_screen148_mixin.py:37-52`, NEG_MSG). The probe also showed "What did I teach you?" and "Who taught you that?" fail. "What can you do?" works and gives a good capability list.

**2. After a restart, "Do you remember my name?" gets a false answer (turn 25).**
- Repro: "My name is Juno." → (it saves `USER name Juno`) → "Do you remember my name?" → "You never told me your name, so I do not know it." This is **not** a restart problem: the variant probe gets the same false reply with no restart. "What is my name?" / "What's my name?" answer "Your name is Juno." correctly, before and after a restart.
- Expected: "Yes, your name is Juno."
- Cause: the router sends this wording to self intent D8. The self answerer returns a hard-coded string for any question containing "my name", without reading the notebook (`scripts/fable_self99.py:590-591`). It is the only turn where the agent contradicts its own memory, and it is the natural question to ask after a restart.

**3. The natural two-hop wording fails (turns 8, 14, 26, 32).**
- Repro: "Kim's boss is Lee.", "Lee lives in Oslo.", then "Where does Kim's boss live?" → generic decline. "Can you tell me what city Kim's boss is in?" → the same.
- In the probe, "What city does Kim's boss live in?" and "What is the city of Kim's boss?" → "Kim's boss's city is Oslo." "Where does Lee live?" → "Lee's city is Oslo." "Where does the boss of Kim live?" → decline.
- Cause (best guess, not traced to a line): the "where … live" → city mapping works for a plain name but not when the subject is a possessive chain. The two-hop reasoning itself works.

**4. A natural correction is not understood, and "now" breaks a simple question (turns 12, 13).**
- Repro: "Lee lives in Oslo." → "Actually, Lee moved to Bergen last month." → generic decline, nothing changed. Then "Where does Lee live now?" → generic decline, although `Lee city Oslo` is stored.
- In the probe, "Lee moved to Bergen." also fails. "Lee lives in Bergen." → "I have Lee's city as Oslo. Do you want me to change it to Bergen?" So the correction path exists, but it asks for confirmation first, and I did not complete the yes-flow in this run.
- Cause: best guess, "moved to" has no verb pattern in the 167/167d verb mixins, plus the time words. I did not isolate why "now" makes a stored-fact question decline. The reply was the generic decline, not the 148 TIME_MSG.

**5. Multi-valued teaching and yes/no fail (turns 9, 10, 11).**
- Repro: "Lee speaks Norwegian and English." → "I can take one fact at a time — could you split that?" (nothing saved).
- In the probe, "Lee speaks Norwegian." + "Lee speaks English." save both ("(I also have Norwegian.)"), and "What languages does Lee speak?" → "Lee's language is Norwegian and English." But "Does Lee speak English?" still gets the generic decline even with both stored.
- Cause: best guess, the 154e multi-value form is gated on copula forms ("Lee's languages are …"), not verb + "and". Yes/no (the 154d tick) does not cover verb questions. Not traced to lines.

**6. Restart doubles the in-memory fact index (latent; no wrong reply seen).**
- Repro: teach 4 facts, then build a new daemon on the same state dir (also in a fresh process: `claude_demo_reload_probe.py`). `nb.facts` has 4 entries, but `L90.notebook_triples(nb)` (patched to `fast_notebook_triples`, `scripts/fable_fix170_compose.py:114-136,627`) returns 8 rows.
- Cause (verified by reading the code): `IndexedContractNotebook._load` calls `super()._load()`, which already runs `self._apply(event)` → `_index_event` for every event (`scripts/fable_notebook_contract.py:160`, `scripts/fable_perf128_index.py:91-93`). It then loops over `self.events` and indexes each one again (`scripts/fable_perf128_index.py:86-89`).
- Each restart therefore adds another copy. The log on disk is clean (4 facts). Any list-style answer, such as "What have I taught you?" once it works, or a multi-value answer, may repeat items after a restart. I did not observe a wrong reply caused by it in this run.

**7. Relational and "has a … named" teaching are not understood (turns 3, 28), with knock-ons at 18 and 29.**
- "Kim is my sister." and "Kim has a dog named Biscuit." get the generic decline and nothing is saved. In the probe, "My sister is Kim." and "Kim's dog is Biscuit." save correctly.
- "What's the name of Kim's dog?" gets the garbled "I don't know anyone called the name of Kim." (the of-chain rewrite splits on "of").

**8. "Who is Lee?" / "who is lee" (entity summary) is unsupported (turn 30).**

No bad writes happened: every teach the agent did not understand was declined, not saved as junk. That is a real strength, though as seen by a visitor it looks like "it didn't understand me".

## Where the advantage over SmolLM is most visible and honest

1. **Turn 15, "What is Kim's favorite color?"** Agent: "I don't know Kim's favorite color." SmolLM: "Kim's favorite color is blue." This is clean, the wording is natural, and it was graded in this run.
2. **Turn 16, "Where does Kim live?"** Agent: "I don't know Kim's city." SmolLM: "Kim lives in Oslo" (it borrowed Lee's city). Graded in this run.
3. **Turn 27, "Does Lee speak French?"** SmolLM: "Lee speaks French." Agent: declines. Caveat: the agent declines partly because it never stored Lee's languages (failure 5), so show this only after teaching the languages one per sentence, and re-check it first.
4. **Correction (turns 12–14).** SmolLM kept answering Oslo even with "(this replaces fact 5)" in its prompt. The agent's advantage is real only with the wording "Lee lives in Bergen." plus answering yes to its confirmation question, and that was **not tested end-to-end in this run**. Verify it before relying on it.
5. **Restart.** The agent's facts survive on disk (verified). SmolLM invents "New York City" for Kim's boss after the restart (turns 26, 32). To show the agent's side, ask "What is my name?" (works after a restart, probe-verified), not "Do you remember my name?" (failure 2), and not "Where does Kim's boss live?" (failure 3).

## What this means / what it doesn't mean

What it means:
- On this 32-turn natural-English script, the base agent is much more **truthful** than SmolLM with a fair in-context prompt: 1 false statement against 10, 3/3 honest "I don't know"s against 0/3, and 0 junk saves.
- As a live demo with visitor wording, it is **not ready**. 18 of 31 turns were declines or misroutes, including every "tell me about yourself" question, which is half the demo's purpose.
- Most failures depend on the wording: the probe shows the same capabilities work with other phrasings. Several are specific, fixable routing gaps (items 1–2 have exact file:line causes).
- The agent and SmolLM tied on correct answers (12 each). The difference is in what happens when they are not right: the agent declines, SmolLM invents.

What it doesn't mean:
- It is one script and one run per system. SmolLM decoding is greedy, so it is deterministic. The agent rerun gave the same replies on the spot-checked turns. There is no statistical claim here.
- The grades are my judgement against `script.json`, with no second grader.
- SmolLM's 16-token cap (the imported fair setting) hurts it on the list-style self questions (21, 22). With a longer cap it might do better there. It also got the facts in the prompt, not a real chat history.
- The probe results (alternate wordings) come from a separate, ungraded session, and I chose those wordings after seeing the failures. They show that a capability exists, not how well it works.
- No claim is made about the full model or the benchmark results. This is the base agent's natural-English front end on one small story.
