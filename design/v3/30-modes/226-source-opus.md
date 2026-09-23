# 226 — "Who told you that?" (source questions about the last reply)

## Problem
On loop138i, after "Kim lives in Oslo." → "Saved: Kim's city is Oslo.", the question "Who told you that?" got the glued decline ("I do not know that from what you taught me … could you say it another way?"). Meanwhile the capability sheet says the assistant can "tell you where each fact came from", which was false in practice.

## The one change
`scripts/fable_loop226_agent.py` = loop138i + one outer loop layer, `Source226Mixin`. Nothing else in the pipeline changes and nothing new is stored in the notebook.

1. **Record what the last reply used.** After every normal turn the loop writes down (in memory only) which notebook facts the reply stated or used. The list comes from what the pipeline did, not from reading the reply's words:
   - **Saved**: a write record with `wrote=True` plus the new active taught facts that appeared in the notebook during that turn.
   - **Answer**: the reasoner's own `trail` (the fact ids of the notebook path it walked). It is only accepted when it matches the record: one fact per hop, relations in order, each hop's value is the next hop's subject, and the last value equals the answer (multi-valued answers: every value listed, and nothing more).
   - **Name check** ("Is Juno my name?"): the reasoner record captured while the base answers it.
   - **Yes/no** (154d) and **worked out backwards** (153 reverse questions): these stages leave no record, so the layer re-runs the stage's own pure function on the same notebook and accepts it only if it gives exactly the reply that was said. It then takes the facts that function read. (The stage tag cannot be trusted: 154d writes it on the outer ears wrapper, so it goes stale.)
   - **No fact**: the base's DECLINE route, an answer with an empty trail (MISSING_FACT / UNKNOWN_ENTITY), a forget, a first turn, a turn after a restart, or any other reply that mentions no stored name and no stored value. These give the "no fact" reply.
   - **Untraced**: everything else, for example self-router replies that might quote notebook content. These give an honest "I can't say" reply.
2. **Answer source questions.** A closed list of 19 normalised templates (lower-case, curly quotes made straight, trailing `?.!` and spaces removed, then an exact match): "who told you that", "how do you know (that/this)", "where did you learn/get/hear that", "who said that", "what's/what is your source (for that)", "says who", "where did that come from", and a few more. It never matches on keywords. The question is caught at the start of the listening tick, before the ears run, so it cannot write. The counters, the experience log and the turn log get the same entries a normal clarify turn would get. The record is left alone, so asking twice gets the same answer.

## Replies (each one only says what the notebook holds)
| last reply | answer |
|---|---|
| saved a fact | You did — you just told me Kim's city is Oslo. |
| one taught fact / multi values / yes-no | You told me: Kim's city is Oslo. |
| chain (2+ hops) | I put together things you told me: Kim's boss is Lee. Lee's city is Bergen. |
| reverse (never stored) | Nobody told me directly; I worked it out backwards from what you told me: Kim's boss is Lee. |
| web / sleep / inferred rows | the stored provenance (URLs, "worked out during sleep", the facts it was inferred from); if the notebook holds no provenance, the untraced reply |
| no fact / first turn / restart | I'm not sure what "that" means — I haven't just told you a fact. |
| untraced | I can't say where that came from — I didn't keep track of which notes that reply used, so I won't guess. |

"Taught" means `source == "taught"` and `actor == "listening"`. A fact is rendered as "<subject>'s <relation> is <value>". The single user's facts render as "your …".

## Limits
- The record lives in memory, so a restart forgets it. That is deliberate: after a restart there is no "last reply" to point at.
- Web and sleep-derived answers cannot be produced through dialogue on the base in these sessions. That provenance wording is written but not tested by sealed cases.
- Self-router answers (for example "What did I teach you last?") get the untraced reply, not their source.
- The "no fact" test for otherwise unclassified replies uses a whole-word check for stored names and values. It is only used to choose between the two replies that make no claim about a source.

Files: `scripts/fable_loop226_agent.py`, `scripts/fable_source226_cases.py`, `scripts/fable_source226_run.py`, `artifacts/fable-source226-20260922/`.
