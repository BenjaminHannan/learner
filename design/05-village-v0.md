# 05 — Village v0: what happens in the world (AGREED with Ben, 2026-09-18)

This document is the list of everything that can happen in the first version of the village. It defines what the model reads during childhood (Step 1), what Bonsai writes sentence patterns for (B), and what the oracle can grade. Anything not listed here does not exist in v0.

**Guiding rule:** the oracle must know the exact right answer to every question. So in v0, everything is deterministic (no randomness inside a rule) and every event changes a tracked state.

---

## 1. What a village contains

| Thing | v0 range | Notes |
|---|---|---|
| Grid | 6×6 to 10×10 cells | Places sit on cells. Directions (north/south/east/west) and "next to" come from the grid. |
| Places | 6–12 per village | Common nouns (barn, mill, well, market, …) from a fixed list of about 40. |
| People | 5–12 per village | Fresh made-up names built from syllables. Names are bursty: a few people appear constantly, most rarely. Train, validation and test villages use **separate name pools**. |
| Objects | 8–20 per village | Common nouns (cup, key, rope, …, about 60 types), with a **colour** (8) and a **material** (glass, wood, iron, cloth, clay, stone). Each object may have an **owner**. |
| Containers | 2–4 per village | box, basket, chest, sack. They can be open or closed and carry their contents when moved. |
| Village rules | 1–3 per village | Made-up rules drawn from the rule families in §3. They differ between villages, and this is how the model has to learn new rules. |
| Time | morning / noon / evening / night, then the next day | Some rules fire at a time of day. |

## 2. Universal events (the same in every village)

| # | Event | State change | Example narration (Bonsai will write many per event) |
|---|---|---|---|
| E1 | go | person moves to a place | "Kelo walked to the mill." |
| E2 | pick up | person now holds an object at their place | "Rami picked up the red cup." |
| E3 | put down | object is left at the person's place | "Rami left the cup by the well." |
| E4 | give | object passes to another person in the same place | "Tosa handed the key to Vemi." |
| E5 | put in / take out | object goes into or out of an open container | "Nuba put the rope in the chest." |
| E6 | open / close | container becomes open or closed | "Kelo shut the basket." |
| E7 | carry container | the container and **everything inside it** move with its holder | "Vemi carried the sack to the barn." |
| E8 | swap | two people exchange what they are holding | "Rami and Tosa traded." |
| E9 | time passes | the time of day advances, and rules tied to times fire | "Night fell." / "The next morning…" |
| E10 | fail | a blocked action does not happen, and the narration says so | "Kelo tried to open the chest, but it would not open." |

E10 exists so the model sees attempts that fail. Otherwise every sentence would be a true state change, and "tried to" would be a cue it could exploit.

## 3. Village rule families (made-up rules)

Each family generates many concrete rules with random parts. A village gets 1–3 rules. The teacher either **states** a rule or only **shows** it through events, in which case the model has to induce it.

| Family | Template of a rule | Concrete example |
|---|---|---|
| R1 property effect | things made of M do X when action A happens | "In Zobaki, glass things break when dropped." |
| R2 follower | person P goes wherever person Q goes | "Tavi always follows Nera." |
| R3 place effect | objects left at place L move to place L2 at time T | "Anything left at the well is taken to the market at night." |
| R4 return to owner | lost objects return to their owner at time T | "Lost things find their owner by morning." |
| R5 container effect | objects put in container C become colour K | "Whatever goes in the blue box turns green." |
| R6 permission | only person P may do action A to thing X | "Only Rami can open the chest." |
| R7 schedule | person P goes to place L at time T every day | "Every noon, Kelo goes to the mill." |
| R8 exchange | at place L, N of object X can be traded for one of object Y | "At the market, two cups buy a lamp." |
| R9 chain | two rules from different families, where one triggers the other | "R3 + R5: the well sends things to the market, and the market basket turns them gold." |

**Held out for testing (agreed):** R8 exchange and R9 chain never appear in training villages. Validation gets R8 and test gets R9, or the reverse. Both reuse the pieces the model has seen (places, counting, other rules), so they test **combining** old knowledge, which is the bike→car kind of transfer Ben wants.

## 4. What the teacher does

| Act | What it looks like | What it trains | Reliability tier |
|---|---|---|---|
| T1 state | "Remember: the key is in the barn." (optionally flagged *remember*) | one-shot facts → cards | oracle (it is true) |
| T2 ask | "Where is the red cup?" | answering from memory | — |
| T3 feedback | "Right." / "No — it's in the mill." | corrections and versions ("used to") | oracle |
| T4 demonstrate | a rule, step by step with a worked example | skills: imitation and copying | oracle for facts, Bonsai for wording |
| T5 change | "Kelo moved away; he lives by the pond now." | updating while keeping the history | oracle |
| T6 quiz later | the same fact asked after a delay (short, long, after sleep) | retention and forgetting | — |
| T7 explain | free text from Bonsai ("Glass is fragile, so…") | language only, **never used as a fact target** | Bonsai (tier 3) |

