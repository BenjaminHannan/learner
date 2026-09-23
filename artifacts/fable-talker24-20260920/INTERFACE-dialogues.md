# INTERFACE — dialogue data format (build task 2 → build task 3)

**Format version `fable-talker24-dialogues/1`.** Written by the dialogue-generator builder
*before* the generator was finished, so the model/trainer builder can code against it in
parallel. Producer: `scripts/fable_talker24_dialogues.py`. Design source:
`design/v3/24-talker-from-scratch-fable-design.md` §3.2, §4.1–4.4, §5; decisions
`design/v3/24b-talker-decisions-ben.md`.

**Scope boundary.** Everything here is **raw text plus exact labels**. There is no
tokenization, no `<ENT>` substitution, no tensor, no padding, no vocabulary id. That is the
data-pipeline builder's job and their format lives in `INTERFACE-data.md` (this builder does
not write or edit that file). All character offsets in this file are **UTF-8 Python string
indices into the exact `text` string in the same record**, half-open `[start, end)`. The
pipeline builder converts them to token spans.

If anything below turns out to be wrong or impossible, the generator is the source of truth
and this file is corrected; the version string changes only if a field changes meaning.

---

## 1. Files

```
artifacts/fable-talker24-20260920/dialogues/
  L1-test.jsonl          sealed L1 test set   (training frames, new people/values/worlds)
  L1-test.meta.json      counts + sha256 + generator version + seed key
  L2-test.jsonl          sealed L2 test set   (held-out frames, openers, closers)
  L2-test.meta.json
  L1-sample.jsonl        20 dialogues, human-readable pretty-printed copy (SAMPLES.md)
  frame-split.json       the sealed L1/L2 frame split (ids + sha256 of every frame string)
  LEXICON.json           the published word list the name rule and the parser use
  L3/                    outside wordings — EMPTY ON PURPOSE, see L3/TODO-L3.md
../SEALED-SPLITS.md      sha256 of every file above, written before any model existed
```

Training data is **not** shipped as a file. It is streamed on demand:

```sh
python3 scripts/fable_talker24_dialogues.py generate --split L1 --n 200000 --out train.jsonl
```

Dialogue *i* depends only on `(namespace, split, i)`, never on dialogue *i−1*, so a trainer
may shard, resume or re-draw any range and get byte-identical records.

**File format:** JSON Lines. One dialogue per line, UTF-8, `\n` line endings, no trailing
blank line, emitted with `json.dumps(obj, sort_keys=True, separators=(',', ':'))`. Keys are
therefore in sorted order and the file is byte-reproducible.

---

## 2. Text conventions (read this before tokenising)

1. **All generated text is lower-case except names.** A name keeps its leading capital;
   every other word is lower-case, including the first word of a sentence — *unless* the
   `capitalise_start` noise op fired, which upper-cases the first letter, and the `upper_i`
   op, which writes the pronoun `I`. This matches §2.1's lower-cased tokenizer.
2. **The name rule** (supplied, declared): a token is a name iff it starts with a capital
   letter **and** its lower-cased form is not in `LEXICON.json`. That is the rule the
   `<ENT>` substitution in the data pipeline should use. `LEXICON.json` is published beside
   the data and contains every non-name word any frame, opener or closer can emit.
3. **Apostrophes** are always ASCII `'`. Possessives are written `Mira's`, `friend's`.
4. **No double spaces**, no tabs, no newlines inside a turn's `text`.
5. Values (`drum`, `kite`, …) are ordinary lower-case words and are **not** capitalised.
   They are still copy-only for the mouth (see §5).

---

## 3. Dialogue record

