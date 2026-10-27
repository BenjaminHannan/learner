# Exp 140 PASSMARKS (sealed BEFORE the registered run — do not edit after)

One change: exp-129 sanitizer extended (new mixin, file untouched) to drop
trailing symbol/emoji runs + unmatched trailing quotes; FakeEars possessive
path uses the cleaner instead of rstrip("."). Base loop: loop129b.

## Sealed case files (sha256)

- t1-cases.json (44 NEW teach sentences, written before any run):
  98103743c0e7ff2381dca87c7c9dd75830bab9f2b21dd480db54e065f92b9a0e
- cases136.json (red team 136 sealed set, read-only, never overwritten):
  ff141707e65af8b416a45151b311656ad299789f9eb710463356029d369d0380
- loop140-config.json (loop129b config + 2 renamed plug strings):
  50a95cc273dffb601ead526fc4ce866667772cd214179cbd23dee4049ab1a46a

## Marks

- T1 NEW probe (artifacts/fable-fix140-20260922/t1-cases.json, 44 teach
  sentences: possessive + bench73 + bench92 frames with emoji/symbol tails,
  unmatched/matched quotes, abbrev endings incl. 7 symbol-in-name values
  Either/Or Frost/Nixon Frankfurt/Main A/UX FutureSex/LoveSounds
  Speakerboxxx/The Love Below): every value stored exactly, 0 wrong writes.
  Bar: 44/44 OK + 5/5 subject-span unit checks.
- T2 red team 136 re-run (sealed cases136.json, daemon factory swapped to
  loop140, artifacts never overwritten): C117 C118 C119 C126 C140 exact
  expected triples; every 136 case that was OK stays OK (119/119).
- T3 marks123 all suites identical verdicts to loop129b; Fable-Edit /
  old fresh / bench121 per-item identical (via loop129b_bench by import,
  class/config swapped, outputs into artifact dir only).
- T4 whole registered wave < 25 min wall-clock, Mac CPU, OMP_NUM_THREADS=1
  MKL_NUM_THREADS=1.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix140_t1.py --out artifacts/fable-fix140-20260922
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix140_redteam136.py --out artifacts/fable-fix140-20260922
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop140_agent.py --config artifacts/fable-fix140-20260922/loop140-config.json --out artifacts/fable-fix140-20260922/marks123 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop129b_agent.py --config artifacts/fable-fix129-20260922/loop129b-config.json --out artifacts/fable-fix140-20260922/marks123-129b --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix140_bench.py --run
