"""RegisterLoopScratch: student A with its 7 scratch slots taught (Ben's directive, 2026-10-15: "teach the
model what the scratch word should look like").

Same architecture, same answer-register loss as RegisterLoop. The one change: the scratch slots stop being
free latent space. At round r the scratch slots are read out through the SAME tied talker readout and trained
to hold the NEXT worked-step value (the value the answer registers must say at round r + 1), encoded exactly
like an answer: units-first chars, the value truncated to MAX_ANS chars first, then to the 7 scratch slots,
EOS appended when it fits. The talker still reads only the answer registers at generate time. The point of
the arm is the training signal, plus that the model's planned next value becomes readable (scratch_strings).

Lesions 'scratch_zero' / 'scratch_shuffle' (optional ':K' = apply after round K, default after round 1)
damage only the scratch slots mid-computation, so an eval can measure whether the model actually uses its
scratch: if scrambling it costs nothing, the supervision never made the scratch load-bearing. The same
scramble can be run on the base model through rounds(S0=..., start=...) for the control arm.
"""
import torch
import torch.nn.functional as F
from custom_io import diag_register as dg
from custom_io.data import EOS, MAX_ANS
from custom_io.models.base import parse_lesion
from custom_io.models.register_loop import RegisterLoop


class RegisterLoopScratch(RegisterLoop):
    LESIONS = RegisterLoop.LESIONS + ['scratch_zero', 'scratch_shuffle']

    def __init__(self, vocab, *a, scratch_weight=1.0, **kw):
        super().__init__(vocab, *a, **kw)
        self.scratch_weight = float(scratch_weight)
        self._sc = {}

    @property
    def n_scratch(self):
        return self.codes().shape[0] - self.n_reg

    # ---- targets: scratch at round r holds worked value r + 1 (clamped at the last value) ----
    def scratch_row_targets(self, row):
        """[R,n_scratch] int16: next-step value per round, same encoding as row_targets, truncated to the slots."""
        key = (row.get('id'), row['prompt'], row['answer'])
        t = self._sc.get(key)
        if t is None:
            vals = dg.step_values(row, self.use_steps)
            ns = self.n_scratch
            t = torch.full((self.n_loops, ns), -100, dtype=torch.int16)
            for r in range(self.n_loops):
                ids = self.vocab.encode(vals[min(r + 2, len(vals)) - 1][:MAX_ANS][::-1]) + [EOS]
                keep = min(len(ids), ns)
                t[r, :keep] = torch.tensor(ids[:keep], dtype=torch.int16)
            self._sc[key] = t
        return t

    def scratch_targets(self, rows, device=None):
        """[R,B,n_scratch] long, -100 after the value's chars (and its EOS when it fits)."""
        tg = torch.stack([self.scratch_row_targets(r) for r in rows], 1).long()
        return tg.to(device) if device is not None else tg

    def loss(self, batch):
        dev = batch['prompt_ids'].device
        tg, sg = self.targets(batch['rows'], dev), self.scratch_targets(batch['rows'], dev)
        la, ls = [], []
        for r, S in enumerate(self.rounds(batch)):
            la.append(F.cross_entropy(self.readout(S[:, :self.n_reg]).float().flatten(0, 1),
                                      tg[r].flatten(), ignore_index=-100))
            ls.append(F.cross_entropy(self.readout(S[:, self.n_reg:]).float().flatten(0, 1),
                                      sg[r].flatten(), ignore_index=-100))
        a, s = sum(la) / len(la), sum(ls) / len(ls)
        return a + self.scratch_weight * s, {'loss_r1': la[0].detach(), 'loss_last': la[-1].detach(),
                                             'loss_ans': a.detach(), 'loss_scratch': s.detach()}

    # ---- readability: what the scratch slots currently "say" each round ----
    @torch.no_grad()
    def scratch_strings(self, batch):
        """Per round, the scratch slots decoded through the talker (units-first, like talk())."""
        was = self.training
        self.eval()
        out = [[self.vocab.decode(r)[::-1] for r in self.readout(S[:, self.n_reg:]).argmax(-1).tolist()]
               for S in self.rounds(batch)]
        self.train(was)
        return out

    # ---- lesions on the scratch slots only, applied mid-computation ----
    @torch.no_grad()
    def generate(self, batch, lesion=None):
        name, arg = parse_lesion(lesion)
        if name not in ('scratch_zero', 'scratch_shuffle'):
            return super().generate(batch, lesion)
        self.check_lesion(lesion)
        after = min(1 if arg is None else arg, self.n_loops)     # scramble once this many rounds are done

        def damaged(S):
            S = S.clone()
            if name == 'scratch_zero':
                S[:, self.n_reg:] = 0
            else:
                S[:, self.n_reg:] = S[:, self.n_reg:].roll(1, 0)
            return S

        if after == 0:
            S0 = damaged(self.codes().expand(batch['prompt_ids'].shape[0], -1, -1))
            S = S0
            for S in self.rounds(batch, S0=S0, start=0):
                pass
            return self.talk(S[:, :self.n_reg], batch)
        S = None
        for r, S in enumerate(self.rounds(batch)):
            if r + 1 >= after:
                break
        S = damaged(S)
        for S in self.rounds(batch, S0=S, start=after):
            pass
        return self.talk(S[:, :self.n_reg], batch)
