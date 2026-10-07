"""Model registry: name -> class. Constructors are Cls(vocab, **cfg) (cfg = the --cfg JSON dict)."""
import torch
from custom_io.data import CharVocab
from custom_io.models.plain_tf import PlainTF

MODELS = {'plain_tf': PlainTF}
# designs from custom_io/PASS-MARKS.md, imported lazily so each lives in its own file: name -> 'module:Class'
LAZY = {
    'register_loop': 'custom_io.models.register_loop:RegisterLoop',     # A (steps=True) and A0 (steps=False)
    'ledger': 'custom_io.models.ledger:Ledger',                         # B (Ledger-lite)
    'plain_tf_steps': 'custom_io.models.plain_tf_steps:PlainTFSteps',   # writes steps then ' # ' answer; C1' decode
    'plain_tf_steps_g': 'custom_io.models.plain_lm:PlainStepsG',        # 8a: plain_tf_steps with a free feed-forward width
    'plain_lm': 'custom_io.models.plain_lm:PlainLM',                    # 8a: the plain LLM recipe arm (next-char loss on web text + question rows)
    'tool': 'custom_io.models.tool:Tool',                               # T1: B2 with the calculator outside (talker writes calls)
}
NAMES = sorted(set(MODELS) | set(LAZY))


def get_class(name):
    if name not in MODELS:
        mod, cls = LAZY[name].split(':')
        MODELS[name] = getattr(__import__(mod, fromlist=[cls]), cls)
    return MODELS[name]


def build(name, vocab, **cfg):
    return get_class(name)(vocab, **cfg)


def load_model(path, device='cpu'):
    """Rebuild a model from a train.py checkpoint.pt."""
    ck = torch.load(path, map_location=device)
    m = build(ck['name'], CharVocab(ck['chars']), **ck['cfg'])
    m.load_state_dict(ck['model'])
    return m.to(device).eval()
