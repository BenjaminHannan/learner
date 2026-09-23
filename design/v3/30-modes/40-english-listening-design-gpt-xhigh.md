Use the 27B Qwen only as **English ears**. It should never touch the notebook directly: Qwen proposes a typed interpretation, deterministic software rejects unsafe interpretations, then the existing `Listening.hear()` remains the only path that can write a taught fact.

Two tiny additions to the structured listener are needed to fully meet your requirements:

1. **JSON-quoted atoms** for multi-word names/values:  
   `teach "Mary Jane" city = "New York"`
2. **`undo last`**, implemented as an append-only retraction/restoration event, never deletion of history.

Everything else can sit in front of your current listener.

## 1\. Prototype architecture

```
Ben speaks English
      ↓
Qwen 27B "ears"
      ↓
JSON-schema constrained intent
      ↓
DETERMINISTIC VALIDATOR
  • schema
  • copy constraint
  • relation normalization
  • question/hypothetical/negation guards
  • pending-state legality
  • confidence
      ↓
0..N structured lines
      ↓
confirmation gate, if needed
      ↓
Listening.hear(line)
      ↓
NOTEBOOK
      ↓
existing truthful template reply
      ↓
optional cosmetic verbalizer
```

The important boundary is:

```
Qwen ──X──> Notebook
Qwen ──X──> "Saved"
Qwen ──X──> entity IDs chosen from imagination

Qwen → proposal → deterministic validator → Listening → Notebook
```

### Pronouns

Use two permanent notebook entities:

- `Ben` = first person: `I`, `me`, `my`, `mine`
- `self` = the system: `you`, `your`, `yourself`

So:

```
I live in Hanover.
→ teach Ben city = Hanover

What is my mother's city?
→ ask Ben mother city

What were you trained on?
→ ask self training_data
```

`self` is ordinary notebook knowledge. If `self.training_data` has never been taught, the system should simply say it does not know.

Third-person pronouns are intentionally stricter:

```
Mira lives in Lisbon. She works at Acme.
```

may resolve `She → Mira`, because `Mira` occurs in the same utterance.

But:

```
She works at Acme.
```

with no explicit antecedent becomes `unsure`, not a guess.

### Relation normalization

I would make a small permanent normalization registry:

| English | Stored key |
| --- | --- |
| lives in, resides in, moved to | `city` |
| is from, comes from | `origin` |
| was born in | `birthplace` |
| mother, mom | `mother` |
| father, dad | `father` |
| works at, works for | `employer` |
| trained on, training data | `training_data` |
| made, created by | `creator` |
| favorite colour/color | `favorite_color` |

Crucially, **`lives in` and `is from` should not both mean `city`**:

```
Mira lives in Boston.
→ city = Boston

Mira is from Chicago.
→ origin = Chicago
```

For an unseen relation, Qwen may propose lowercase snake case derived from an exact copied phrase, but the adapter should require confirmation the first time. That prevents `attends_school`, `school`, `goes_to_school`, etc. from silently becoming three relations.

### Multiple facts

One sentence can emit multiple items:

```
Mira lives in Lisbon and works at Acme.
```

becomes:

```
teach Mira city = Lisbon
teach Mira employer = Acme
```

I would echo-confirm a multi-write bundle before committing it.

### Small talk

Small talk returns zero structured lines:

```
"Thanks!"
"How are you?"
"That's funny."
→ []
```

Do not turn it into `quote`; `quote` is useful specifically for language that contains apparent factual content that must **not** become a fact.

* * *

## 2\. Write safety

The parser should be optimized for **precision over recall**. Missing one fact is annoying. Silently teaching a false fact is much worse.

### Copy constraint

Every entity name and factual value emitted by Qwen must literally occur in Ben's utterance, ignoring case.

Exceptions are only:

- `I/my/me` → reserved `Ben`
- `you/your` → reserved `self`
- an `E####` chosen from the currently displayed pending ambiguity choices

Thus:

```
Ben: Mira lives in Lisbon.
```

Qwen output containing:

JSON

```
{"subject":"Maria"}
```

is rejected even if `Maria` exists in the notebook.

`known_names` helps Qwen understand text. It **does not authorize it to emit absent names**.

### Deterministic non-write guards

Even valid JSON is rejected if Qwen attempts a write from:

- a question,
- reported speech,
- a hypothetical,
- unsupported negation,
- an invented span,
- an implicit correction with no correction language.

Examples:

```
If Mira lived in Paris...
Mira said she lives in Paris.
I heard Mira works at Acme.
Mira doesn't live in Paris.
```

must not produce `teach`.

