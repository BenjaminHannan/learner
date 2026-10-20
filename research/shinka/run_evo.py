#!/usr/bin/env python3
"""ShinkaEvolve run for the card-writer binding trial (research/shinka/CARD.md).

Additions on top of stock ShinkaEvolve, all made from this script and none
inside the ShinkaEvolve package:
  1. Cost ledger: every Anthropic call's token usage and dollars go to the
     trial-wide results/TRIAL_LEDGER.jsonl (ledger.py). A call is refused when
     the trial total could pass $4.50 (Shinka's own max_api_costs cap is lower).
  2. Effort cap: Opus 5.5 runs at effort "medium" to keep thinking spend bounded.
  3. Strange slot: with probability STRANGE_P a parent is drawn from the
     correct programs (score >= baseline - noise) that are most behaviourally
     different from the current top scorers, by distance in the evaluator's
     behaviour descriptor (key/value sensitivity to each token role), not by score.
  4. Known-ideas list: research/shinka/KNOWN_SHORT.md is put in the system
     message as "do not reproduce these".

Run (from the repo root, embedding server already running on :8765):
  ANTHROPIC_API_KEY=$LEARNER_ANTHROPIC_API_KEY OPENAI_API_KEY=unused \
    /home/user/shinka_venv/bin/python research/shinka/run_evo.py --run evo1
Run the trial's paid tools one at a time (ledger.py keeps an in-process total).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
import threading
import time
from pathlib import Path

import os

# One price list for the whole trial: the bundled catalog plus shinka_local.patch, the
# same one novelty_judge.py and the reservation arithmetic use (no live models.dev fetch).
os.environ["SHINKA_PRICING_MODE"] = "offline"

import shinka.llm.query as shinka_query  # noqa: E402
from shinka.core import EvolutionConfig, ShinkaEvolveRunner  # noqa: E402
from shinka.database import DatabaseConfig  # noqa: E402
from shinka.database import parents as shinka_parents  # noqa: E402
from shinka.launch import LocalJobConfig  # noqa: E402
from shinka.llm.providers.pricing import calculate_cost  # noqa: E402

HERE = Path(__file__).resolve().parent
TASK = HERE / "task"
sys.path.insert(0, str(HERE))
import ledger  # noqa: E402

MODEL = "claude-opus-5-5"     # Ben's instruction, 2026-10-20: use Opus 5.5
STRANGE_P = 0.25
SCORE_FLOOR = 0.497 - 0.06    # CARD.md: baseline noise-seed mean minus the noise mark
EFFORT = {MODEL: "medium"}
JUDGE_RESERVE_USD = 1.60     # CARD.md section 5: kept back for the novelty judge
MAX_PROPOSAL_JOBS = 2
MAX_TOKENS = 12000             # room for Opus 5.5's always-on thinking plus a full rewrite
# Reserved per mutation call: 30k input (generous for Shinka's prompts) + a full output.
# Calls are refused when the trial ledger, minus calls in flight, cannot absorb one more.
MAX_CALL_USD = sum(calculate_cost(MODEL, 30_000, MAX_TOKENS))
RUN_TAG = "evolve"             # set to "evolve:<run>" in main()
EVO = None                     # the run's EvolutionConfig, so the backstop can end the run
_inflight_lock = threading.Lock()
_inflight = 0.0


def _release() -> None:
    global _inflight
    with _inflight_lock:
        _inflight -= MAX_CALL_USD


def _record(model: str, usage) -> None:
    inp, out = usage.input_tokens, usage.output_tokens
    tot = ledger.record(model, RUN_TAG, inp, out, sum(calculate_cost(model, inp, out)))
    if tot > ledger.HARD_STOP_USD:
        print(f"HARD STOP: trial ledger ${tot:.3f} > ${ledger.HARD_STOP_USD}", flush=True)


def _wrap(fn, is_async: bool):
    def prep(model, kwargs):
        global _inflight
        if model in EFFORT:
            kwargs.setdefault("output_config", {"effort": EFFORT[model]})
        with _inflight_lock:
            if ledger.remaining() - JUDGE_RESERVE_USD - _inflight < MAX_CALL_USD:
                # Backstop only; Shinka's own max_api_costs (set in main) normally ends the
                # run first. Refusing the call stops spend without killing running evals,
                # and dropping Shinka's cap to a tiny positive value (Shinka divides by it
                # when logging) makes the runner stop submitting new proposals.
                if EVO is not None:
                    EVO.max_api_costs = 1e-6
                    # (num_generations is left alone: lowering it makes Shinka cancel running
                    # evaluations and in-flight calls, whose spend would then be unrecorded)
                raise RuntimeError(f"trial budget stop: ${ledger.total():.3f} spent")
            _inflight += MAX_CALL_USD

    class _Client:  # proxy that records usage on messages.create
        def __init__(self, client, model):
            self._c, self._m = client, model

        @property
        def messages(self):
            outer = self

            class _M:
                def create(self, **kw):
                    if is_async:
                        async def _await():
                            resp = await outer._c.messages.create(**kw)
                            _record(outer._m, resp.usage)
                            return resp
                        return _await()
                    r = outer._c.messages.create(**kw)
                    _record(outer._m, r.usage)
                    return r
            return _M()

    # One reservation per wrapped query, released exactly once whatever happens inside
    # (Shinka's backoff may call messages.create several times; each call is recorded).
    if is_async:
        async def wrapped(client, model, *a, **kw):
            prep(model, kw)
            try:
                return await fn(_Client(client, model), model, *a, **kw)
            finally:
                _release()
    else:
        def wrapped(client, model, *a, **kw):
            prep(model, kw)
            try:
                return fn(_Client(client, model), model, *a, **kw)
            finally:
                _release()
    return wrapped


shinka_query.query_anthropic = _wrap(shinka_query.query_anthropic, False)
shinka_query.query_anthropic_async = _wrap(shinka_query.query_anthropic_async, True)


# ---------------------------------------------------------------- strange slot
_orig_sample_parent = shinka_parents.CombinedParentSelector.sample_parent
STRANGE_LOG: Path | None = None


def _strange_parent(self, island_idx):
    q = "SELECT id, combined_score, private_metrics FROM programs WHERE correct = 1"
    args: tuple = ()
    if island_idx is not None:
        q += " AND island_idx = ?"
        args = (island_idx,)
    self.cursor.execute(q, args)
    rows = []
    for pid, score, priv in self.cursor.fetchall():
        d = (json.loads(priv) if priv else {}).get("descriptor")
        if score is not None and score >= SCORE_FLOOR and d and all(isinstance(x, (int, float)) for x in d):
            rows.append((pid, score, d))
    if len(rows) < 4:
        return None
    vecs = [r[2] for r in rows]
    dim = len(vecs[0])
    mu = [sum(v[i] for v in vecs) / len(vecs) for i in range(dim)]
    sd = [math.sqrt(sum((v[i] - mu[i]) ** 2 for v in vecs) / len(vecs)) or 1.0 for i in range(dim)]
    z = [[(v[i] - mu[i]) / sd[i] for i in range(dim)] for v in vecs]
    order = sorted(range(len(rows)), key=lambda i: -rows[i][1])
    elite = order[: max(1, min(5, len(order) // 3))]
    def dist(i):
        return min(math.dist(z[i], z[j]) for j in elite)
    candidates = sorted((i for i in range(len(rows)) if i not in elite), key=dist, reverse=True)[:3]
    if not candidates:
        return None
    pick = random.choice(candidates)
    parent = self.get_program(rows[pick][0])
    if parent is None:
        return None
    with STRANGE_LOG.open("a") as f:
        f.write(json.dumps({"t": time.time(), "parent": rows[pick][0],
                            "score": rows[pick][1], "distance": dist(pick)}) + "\n")
    return parent


def sample_parent(self, island_idx=None):
    if random.random() < STRANGE_P:
        try:
            p = _strange_parent(self, island_idx)
            if p is not None:
                return p
        except Exception as exc:  # noqa: BLE001 - never let the slot kill a run
            print(f"strange slot failed: {exc}", flush=True)
    return _orig_sample_parent(self, island_idx)


shinka_parents.CombinedParentSelector.sample_parent = sample_parent


# ---------------------------------------------------------------- task message
def task_message() -> str:
    known = (HERE / "KNOWN_SHORT.md").read_text()
    return f"""You are inventing a NEW memory-writing mechanism for a small neural model.