```jsonc
{
  "id": "L1/000123",
  "format": "fable-talker24-dialogues/1",
  "split": "L1",                      // L1 | L2 | L3
  "index": 123,                       // the i in (namespace, split, i)
  "seed_key": "fable-talker24-dialogues-v1:L1:123",
  "symbol_mode": "m0",                // m0 | pool   (see §7)
  "world": {
    "people": [                       // the per-dialogue symbol table
      {"slot": 0, "name": "Mira", "symbol": 52},
      {"slot": 1, "name": "Oren", "symbol": 53}
    ],
    "values": {"drum": 12, "kite": 13, "...": 0},   // value word -> symbol
    "relations": {"friend": 11, "gift": 8, "prize": 9, "charm": 10},
    "n_people": 2,
    "code_pool": null                 // pool mode only: {"pool":"train","indices":[...]}
  },
  "turns": [ /* §4 */ ],
  "final_view": {"52,11": 53},        // "subject,relation" -> object symbol, after the last turn
  "counts": {"TELL": 4, "ASK": 3, "CORRECT": 1, "CHAT": 3, "UNCLEAR": 0},
  "levels": {"frames": "L1", "openers": "L1", "closers": "L1"}
}
```

* `world.people` **is** the symbol table for this dialogue: `slot` is the position, `symbol`
  is what the reasoner sees. Names are re-drawn for every dialogue, so nothing about a name
  is learnable across dialogues — that is the point (§3.4).
* A person can join the table mid-dialogue (a question about a never-mentioned person costs
  a symbol but states no fact, exactly as `fable_notebook_m0.Notebook.name_token` does). Such
  people are present in `world.people` from the start of the record; `turns[i].notebook`
  says when they were first named.

---

## 4. Turn record

```jsonc
{
  "i": 0,
  "user":  { "text": "...", "thought": {...}, "frame_id": "tell.attr.003",
             "opener_id": "op.04", "closer_id": null, "noise": ["drop_period"],
             "level": "L1" },
  "reply": { "text": "...", "surface": "...", "copy": [...], "thought": {...},
             "frame_id": "reply.ack.attr.011" },
  "notebook": {...}
}
```

`user.text` is what the person typed. `reply.text` is what the **mouth is trained to
produce** and `reply.surface` is what the **printer prints** — see §5. `frame_id`,
`opener_id`, `closer_id`, `noise` and `level` are bookkeeping: a trainer must never feed
them to a model, they exist so a failure can be traced to a wording.

---

## 5. Reply text: copy actions vs surface

The mouth's vocabulary contains the three copy actions `<SUBJ>`, `<OBJ>`, `<OLD>` and does
**not** contain names or values as fact answers (§3.4). So a reply is shipped twice:

```jsonc
"reply": {
  "text":    "ok. <SUBJ>'s gift is a <OBJ>.",        // TRAIN THE MOUTH ON THIS
  "surface": "ok. Mira's gift is a drum.",           // what a person sees
  "copy": [
    {"action": "<SUBJ>", "field": "subject", "slot": 0, "symbol": 52,
     "word": "Mira", "text_span": [4, 10], "surface_span": [4, 8]},
    {"action": "<OBJ>",  "field": "object",  "slot": null, "symbol": 12,
     "word": "drum", "text_span": [22, 27], "surface_span": [20, 24]}
  ]
}
```

* `text_span` is the span of the literal `<SUBJ>` / `<OBJ>` / `<OLD>` marker inside
  `reply.text`; `surface_span` is the span of the substituted word inside `reply.surface`.
* `field` says which field of `reply.thought` the printer must read to substitute the
  action: `subject`, `object` or `old`.
* `slot` is the index into `world.people` for a person, and `null` for a value (values are
  not people); `symbol` is always filled.
* A reply may contain **zero** copy actions (`CLARIFY`, `CHAT`, the not-teachable `UNKNOWN`).
* An `UNKNOWN` reply about a known person contains `<SUBJ>` but **never** `<OBJ>` — there is
  no object symbol in the thought, so the printer has nothing to substitute and the model is
  structurally unable to name an answer.
* Substituting each action with `copy[k].word` turns `text` into `surface` exactly. There is
  a unit test for this.

---

## 6. Thought record (the gold label)