Grammar-constrained decoding is useful because it makes syntactically malformed output much harder, but valid JSON can still contain a semantically wrong action; that is why the validator remains necessary. XGrammar is recent evidence that this kind of constrained structured generation can be made very efficient. [arXiv](https://arxiv.org/abs/2411.15100?utm_source=chatgpt.com)

### When to echo-confirm

**Do not add another confirmation** for:

- one direct, high-confidence ordinary fact;
- an explicit high-confidence correction such as `"Actually..."`;
- a direct `forget`;
- questions;
- quotes;
- single-person creation;
- yes/no/pick responses.

Your existing Listener still catches conflicting existing values and ambiguous entities.

**Do confirm** when:

- ≥2 facts would be written from one utterance;
- confidence `< 0.98`;
- a previously unknown relation key is proposed;
- later, any new high-risk semantic construction you discover experimentally.

Example:

> I heard: Mira's city is Lisbon; Mira's employer is Acme. Save both?

The English adapter owns that pending bundle. An unrelated response cancels it.

### Corrections

A plain contradictory statement remains `teach`:

```
Mira lives in Paris.
→ teach Mira city = Paris
```

If Lisbon is already stored, **Listening** notices the conflict and asks.

Only explicit correction language becomes `correct`:

```
Actually Mira lives in Paris.
Wait, I meant Paris, not Lisbon.
Sorry—Ana is Mira's mother, not Bea.
```

That keeps the LLM from silently interpreting new information as permission to overwrite old information.

### Raw sentence

Every successfully committed fact should ultimately contain:

```
raw_utterance
parser_version
structured_line
source = taught
```

in notebook provenance.

Because your current interface is only `hear(line)`, the module below also writes a hash-chained raw-utterance sidecar. I would eventually move `raw_utterance` into the notebook event itself; the sidecar is an interim compatibility layer.

### Undo

`undo last` should mean:

> Append an event that reverses the last user-initiated committed transaction.

Not:

> erase the last record.

That preserves your append-only/history design.

* * *

# 3\. Exact parser prompt

This prompt plus the 12 semantic few-shots is under 900 tokens.

```
You are Fable's English ears. Convert the user's utterance into typed intents;
never answer it and never invent a name or value. Final output must match the
provided JSON schema.

A subject/value denoting a person must copy the exact surface name from the
utterance, except first person maps to Ben and second person maps to self.
Third-person pronouns may resolve only when their explicit antecedent occurs in
the same utterance; otherwise use unsure.

relation_surface must copy words from the utterance. relation_path contains
canonical keys. Normalize:
live/reside/moved-to→city; from/comes-from→origin; born→birthplace;
mom/mother→mother; dad/father→father; work-at/work-for→employer;
trained-on/training-data→training_data; made/created→creator;
favorite-colour/color→favorite_color.
Unknown relations become lowercase_snake_case of relation_surface.

Statements teach. Use correct only for explicit correction language such as
actually, I meant, correction, sorry, or "not X but Y". Questions ask.
Reported speech, hypotheticals, and unsupported negated facts use quote and copy
the complete utterance. Chit-chat uses smalltalk. Natural yes/no/pick is legal
only when pending_state exists. Multiple asserted facts become multiple items.
If uncertain, set unsure=true and emit no actionable item.
```

### 12 few-shots

```
1. Mira lives in Lisbon.
   → teach(Mira, city=Lisbon; surface="lives in")

2. Actually Mira lives in Paris.
   → correct(Mira, city=Paris; surface="lives in")

3. Mira's mother is Ana.
   → teach(Mira, mother→Ana; surface="mother")

4. Where does Mira's mother live?
   → ask(Mira, mother, city; surfaces="mother","live")

5. If Mira lived in Paris, she'd smile.
   → quote(full utterance)

6. Mira said she lives in Paris.
   → quote(full utterance)

7. Hi, how are you?
   → smalltalk

8. I live in Hanover.
   → teach(Ben, city=Hanover; surface="live in")

9. What were you trained on?
   → ask(self, training_data; surface="trained on")

10. Mary Jane lives in New York.
    → teach(Mary Jane, city=New York)

11. [pending yes/no] Yep, that's right.
    → yes

12. [pending E0002,E0007] The second one.
    → pick(E0007)
```

### Exact JSON schema

JSON

```
{
  "type": "object",
  "additionalProperties": false,
  "required": ["items", "unsure", "unsure_reason"],
  "properties": {
    "items": {
      "type": "array",
      "maxItems": 8,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "act",
          "subject",
          "relation_path",
          "relation_surface",
          "value",
          "value_kind",
          "alias",
          "canonical",
          "choice",
          "text",
          "confidence"
        ],
        "properties": {
          "act": {
            "type": "string",
            "enum": [
              "person",
              "alias",
              "teach",
              "correct",
              "ask",
              "forget",
              "quote",
              "yes",
              "no",
              "pick",
              "undo",
              "smalltalk",
              "unsure"
            ]
          },
          "subject": {"type": ["string", "null"]},
          "relation_path": {
            "type": "array",
            "maxItems": 8,
            "items": {"type": "string"}
          },
          "relation_surface": {
            "type": "array",
            "maxItems": 8,
            "items": {"type": "string"}
          },
          "value": {"type": ["string", "null"]},
          "value_kind": {
            "type": "string",
            "enum": ["literal", "person", "none"]
          },
          "alias": {"type": ["string", "null"]},
          "canonical": {"type": ["string", "null"]},
          "choice": {"type": ["string", "null"]},
          "text": {"type": ["string", "null"]},
          "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1
          }
        }
      }
    },
    "unsure": {"type": "boolean"},
    "unsure_reason": {"type": "string"}
  }
}
```

I prefer the slightly repetitive fixed schema over clever `oneOf` branches because it is easier for both llama.cpp's grammar machinery and your deterministic validator.

* * *

# 4\. Sixty-utterance test set

`∅` means no structured line.

| # | English | Expected |
| --- | --- | --- |
| 1 | Remember Mira as a person. | `person Mira` |
| 2 | Mira lives in Lisbon. | `teach Mira city = Lisbon` |
| 3 | Mira resides in Porto. | `teach Mira city = Porto` |
| 4 | Mira is from Madrid. | `teach Mira origin = Madrid` |
| 5 | Mira was born in Seville. | `teach Mira birthplace = Seville` |
| 6 | Mira works at Acme. | `teach Mira employer = Acme` |
| 7 | Mira's mother is Ana. | `teach Mira mother -> Ana` |
| 8 | My city is Hanover. | `teach Ben city = Hanover` |
| 9 | I'm from Boston. | `teach Ben origin = Boston` |
| 10 | My mother is Sara. | `teach Ben mother -> Sara` |
| 11 | Your creator is Ben. | `teach self creator -> Ben` |
| 12 | You were trained on my experiments. | `teach self training_data = "my experiments"` |
| 13 | Mary Jane lives in New York. | `teach "Mary Jane" city = "New York"` |
| 14 | José de la Cruz works at Bell Labs. | `teach "José de la Cruz" employer = "Bell Labs"` |
| 15 | Tommy is another name for Tom. | `alias Tommy = Tom` |
| 16 | Call Katherine Kate. | `alias Kate = Katherine` |
| 17 | Actually, Mira lives in Paris. | `correct Mira city = Paris` |
| 18 | Wait, I meant Porto, not Paris, for Mira's city. | `correct Mira city = Porto` |
| 19 | Sorry—Mira's mother is Ana, not Bea. | `correct Mira mother -> Ana` |
| 20 | Wait, Mira's in Lyon now, not Paris. | `correct Mira city = Lyon` |
| 21 | Mira lives in Rome. | `teach Mira city = Rome` |
| 22 | Mira lives in Lisbon and works at Acme. | `teach Mira city = Lisbon`; `teach Mira employer = Acme` |
| 23 | Ana is from Porto and her mother is Bea. | `teach Ana origin = Porto`; `teach Ana mother -> Bea` |
| 24 | Mira's mother is Ana, and Ana's mother is Bea. | `teach Mira mother -> Ana`; `teach Ana mother -> Bea` |
| 25 | I live in Hanover and I'm from Boston. | `teach Ben city = Hanover`; `teach Ben origin = Boston` |
| 26 | Where does Mira live? | `ask Mira city` |
| 27 | Where is Mira from? | `ask Mira origin` |
| 28 | Who is Mira's mother? | `ask Mira mother` |
| 29 | Where does Mira's mother live? | `ask Mira mother city` |
| 30 | Where is Mira's mother's mother from? | `ask Mira mother mother origin` |
| 31 | Where does Ana's mother work? | `ask Ana mother employer` |
| 32 | What is my mother's city? | `ask Ben mother city` |
| 33 | Where was my mother born? | `ask Ben mother birthplace` |
| 34 | What were you trained on? | `ask self training_data` |
| 35 | Who made you? | `ask self creator` |
| 36 | Where does your creator live? | `ask self creator city` |
| 37 | What city is Jordan in? `[Jordan ambiguous]` | `ask Jordan city` → Listening must clarify |
| 38 | Where does Alex live? `[Alex ambiguous]` | `ask Alex city` → Listening must clarify |
| 39 | If Mira lived in Paris, she'd be closer. | `quote If Mira lived in Paris, she'd be closer.` |
| 40 | Suppose Ana worked at Acme. | `quote Suppose Ana worked at Acme.` |
| 41 | Imagine I were from Rome. | `quote Imagine I were from Rome.` |
| 42 | Mira said, "I live in Lisbon." | `quote Mira said, "I live in Lisbon."` |
| 43 | Tom told me Ana's mother is Bea. | `quote Tom told me Ana's mother is Bea.` |
| 44 | I heard that Mira works at Acme. | `quote I heard that Mira works at Acme.` |
| 45 | Mira does not live in Paris. | `quote Mira does not live in Paris.` |
| 46 | Mira isn't from Spain. | `quote Mira isn't from Spain.` |
| 47 | My mother is not Ana. | `quote My mother is not Ana.` |
| 48 | Hi, how are you? | `∅` |
| 49 | Thanks! | `∅` |
| 50 | That's funny. | `∅` |
| 51 | `[pending yes/no]` Yep, that's right. | `yes` |
| 52 | `[pending yes/no]` Nope, don't change it. | `no` |
| 53 | `[pending choices E0002,E0007]` The second one. | `pick E0007` |
| 54 | `[pending choices E0002,E0007]` E0002. | `pick E0002` |
| 55 | `[no pending]` yes | `∅` |
| 56 | Forget Mira's city. | `forget Mira city` |
| 57 | Please forget where I'm from. | `forget Ben origin` |
| 58 | Undo that last save. | `undo last` |
| 59 | Mira lives in Lisbon. She works at Acme. | `teach Mira city = Lisbon`; `teach Mira employer = Acme` |
| 60 | She works at Acme. `[no antecedent]` | `∅` / `unsure` |

### Prototype pass mark

I would not use a single average score.

The gate should be:

- **0 unsafe writes out of 60. Any one = fail.**
- 100% of #39–47 produce no taught fact.
- 100% copy-constraint enforcement.
- 100% control legality for #51–55.
- at least **58/60 exact structured outputs** overall.
- identical result on three temperature-0 runs.

Then make a separate 300+ case adversarial paraphrase set before trusting it in normal conversation.

* * *

# 5\. Replacing Qwen with Ben's own ears/mouth

The best training-data strategy is **logical-form first**, not "ask Qwen to invent sentences and then ask Qwen what they mean."

Generate the known truth first:

```
teach Mira city = Lisbon
```

Then ask Qwen for many ways a human might naturally express exactly that meaning:

```
Mira lives in Lisbon.
Mira's living in Lisbon these days.
Lisbon is where Mira lives.
Mira currently lives over in Lisbon.
...
```

The label remains the original structured operation. Qwen never gets to decide the ground truth.

That is much cleaner.

### Dataset I would build

First target:

- **500k–1M ears examples**
- perhaps 30–80M natural-language tokens total
- 25–35% must be **non-writing negatives**
- aggressive generation of uncommon wording, punctuation, contractions, typos and multi-clause sentences

Rough mixture:

```
30% ordinary teaching
15% questions
10% 2-4 hop questions
10% corrections/conflicts
10% multi-fact statements
10% hypotheticals/reported speech/negation
5% pronouns
5% pending yes/no/pick
5% aliases/forget/undo/chit-chat
```

Do not repeatedly train later ears generations on their own generated language. Work on recursively model-generated data has shown loss of distribution tails under that sort of process, so preserve real/human/open-text phrasing and fixed original synthetic sources rather than continually resampling your student. [Nature](https://www.nature.com/articles/s41586-024-07566-y?utm_source=chatgpt.com)

Large-scale synthetic instruction generation itself is quite viable—the 2024 Magpie work generated millions of instructions from an aligned model—so using Qwen as a temporary data generator is reasonable; your logical-form-first labels make the setup safer than trusting it as both generator and judge. [arXiv](https://arxiv.org/abs/2406.08464?utm_source=chatgpt.com)

### Prevent template memorization

Split by **phrasing family**, not random sentence.

For example, if training includes:

```
Where does X live?
```

the held-out family contains:

```
What city is X based in?
X calls what place home?
Whereabouts is X living?
```

Also hold out:

- entire names;
- entire value sets;
- contractions;
- correction styles;
- possessive question syntax;
- relative clauses;
- two-sentence anaphora;
- filler/disfluencies;
- slang confirmation phrases;
- sentence ordering;
- punctuation styles.

If you randomly split paraphrases from the same generation family, you will badly overestimate generalization.

### Realistic model sizes

For this narrow job, I would start around:

```
Ears:
6–12M parameters

Mouth:
8–15M parameters

Shared language front/back end:
roughly 15–25M total
```

A 1–3M model is worth testing because experiments are cheap, but I would expect its English robustness to be the first bottleneck.

You probably do **not** need 30M just to map:

```
English → typed thought
```

The mouth can be somewhat larger because generating fluent English is harder than selecting a tiny structured semantic representation.

### Swap gate

Do not replace Qwen because the small model "seems good."

Require:

1. own ears achieve at least the Qwen prototype's score on the fixed 60;
2. zero unsafe writes;
3. own ears match or exceed Qwen on a **never-used held-out paraphrase-family test**;
4. same evaluation across three seeds;
5. length/hop tests explicitly include examples longer than training, because that is already your recurring failure mode.

I would want ≥97% exact intent+slot accuracy on a large held-out set and **effectively 100% precision on write decisions** before giving it automatic write permission.

### Keep these as software forever

Do **not** spend neural capacity learning:

- who has permission to write;
- append-only notebook transactions;
- hash chaining;
- provenance;
- conflict detection;
- entity IDs;
- alias uniqueness;
- ambiguous-name clarification;
- copy constraint;
- schema validation;
- confirmation transactions;
- raw-utterance logging;
- undo/retraction semantics;
- maximum-hop safety guard;
- pending-question cancellation.

Those are invariants, not intelligence.

The neural model should learn:

```
What did Ben mean?
What relation is this?
What information is relevant?
How should I reason?
How should I say the answer?
```

* * *

# 6\. `fable_listening_english.py`

The module below has no third-party dependencies. HTTP uses `urllib`; JSON uses `json`. `--selftest` performs no network calls.

The current M1 needs the two structured-language additions mentioned above—quoted atoms and `undo last`—for those paths to execute end-to-end.

Python

```
# fable_listening_english.py
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request


DEFAULT_BASE_URL = os.environ.get(
    "FABLE_LLM_BASE_URL",
    "http://127.0.0.1:18081",
)
DEFAULT_MODEL = os.environ.get(
    "FABLE_LLM_MODEL",
    "local-model",
)

ACTS = [
    "person",
    "alias",
    "teach",
    "correct",
    "ask",
    "forget",
    "quote",
    "yes",
    "no",
    "pick",
    "undo",
    "smalltalk",
    "unsure",
]

WRITE_ACTS = {
    "person",
    "alias",
    "teach",
    "correct",
    "forget",
}

PARSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["items", "unsure", "unsure_reason"],
    "properties": {
        "items": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "act",
                    "subject",
                    "relation_path",
                    "relation_surface",
                    "value",
                    "value_kind",
                    "alias",
                    "canonical",
                    "choice",
                    "text",
                    "confidence",
                ],
                "properties": {
                    "act": {
                        "type": "string",
                        "enum": ACTS,
                    },
                    "subject": {
                        "type": ["string", "null"],
                    },
                    "relation_path": {
                        "type": "array",
                        "maxItems": 8,
                        "items": {"type": "string"},
                    },
                    "relation_surface": {
                        "type": "array",
                        "maxItems": 8,
                        "items": {"type": "string"},
                    },
                    "value": {
                        "type": ["string", "null"],
                    },
                    "value_kind": {
                        "type": "string",
                        "enum": [
                            "literal",
                            "person",
                            "none",
                        ],
                    },
                    "alias": {
                        "type": ["string", "null"],
                    },
                    "canonical": {
                        "type": ["string", "null"],
                    },
                    "choice": {
                        "type": ["string", "null"],
                    },
                    "text": {
                        "type": ["string", "null"],
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                },
            },
        },
        "unsure": {
            "type": "boolean",
        },
        "unsure_reason": {
            "type": "string",
        },
    },
}


