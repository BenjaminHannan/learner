"""Model registry: name -> class. Constructors are Cls(vocab, **cfg) (cfg = the --cfg JSON dict)."""
import torch
from custom_io.data import CharVocab
from custom_io.models.plain_tf import PlainTF

MODELS = {'plain_tf': PlainTF}


def build(name, vocab, **cfg):
    return MODELS[name](vocab, **cfg)


def load_model(path, device='cpu'):
    """Rebuild a model from a train.py checkpoint.pt."""
    ck = torch.load(path, map_location=device)
    m = build(ck['name'], CharVocab(ck['chars']), **ck['cfg'])
    m.load_state_dict(ck['model'])
    return m.to(device).eval()