## 5. Question types (all graded by the oracle)

| # | Question | Answer |
|---|---|---|
| Q1 | where is X now (object or person) | place, or "with P", or "in C" |
| Q2 | who has X | person or "nobody" |
| Q3 | what is in C | list of objects, or "nothing" |
| Q4 | where was X before / at time T | place (history, "used to") |
| Q5 | how many X at L / held by P | number 0–9 |
| Q6 | which way from L to L2 / what is next to L | direction or place |
| Q7 | what happens if … (hypothetical) | result of applying a rule the model has been told or shown |
| Q8 | what is the rule about M / P / L in this village | rule stated in canonical form |
| Q9 | yes/no versions of Q1–Q7 | yes / no |
| Q10 | a question whose answer was **never shown** | "not told" |

Q10 matters: it gives the model an honest "I don't know" to learn, and it lets us measure made-up answers (hallucination) and calibration. The oracle tracks what the model has actually seen, not only the true state.

### 5b. Added for reasoning (Ben's first priority)

| # | Question | Answer | Why it matters |
|---|---|---|---|
| Q11 | why is X at L? | the cause, in canonical form ("it was left at the well at night") | tracing cause and effect backwards |
| Q12 | how could P get X? | a short plan of actions; **the oracle checks it by acting it out**, so any working plan counts | planning, and the bridge to acting later |
| Q13 | are there more X at L or at L2? | place | comparison |
| — | groups of things | objects belong to groups (dishes, tools, clothes, toys, food) and rules can name a group ("dishes break when put down") | abstraction: applying a rule to a thing never seen with that rule |

**Reasoning depth:** the simulator records how many inference steps each question needs (for example, cup in a box → box carried by Kelo → Kelo follows Rami → where is the cup = 3 steps). Training sees depths 1–3; validation and test also include depths 4–6. Passing on longer chains than it trained on shows that it reasons step by step and has not memorised shortcuts.

Every question has a **counterfactual twin**: same wording, different history, different answer (as in Step 0).

## 6. Held-out axes (what is never seen in training)

Following the Step 0 bench, every one of these is split train / validation / test, and the splits are recorded in a manifest that is checked on every run:

1. Name pools (people and villages)
2. Narrator templates (Bonsai sentence patterns, split per event type)
3. Teacher styles (proposed 10 styles: plain, cheerful, terse, storyteller, formal, questioning, childlike, grandparent, bossy, poetic; 6 train / 2 validation / 2 test)
4. Rule families (R8/R9 held out, see §3)
5. Update families from Step 0 (direct, moved, corrected, chained, swapped, restated)

The Step 1 gate is: ≥ 90% on visible-text questions with **held-out templates, styles and rule families**; counterfactual pairs above chance; leak detectors clean; a forgetting baseline recorded.

## 7. The stream the model reads

One continuous text stream per "life", with tags (these are atomic tokens in the tokenizer):

```
[world] Night fell. Anything left at the well was taken to the market.
[teacher] Remember: only Rami can open the chest.
[question] Who can open the chest? [answer] Rami [feedback] Right.
[think] … [done]      (from Step 6; the model writes these itself)
[sleep]               (from Step 5; marks a sleep phase)
```

A village runs for a number of days, then the stream moves to another village. Villages come back later (so memory across time is tested), and new villages keep arriving (so transfer is tested).

## 8. What Bonsai writes (task B, after this list is approved)

- **Narrator patterns:** about 40 per event type (E1–E10) and 20 per rule family phrasing, with exact placeholders such as `{person} {object} {place}`. Each is checked mechanically: the placeholder set is exact and it adds **no new fact words** (no extra places, colours or names). Rejects are regenerated.
- **Teacher patterns:** each act T1–T6 × 10 styles, with the same checks.
- **Explanations (T7):** short, simple-English text; language only.
- Estimated time on the Mac at about 12 tok/s: roughly 3–6 hours for the whole bank, run in the background.

## 9. Speed requirement

The world must never slow training down by more than 5%. The 4M model trains at about 1.2M tokens/s, which a single Python simulator cannot match. Plan: parallel simulator processes on BensPC's 12 threads, streaming token shards ahead of the trainer; measure world tokens/s before Step 1 starts and scale the number of processes to fit.

---

## Decisions for Ben

1. **"Not told" answers (Q10):** **AGREED (Ben, 2026-09-18): included from v0.**
2. **Beliefs** ("where does Kelo *think* the key is?"): **AGREED: v1, not v0.**
3. **Randomness inside rules:** **AGREED: v0 is deterministic; probabilistic rules come in v1.**
4. **Held-out rule families:** **AGREED: R8 exchange and R9 chain are never in training.**
5. **Priorities (Ben): reasoning first, language second.** Talking to it is a nice extra that can be traded away. Added for reasoning (see §5b): why questions, planning questions checked by the oracle, comparisons, groups of things, and a reasoning-depth axis with held-out depths.