SYSTEM_PROMPT = r"""
You are Fable's English ears. Convert the user's utterance into typed intents;
never answer it and never invent a name or value. Final output must match the
provided JSON schema.

A subject/value denoting a person must copy the exact surface name from the
utterance, except first person maps to Ben and second person maps to self.
Third-person pronouns may resolve only when their explicit antecedent occurs in
the same utterance; otherwise use unsure.

relation_surface must copy words from the utterance. relation_path contains
canonical keys. Normalize:
live/reside/moved-to->city; from/comes-from->origin; born->birthplace;
mom/mother->mother; dad/father->father; work-at/work-for->employer;
trained-on/training-data->training_data; made/created->creator;
favorite-colour/color->favorite_color.
Unknown relations become lowercase_snake_case of relation_surface.

Statements teach. Use correct only for explicit correction language such as
actually, I meant, correction, sorry, or "not X but Y". Questions ask.
Reported speech, hypotheticals, and unsupported negated facts use quote and copy
the complete utterance. Chit-chat uses smalltalk. Natural yes/no/pick is legal
only when pending_state exists. Multiple asserted facts become multiple items.
If uncertain, set unsure=true and emit no actionable item.

Semantic examples:
1 Mira lives in Lisbon. => teach(Mira,city=Lisbon; surface="lives in")
2 Actually Mira lives in Paris. => correct(Mira,city=Paris)
3 Mira's mother is Ana. => teach(Mira,mother->Ana)
4 Where does Mira's mother live? => ask(Mira,mother,city)
5 If Mira lived in Paris, she'd smile. => quote(full utterance)
6 Mira said she lives in Paris. => quote(full utterance)
7 Hi, how are you? => smalltalk
8 I live in Hanover. => teach(Ben,city=Hanover)
9 What were you trained on? => ask(self,training_data)
10 Mary Jane lives in New York. => teach(Mary Jane,city=New York)
11 [pending yes/no] Yep, that's right. => yes
12 [pending E0002,E0007] The second one. => pick(E0007)
""".strip()