The model reads text one line at a time. Each line states one fact such as
"Mira's colour is teal", with the person, the relation and the value at
arbitrary positions among filler words. A frozen reader gives one state vector
per token. Your `CardWriter` turns one line's token states into ONE memory card:
a key (used to find the card later) and a value (decoded into the answer).
Later a question "Mira colour?" is turned into a query, cards are scored by
cosine(query, key), and the attention-weighted card value must decode to "teal".

The known failure: the card keeps the VALUE but loses the PERSON. Questions then
fetch the right relation for the wrong person, worst of all for names never seen
in training. The score is the mean held-out accuracy on familiar names and on
novel names, averaged over 3 training seeds. Everything is trained jointly from
scratch with answer-only cross-entropy.

Interface (fixed): class CardWriter(nn.Module) with __init__(self, d, dk) and
forward(states [B, C, L, d], mask [B, C, L] bool) -> (keys [B, C, dk], values [B, C, d]).
Rules (checked automatically; a program that breaks one scores 0):
- each card may depend ONLY on its own line's states (no mixing across lines or visits);
- in eval mode the writer is a pure, deterministic function (no state kept between calls);
- at most 20000 numbers stored in the writer (parameters, buffers, any tensors it keeps);
- imports: only math, torch, torch.nn (as nn), torch.nn.functional (as F); common torch,
  nn, F, torch.linalg and nn.init functions are allowed, module internals are not;
