"""SleepReplay: verified-experience buffer, 50/30/20 replay mix, and a night step that updates weights.

Records are checked by re-running the calculator against the generator's key: that is V1-key
checking in the sleep design's terms, never independent checking. The notebook is locked during a night.
Arms: S (checked mix), PF (day records only, plain fine-tune), SU (unchecked own attempts), F0 (no update).
claims: plumbing only; toy data; not an eval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import random
import torch

from .model import WiredModel, StepSpec, gold_steps, run_episode
from .notebook import Notebook
from .train import fit

CHECKER = "V1-key"
CHECKER_HASH = hashlib.sha256(b"wired_demo.toyworld generator key v1").hexdigest()
SHARES = {"day": 0.5, "earlier": 0.3, "anchor": 0.2}


@dataclass
class ExperienceRecord:
    episode_spec: object            # toyworld.Episode (the question, notebook and gold trace)
    step_targets: list              # list[StepSpec] used for replay
    class_: str                     # "A_correct" (model got it right) | "B_corrected" (gold trace)
    checker: str
    checker_hash: str
    day: int
    family: str
    input_hash: str


def input_hash(ep) -> str:
    return hashlib.sha256((ep.question + "|" + "|".join(ep.notebook)).encode()).hexdigest()


class Buffer:
    """Per-family cap, dedup by input hash, records stored per night."""
    def __init__(self, per_family_cap: int = 64):
        self.cap, self.nights, self.seen = per_family_cap, {}, set()

    def add(self, night: int, rec: ExperienceRecord) -> bool:
        if rec.input_hash in self.seen: return False
        if sum(r.family == rec.family for rs in self.nights.values() for r in rs) >= self.cap: return False
        self.seen.add(rec.input_hash); self.nights.setdefault(night, []).append(rec)
        return True

    def before(self, night: int):
        return {k: v for k, v in self.nights.items() if k < night}


def day_records(model: WiredModel, episodes, day: int, tok, checked: bool = True):
    """The day: attempt each episode with frozen weights, check against the key, store A (right) or B (gold trace)."""
    out = []
    for ep in episodes:
        r = run_episode(model, ep.question, Notebook.from_facts(list(ep.notebook)), say=False)
        right = r.status == "ANSWER" and r.value == ep.key
        if checked:
            cls = "A_correct" if right else "B_corrected"
            out.append(ExperienceRecord(ep, gold_steps(ep, tok), cls, CHECKER, CHECKER_HASH, day, ep.family, input_hash(ep)))
        else:   # SU: unchecked; replays the model's OWN actions whatever they were
            out.append(ExperienceRecord(ep, own_steps(ep, r, tok), "unchecked", "none", "", day, ep.family, input_hash(ep)))
    return out


def own_steps(ep, result, tok) -> list:
    """Replay targets made of the model's own actions (used only by the unchecked SU control)."""
    from . import tools
    nb, results, steps = Notebook.from_facts(list(ep.notebook)), [], []
    traces = iter(result.traces)
    _, offsets = tok.encode(ep.question)
    for a in result.actions:
        text = tools.render(result.value) if a.kind == "ANSWER" and result.value is not None else None
        if a.kind == "ANSWER" and text is None: break
        steps.append(StepSpec(ep.question, nb.texts(), list(results), a, text))
        if a.kind == "CALC":
            tr = next(traces)
            if tr.status != "OK": break
            results.append(tr.value)
        elif a.kind == "NOTE_WRITE":
            try: nb.apply_write(a.slot, (a.start, a.end), ep.question, offsets, tok)
            except Exception: break
    return steps


def assemble_mix(day, earlier: dict, anchor, U: int, rng: random.Random):
    """U records: 50% day (A:B at most 1:2), 30% earlier nights (uniform per night), 20% anchor.
    With no earlier nights yet its share goes to the day records (documented, not hidden)."""
    n_day, n_early, n_anchor = round(U * SHARES["day"]), round(U * SHARES["earlier"]), U - round(U * .5) - round(U * .3)
    if not earlier: n_day, n_early = n_day + n_early, 0
    A = [r for r in day if r.class_ == "A_correct"]; B = [r for r in day if r.class_ != "A_correct"]
    day_pick = rng.sample(B, min(len(B), n_day)) if B else []
    room = max(0, 2 * len(day_pick)) if day_pick else n_day            # keep A <= half of B
    day_pick += rng.sample(A, min(len(A), n_day - len(day_pick), room if day_pick else n_day))
    pool = [r for rs in earlier.values() for r in rs]
    early = [rng.choice(earlier[rng.choice(sorted(earlier))]) for _ in range(n_early)] if pool else []
    anch = [rng.choice(anchor) for _ in range(n_anchor)]
    return {"day": day_pick, "earlier": early, "anchor": anch}


@dataclass
class NightReport:
    arm: str
    updates: int
    examples: int
    distinct: int
    loss_before: float
    loss_after: float
    trainable_hash_before: str
    trainable_hash_after: str
    lm_fingerprint: str
    notebook_hash: str
    shares: dict = field(default_factory=dict)


def _mean_loss(model, steps):
    model.eval()
    with torch.no_grad():
        return float(sum(model.step_loss(model.collate(steps[i:i + 16])) * len(steps[i:i + 16])
                         for i in range(0, len(steps), 16)) / len(steps))


def night(model: WiredModel, mix: dict, notebook: Notebook, steps: int = 32, lr: float = 1e-4,
          arm: str = "S", seed: int = 0) -> NightReport:
    records = [r for k in ("day", "earlier", "anchor") for r in mix[k]]
    spec = [s for r in records for s in r.step_targets]
    before, fp = model.trainable_hash(), model.lm.fingerprint()
    l0 = _mean_loss(model, spec) if spec else float("nan")
    with notebook.write_lock():            # sleep cannot write the main notebook
        nb_hash = notebook.hash()
        if arm != "F0" and spec:
            opt = torch.optim.AdamW(model.trainable_parameters(), lr=lr, weight_decay=0.0)
            fit(model, spec, steps, batch=8, seed=seed, optimizer=opt)
    done = 0 if arm == "F0" else steps
    return NightReport(arm, done, len(records), len({r.input_hash for r in records}), l0,
                       _mean_loss(model, spec) if spec else float("nan"), before, model.trainable_hash(),
                       fp, nb_hash, {k: len(v) for k, v in mix.items()})


def arms_matched(reports) -> bool:
    """Controls hook: compared arms must have the same update count and the same number of replayed records (F0 makes no update)."""
    live = [r for r in reports if r.arm != "F0"]
    return len({r.updates for r in live}) == 1 and len({r.examples for r in live}) == 1


def plain_mix(day, U: int, rng: random.Random):
    """PF control: day records only, same number of records as the S mix."""
    return {"day": [day[i % len(day)] for i in rng.sample(range(max(U, len(day))), U)], "earlier": [], "anchor": []}