RELATION_MAP = {
    "city": "city",
    "town": "city",
    "live": "city",
    "lives": "city",
    "live in": "city",
    "lives in": "city",
    "reside": "city",
    "resides": "city",
    "reside in": "city",
    "resides in": "city",
    "move to": "city",
    "moved to": "city",

    "from": "origin",
    "is from": "origin",
    "come from": "origin",
    "comes from": "origin",
    "origin": "origin",
    "hometown": "origin",

    "born": "birthplace",
    "born in": "birthplace",
    "birthplace": "birthplace",

    "mother": "mother",
    "mom": "mother",
    "mum": "mother",

    "father": "father",
    "dad": "father",

    "work": "employer",
    "works": "employer",
    "work at": "employer",
    "works at": "employer",
    "work for": "employer",
    "works for": "employer",
    "employer": "employer",

    "trained on": "training_data",
    "training data": "training_data",
    "training_data": "training_data",

    "made": "creator",
    "made you": "creator",
    "created": "creator",
    "created by": "creator",
    "creator": "creator",

    "favorite color": "favorite_color",
    "favourite color": "favorite_color",
    "favorite colour": "favorite_color",
    "favourite colour": "favorite_color",

    "age": "age",
    "friend": "friend",
    "sibling": "sibling",
}

KNOWN_RELATIONS = set(RELATION_MAP.values())

REPORTED_SPEECH_MARKERS = (
    " said ",
    " says ",
    " told me ",
    " i heard ",
    " according to ",
    " claims ",
)


class ParseRejected(ValueError):
    """Model output failed a deterministic safety check."""


def blank_item(act: str, confidence: float = 1.0, **changes) -> dict:
    item = {
        "act": act,
        "subject": None,
        "relation_path": [],
        "relation_surface": [],
        "value": None,
        "value_kind": "none",
        "alias": None,
        "canonical": None,
        "choice": None,
        "text": None,
        "confidence": confidence,
    }
    item.update(changes)
    return item


def _snake(text: str) -> str:
    text = text.casefold().strip()
    text = re.sub(
        r"[^\w]+",
        "_",
        text,
        flags=re.UNICODE,
    ).strip("_")
    return text


def canonical_relation(surface: str) -> str:
    key = re.sub(
        r"\s+",
        " ",
        surface.casefold().strip(" .?!,:;\"'"),
    )
    return RELATION_MAP.get(
        key,
        _snake(key),
    )


def _contains(text: str, fragment: str) -> bool:
    return (
        isinstance(fragment, str)
        and bool(fragment)
        and fragment.casefold() in text.casefold()
    )


def _has_first_person(text: str) -> bool:
    return bool(
        re.search(
            r"\b(i|i'm|i’m|me|my|mine|myself)\b",
            text,
            re.I,
        )
    )


def _has_second_person(text: str) -> bool:
    return bool(
        re.search(
            r"\b(you|you're|you’re|your|yours|yourself)\b",
            text,
            re.I,
        )
    )


def _has_correction_cue(text: str) -> bool:
    t = text.casefold()

    if any(
        cue in t
        for cue in (
            "actually",
            "i meant",
            "correction",
            "sorry",
            "wait,",
        )
    ):
        return True

    padded = f" {t} "
    if " not " in padded and (
        " but " in padded
        or " now" in t
    ):
        return True

    return False


