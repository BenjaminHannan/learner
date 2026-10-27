"""Saved answers only (no model): O-vs-N / O-vs-P answer sameness by question type, and the predeclared examples
(first 3 fresh triplets; answer-address-s0 vs answer-original-s0; conditions O and NP). Exploratory; fresh examples
from the existing task family."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_address_confirm as C  # noqa: E402
started = time.perf_counter()
C.bootstrap()
import torch  # noqa: E402
manifest = json.loads((HERE / "data" / "manifest.json").read_text())
data = {n: torch.load(ROOT / i["file"], weights_only=False) for n, i in manifest["files"].items()}
answers = json.loads((HERE / "answers.json").read_text())
spec = C.L.spec()
hops = torch.cat([it[2] for it in data["ladder-O"]]).tolist()
held = torch.cat([it[0].slices["heldout"] for it in data["ladder-O"]]).tolist()
kind = ["one_hop" if h == 1 else ("two_hop_heldout_rel" if x else "two_hop_trained_rel") for h, x in zip(hops, held)]
slices = {}
for name, ans in answers.items():
    lad = ans["ladder"]
    entry = {}
    for k in ("one_hop", "two_hop_trained_rel", "two_hop_heldout_rel"):
        idx = [i for i, s in enumerate(kind) if s == k]
        entry[k] = {"n": len(idx), "same_O_vs_N": sum(lad["O"]["all"][i] == lad["N"]["all"][i] for i in idx),
                    "same_O_vs_P": sum(lad["O"]["all"][i] == lad["P"]["all"][i] for i in idx)}
    slices[name] = entry
word = lambda t: (f"V{t - spec.value(0)}" if spec.value(0) <= t < spec.value(0) + spec.values else "<eos>" if t == 2
                  else f"t{t}")
examples = []
for cond, key in (("O", "triplets-O"), ("NP", "triplets-N")):
    item, meta = data[key][0]
    batch, supplied, _ = item
    for t in range(3):
        row = {"condition": cond, "triplet": t, "kind_u": meta.kind_u[t], "kind_v": meta.kind_v[t]}
        for role in ("x", "u", "v"):
            q = int(getattr(meta, f"{role}_q")[t])
            v, end = int(batch.q_visit[q]), int(batch.q_span[q, 1])
            vals = C.D.H and [int(batch.tokens[v, int(batch.line_start[v, int(supplied[q, c])]) + 3]) for c in range(4)]
            row[role] = {"question": f"P{int(batch.tokens[v, end - 3]) - spec.vocab_size} R{int(batch.tokens[v, end - 2]) - spec.relation(0)}",
                         "cards": dict(zip(("gold", "same_person", "same_relation", "other"), map(word, vals))),
                         "right": word(int(meta.a[t] if role != "v" else meta.b[t])),
                         "address_s0": " ".join(map(word, answers["answer-address-s0"]["triplets"][cond][t][role])),
                         "pooled_s0": " ".join(map(word, answers["answer-original-s0"]["triplets"][cond][t][role]))}
        examples.append(row)
seconds = time.perf_counter() - started
(HERE / "examples_and_slices.json").write_text(json.dumps({"slices": slices, "examples": examples}, indent=1))
C.charge("analysis", "answer sameness by question type + predeclared examples (saved answers only)", seconds)
print(json.dumps(slices, indent=0)); print(json.dumps(examples, indent=0)); print(f"({seconds:.2f} s)")
