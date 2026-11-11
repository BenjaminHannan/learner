"""CPU check before any B3 run: under the B3 caps the B3 model's thinking-round cap must be the sealed 32 (H1 addendum 21; big-run PLAN.md sec. 5,
mark B3-4; spec design/8a-g-gemma-growth-2026-10-08.md addendum O). Builds a tiny B3 (no Gemma) after caps.apply, exactly as train.py orders it.
  python b3_capcheck.py SRC CAPS_JSON      exit 0 = cap 32, 1 = anything else"""
import json, sys
sys.path.insert(0, sys.argv[1])
from custom_io.g8a import caps as CP
CP.apply(json.load(open(sys.argv[2])))
from custom_io.data import CharVocab
from custom_io.g8a.b3_cost import SW, SMALL
from custom_io.models import build
m = build('b3', CharVocab.build([]), **dict(SMALL, n_loops=12), **{k: v for k, v in SW.items() if k != 'eg_embed'})
print('B3 thinking-round cap under these caps:', m.cap, '(sealed: 32)')
sys.exit(0 if m.cap == 32 else 1)