- no names or attributes starting with "_" (except __init__), no getattr/type/exec/open,
  no generators, no code at module top level other than imports, defs and constants;
- each evaluation trains in under ~2 minutes on 1 CPU thread.

NOVELTY IS THE GOAL. Do not reproduce any method in the list below, even under a
new name. Before writing code, think of a mechanism that is NOT on this list and
that you cannot name from the literature. Odd but principled ideas are welcome;
an idea that scores a little worse but is genuinely new is still valuable. In
your description, name the closest known method and say how yours differs.

KNOWN METHODS (do not reproduce):
{known}
"""


def main() -> None:
    global STRANGE_LOG, RUN_TAG, EVO
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="evo1")
    ap.add_argument("--generations", type=int, default=150)
    ap.add_argument("--max-api-usd", type=float, default=2.15)
    a = ap.parse_args()
    out = HERE / "results" / a.run
    out.mkdir(parents=True, exist_ok=True)
    STRANGE_LOG = out / "strange_slot.jsonl"
    RUN_TAG = f"evolve:{a.run}"
    if (out / "programs.sqlite").exists() or ledger.spent_with_tag(RUN_TAG) > 0:
        # resuming would need Shinka's reloaded cost and the ledger to agree; not supported
        raise SystemExit(f"run '{a.run}' already exists; use a new --run name (resume is not supported)")
    # Shinka's own cap normally ends the run: it sits below the point where the backstop
    # in prep() starts refusing calls (judge reserve plus every proposal job in flight).
    # Shinka counts a proposal's cost only when the proposal finishes, so the backstop can
    # fire first by up to one unfinished proposal's spend; it then stops the run as well.
    # Either way evolve spend stays <= $4.50 - judge reserve.
    cap = min(a.max_api_usd, ledger.remaining() - JUDGE_RESERVE_USD - MAX_PROPOSAL_JOBS * MAX_CALL_USD)
    print(f"trial spend before this run: ${ledger.total():.4f}; Shinka cap ${cap:.3f}", flush=True)
    if cap <= 0:
        raise SystemExit("no budget left for an evolve run")

    evo = EVO = EvolutionConfig(
        task_sys_msg=task_message(),
        patch_types=["diff", "full", "cross"], patch_type_probs=[0.4, 0.45, 0.15],
        num_generations=a.generations, max_patch_resamples=2, max_patch_attempts=2,
        job_type="local", language="python",
        llm_models=[MODEL], llm_dynamic_selection="fixed",
        llm_kwargs={"temperatures": [1.0], "max_tokens": MAX_TOKENS},
        embedding_model="local/codebag@http://127.0.0.1:8765/v1",
        code_embed_sim_threshold=0.95, max_novelty_attempts=2,
        novelty_llm_models=[MODEL], novelty_llm_kwargs={"max_tokens": MAX_TOKENS},
        meta_rec_interval=None, use_text_feedback=True,
        init_program_path=str(TASK / "initial.py"), results_dir=str(out),
        max_api_costs=cap,
    )
    # Shinka always stores the database as <results_dir>/programs.sqlite
    db = DatabaseConfig(db_path=str(out / "programs.sqlite"), num_islands=2, archive_size=30,
                        num_archive_inspirations=2, num_top_k_inspirations=1,
                        parent_selection_strategy="power_law", migration_interval=10)
    job = LocalJobConfig(eval_program_path=str(TASK / "evaluate.py"), time="01:00:00")
    ShinkaEvolveRunner(evo_config=evo, job_config=job, db_config=db, max_evaluation_jobs=3,
                       max_proposal_jobs=MAX_PROPOSAL_JOBS, max_db_workers=2, verbose=True).run()
    print(f"trial ledger total: ${ledger.total():.4f}")


if __name__ == "__main__":
    main()
