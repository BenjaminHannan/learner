# Exp 235 PASSMARKS -- SmolLM2-360M-Instruct as the ear (sealed before the panel is opened)

The one change: the reader. A fine-tuned SmolLM2-360M-Instruct turns each chat turn into frame lines
(`TEACH | subject | relation | value`, `ASK | subject | rel1 > rel2`, `NONE`), then a plain-software
brake drops any frame whose subject/value is not an exact span of the turn (only case and edge
punctuation trimmed) or whose relation is not in relation table v1 (canonical name, or a listed
alias mapped to its canonical name).

Frozen checkpoint (kept on BensPC `C:\Users\benja\smolear235\out_v3\smolear235.safetensors`):
sha256 `2852a5c0d60b2ef361cbf45eb14863b0047b56bd89e65fa90db4479ddf3fd8f8` (train/CKPT.sha256.txt).
Why Instruct, not base: it is the only SmolLM2-360M in the Mac cache (no network), and the
chat-tuned prior already follows the `<|im_start|>` prompt format we train on.

## Panel
artifacts/claude-earpanel235-20260922/panel.jsonl (150 turns; written blind by another agent). Loaded with
scripts/claude_smolear235_panel.py (schema-tolerant). Arm A sees only the final turn text. Arm B runs
context turns (if any) and then the turn through scripts/claude_loop228_agent.py (138i + the 228 flake
guard) with the 138i config in a fresh isolated workdir; its frames = taught triples newly active after
the turn. Question families are scored for A only. Arm C (SciBERT 119h + 213 gate) is NOT run (optional in the
brief; BensPC's transformers install currently fails its hub-version import check and we install nothing).

## Scoring rules (scripts/claude_smolear235_score.py)
subject/value: lower-case, edge punctuation trimmed, a leading the/a/an dropped, trailing "years old" dropped
from values; first-person subjects {i, me, my, myself, mine, user} = one entity (138i stores USER).
relation: match if the canonical table name of the prediction equals the canonical name of the gold
relation or of any gold relation_alias, or the plain strings match (_ - space treated alike).
Each gold frame is matched at most once.

## Marks (arm A = after the brake; A_raw and B reported beside it)
| mark | bar |
|---|---|
| M1 | no_save family: TEACH frames kept <= 1 (of 25 turns) |
| M2 | wrong saves across plain_teach + varied_teach + full_names + corrections + no_save: TEACH frames kept that match no gold TEACH frame of that turn <= 2 |
| M3 | exact TEACH-frame recall on plain_teach + varied_teach + full_names + corrections >= 80% for A, and A >= B + 15 points |
| M4 | exact ASK-frame recall on questions + chain_questions >= 80% for A |
| M5 | median GPU (RTX 5070 Ti) time per turn, generation + parse + brake, <= 300 ms. Mac CPU (1 thread, OMP_NUM_THREADS=1) reported, no bar |

Registered verdict = PASS only if M1-M5 all pass. Extra numbers (no bar): stray TEACH frames on question turns,
exact whole-turn rates per family, frames dropped by the brake by reason.

## Pilot evidence (no panel opened)
- Dev split (59 whole templates held out; 800 sampled rows): 783/800 exact after the brake; NONE 169/169,
  corrections 40/40, ask 159/159, chain 4/4, ask_fp 65/72 (the model invents a name for "When is my birthday?";
  the brake drops it), teach 341/351 (misses: symmetric "lives next door to" direction, "was born in May 18"
  read as place_of_birth, an odd wife template).
- 24 hand-written probe sentences (artifacts/.../pilot/): nested facts ("Ottoline's mom works as a potter") now NONE,
  appositives ("My grandma, Tilda Fenwick, is 91") give 2 frames; "favourite food" invents relation
  favorite_food (brake drops it).
- GPU median 63 ms per turn (dev), CPU 1-thread median 640 ms (v2 checkpoint, same size).

## Predictions (also in the ledger)
- P235.1 M1 passes (0-1 no_save saves).
- P235.2 M2: 1-4 wrong saves; pass probability about 50%.
- P235.3 M3: A recall 75-90%; B 30-55%; A >= B+15 very likely; the 80% bar about 55%.
- P235.4 M4: 78-92%; pass about 60%.
- P235.5 M5 passes (median 50-100 ms).
- P235.6 Overall PASS probability about 30%.
