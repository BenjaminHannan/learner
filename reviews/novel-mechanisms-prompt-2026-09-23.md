# Prompt for Ben to relay: novel brain-inspired mechanisms (2026-09-23)

Ben asked (19:11-19:14 UTC) for a concise, self-contained prompt instead of a workflow.

```
I'm building Premonition, a small helpful assistant meant to copy the brain's strengths and beat them wherever possible. Top priority: reasoning.

What exists now:
- Reader: a fine-tuned 1B transformer (MiniCPM5-1B + LoRA) turns each chat message into typed facts (owner, relation, value).
- Notebook: an exact, append-only fact store. Each fact keeps its source sentence and history; corrections add, never erase. Only facts the user taught can answer questions.
- Reasoner: hand-written code that chains up to 3 lookups, answers backwards and yes/no questions, and says "I don't know" instead of guessing. I want to replace it with a learned neural reasoner, trained mostly by reinforcement learning.
- Sleep: an offline phase that today only learns a few routing numbers for new relation words.
- Mouth: the same 1B base, speaking only from checked facts.
My worry: this is standard parts plus a notebook. I want genuinely new mechanisms.

Task: propose 8 mechanisms that do NOT appear in published work. Search to confirm; if something close exists, name it and say exactly what is new. Rank them by how much they would improve reasoning.

For each:
1. The mechanism in plain words, and which brain ability it copies or beats.
2. Why it should improve reasoning (multi-step chains, handling relations it never saw, knowing when it doesn't know).
3. The closest prior work and the difference.
4. One single-change experiment that fits a 1B model on one RTX 5070 Ti or about $30 of rented GPU: what changes, pass marks fixed in advance, and the result that would prove the idea wrong.

Label every claim shown / suggested / untested. Every idea must keep these rules: never save a wrong fact, never guess (say "I don't know"), taught facts stay exact.
End with a plain-language summary for a high-school senior.
```