def _pending_ids(pending_state) -> set[str]:
    if pending_state is None:
        return set()

    try:
        raw = json.dumps(
            pending_state,
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        raw = str(pending_state)

    return set(
        re.findall(
            r"\bE\d{4,}\b",
            raw,
        )
    )


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


def _compact_known_names(known_names) -> list[str]:
    if known_names is None:
        return []

    if isinstance(known_names, dict):
        values = list(known_names.keys())
    elif isinstance(
        known_names,
        (list, tuple, set),
    ):
        values = list(known_names)
    else:
        values = [known_names]

    out = []

    for value in values:
        if isinstance(value, str):
            out.append(value)

        elif isinstance(value, dict):
            for key in (
                "name",
                "alias",
                "display_name",
            ):
                candidate = value.get(key)
                if isinstance(candidate, str):
                    out.append(candidate)

    return out[:200]


def _require_string(item: dict, key: str) -> None:
    value = item[key]

    if not isinstance(value, str) or not value:
        raise ParseRejected(
            f"{item['act']} requires non-empty {key}"
        )


def _require_none(item: dict, *keys: str) -> None:
    for key in keys:
        if item[key] is not None:
            raise ParseRejected(
                f"{item['act']}.{key} must be null"
            )


def _require_empty_relations(item: dict) -> None:
    if (
        item["relation_path"]
        or item["relation_surface"]
    ):
        raise ParseRejected(
            f"{item['act']} must not contain relations"
        )


def _require_relation_count(
    item: dict,
    low: int,
    high: int,
) -> None:
    n = len(item["relation_path"])

    if not low <= n <= high:
        raise ParseRejected(
            f"{item['act']} requires "
            f"{low}..{high} relation hops"
        )


def _validate_shape(
    doc: dict,
    utterance: str,
    pending_state,
) -> None:
    if not isinstance(doc, dict):
        raise ParseRejected(
            "top level must be an object"
        )

    expected_top = {
        "items",
        "unsure",
        "unsure_reason",
    }

    if set(doc) != expected_top:
        raise ParseRejected(
            "wrong top-level JSON fields"
        )

    if (
        not isinstance(doc["items"], list)
        or len(doc["items"]) > 8
    ):
        raise ParseRejected(
            "items must be an array of <= 8"
        )

    if not isinstance(doc["unsure"], bool):
        raise ParseRejected(
            "unsure must be boolean"
        )

    if not isinstance(
        doc["unsure_reason"],
        str,
    ):
        raise ParseRejected(
            "unsure_reason must be string"
        )

    item_fields = {
        "act",
        "subject",
        "relation_path",
        "relation_surface",
        "value",
        "value_kind",
        "alias",
        "canonical",
        "choice",
        "text",
        "confidence",
    }

    meaningful_acts = []

    for item in doc["items"]:
        if (
            not isinstance(item, dict)
            or set(item) != item_fields
        ):
            raise ParseRejected(
                "wrong item JSON fields"
            )

        act = item["act"]
        meaningful_acts.append(act)

        if act not in ACTS:
            raise ParseRejected(
                f"unknown act {act!r}"
            )

        confidence = item["confidence"]

        if (
            not isinstance(
                confidence,
                (int, float),
            )
            or isinstance(confidence, bool)
            or not 0 <= confidence <= 1
        ):
            raise ParseRejected(
                "confidence must be in [0,1]"
            )

        if item["value_kind"] not in {
            "literal",
            "person",
            "none",
        }:
            raise ParseRejected(
                "invalid value_kind"
            )

        if not isinstance(
            item["relation_path"],
            list,
        ):
            raise ParseRejected(
                "relation_path must be array"
            )

        if not isinstance(
            item["relation_surface"],
            list,
        ):
            raise ParseRejected(
                "relation_surface must be array"
            )

        if (
            len(item["relation_path"])
            != len(item["relation_surface"])
        ):
            raise ParseRejected(
                "relation path/surface lengths differ"
            )

        if len(
            item["relation_path"]
        ) > 8:
            raise ParseRejected(
                "too many relation hops"
            )

        if act == "person":
            _require_string(
                item,
                "subject",
            )
            _require_empty_relations(item)
            _require_none(
                item,
                "value",
                "alias",
                "canonical",
                "choice",
            )

        elif act == "alias":
            _require_string(
                item,
                "alias",
            )
            _require_string(
                item,
                "canonical",
            )
            _require_empty_relations(item)
            _require_none(
                item,
                "subject",
                "value",
                "choice",
            )

        elif act in {
            "teach",
            "correct",
        }:
            _require_string(
                item,
                "subject",
            )
            _require_relation_count(
                item,
                1,
                1,
            )
            _require_string(
                item,
                "value",
            )

            if item["value_kind"] not in {
                "literal",
                "person",
            }:
                raise ParseRejected(
                    f"{act} requires a value"
                )

            _require_none(
                item,
                "alias",
                "canonical",
                "choice",
            )

        elif act == "ask":
            _require_string(
                item,
                "subject",
            )
            _require_relation_count(
                item,
                1,
                8,
            )
            _require_none(
                item,
                "value",
                "alias",
                "canonical",
                "choice",
            )

            if item["value_kind"] != "none":
                raise ParseRejected(
                    "ask value_kind must be none"
                )

        elif act == "forget":
            _require_string(
                item,
                "subject",
            )
            _require_relation_count(
                item,
                1,
                1,
            )
            _require_none(
                item,
                "value",
                "alias",
                "canonical",
                "choice",
            )

        elif act == "quote":
            _require_string(
                item,
                "text",
            )

            if item["text"] != utterance:
                raise ParseRejected(
                    "quote.text must exactly copy "
                    "the utterance"
                )

        elif act in {
            "yes",
            "no",
        }:
            if pending_state is None:
                raise ParseRejected(
                    f"{act} is illegal without "
                    "pending state"
                )

        elif act == "pick":
            _require_string(
                item,
                "choice",
            )

            if pending_state is None:
                raise ParseRejected(
                    "pick is illegal without "
                    "pending state"
                )

            choices = _pending_ids(
                pending_state
            )

            if (
                choices
                and item["choice"]
                not in choices
            ):
                raise ParseRejected(
                    "pick ID is not pending"
                )

        for (
            surface,
            relation,
        ) in zip(
            item["relation_surface"],
            item["relation_path"],
        ):
            if (
                not isinstance(surface, str)
                or not isinstance(
                    relation,
                    str,
                )
            ):
                raise ParseRejected(
                    "relations must be strings"
                )

            expected = canonical_relation(
                surface
            )

            if relation != expected:
                raise ParseRejected(
                    f"relation {relation!r} "
                    f"does not match copied "
                    f"surface {surface!r}; "
                    f"expected {expected!r}"
                )

    control = [
        act
        for act in meaningful_acts
        if act in {
            "yes",
            "no",
            "pick",
            "undo",
        }
    ]

    if control and len(
        [
            x
            for x in meaningful_acts
            if x not in {
                "smalltalk",
                "unsure",
            }
        ]
    ) != 1:
        raise ParseRejected(
            "control responses must stand alone"
        )

    has_quote = (
        "quote" in meaningful_acts
    )
    has_write = any(
        act in WRITE_ACTS
        for act in meaningful_acts
    )

    if has_quote and has_write:
        raise ParseRejected(
            "quote may not coexist with a write"
        )

    if doc["unsure"]:
        actionable = [
            act
            for act in meaningful_acts
            if act not in {
                "unsure",
                "smalltalk",
            }
        ]

        if actionable:
            raise ParseRejected(
                "unsure parse may not contain "
                "an actionable item"
            )


def _validate_copy_constraints(
    doc: dict,
    utterance: str,
) -> None:
    first_person = _has_first_person(
        utterance
    )
    second_person = _has_second_person(
        utterance
    )

    def copied(
        value,
        role: str,
    ) -> None:
        if value is None:
            return

        if role in {
            "subject",
            "person_value",
        }:
            if (
                value == "Ben"
                and first_person
            ):
                return

            if (
                value == "self"
                and second_person
            ):
                return

        if not _contains(
            utterance,
            value,
        ):
            raise ParseRejected(
                "copy constraint rejected "
                f"{role} {value!r}"
            )

    for item in doc["items"]:
        act = item["act"]

        if act in {
            "person",
            "teach",
            "correct",
            "ask",
            "forget",
        }:
            copied(
                item["subject"],
                "subject",
            )

        if act == "alias":
            copied(
                item["alias"],
                "alias",
            )
            copied(
                item["canonical"],
                "canonical",
            )

        if act in {
            "teach",
            "correct",
        }:
            role = (
                "person_value"
                if item["value_kind"]
                == "person"
                else "value"
            )

            copied(
                item["value"],
                role,
            )

        for surface in item[
            "relation_surface"
        ]:
            copied(
                surface,
                "relation_surface",
            )


def _validate_nonwrite_guards(
    doc: dict,
    utterance: str,
) -> None:
    writes = [
        item
        for item in doc["items"]
        if item["act"] in WRITE_ACTS
    ]

    if not writes:
        return

    lower = utterance.casefold()
    padded = f" {lower} "

    if "?" in utterance:
        raise ParseRejected(
            "question may not write"
        )

    if re.match(
        r"^\s*(if\b|suppose\b|imagine\b)",
        lower,
    ):
        raise ParseRejected(
            "hypothetical may not write"
        )

    if any(
        marker in padded
        for marker
        in REPORTED_SPEECH_MARKERS
    ):
        raise ParseRejected(
            "reported speech may not write"
        )

    negation = bool(
        re.search(
            r"\b("
            r"not|never|no longer|"
            r"isn't|isn’t|"
            r"doesn't|doesn’t|"
            r"wasn't|wasn’t"
            r")\b",
            lower,
        )
    )

    if (
        negation
        and not all(
            item["act"] == "correct"
            for item in writes
        )
    ):
        raise ParseRejected(
            "unsupported negation "
            "may not write"
        )

    has_correct = any(
        item["act"] == "correct"
        for item in writes
    )

    if (
        has_correct
        and not _has_correction_cue(
            utterance
        )
    ):
        raise ParseRejected(
            "correct requires explicit "
            "correction language"
        )

    has_teach = any(
        item["act"] == "teach"
        for item in writes
    )

    if (
        has_teach
        and _has_correction_cue(
            utterance
        )
    ):
        raise ParseRejected(
            "correction language may not "
            "be downgraded to teach"
        )


def validate_model_output(
    doc: dict,
    utterance: str,
    pending_state=None,
) -> None:
    _validate_shape(
        doc,
        utterance,
        pending_state,
    )

    _validate_copy_constraints(
        doc,
        utterance,
    )

    _validate_nonwrite_guards(
        doc,
        utterance,
    )


def _atom(value: str) -> str:
    """
    Single-token values preserve M1 syntax.

    Multi-word/special values use JSON string syntax.
    M1 therefore needs a small quoted-atom parser.
    """
    if (
        re.fullmatch(
            r"[^\s=]+",
            value,
        )
        and '"' not in value
        and "\\" not in value
    ):
        return value

    return json.dumps(
        value,
        ensure_ascii=False,
    )


def render_item(
    item: dict,
    utterance: str,
) -> str | None:
    act = item["act"]

    if act == "person":
        return (
            f"person "
            f"{_atom(item['subject'])}"
        )

    if act == "alias":
        return (
            f"alias "
            f"{_atom(item['alias'])} = "
            f"{_atom(item['canonical'])}"
        )

    if act in {
        "teach",
        "correct",
    }:
        operator = (
            "->"
            if item["value_kind"]
            == "person"
            else "="
        )

        return (
            f"{act} "
            f"{_atom(item['subject'])} "
            f"{item['relation_path'][0]} "
            f"{operator} "
            f"{_atom(item['value'])}"
        )

    if act == "ask":
        path = " ".join(
            item["relation_path"]
        )

        return (
            f"ask "
            f"{_atom(item['subject'])} "
            f"{path}"
        )

    if act == "forget":
        return (
            f"forget "
            f"{_atom(item['subject'])} "
            f"{item['relation_path'][0]}"
        )

    if act == "quote":
        return (
            f"quote {utterance}"
        )

    if act in {
        "yes",
        "no",
    }:
        return act

    if act == "pick":
        return (
            f"pick {item['choice']}"
        )

    if act == "undo":
        return "undo last"

    if act in {
        "smalltalk",
        "unsure",
    }:
        return None

    raise ParseRejected(
        f"cannot render {act!r}"
    )


def render_lines(
    doc: dict,
    utterance: str,
) -> list[str]:
    result = []

    for item in doc["items"]:
        line = render_item(
            item,
            utterance,
        )

        if line is not None:
            result.append(line)

    return result


def confirm_before_write_policy(
    doc: dict,
) -> bool:
    """
    Hook for the English adapter's extra
    echo-back confirmation.

    Existing Listening conflict/ambiguity
    confirmation still remains authoritative.
    """
    writes = [
        item
        for item in doc["items"]
        if item["act"] in WRITE_ACTS
    ]

    if not writes:
        return False

    # A bundle is easier to mis-hear.
    if len(writes) > 1:
        return True

    if min(
        float(item["confidence"])
        for item in writes
    ) < 0.98:
        return True

    # Unknown relation normalization is
    # semantically riskier.
    for item in writes:
        if any(
            relation
            not in KNOWN_RELATIONS
            for relation
            in item["relation_path"]
        ):
            return True

    return False


def _decode_model_content(
    response_obj: dict,
) -> dict:
    try:
        content = (
            response_obj[
                "choices"
            ][0][
                "message"
            ][
                "content"
            ]
        )
    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        raise ParseRejected(
            "server response had no "
            "choices[0].message.content"
        ) from exc

    if isinstance(content, dict):
        return content

    if not isinstance(content, str):
        raise ParseRejected(
            "model content was not text"
        )

    text = content.strip()

    # Should not occur with JSON-schema
    # decoding, but harmless defensive code.
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    try:
        return json.loads(
            text.strip()
        )
    except json.JSONDecodeError as exc:
        raise ParseRejected(
            f"invalid model JSON: {exc}"
        ) from exc


def _request_doc(
    utterance: str,
    pending_state,
    known_names,
    base_url: str,
    model: str,
) -> dict:
    context = {
        "utterance": utterance,
        "pending_state": _jsonable(
            pending_state
        ),
        "known_names": (
            _compact_known_names(
                known_names
            )
        ),
    }

    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 900,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(
                    context,
                    ensure_ascii=False,
                ),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": (
                    "fable_listening_parse"
                ),
                "strict": True,
                "schema": PARSE_SCHEMA,
            },
        },
    }

    url = (
        base_url.rstrip("/")
        + "/v1/chat/completions"
    )

    request = urllib.request.Request(
        url,
        data=json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type":
                "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:
            response_obj = json.loads(
                response.read().decode(
                    "utf-8"
                )
            )

    except urllib.error.HTTPError as exc:
        body = exc.read().decode(
            "utf-8",
            "replace",
        )

        raise RuntimeError(
            f"llama.cpp HTTP "
            f"{exc.code}: "
            f"{body[:1000]}"
        ) from exc

    except urllib.error.URLError as exc:
        raise RuntimeError(
            "cannot reach llama.cpp at "
            f"{base_url}: {exc.reason}"
        ) from exc

    return _decode_model_content(
        response_obj
    )


def parse_english_proposal(
    utterance: str,
    pending_state,
    known_names,
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> dict:
    """
    Parse and validate, but never write memory.
    """
    base_url = (
        base_url
        or DEFAULT_BASE_URL
    )
    model = (
        model
        or DEFAULT_MODEL
    )

    doc = _request_doc(
        utterance,
        pending_state,
        known_names,
        base_url,
        model,
    )

    validate_model_output(
        doc,
        utterance,
        pending_state,
    )

    return {
        "doc": doc,
        "lines": render_lines(
            doc,
            utterance,
        ),
        "confirm_before_write":
            confirm_before_write_policy(
                doc
            ),
    }


def parse_english(
    utterance: str,
    pending_state,
    known_names,
    *,
    base_url: str | None = None,
    model: str | None = None,
) -> list[str]:
    """
    Required public interface.

    Returns zero or more validated structured
    lines. It does NOT call Listening and does
    NOT write the notebook.
    """
    proposal = (
        parse_english_proposal(
            utterance,
            pending_state,
            known_names,
            base_url=base_url,
            model=model,
        )
    )

    return proposal["lines"]


def _doc(
    *items,
    unsure=False,
    reason="",
) -> dict:
    return {
        "items": list(items),
        "unsure": unsure,
        "unsure_reason": reason,
    }


def _selftest() -> int:
    """
    Offline tests. No HTTP requests.
    """
    valid_cases = [
        (
            "Mira lives in Lisbon.",
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Mira",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "lives in"
                    ],
                    value="Lisbon",
                    value_kind="literal",
                )
            ),
            [
                "teach Mira city = Lisbon"
            ],
        ),
        (
            "Mary Jane lives in New York.",
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Mary Jane",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "lives in"
                    ],
                    value="New York",
                    value_kind="literal",
                )
            ),
            [
                'teach "Mary Jane" '
                'city = "New York"'
            ],
        ),
        (
            (
                "Where does Mira's "
                "mother live?"
            ),
            None,
            _doc(
                blank_item(
                    "ask",
                    subject="Mira",
                    relation_path=[
                        "mother",
                        "city",
                    ],
                    relation_surface=[
                        "mother",
                        "live",
                    ],
                )
            ),
            [
                "ask Mira mother city"
            ],
        ),
        (
            "What were you trained on?",
            None,
            _doc(
                blank_item(
                    "ask",
                    subject="self",
                    relation_path=[
                        "training_data"
                    ],
                    relation_surface=[
                        "trained on"
                    ],
                )
            ),
            [
                "ask self training_data"
            ],
        ),
        (
            (
                "If Mira lived in Paris, "
                "she'd smile."
            ),
            None,
            _doc(
                blank_item(
                    "quote",
                    text=(
                        "If Mira lived in "
                        "Paris, she'd smile."
                    ),
                )
            ),
            [
                (
                    "quote If Mira lived in "
                    "Paris, she'd smile."
                )
            ],
        ),
        (
            "The second one.",
            {
                "choices": [
                    "E0002",
                    "E0007",
                ]
            },
            _doc(
                blank_item(
                    "pick",
                    choice="E0007",
                )
            ),
            [
                "pick E0007"
            ],
        ),
    ]

    passed = 0

    for (
        utterance,
        pending,
        doc,
        expected,
    ) in valid_cases:
        validate_model_output(
            doc,
            utterance,
            pending,
        )

        got = render_lines(
            doc,
            utterance,
        )

        assert got == expected, (
            utterance,
            got,
            expected,
        )

        passed += 1

    unsafe_cases = [
        (
            "Mira lives in Lisbon.",
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Ana",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "lives in"
                    ],
                    value="Lisbon",
                    value_kind="literal",
                )
            ),
        ),
        (
            (
                "Mira does not live "
                "in Paris."
            ),
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Mira",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "live in"
                    ],
                    value="Paris",
                    value_kind="literal",
                )
            ),
        ),
        (
            (
                "Actually Mira lives "
                "in Paris."
            ),
            None,
            _doc(
                blank_item(
                    "teach",
                    subject="Mira",
                    relation_path=[
                        "city"
                    ],
                    relation_surface=[
                        "lives in"
                    ],
                    value="Paris",
                    value_kind="literal",
                )
            ),
        ),
    ]

    for (
        utterance,
        pending,
        doc,
    ) in unsafe_cases:
        try:
            validate_model_output(
                doc,
                utterance,
                pending,
            )

        except ParseRejected:
            passed += 1

        else:
            raise AssertionError(
                "validator accepted "
                f"unsafe parse: {utterance}"
            )

    bundle = _doc(
        blank_item(
            "teach",
            subject="Mira",
            relation_path=[
                "city"
            ],
            relation_surface=[
                "lives in"
            ],
            value="Lisbon",
            value_kind="literal",
        ),
        blank_item(
            "teach",
            subject="Mira",
            relation_path=[
                "employer"
            ],
            relation_surface=[
                "works at"
            ],
            value="Acme",
            value_kind="literal",
        ),
    )

    assert (
        confirm_before_write_policy(
            bundle
        )
        is True
    )

    passed += 1

    print(
        f"selftest: {passed} checks "
        "passed; no network used"
    )

    return 0


