"""WiredModel: frozen TinyLM stand-in -> reader -> looped core -> action heads (+ prefix talker), and the host loop.

claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import torch
from torch import nn
import torch.nn.functional as F

from . import tools
from .actions import Action
from .core import LatentCore
from .heads import ActionHeads, ActionLogits, KINDS, OPS, NEG
from .notebook import MAX_SLOTS, Notebook, NotebookError
from .reader import ContextualReader
from .talker import PrefixAdapter, Talker
from .tinylm import Tokenizer, TinyLM
from .workspace import SEGMENTS, Workspace

CONFIG_KEYS = ("n_loops", "d_lm")


@dataclass
class StepSpec:
    """One decision point: what the model sees (question, notebook, earlier results) and the gold action."""
    question: str
    notebook: list
    results: list = field(default_factory=list)   # Fractions from earlier CALC steps
    gold: Action | None = None
    answer_text: str | None = None                # for ANSWER steps (talker target)


@dataclass
class Batch:
    ws: Workspace
    reg_pool: torch.Tensor
    reg_present: torch.Tensor
    slot_pool: torch.Tensor
    slot_present: torch.Tensor
    span_ok: torch.Tensor
    registries: list
    offsets: list
    specs: list


class WiredModel(nn.Module):
    def __init__(self, lm: TinyLM, tok: Tokenizer, n_loops: int = 4):
        super().__init__()
        self.tok, self.lm = tok, lm
        self.reader = ContextualReader(lm.d_model)
        self.core = LatentCore(n_loops=n_loops)
        self.heads = ActionHeads()
        self.adapter = PrefixAdapter(lm.d_model)
        self.talker = Talker(lm, self.adapter)
        self._cache: dict = {}
        assert not any(p.requires_grad for p in lm.parameters()), "the LM must be frozen"

    # ---------------------------------------------------------------- parameters
    def trainable_parameters(self):
        return [p for n, p in self.named_parameters() if not n.startswith("lm.")]

    def trainable_state(self):
        return {n: p.detach().clone() for n, p in self.named_parameters() if not n.startswith("lm.")}

    def trainable_hash(self) -> str:
        h = hashlib.sha256()
        for n, p in sorted((n, p) for n, p in self.named_parameters() if not n.startswith("lm.")):
            h.update(n.encode()); h.update(p.detach().contiguous().numpy().tobytes())
        return h.hexdigest()

    def count(self):
        tr = sum(p.numel() for p in self.trainable_parameters())
        lm = sum(p.numel() for p in self.lm.parameters())
        return {"lm_stand_in_frozen": lm, "trainable": tr, "total": lm + tr,
                **{k: sum(p.numel() for p in getattr(self, k).parameters())
                   for k in ("reader", "core", "heads", "adapter")}}

    # ---------------------------------------------------------------- host side: rows of a step
    def _text(self, text: str):
        """Frozen-LM hidden states for one text segment (bos dropped). Cached: the LM never changes."""
        if text not in self._cache:
            ids, offsets = self.tok.encode(text)
            x = torch.tensor([[self.tok.bos_id] + ids])
            with torch.no_grad():
                h = self.lm.hidden(x, torch.ones_like(x, dtype=torch.bool))[0, 1:]
            self._cache[text] = (h, offsets)
        return self._cache[text]

    def _step_rows(self, spec: StepSpec):
        hs, seg, crd = [], [], []
        qh, qoff = self._text(spec.question)
        n = qh.shape[0]
        hs.append(qh); seg += [[SEGMENTS["question"], SEGMENTS["text"]]] * n
        crd += [[0., float(i), -1.] for i in range(n)]
        registry = tools.build_registry(spec.question, self.tok)
        slot_rows = []
        for s, text in enumerate(spec.notebook):
            h, _ = self._text(text)
            start = sum(x.shape[0] for x in hs)
            hs.append(h); seg += [[SEGMENTS["notebook"], SEGMENTS["text"]]] * h.shape[0]
            crd += [[float(s), float(i), -1.] for i in range(h.shape[0])]
            slot_rows.append(list(range(start, start + h.shape[0])))
        for k, value in enumerate(spec.results):
            h, _ = self._text("= " + tools.render(value))
            start = sum(x.shape[0] for x in hs)
            hs.append(h); seg += [[SEGMENTS["tool_result"], SEGMENTS["text"]]] * h.shape[0]
            crd += [[float(k), float(i), -1.] for i in range(h.shape[0])]
            registry.append(tools.Entry(f"result:{k + 1}", value, list(range(start, start + h.shape[0])), "result"))
        return (torch.cat(hs), torch.tensor(seg), torch.tensor(crd), registry, slot_rows, n, qoff)

    def collate(self, specs) -> Batch:
        rows = [self._step_rows(s) for s in specs]
        B, N = len(rows), max(r[0].shape[0] for r in rows)
        C = tools.MAX_LITERALS + tools.MAX_RESULTS
        hid = torch.zeros(B, N, self.lm.d_model)
        segment = torch.zeros(B, N, 2, dtype=torch.long)
        coords = torch.full((B, N, 3), -1.0)
        valid = torch.zeros(B, N, dtype=torch.bool)
        reg_pool, slot_pool = torch.zeros(B, C, N), torch.zeros(B, MAX_SLOTS, N)
        reg_present, slot_present = torch.zeros(B, C, dtype=torch.bool), torch.zeros(B, MAX_SLOTS, dtype=torch.bool)
        span_ok = torch.zeros(B, N, dtype=torch.bool)
        for i, (h, sg, cr, reg, slots, nq, _) in enumerate(rows):
            k = h.shape[0]
            hid[i, :k], segment[i, :k], coords[i, :k], valid[i, :k] = h, sg, cr, True
            span_ok[i, :nq] = True
            for c, e in enumerate(reg):
                reg_pool[i, c, e.token_indices] = 1.0 / len(e.token_indices); reg_present[i, c] = True
            for s, r in enumerate(slots):
                slot_pool[i, s, r] = 1.0 / len(r); slot_present[i, s] = True
        ws = Workspace(self.reader(hid, valid), segment, coords, valid)
        return Batch(ws, reg_pool, reg_present, slot_pool, slot_present, span_ok,
                     [r[3] for r in rows], [r[6] for r in rows], list(specs))

    def logits(self, batch: Batch, n_loops=None):
        out = self.core(batch.ws, n_loops)
        act = self.heads(out.tokens, out.registers, batch.reg_pool, batch.reg_present,
                         batch.slot_pool, batch.slot_present, batch.span_ok)
        return out, act

    # ---------------------------------------------------------------- loss
    def step_loss(self, batch: Batch, talker_weight: float = 0.5, parts: bool = False):
        out, a = self.logits(batch)
        gold = [s.gold for s in batch.specs]
        B = len(gold)
        idx = lambda kinds: [i for i, g in enumerate(gold) if g.kind in kinds]
        t = lambda xs: torch.tensor(xs, dtype=torch.long)
        zero = torch.zeros(())
        L = {}
        L["kind"] = F.cross_entropy(a.kind, t([KINDS.index(g.kind) for g in gold]))
        calc, wr, ans = idx(("CALC",)), idx(("NOTE_WRITE",)), idx(("ANSWER",))
        def ce(logit, rows, tg): return F.cross_entropy(logit[rows], t(tg)) if rows else zero
        L["arith"] = ce(a.arith, calc, [OPS.index(gold[i].op) for i in calc])
        L["ptr_a"] = ce(a.ptr_a, calc + ans, [gold[i].ptr_a for i in calc + ans])
        L["ptr_b"] = ce(a.ptr_b, calc, [gold[i].ptr_b for i in calc])
        L["slot"] = ce(a.slot, wr, [MAX_SLOTS if gold[i].slot >= len(batch.specs[i].notebook) else gold[i].slot for i in wr])
        L["start"] = ce(a.start, wr, [gold[i].start for i in wr])
        L["end"] = ce(a.end, wr, [gold[i].end for i in wr])
        if ans:
            ids = [self.tok.encode(batch.specs[i].answer_text)[0] + [self.tok.eos_id] for i in ans]
            tgt = torch.full((len(ans), max(map(len, ids))), -100, dtype=torch.long)
            for r, x in enumerate(ids): tgt[r, :len(x)] = torch.tensor(x)
            L["talker"] = self.talker.loss(out.registers[ans], tgt)
        else:
            # keep the adapter in the graph so every trainable module always gets a gradient path
            L["talker"] = self.adapter(out.registers).sum() * 0.0
        total = sum(v for k, v in L.items() if k != "talker") + talker_weight * L["talker"]
        return (total, L) if parts else total

    # ---------------------------------------------------------------- decode and host loop
    @torch.no_grad()
    def decode(self, batch: Batch, n_loops=None):
        out, a = self.logits(batch, n_loops)
        actions = []
        for i, spec in enumerate(batch.specs):
            kind = KINDS[int(a.kind[i].argmax())]
            pa = int(a.ptr_a[i].argmax())
            if kind == "CALC":
                lb = a.ptr_b[i].clone(); lb[pa] = NEG                      # host mask: no duplicate reference
                actions.append(Action("CALC", OPS[int(a.arith[i].argmax())], pa, int(lb.argmax())))
            elif kind == "NOTE_WRITE":
                st = int(a.start[i].argmax())
                le = a.end[i].clone(); le[:st] = NEG; le[st + tools_span():] = NEG   # end >= start, short span
                sl = int(a.slot[i].argmax())
                sl = len(spec.notebook) if sl >= MAX_SLOTS else sl           # last logit = NEW
                actions.append(Action("NOTE_WRITE", slot=sl, start=st, end=int(le.argmax())))
            elif kind == "ANSWER":
                actions.append(Action("ANSWER", ptr_a=pa))
            else:
                actions.append(Action("DONE"))
        return actions, out


def tools_span():
    from .notebook import MAX_ENTRY_TOKENS
    return MAX_ENTRY_TOKENS


@dataclass
class EpisodeResult:
    status: str                       # "ANSWER" | "DONE" | "FAIL:<code>"
    actions: list
    value: Fraction | None = None
    text: str | None = None
    traces: list = field(default_factory=list)
    notebook: Notebook | None = None


@torch.no_grad()
def run_episode(model: WiredModel, question: str, notebook: Notebook, n_loops=None, say: bool = True) -> EpisodeResult:
    """Greedy episode: core -> action -> host executes -> result re-enters -> ... (at most MAX_CALLS tool calls)."""
    model.eval()
    results, actions, traces = [], [], []
    registry0 = tools.build_registry(question, model.tok)
    _, offsets = model.tok.encode(question)
    for call in range(tools.MAX_CALLS + 2):
        spec = StepSpec(question, notebook.texts(), list(results))
        batch = model.collate([spec])
        (act,), out = model.decode(batch, n_loops)
        actions.append(act)
        if act.kind == "CALC":
            reg = batch.registries[0]
            tr = tools.execute(act.op, act.ptr_a, act.ptr_b, reg, len(results))
            traces.append(tr)
            if tr.status != "OK":
                return EpisodeResult(f"FAIL:{tr.error_code}", actions, traces=traces, notebook=notebook)
            results.append(tr.value)
        elif act.kind == "NOTE_WRITE":
            try:
                notebook.apply_write(act.slot, (act.start, act.end), question, offsets, model.tok)
            except NotebookError as err:
                return EpisodeResult(f"FAIL:{err}", actions, traces=traces, notebook=notebook)
        elif act.kind == "ANSWER":
            reg = batch.registries[0]
            if not (0 <= act.ptr_a < len(reg)):
                return EpisodeResult("FAIL:BAD_REFERENCE", actions, traces=traces, notebook=notebook)
            text = model.tok.decode(model.talker.generate(out.registers)[0]) if say else None
            return EpisodeResult("ANSWER", actions, reg[act.ptr_a].value, text, traces, notebook)
        else:
            return EpisodeResult("DONE", actions, traces=traces, notebook=notebook)
    return EpisodeResult("FAIL:MAX_CALLS", actions, traces=traces, notebook=notebook)


# -------------------------------------------------------------------- gold unrolling
def gold_steps(episode, tok) -> list:
    """Execute the gold actions on the host to get the Workspace inputs at every step (teacher forcing)."""
    nb, results, steps = Notebook.from_facts(list(episode.notebook)), [], []
    _, offsets = tok.encode(episode.question)
    for g in episode.gold:
        text = tools.render(episode.key) if g.kind == "ANSWER" else None
        steps.append(StepSpec(episode.question, nb.texts(), list(results), g, text))
        if g.kind == "CALC":
            reg = tools.build_registry(episode.question, tok) + [
                tools.Entry(f"result:{k + 1}", v, [0], "result") for k, v in enumerate(results)]
            tr = tools.execute(g.op, g.ptr_a, g.ptr_b, reg, len(results))
            assert tr.status == "OK", tr
            results.append(tr.value)
        elif g.kind == "NOTE_WRITE":
            nb.apply_write(g.slot, (g.start, g.end), episode.question, offsets, tok)
    return steps


# -------------------------------------------------------------------- checkpoint
def save_checkpoint(model: WiredModel, path, extra=None):
    torch.save({"claims": "plumbing only; toy data; not an eval",
                "lm_fingerprint": model.lm.fingerprint(),
                "config": {"n_loops": model.core.n_loops, "d_lm": model.lm.d_model},
                "trainable": model.trainable_state(), "extra": extra or {}}, path)


def load_checkpoint(model: WiredModel, path):
    blob = torch.load(path, map_location="cpu", weights_only=False)
    if blob["lm_fingerprint"] != model.lm.fingerprint():
        raise ValueError("checkpoint was made with a different LM")
    if blob["config"] != {"n_loops": model.core.n_loops, "d_lm": model.lm.d_model}:
        raise ValueError("checkpoint constructor config differs")
    own = {n for n, _ in model.named_parameters() if not n.startswith("lm.")}
    if set(blob["trainable"]) != own:
        raise ValueError("checkpoint parameter set differs")
    with torch.no_grad():
        for n, p in model.named_parameters():
            if n in blob["trainable"]: p.copy_(blob["trainable"][n])
    return blob["extra"]
