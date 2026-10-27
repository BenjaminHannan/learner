"""Past-experience-only stop learning, with the reasoning cores frozen.

Development hypothesis: masked answer confidence and state can predict a safe
stop better than an inherited halt head pooled over every input position.
The same fixed recipe is offered to both acquired dense and operator cores.
No query targets enter features, fitting, runtime stopping or checkpoint choice.
"""
import argparse
import hashlib
import io
import json
import math
import random
import time
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

import active_eval as A
import capsule_screen as C
import real_screen as S
from capsule_moe import CapsuleMoE


class StopController(nn.Module):
    def __init__(self, features=520, hidden=32):
        super().__init__()
        self.register_buffer("mean", torch.zeros(features))
        self.register_buffer("scale", torch.ones(features))
        self.mlp = nn.Sequential(nn.Linear(features, hidden), nn.GELU(), nn.Linear(hidden, 1))

    def forward(self, features):
        return self.mlp((features - self.mean) / self.scale).squeeze(-1)


def state_hash(model):
    stream = io.BytesIO()
    torch.save(model.state_dict(), stream)
    return hashlib.sha256(stream.getvalue()).hexdigest()


def stop_features(h, logits, mask, round_number):
    """Only live inference state, logits, translated fill slots and loop index."""
    h = h[..., :256].float()
    mask = mask.bool()
    denominator = mask.sum(-1).clamp_min(1)
    masked_state = (h * mask[..., None]).sum(1) / denominator[:, None]
    mean_state = h.mean(1)
    probabilities = logits.float().softmax(-1)
    entropy = -(probabilities * probabilities.clamp_min(1e-12).log()).sum(-1)
    best = logits.float().topk(2, -1).values
    margin = best[..., 0] - best[..., 1]
    confidence = probabilities.max(-1).values
    stats = torch.stack((
        (entropy * mask).sum(-1) / denominator,
        entropy.masked_fill(~mask, -math.inf).max(-1).values,
        (margin * mask).sum(-1) / denominator,
        margin.masked_fill(~mask, math.inf).min(-1).values,
        (confidence * mask).sum(-1) / denominator,
        confidence.masked_fill(~mask, math.inf).min(-1).values,
        torch.full_like(denominator, round_number, dtype=torch.float32) / 48,
        torch.full_like(denominator, math.log1p(round_number), dtype=torch.float32),
    ), -1)
    # Empty answer sets are outside this screen, and must not silently produce
    # NaN/inf features in a more general caller.
    if not bool(mask.any(-1).all()):
        raise ValueError("each puzzle needs at least one translated answer slot")
    return torch.cat((masked_state, mean_state, stats), -1)


def training_memories(seed=0):
    historical, supports, replay, digest = S.make_development(seed, 64)
    panel = C.fresh_panel(supports, historical, 64)
    banned = {S.D.layout_key(x) for groups in (historical, panel)
              for name, rows in groups.items() if name.startswith("mazes") for x in rows}
    seen = {S.D.layout_key(x) for x in supports}
    additions = []
    for cycle in (2, 3):
        rng = random.Random(74039000 + cycle)
        extra = [S.D.unique_maze(rng, 9, banned, seen) for _ in range(64)]
        additions.append(C.input_digest(extra))
        supports.extend(extra)
    return panel, supports, digest, additions


@torch.no_grad()
def collect(model, memories, batch=8):
    model.eval().requires_grad_(False)
    features, labels = [], []
    started = time.monotonic()
    for begin in range(0, len(memories), batch):
        t, slots, targets = S.tensor_batch(memories[begin:begin + batch], "cpu")
        mask, targets = slots.flatten(1).bool(), targets.flatten(1)
        e, (dr, dc) = model.embed(t, slots)
        h = torch.zeros_like(e)
        fs, ys = [], []
        for r in range(1, 49):
            h = model.step(h, e, dr, dc)
            logits, _ = model.read(h)
            fs.append(stop_features(h, logits, mask, r))
            pred = logits.argmax(-1)
            ys.append(((pred == targets) | ~mask).all(-1).float())
        current = torch.stack(ys, 1)
        # A positive training stop must stay correct through the entire cached
        # continuation. This uses TRAIN answers only, not a runtime checker.
        persistent = current.flip(1).cummin(1).values.flip(1)
        features.append(torch.stack(fs, 1).flatten(0, 1))
        labels.append(persistent.flatten())
        print(json.dumps({"phase": "TRAIN_stop_features", "examples": begin + len(t),
                          "elapsed_seconds": time.monotonic() - started}), flush=True)
    return torch.cat(features), torch.cat(labels), {
        "examples": len(memories), "row_rounds": 48 * len(memories),
        "seconds": time.monotonic() - started, "query_examples": 0,
        "labels": "canonical masked exact now AND at every later TRAIN round through48",
    }


