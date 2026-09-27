# TODO -- the L3 "outside wording" set is EMPTY ON PURPOSE

L3 is the only wording level that does not come from our grammar.  Design section 4.2:

| file | who writes it | how many | state |
|---|---|---|---|
| `l3-ben.txt` | **Ben**, by hand, one sentence per line | 100 | **empty -- waiting for Ben** |
| `l3-qwen.jsonl` | Qwen on BensPC, a different prompt ("how might a person casually say this?") | 200 | **empty -- needs a Qwen night and Ben's yes** |

## Rules that make this set worth anything

1. **Ben types his 100 before he ever sees a model output.** If he writes them after seeing
   what the model gets wrong, L3 stops measuring "wordings from outside the grammar" and
   starts measuring "wordings Ben knows are hard". Roughly 20 minutes of his time.
2. **Nothing here is ever trained on.** Not one sentence, not a paraphrase of one.
3. **Both files are hashed the moment they are filled** (`seal` writes the hashes into
   `SEALED-SPLITS.md`), and the hashes go in the run log of every evaluation that uses them.
4. If a failed L3 wording is later added to the grammar (design section 5, S3), that must be
   declared and **a fresh set of sealed L3 sentences is needed** -- the old ones are burnt.

## What Ben should write

Ordinary sentences that teach, ask, correct or chat -- in his own words, not the grammar's.
Names may be anything capitalised. Only the four relations (`friend`, `gift`, `prize`,
`charm`) and the sixteen values (`drum kite lamp rope coin flute brush candle mirror ladder
kettle basket ribbon feather pebble whistle`) exist, because the frozen operator has no
other symbols. A rough mix, not a rule: 35 teaching, 30 asking (some two-step), 10
correcting, 15 small talk, 10 things it cannot possibly know.

## Format

`l3-ben.txt` -- one sentence per line, `#` comments allowed, blank lines ignored. Case is
normalised on load by `fable_talker24_dialogues.normalise_case`, which keeps a capitalised
word as a NAME only when the published lexicon has never seen it.

`l3-qwen.jsonl` -- one JSON object per line: `{"text": "...", "prompt_id": "...",
"model": "...", "seed": 0}`.

The loader is `fable_talker24_dialogues.load_l3(folder)`. It returns
`{"items": [...], "counts": {...}, "complete": false}` today and needs no change when the
files arrive.