def _listener_pending(listener):
    """
    M1 may use one of these common attribute
    names. If it exposes a dedicated accessor,
    replace this helper with that accessor.
    """
    for name in (
        "pending_state",
        "pending",
        "clarification",
    ):
        if hasattr(listener, name):
            return _jsonable(
                getattr(
                    listener,
                    name,
                )
            )

    return None


def _known_names_from_notebook(
    notebook,
    extras,
) -> list[str]:
    """
    Best-effort read-only extraction. The
    validator never trusts this list enough to
    bypass the copy constraint.
    """
    names = list(
        extras or []
    )

    entities = getattr(
        notebook,
        "entities",
        None,
    )

    if isinstance(
        entities,
        dict,
    ):
        for entity in (
            entities.values()
        ):
            if not isinstance(
                entity,
                dict,
            ):
                continue

            for key in (
                "name",
                "display_name",
            ):
                value = entity.get(
                    key
                )

                if isinstance(
                    value,
                    str,
                ):
                    names.append(
                        value
                    )

            aliases = entity.get(
                "aliases",
                [],
            )

            if isinstance(
                aliases,
                (
                    list,
                    tuple,
                    set,
                ),
            ):
                names.extend(
                    alias
                    for alias
                    in aliases
                    if isinstance(
                        alias,
                        str,
                    )
                )

    return list(
        dict.fromkeys(names)
    )[:500]


