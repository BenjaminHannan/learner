"""Eval-only (Claude, 2026-09-19): what does the FIRST request (empty workspace, loop 0) look like in stuck vs learned
runs? Tests "right kind of card, wrong person". Validation split, no training, no edits.

Per checkpoint, split one-hop / two-hop:
  hit            ungated top-1 card is a gold card
  family         top-1 card is in the right family (one-hop: relation r cards; two-hop: LINK cards or relation r cards)
  person_in_fam  restricted to the family of the gold card(s), is the best-scoring card a gold card? (chance 1/6)
  mass_gold / mass_family / mass_null   softmax probability mass
  set_ce, bce, ask_rate                 the two parts of the logged ASK loss, separately
  by_ent / by_rel                       one-hop hit rate per asked person / relation
  earliest / latest                     top-1 is the earliest / latest eligible card of the right family
  kappa sweep                           hit and set CE when the same cosines are rescored at kappa in {3,10,30,100},
                                        with learned age biases and with them zeroed

    PY -B scripts/premonition_stuck_probe.py <ckpt_dir>/<name> ... [--out path.json]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_first_card_probe as P  # noqa: E402

L = P.L
KAPPAS = (3.0, 10.0, 30.0, 100.0)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--out")]
    out_path = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--out=")), None)
    L.bootstrap()
    import torch
    import torch.nn.functional as F
    torch.set_num_threads(4)
    spec = L.spec()
    items = L.load_split("validation")
    result = {}
    for arg in args:
        ckpt_dir, name = arg.rsplit("/", 1)
        model, blob = P.load_from(name, ckpt_dir)
        before = P.fingerprint(model)
        kappa = float(model.heads.log_kappa.exp())
        acc = {h: {"n": 0, "hit": 0, "family": 0, "person_in_fam": 0, "mass_gold": 0.0, "mass_family": 0.0,
                   "mass_null": 0.0, "set_ce": 0.0, "bce": 0.0, "ask": 0, "earliest": 0, "latest": 0,
                   "top_null": 0, "fam_size": 0,
                   "sweep": {f"{b}_{k:g}": [0, 0.0] for b in ("bias", "nobias") for k in KAPPAS}}
               for h in (1, 2)}
        by_ent, by_rel = {}, {}
        with torch.no_grad():
            for batch, supplied, hops in items:
                hidden = model.read(batch)
                store = model.build_store(hidden, batch)
                ep = model._start(batch, hidden, store, model._mentions(batch))
                everyone = torch.arange(batch.q_visit.shape[0])
                rows, halt, ask, scores = model._step(ep, everyone, 0, store)
                gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
                bias = model.think.age_bias.float()[store.ages(ep.q_line, model.think.age_bias.shape[0])]
                bias[:, store.null] = 0.0
                eligible = scores > float("-inf")
                cos = ((scores - bias) / kappa).masked_fill(~eligible, 0.0)
                prob = torch.softmax(scores, 1)
                for q in range(len(hops)):
                    hop = int(hops[q])
                    if hop not in acc or not bool(gold[q].any()):
                        continue
                    v = int(batch.q_visit[q])
                    span = batch.tokens[v, int(batch.q_span[q, 0]):int(batch.q_span[q, 1])].tolist()
                    a = span[1] - spec.vocab_size
                    r = int(batch.tokens[v, int(batch.q_span[q, 1]) - 2])
                    fam = torch.zeros_like(eligible[q])
                    for line in range(store.lines):
                        if not bool(eligible[q, line]):
                            continue
                        mid = int(batch.tokens[v, int(batch.line_start[v, line]) + 2])
                        fam[line] = mid == r or (hop == 2 and mid == spec.link)
                    g = acc[hop]
                    g["n"] += 1
                    top = int(scores[q].argmax())
                    hit = bool(gold[q, top])
                    g["hit"] += hit
                    g["family"] += bool(fam[top])
                    g["top_null"] += top == store.null
                    g["fam_size"] += int(fam.sum())
                    # person within family: restrict to the family members that share a middle token with a gold card
                    gold_mids = {int(batch.tokens[v, int(batch.line_start[v, ln]) + 2])
                                 for ln in gold[q, :store.lines].nonzero().squeeze(-1).tolist()}
                    sub = torch.zeros_like(fam)
                    for line in fam.nonzero().squeeze(-1).tolist():
                        sub[line] = int(batch.tokens[v, int(batch.line_start[v, line]) + 2]) in gold_mids
                    if bool(sub.any()):
                        best = int(scores[q].masked_fill(~sub, float("-inf")).argmax())
                        g["person_in_fam"] += bool(gold[q, best])
                    fam_lines = fam.nonzero().squeeze(-1).tolist()
                    if fam_lines:
                        g["earliest"] += top == min(fam_lines)
                        g["latest"] += top == max(fam_lines)
                    g["mass_gold"] += float(prob[q][gold[q]].sum())
                    g["mass_family"] += float(prob[q][fam].sum())
                    g["mass_null"] += float(prob[q, store.null])
                    g["set_ce"] += -math.log(max(float(prob[q][gold[q]].sum()), 1e-30))
                    g["bce"] += float(F.binary_cross_entropy_with_logits(ask[q], torch.ones(())))
                    g["ask"] += bool(ask[q] > 0)
                    for use_bias in (True, False):
                        for k in KAPPAS:
                            s = (k * cos[q] + (bias[q] if use_bias else 0.0)).masked_fill(~eligible[q], float("-inf"))
                            slot = g["sweep"][f"{'bias' if use_bias else 'nobias'}_{k:g}"]
                            slot[0] += bool(gold[q, int(s.argmax())])
                            slot[1] += float(torch.logsumexp(s, 0) - torch.logsumexp(s[gold[q]], 0))
                    if hop == 1:
                        e = by_ent.setdefault(a, [0, 0]); e[0] += hit; e[1] += 1
                        e = by_rel.setdefault(r - spec.relation(0), [0, 0]); e[0] += hit; e[1] += 1
        assert P.fingerprint(model) == before, "model changed during an eval-only probe"
        report = {"kappa": round(kappa, 2), "age_bias": [round(float(x), 3) for x in model.think.age_bias]}
        for hop, g in acc.items():
            n = max(g["n"], 1)
            report[f"hop{hop}"] = {
                "n": g["n"], **{k: round(g[k] / n, 3) for k in ("hit", "family", "person_in_fam", "mass_gold",
                                                                 "mass_family", "mass_null", "set_ce", "bce", "ask",
                                                                 "earliest", "latest", "top_null", "fam_size")},
                "sweep": {k: [round(v[0] / n, 3), round(v[1] / n, 3)] for k, v in g["sweep"].items()}}
        report["one_hop_hit_by_ent"] = {str(k): f"{v[0]}/{v[1]}" for k, v in sorted(by_ent.items())}
        report["one_hop_hit_by_rel"] = {str(k): f"{v[0]}/{v[1]}" for k, v in sorted(by_rel.items())}
        result[name] = report
        print(name, json.dumps(report), flush=True)
    if out_path:
        Path(out_path).write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
