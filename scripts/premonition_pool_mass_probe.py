"""Eval-only (Claude, 2026-09-19): where does the card writer's pooling weight sit, per token position of a fact line,
in runs that learned retrieval vs runs that stayed stuck? Validation split, no training, no edits. Prints a table.

Checkpoints of the key-pool variant (scripts/premonition_key_pool.py) have a second scorer for the card KEYS; for
those the KEY pooling mass is printed too, as `attr_key` / `link_key` beside the value-pool `attr` / `link`."""
from __future__ import annotations
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_first_card_probe as P
L = P.L


def main() -> None:
    L.bootstrap()
    import torch
    torch.set_num_threads(4)
    items = L.load_split("validation")
    spec = L.spec()
    out = {}
    for arg in sys.argv[1:]:
        ckpt_dir, name = arg.rsplit("/", 1)
        model, blob = P.load_from(name, ckpt_dir)
        writer = next(m for m in model.modules()
                      if m.__class__.__name__ in ("CardWriter", "KeyPoolCardWriter"))
        key_pool = getattr(writer, "key_pool", None)          # key-pool variant only
        kinds = ["attr", "link"] + (["attr_key", "link_key"] if key_pool is not None else [])
        mass = {k: torch.zeros(8) for k in kinds}
        count = {k: 0 for k in kinds}
        with torch.no_grad():
            for batch, supplied, hops in items[:8]:
                hidden = model.read(batch)
                score = writer.pool(hidden).squeeze(-1).float()
                key_score = None if key_pool is None else key_pool(hidden).squeeze(-1).float()
                visits, lines = batch.line_start.shape
                for v in range(visits):
                    for ln in range(lines):
                        start = int(batch.line_start[v, ln])
                        if start < 0 or bool(batch.line_is_question[v, ln]):
                            continue
                        idx = (batch.line_of[v] == ln).nonzero().squeeze(-1)
                        if idx.numel() < 4 or idx.numel() > 8:
                            continue
                        toks = batch.tokens[v, idx].tolist()
                        mid = toks[2]
                        kind = "link" if mid == spec.link else ("attr" if 8 <= mid < spec.link else None)
                        if kind is None:
                            continue
                        w = torch.softmax(score[v, idx], 0)
                        mass[kind][: idx.numel()] += w
                        count[kind] += 1
                        if key_score is None:
                            continue
                        wk = torch.softmax(key_score[v, idx], 0)
                        mass[kind + "_key"][: idx.numel()] += wk
                        count[kind + "_key"] += 1
        out[name] = {k: [round(float(x) / max(count[k], 1), 3) for x in mass[k][:6]] for k in mass}
        out[name]["kappa"] = round(float(model.heads.log_kappa.exp()), 2)
        print(name, json.dumps(out[name]), flush=True)


if __name__ == "__main__":
    main()