def fit(features, labels, seed=0):
    torch.manual_seed(74069000 + seed)
    controller = StopController(features.shape[-1])
    controller.mean.copy_(features.mean(0))
    controller.scale.copy_(features.std(0, unbiased=False).clamp_min(.05))
    optimizer = torch.optim.AdamW(controller.parameters(), lr=.001, weight_decay=.1, betas=(.9, .95))
    rng = torch.Generator().manual_seed(74079000 + seed)
    losses = []
    started = time.monotonic()
    for _ in range(256):
        ids = torch.randint(len(features), (256,), generator=rng)
        loss = F.binary_cross_entropy_with_logits(controller(features[ids]), labels[ids])
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach()))
    controller.eval().requires_grad_(False)
    return controller, {"updates": 256, "minibatch": 256, "lr": .001,
                        "cached_round_presentations": 65536,
                        "positive_fraction": float(labels.mean()),
                        "first16_loss": sum(losses[:16]) / 16,
                        "last16_loss": sum(losses[-16:]) / 16,
                        "seconds": time.monotonic() - started,
                        "learned_parameters": sum(p.numel() for p in controller.parameters()),
                        "query_training_or_threshold_selection": False}


@torch.no_grad()
def execute(model, controller, tokens, slots, policy="masked_learned", *, compact=True, cap=48):
    """Slot-aware or original stability; old frozen program keeps original stop."""
    if policy not in ("masked_learned", "all_learned", "masked_original", "original"):
        raise ValueError("unknown fixed policy")
    e, (dr, dc) = model.embed(tokens, slots)
    h = torch.zeros_like(e)
    b, cells = h.shape[:2]
    mask = slots.flatten(1).bool()
    live = torch.arange(b)
    result = torch.empty((b, cells), dtype=torch.long)
    rounds = torch.full((b,), cap, dtype=torch.long)
    fired_result = torch.zeros(b, dtype=torch.bool)
    finished = torch.zeros(b, dtype=torch.bool)
    previous, previous2 = None, None
    sizes = []
    for r in range(1, cap + 1):
        h = model.step(h, e, dr, dc)
        logits, original_q = model.read(h)
        prediction = logits.argmax(-1)
        old_route = e[:, 0, -1].long() == 0 if isinstance(model, CapsuleMoE) else torch.zeros(
            len(e), dtype=torch.bool, device=e.device)
        q = original_q
        if policy not in ("original", "masked_original"):
            acquired = (~old_route).nonzero(as_tuple=True)[0]
            if len(acquired):
                q = q.clone()
                q[acquired] = controller(stop_features(h[acquired], logits[acquired], mask[acquired], r))
        if previous2 is None:
            fire = torch.zeros_like(q, dtype=torch.bool)
        else:
            changed = (prediction != previous) | (previous != previous2)
            masked = policy in ("masked_learned", "masked_original")
            changed = torch.where(old_route[:, None], changed, changed & mask) if masked else changed
            fire = ~changed.any(-1) & (q.float().sigmoid() > .5)
        done = fire | (r == cap)
        if not compact:
            done = done & ~finished
        if bool(done.any()):
            ids = live[done]
            result[ids], rounds[ids], fired_result[ids] = prediction[done], r, fire[done]
        sizes.append(len(live) if compact else int((~finished).sum()))
        if compact:
            keep = (~done).nonzero(as_tuple=True)[0]
            if len(keep) == 0:
                break
            previous2 = previous[keep] if previous is not None else None
            previous = prediction[keep]
            h, e, mask, live = h[keep], e[keep], mask[keep], live[keep]
        else:
            finished |= done
            previous2, previous = previous, prediction
    return A.ActiveResult(result, rounds, fired_result, tuple(sizes))


