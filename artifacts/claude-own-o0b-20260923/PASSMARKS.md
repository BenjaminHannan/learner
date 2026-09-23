# PASSMARKS own-O0b — frame data generator for the own ear (plan §2.4)

Sealed BEFORE the full generation run (2026-09-23). Code frozen:
scripts/claude_own_o0b_gen.py, scripts/claude_own_o0b_check.py.
Pilot evidence (pre-seal): 2 × 10,000 rows, seeds 3 and 43, checker
mismatches 0/10,000 both times.

## Output contract

Per turn: {prev_reply, turn, act, count, facts:[{owner_span|ME|WE,
relation (relation_table_v2 name), relation_cue_span, value_span, mode}],
question:{owner_span, relations[<=3], inverse}}. Spans are character offsets
into the turn. 10 families: tell, ask, chat, act, binding, plural,
appositive, correction, noise, typo. Split BY FRAME: L1 = seen frames with
new names; L2 = 20% of frames held out + 2 openers + 2 closers never trained
+ reserved names; L3 empty. 200,000 train + 5,000 L1 dev + 5,000 L2 dev,
jsonl.gz shards each under 5 MB. counts.json per family. Fictional names only.

## Marks (bars)

- Pown0b.1: re-deriver (check.py, text + world intent, never frame id)
  mismatches = 0 on 10,000 sampled rows (seed 7).
- Pown0b.2: no L2 frame id appears in train (checked on every train row).
- Pown0b.3: every span is a whole-word span of its turn (checked on every
  row of every split).
- Pown0b.4: each of the 10 families >= 3% of train rows (>= 6,000 rows).

## Predicted moves

- Pown0b.1 0 mismatches / 10,000.
- Pown0b.2 0 train rows carry an L2 frame id.
- Pown0b.3 0 non-whole-word spans in 210,000 rows.
- Pown0b.4 every family in [9%, 11%] of train (uniform draw over families).

A FAIL is reported as FAIL with one diagnosis note; no silent re-runs.
Any post-seal change to gen/check scripts voids the verdict (reported, never
re-sealed).
