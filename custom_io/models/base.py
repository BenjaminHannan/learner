"""Interface every model follows."""
import torch.nn as nn


def parse_lesion(lesion):
    """None -> (None, None); 'zero_state' -> ('zero_state', None); 'loops:3' -> ('loops', 3)."""
    if lesion is None:
        return None, None
    name, _, arg = lesion.partition(':')
    return name, (int(arg) if arg else None)


class Model(nn.Module):
    """Contract used by train.py / evalx.py.

    loss(batch)            -> scalar tensor, or (scalar, {name: float/tensor}) with aux losses to log.
    generate(batch, lesion=None) -> list[str], one answer per row, in batch['rows'] order, greedy, no labels used.
    n_params()             -> trainable parameters (shared/tied weights counted once).
    LESIONS                -> names this model supports among 'shuffle_state' (permute the reasoner's final
                              state across the batch before the talker), 'zero_state', 'loops' ('loops:K' =
                              run the reasoner K loops instead of the trained number). Any model with an
                              `n_loops` attribute is also swept over loops:K by train.py.
    self.vocab             -> CharVocab (set by __init__); batches follow data.collate.
    """
    LESIONS = []

    def __init__(self, vocab):
        super().__init__()
        self.vocab = vocab

    def loss(self, batch):
        raise NotImplementedError

    def generate(self, batch, lesion=None):
        raise NotImplementedError

    def n_params(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)

    def check_lesion(self, lesion):
        """Validate and parse a lesion string; call first thing in generate()."""
        name, arg = parse_lesion(lesion)
        ok = name is None or name in {l.split(':')[0] for l in self.LESIONS} or (name == 'loops' and hasattr(self, 'n_loops'))
        if not ok:
            raise ValueError(f'{type(self).__name__} does not support lesion {lesion!r}; has {self.LESIONS}')
        if name == 'loops' and arg is None:
            raise ValueError("loops lesion needs a count, e.g. 'loops:2'")
        return name, arg