@torch.no_grad()
def evaluate(model, controller, panel, policy, batch=8):
    result = {}
    for name, items in panel.items():
        correctness, rounds = [], []
        for begin in range(0, len(items), batch):
            chunk = items[begin:begin + batch]
            t = torch.tensor([x.tokens for x in chunk])
            slots = torch.tensor([x.slot for x in chunk])
            active = execute(model, controller, t, slots, policy)
            assert active.row_rounds == int(active.rounds.sum())
            correctness.extend(C.correctness(name, chunk, active.predictions).tolist())
            rounds.extend(active.rounds.tolist())
            if begin == 0:
                offline = execute(model, controller, t, slots, policy, compact=False)
                assert torch.equal(active.predictions, offline.predictions)
                assert torch.equal(active.rounds, offline.rounds)
                assert torch.equal(active.stopped, offline.stopped)
                if policy == "original":
                    original = A.active_execute(model, t, slots)
                    assert torch.equal(active.predictions, original.predictions)
                    assert torch.equal(active.rounds, original.rounds)
                    assert torch.equal(active.stopped, original.stopped)
        result[name] = {"exact": sum(correctness), "n": len(items),
                        "actually_executed_row_rounds": sum(rounds),
                        "mean_rounds": sum(rounds) / len(items),
                        "cap_hits": sum(x == 48 for x in rounds),
                        "per_puzzle_correctness": correctness, "per_puzzle_rounds": rounds,
                        "first_batch_active_offline_prediction_round_stop_parity": True}
    return result


def run(args):
    torch.set_num_threads(2)
    out = Path(args.out)
    if out.exists():
        raise FileExistsError(out)
    panel, memories, initial_support_hash, additions = training_memories()
    proof = json.loads((S.HERE / "capsule_screen.json").read_text())
    record = {"development_only": True, "official_holdout_opened": False,
              "threshold": .5, "minimum_rounds": 3, "cap": 48,
              "training_memories": 192, "support_input_sha256": C.input_digest(memories),
              "initial_support_layout_sha256": initial_support_hash,
              "extra_support_input_sha256": additions,
              "input_sha256": {k: C.input_digest(v) for k, v in panel.items()},
              "reasoning_updates": 0, "isolated_timing_claim": False,
              "core_parameters_frozen": True,
              "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "models": {}}
    for tag, arm in (("dense", "loop_legacy"),
                     ("all2", "moe_local_manual_plastic_all2_anchor_replay")):
        stream = json.loads((S.HERE / f"cycles-{tag}-s0.json").read_text())
        if len(stream["cycles"]) != 3:
            raise ValueError("requires completed three-night stream")
        if stream["input_sha256"] != record["input_sha256"]:
            raise ValueError("fresh panel identity differs")
        assert additions == [x["wake"]["new_input_sha256"] for x in stream["cycles"][1:]]
        checkpoint = stream["cycles"][-1]["after_sleep"]["checkpoint"]
        body, _ = S.load(arm, 0, "cpu")
        body.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
        source, _ = S.load("loop_legacy", 0, "cpu")
        net = CapsuleMoE(source, body).eval().requires_grad_(False)
        net.router.load_state_dict({k: torch.tensor(v) for k, v in proof["router_state_dict"].items()})
        before = state_hash(net)
        features, labels, collection = collect(net, memories)
        assert state_hash(net) == before
        controller, fitting = fit(features, labels)
        ck = out.with_suffix(f".{tag}.controller.pt")
        torch.save(controller.state_dict(), ck)
        scores = {policy: evaluate(net, controller, panel, policy) for policy in
                  ("original", "masked_original", "all_learned", "masked_learned")}
        reference = stream["cycles"][-1]["after_sleep"]["routed"]
        for name, value in scores["original"].items():
            assert value["exact"] == reference[name]["exact"]
            assert value["actually_executed_row_rounds"] == reference[name]["actually_executed_row_rounds"]
        assert state_hash(net) == before
        record["models"][tag] = {"arm": arm, "body_checkpoint": checkpoint,
                                 "body_checkpoint_sha256": C.sha(checkpoint),
                                 "core_state_sha256_before_after": before,
                                 "controller_checkpoint": str(ck),
                                 "controller_checkpoint_sha256": C.sha(ck),
                                 "collection": collection, "fit": fitting, "scores": scores}
        out.write_text(json.dumps(record, indent=2) + "\n")
        print(json.dumps({"model": tag, "scores": {policy: {kind: (v["exact"], v["mean_rounds"])
              for kind, v in rows.items()} for policy, rows in scores.items()}}), flush=True)
    record["complete"] = True
    record["limit"] = "One selected development stream/seed; controller cost charged separately; no global2x proof."
    out.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    run(parser.parse_args())