The same shape for `user.thought` and `reply.thought`. This is the typed part of the
416-number thought of §3.2; the 256-number gist is **not** labelled (it is learned).

```jsonc
{
  "act": "TELL",
  "subject": {"slot": 0, "name": "Mira", "symbol": 52, "span": [0, 4]},
  "relation_path": ["friend", "gift"],
  "relation_symbols": [11, 8],
  "object": {"slot": null, "name": "drum", "kind": "value", "symbol": 12, "span": [19, 23]},
  "old":    null,
  "flags": {
    "path_len": 2,
    "speaker": "user",
    "unknown_reason": null,
    "unknown_step": null,
    "has_old_value": false,
    "teachable": true
  }
}
```

| field | type | meaning |
|---|---|---|
| `act` | user: `TELL` `ASK` `CORRECT` `CHAT` `UNCLEAR` · reply: `ACK` `ANSWER` `UNKNOWN` `CLARIFY` `CHAT` | §3.2 act field (8 numbers) |
| `subject` | object or `null` | §3.2 subject field (48 numbers). `span` is the **pointer target** for the ears: the character span of the name in *this record's* `text`. In a reply thought, `span` is into `reply.surface` and `null` when the name is not spoken. `slot`/`symbol` are what the symbol table returns; no network ever regresses them. |
| `relation_path` | 0–3 relation words | §3.2 relation path (3 × 16). Empty list = "none" (chat, or a question outside anything teachable). Hops before the last are always `friend`, because only a person-valued relation can be chained. |
| `relation_symbols` | the same, as operator tokens | convenience; derivable from `world.relations` |
| `object` | object or `null` | §3.2 object field (48 numbers). `kind` is `person` or `value`. `null` for questions (the object is the answer, not in the text) and for chat. |
| `old` | object or `null` | the previous value a correction names out loud ("not a kite, a drum"). Same shape as `object`. Drives the `<OLD>` copy action. |
| `flags.path_len` | 0–3 | `len(relation_path)` |
| `flags.speaker` | `user` \| `model` | §3.2 speaker flag |
| `flags.unknown_reason` | `null` \| `no_such_person` \| `no_such_fact` \| `chain_broke` \| `not_teachable` \| `unclear` | §4.4. Only ever non-null on a reply thought. |
| `flags.unknown_step` | `null` or `k` | which hop broke, 1-based, for `chain_broke` |
| `flags.has_old_value` | bool | true iff `old` is non-null |
| `flags.teachable` | bool | false for a question with an empty relation path (§4.4 case 3) |

**What a parser can and cannot recover.** The reference parser recovers, from surface text
alone: `act`, `subject`, `relation_path`, `object`, `old`, `flags.path_len`,
`flags.teachable`. It cannot recover `unknown_reason` / `unknown_step` — those are
properties of the notebook, not of the sentence, and they are produced by the notebook
simulator. Any evaluation that scores "thought exactness" (§5 S2) should score the
parser-recoverable fields for the ears and the notebook fields separately.

---

## 7. Symbols and name codes

`symbol_mode` decides what `symbol` means.

**`m0` (default, and what S2 uses first — §4.3).** M0's closed world, so the frozen
79,316-parameter operator can be run unchanged:

* relations `friend` = 11 (`LINK`), `gift` = 8, `prize` = 9, `charm` = 10;
* values = the 16 published words, symbols 12…27, in `fable_notebook_m0.VALUE_WORDS` order;
* people = entity tokens 52…67 (16 maximum, the operator's hard limit), assigned **in order
  of first appearance in the dialogue**, which is exactly `Notebook.derive_symbols`;
* surface names are drawn per dialogue from `fable_notebook_m0.DEFAULT_NAMES`, shuffled, so
  the name↔token pairing is re-drawn every dialogue.

**`pool` (after M1 passes — §4.3).** `symbol` is an **index into the frozen 4,096-code pool**
of `scripts/fable_newnames21.py`, not an entity token. The record then carries

```jsonc
"code_pool": {"pool": "train", "size": 3072, "key": "...", "indices": [814, 2299, ...]}
```

`indices[slot]` is the row of `fable_newnames21.pool_subset(pool, which)` for that person,
drawn by the **same** procedure as `fable_newnames21.assign_codes` —
`random.Random(key).sample(range(len(subset)), n_people)` — so a consumer loads the frozen
pool, takes the subset, and indexes it. `pool` is `train` for training data and `reserved`
for evaluation data whose codes were never trained on. Surface names in this mode come from
a generated 256-name list (`fable_talker24_dialogues.NAME_POOL`), also re-drawn per
dialogue. There is a test that the index draw matches `assign_codes` exactly.

The generator never emits the 48-number code itself. Codes are **routed, never regressed**
(§3.2 rule 1): the label gives a slot and a symbol, and the model copies.

---

## 8. Notebook record

```jsonc
"notebook": {
  "op": "append",                 // append | lookup | none
  "row": [3, 52, 8, 12, 7],       // [WORLD, entity, relation, object, NEWLINE], append only
  "replaced": {"row": [3,52,8,13,7], "object_symbol": 13, "object_word": "kite"},
  "named": [{"slot": 4, "name": "Esme", "symbol": 56}],   // people first named by this turn
  "view_size": 5,                 // rows in the current view AFTER this turn
  "question": [4, 52, 11, 8, 5],  // [QUESTION, entity, op..., ANSWER], lookup only
  "trace": [{"step": 1, "entity": 52, "relation": 11, "answer": 53},
            {"step": 2, "entity": 53, "relation": 8,  "answer": 12}],
  "answerable": true,
  "answer_symbol": 12,
  "unknown_reason": null,
  "unknown_step": null
}
```

* The simulator implements M0's rule exactly: the view is the **latest appended row per
  `(subject symbol, relation symbol)`**, derived by walking the append list in order. A
  correction is an ordinary append that replaces one view row in place.
* `trace` is the chain the fixed loop would run, one entry per hop, computed against the
  view as it stands **after** this turn's appends. On a broken chain the trace stops at the
  missing hop, `answerable` is false and `unknown_step` is that hop.
* `row`, `question` and the token layout are the operator's own, so a consumer can feed them
  straight to `astra_canonical_operator.execute` through `fable_notebook_m0.pack_story`
  (in `m0` mode only).
* `op` is `none` for `CHAT` and `UNCLEAR` turns: the notebook is not touched.

---

## 9. Determinism

* Namespace `fable-talker24-dialogues-v1`. Every draw comes from
  `random.Random(f'{namespace}:{split}:{index}:{purpose}')` — no global RNG, no time, no
  process id, no file-system order.
* `generate --split L1 --n 1000` and `--from 500 --n 500` produce identical lines for
  indices 500…999. A test asserts it.
* The frame split (which frames are L1 and which are L2) is a pure function of the frame
  ids and is sealed in `frame-split.json` with a sha256 over every frame string.
* Re-running the sealed builds reproduces the committed sha256 values in `SEALED-SPLITS.md`.

---

## 10. What is *not* in this data (so nobody waits for it)

* No tokens, no `<ENT>` substitution, no tensors — `INTERFACE-data.md`.
* No gist target. The 256-number gist is learned; nothing here labels it.
* No L3 sentences yet: `dialogues/L3/` is empty by design until Ben types his 100 and Qwen
  writes its 200. The loader, the hashing and the sealed-slot files exist now.
* No Qwen paraphrases yet: the prompt templates, the verifier and a stub client exist and
  are tested, but **no model has been called**.
* No chit-chat spliced from a real corpus. Generated small talk uses a closed word list that
  deliberately avoids the four relation words and the sixteen value words, so a chat turn can
  never look like a fact. When real corpus chat is spliced in later it must be passed through
  `fable_talker24_dialogues.chat_is_safe()` first.