def _audit_path(
    folder: str,
) -> str:
    return os.path.join(
        folder,
        "listening_english_audit.jsonl",
    )


def _append_audit(
    folder: str,
    raw: str,
    line: str,
    reply: str,
) -> None:
    """
    Compatibility-sidecar for raw English.

    It is append-only and hash chained. Once
    Notebook supports raw_utterance provenance,
    put the raw text in the Notebook event too.
    """
    path = _audit_path(
        folder
    )
    previous_hash = "0" * 64

    try:
        with open(
            path,
            "rb",
        ) as fh:
            last_line = None

            for last_line in fh:
                pass

        if last_line:
            previous = json.loads(
                last_line.decode(
                    "utf-8"
                )
            )

            previous_hash = (
                previous.get(
                    "hash",
                    previous_hash,
                )
            )

    except FileNotFoundError:
        pass

    event = {
        "prev": previous_hash,
        "raw": raw,
        "line": line,
        "reply": reply,
    }

    canonical = json.dumps(
        event,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    event["hash"] = (
        hashlib.sha256(
            canonical.encode(
                "utf-8"
            )
        ).hexdigest()
    )

    os.makedirs(
        folder,
        exist_ok=True,
    )

    with open(
        path,
        "a",
        encoding="utf-8",
    ) as fh:
        fh.write(
            json.dumps(
                event,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )

        fh.flush()
        os.fsync(
            fh.fileno()
        )


def _confirmation_echo(
    lines: list[str],
) -> str:
    return (
        "I heard: "
        + "; ".join(lines)
        + ". Save that?"
    )


def _apply_lines(
    listener,
    folder: str,
    raw: str,
    lines: list[str],
) -> list[str]:
    replies = []

    for line in lines:
        reply = listener.hear(
            line
        )

        replies.append(
            reply
        )

        _append_audit(
            folder,
            raw,
            line,
            reply,
        )

    return replies


def _chat(args) -> int:
    try:
        from fable_listening_m1 import (
            Listening,
        )
        import fable_notebook_contract as C

    except ImportError as exc:
        print(
            f"import error: {exc}",
            file=sys.stderr,
        )
        return 2

    notebook = C.Notebook(
        args.folder
    )

    listener = Listening(
        notebook
    )

    adapter_pending = None

    print(
        "English Listening REPL. "
        "Ctrl-D or /quit exits."
    )

    while True:
        try:
            utterance = input(
                "you> "
            ).strip()

        except (
            EOFError,
            KeyboardInterrupt,
        ):
            print()
            return 0

        if not utterance:
            continue

        if utterance in {
            "/quit",
            "/exit",
        }:
            return 0

        known_names = (
            _known_names_from_notebook(
                notebook,
                args.known_name,
            )
        )

        # Adapter-owned bundle confirmation.
        if adapter_pending is not None:
            confirm_state = {
                "kind":
                    "confirm_adapter_bundle",
                "choices": [
                    "yes",
                    "no",
                ],
                "proposed_lines":
                    adapter_pending[
                        "lines"
                    ],
            }

            try:
                confirmation = (
                    parse_english_proposal(
                        utterance,
                        confirm_state,
                        known_names,
                        base_url=(
                            args.base_url
                        ),
                        model=args.model,
                    )
                )

            except (
                ParseRejected,
                RuntimeError,
            ) as exc:
                print(
                    "fable> I couldn't "
                    "safely parse that "
                    "confirmation: "
                    f"{exc}"
                )
                continue

            acts = [
                item["act"]
                for item
                in confirmation[
                    "doc"
                ]["items"]
            ]

            if acts == ["yes"]:
                replies = _apply_lines(
                    listener,
                    args.folder,
                    adapter_pending["raw"],
                    adapter_pending["lines"],
                )

                adapter_pending = None

                for reply in replies:
                    print(
                        f"fable> {reply}"
                    )

                continue

            if acts == ["no"]:
                adapter_pending = None
                print(
                    "fable> Cancelled."
                )
                continue

            # Unrelated input cancels the
            # pending clarification and is
            # processed as a fresh utterance.
            adapter_pending = None

        pending_state = (
            _listener_pending(
                listener
            )
        )

        try:
            proposal = (
                parse_english_proposal(
                    utterance,
                    pending_state,
                    known_names,
                    base_url=(
                        args.base_url
                    ),
                    model=args.model,
                )
            )

        except (
            ParseRejected,
            RuntimeError,
        ) as exc:
            print(
                "fable> I didn't trust "
                "that parse, so I saved "
                f"nothing: {exc}"
            )
            continue

        if proposal["doc"]["unsure"]:
            reason = (
                proposal["doc"][
                    "unsure_reason"
                ]
                or
                "I'm not sure what "
                "you meant."
            )

            print(
                f"fable> {reason} "
                "Nothing was saved."
            )
            continue

        lines = proposal[
            "lines"
        ]

        if proposal[
            "confirm_before_write"
        ]:
            adapter_pending = {
                "raw": utterance,
                "lines": lines,
            }

            print(
                "fable> "
                + _confirmation_echo(
                    lines
                )
            )
            continue

        if not lines:
            print(
                "fable> Okay."
            )
            continue

        replies = _apply_lines(
            listener,
            args.folder,
            utterance,
            lines,
        )

        for reply in replies:
            print(
                f"fable> {reply}"
            )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "English front end for "
            "Fable Listening mode"
        )
    )

    mode = (
        parser.add_mutually_exclusive_group(
            required=True
        )
    )

    mode.add_argument(
        "--selftest",
        action="store_true",
        help=(
            "run offline validator "
            "and rendering tests"
        ),
    )

    mode.add_argument(
        "--chat",
        action="store_true",
        help=(
            "run interactive "
            "Listening REPL"
        ),
    )

    parser.add_argument(
        "--folder",
        default="./fable_notebook",
        help="Notebook folder",
    )

    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
    )

    parser.add_argument(
        "--known-name",
        action="append",
        default=[],
    )

    args = parser.parse_args(
        argv
    )

    if args.selftest:
        return _selftest()

    return _chat(
        args
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
```

The architectural point I would preserve when you replace Qwen is that **English understanding is allowed to be learned; memory integrity is not**. That gives your eventual from-scratch ears room to become genuinely better without ever giving a weak early model permission to corrupt the thing it is learning from.
