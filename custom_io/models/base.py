"""Interface every model follows."""
import torch
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

    Optional split of generate() into reasoner and talker, used by the donor-swap lesion (evalx.donor_eval):
    state(batch, loops=None)  -> the reasoner's final state for the batch: a tensor or tuple of tensors whose first
                              dim is the batch; everything the talker receives from the reasoner. loops=K = run K
                              reasoner loops instead of the trained number. Must not depend on batch['ans_*'].
    talk(state, batch)     -> list[str], the talker's greedy answers given `state`. `batch` is the CURRENT rows'
                              batch (not the rows the state came from): the talker may read from it only what it is
                              allowed to read directly (e.g. a copy source) plus shapes/lengths, and must take
                              lengths from it, never from the state. Under donor_eval `state` comes from a DIFFERENT
                              row of the same family (a time/length dim in it is padded to the common length of the
                              two batches, so it lines up with batch['prompt_ids'] in shape only).
    supports_donor()       -> True iff both state() and talk() are implemented (default False).
    A model with both gets generate() for free: talk(state(batch, loops), batch), where the lesions 'loops:K',
    'zero_state' (zeros like state) and 'shuffle_state' (state rolled by one row) are applied to the state. List the
    ones you want in LESIONS; override generate() for anything else.
    """
    LESIONS = []

    def __init__(self, vocab):
        super().__init__()
        self.vocab = vocab

    def loss(self, batch):
        raise NotImplementedError

    def generate(self, batch, lesion=None):
        if not self.supports_donor():
            raise NotImplementedError
        name, arg = self.check_lesion(lesion)
        st = self.state(batch, arg if name == 'loops' else None)
        if name in ('zero_state', 'shuffle_state'):
            f = torch.zeros_like if name == 'zero_state' else (lambda x: x.roll(1, 0))
            st = tuple(map(f, st)) if isinstance(st, tuple) else f(st)
        return self.talk(st, batch)

    def state(self, batch, loops=None):
        raise NotImplementedError

    def talk(self, state, batch):
        raise NotImplementedError

    def supports_donor(self):
        """True if state() and talk() are both overridden (needed by evalx.donor_eval)."""
        cls = type(self)
        return cls.state is not Model.state and cls.talk is not Model.talk

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
