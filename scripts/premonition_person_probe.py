"""Eval-only (Claude, 2026-09-19): in stuck vs learned runs, WHERE is the person's identity readable?

A small linear read-out (softmax regression, trained on even validation visits, scored on odd ones) tries to name the
person from each of these vectors. The model itself is never updated.
  card side:      reader state at the card's person token, and at its value token (3 tokens into the line)
                  -> pooled-line key -> value
  question side:  register 0 after loop 0 (one-hop questions) -> the query sent to the store
Accuracy is reported 16-way (chance 1/16) and "in-story" (argmax restricted to the people present in that story's
cards; chance about 1/6). A failed linear read-out does not prove the information is absent.

    PY -B scripts/premonition_person_probe.py <ckpt_dir>/<name> ... [--out=path.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_first_card_probe as P  # noqa: E402

L = P.L


def readout(x_train, y_train, x_test, y_test, present_test, classes: int):
    import torch
    torch.manual_seed(0)
    mean, std = x_train.mean(0, keepdim=True), x_train.std(0, keepdim=True).clamp_min(1e-6)
    x_train, x_test = (x_train - mean) / std, (x_test - mean) / std
    w = torch.zeros(x_train.shape[1], classes, requires_grad=True)
    b = torch.zeros(classes, requires_grad=True)
    opt = torch.optim.Adam([w, b], lr=0.05, weight_decay=1e-4)
    for _ in range(400):
        opt.zero_grad()
        torch.nn.functional.cross_entropy(x_train @ w + b, y_train).backward()
        opt.step()
    with torch.no_grad():
        logits = x_test @ w + b
        plain = float((logits.argmax(1) == y_test).float().mean())
        story = float((logits.masked_fill(~present_test, float("-inf")).argmax(1) == y_test).float().mean())
    return round(plain, 3), round(story, 3)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--out")]
    out_path = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--out=")), None)
    L.bootstrap()
    import torch
    torch.set_num_threads(4)
    spec = L.spec()
    items = L.load_split("validation")
    result = {}
    for arg in args:
        ckpt_dir, name = arg.rsplit("/", 1)
        model, blob = P.load_from(name, ckpt_dir)
        before = P.fingerprint(model)
        n_ent = model.config.n_ent
        feats = {k: [] for k in ("card_person_state", "card_value_state", "key", "value", "register0", "query")}
        labels = {"card": [], "question": []}
        present = {"card": [], "question": []}
        fold = {"card": [], "question": []}
        visit_base = 0
        with torch.no_grad():
            for batch, supplied, hops in items:
                hidden = model.read(batch)
                store = model.build_store(hidden, batch)
                ep = model._start(batch, hidden, store, model._mentions(batch))
                everyone = torch.arange(batch.q_visit.shape[0])
                captured = {}
                handle = model.heads.query.register_forward_hook(
                    lambda m, i, o: captured.update(register=i[0].detach().float(), query=o.detach().float()))
                query_fn = getattr(model, "_shortcut_query", None)
                if query_fn is not None:                        # shortcut runs: capture the query actually sent
                    def wrapped(register, episode, index, step=None, _f=query_fn):
                        q = _f(register, episode, index, step)
                        captured["sent"] = q.detach().float()
                        return q
                    model._shortcut_query = wrapped
                model._step(ep, everyone, 0, store)
                handle.remove()
                if query_fn is not None:
                    del model._shortcut_query
                sent = captured.get("sent", captured["query"])
                visits, lines = batch.line_start.shape
                who = torch.zeros(visits, n_ent, dtype=torch.bool)
                for v in range(visits):
                    for line in range(lines):
                        if not bool(store.valid[v, line]):
                            continue
                        start = int(batch.line_start[v, line])
                        person = int(batch.tokens[v, start + 1]) - spec.vocab_size
                        mid = int(batch.tokens[v, start + 2])
                        if not 0 <= person < n_ent or mid == spec.link:
                            continue
                        who[v, person] = True
                        feats["card_person_state"].append(hidden[v, start + 1].float())
                        feats["card_value_state"].append(hidden[v, start + 3].float())
                        feats["key"].append(store.keys[v, line].float())
                        feats["value"].append(store.values[v, line].float())
                        labels["card"].append(person)
                        fold["card"].append((visit_base + v) % 2)
                        present["card"].append(v + visit_base)
                for q in range(len(hops)):
                    if int(hops[q]) != 1:
                        continue
                    v = int(batch.q_visit[q])
                    person = int(batch.tokens[v, int(batch.q_span[q, 0]) + 1]) - spec.vocab_size
                    feats["register0"].append(captured["register"][q])
                    feats["query"].append(torch.nn.functional.normalize(sent[q], dim=-1))
                    labels["question"].append(person)
                    fold["question"].append((visit_base + v) % 2)
                    present["question"].append(v + visit_base)
                present.setdefault("_who", {}).update({visit_base + v: who[v] for v in range(visits)})
                visit_base += visits
        assert P.fingerprint(model) == before, "model changed during an eval-only probe"
        report = {}
        for feat, side in (("card_person_state", "card"), ("card_value_state", "card"), ("key", "card"), ("value", "card"),
                           ("register0", "question"), ("query", "question")):
            x = torch.stack(feats[feat])
            y = torch.tensor(labels[side])
            f = torch.tensor(fold[side])
            mask = torch.stack([present["_who"][i] for i in present[side]])
            report[feat] = dict(zip(("acc16", "acc_in_story"),
                                    readout(x[f == 0], y[f == 0], x[f == 1], y[f == 1], mask[f == 1], n_ent)))
            report[feat]["n_test"] = int((f == 1).sum())
        result[name] = report
        print(name, json.dumps(report), flush=True)
    if out_path:
        Path(out_path).write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
