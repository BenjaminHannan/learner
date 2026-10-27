"""Eval-only diagnostic (Claude, 2026-09-19): where does a 2-hop question fail -- first fetch, second fetch, or combining?

Toy ladder, synthetic vocabulary, existing overnight Exp-2 retrieval checkpoints, VALIDATION split only. No training,
no edits to existing files, no Opus ledger writes. Output: artifacts/claude-firstcard-20260919/.

Conditions per 2-hop question "a LINK r?" (b = a's friend; gold = link card L(a), then answer card A(b, r)):
  own            model fetches everything itself, K loops (K-1 fetch chances)            [existing behaviour]
  preload_link   L(a) is already in memory before loop 0; the model fetches the rest itself
  forced_first   loop 0 runs, the model's own first fetch is REPLACED by L(a) (as the teacher does in training);
                 the model fetches the rest itself
  gold_both      both gold cards in memory, no fetching                                  [existing behaviour]
For every own fetch made once L(a) is in hand we record whose card / which relation was requested (hop2_miss classes).

    PY -B scripts/premonition_first_card_probe.py [ckpt ...]
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import premonition_ovn_retrieval as R  # noqa: E402

L = R.L
OUT = L.ROOT / "artifacts" / "claude-firstcard-20260919"
DEFAULT = ["bypass-k1-s0-1500", "bypass-k1-s0-1500-longread", "bypass-k1-s0-1500-longread-ea0",
           "bypass-k1-s0-4000-longread", "bypass-k1-s1-1500-longread"]
RIGHT_REL = ("answer", "asker_same_rel", "other_same_rel")
RIGHT_PERSON = ("answer", "friend_other_rel")


def classify(tokens, a, b, r, link_id, vocab):
    subject, middle = tokens[1] - vocab, tokens[2]
    if middle == link_id:
        return "link" if subject == a else "other_link"
    if subject == b:
        return "answer" if middle == r else "friend_other_rel"
    if subject == a:
        return "asker_same_rel" if middle == r else "asker_other_rel"
    return "other_same_rel" if middle == r else "other_other_rel"


def fingerprint(model) -> str:
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def run(model, batch, hops, *, mode: str, loops: int):
    """-> ok [Q] bool, answer_card_fetched [Q] bool, own_fetches: list of [Q, k] line ids made AFTER the link is held
    (for mode 'own': every fetch)."""
    import torch
    from learnlab.core import IGNORE_INDEX
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    ep = model._start(batch, hidden, store, mentions)
    everyone = torch.arange(batch.q_visit.shape[0])
    two = hops == 2
    link = torch.where(two.unsqueeze(1), batch.gold_lines[:, :1], torch.full_like(batch.gold_lines[:, :1], -1))
    own = []
    ungated = []
    if mode == "preload_link":
        model._insert(ep, store, everyone, link)
    if mode == "gold_both":
        gold, _, _ = store.gold(batch.gold_lines, batch.q_visit, batch.q_line)
        width = min(gold.shape[1], 2)
        model._insert(ep, store, everyone, torch.where(gold, torch.arange(gold.shape[1]),
                                                       torch.full_like(gold, -1, dtype=torch.long)).topk(width, 1).values)
    for step in range(loops):
        rows, halt, ask, scores = model._step(ep, everyone, step, store)
        if mode == "gold_both" or step + 1 >= loops:
            continue
        gated = store.top(scores, model.config.top_k)
        cards = gated.masked_fill((ask <= 0).unsqueeze(1), -1)
        if mode == "forced_first" and step == 0:
            cards = torch.where(two.unsqueeze(1), link.expand_as(cards[:, :1]), cards[:, :1]) if cards.shape[1] == 1 \
                else torch.cat([torch.where(two.unsqueeze(1), link, cards[:, :1]),
                                cards[:, 1:].masked_fill(two.unsqueeze(1), -1)], 1)
        else:
            own.append(cards.clone())
            ungated.append(gated[:, :1].clone())        # --extra: what it would fetch ignoring the ASK logit
        model._insert(ep, store, everyone, cards)
    tokens, lengths = model._greedy(batch, ep, mentions, None)
    ok = torch.tensor([tokens[q, :int(lengths[q])].tolist() == batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist()
                       for q in range(batch.answer.shape[0])])
    answer_line = batch.gold_lines[:, 1].clamp_min(0)
    got_answer = ep.fetched.gather(1, answer_line.unsqueeze(1)).squeeze(1) & (batch.gold_lines[:, 1] >= 0)
    return ok, got_answer, own, store, ungated


def load_from(name: str, ckpt_dir):
    """R.load, but from an arbitrary checkpoint directory (same blob format)."""
    if ckpt_dir is None:
        return R.load(name)
    import torch
    from premonition import answer_path
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    blob = torch.load(Path(ckpt_dir) / f"{name}.pt", weights_only=False)
    if blob.get("format") == "premonition-recovery-v1":
        import premonition_recovery as recovery
        return recovery.from_blob(blob), blob
    config = MiniConfig(**{k: tuple(v) if isinstance(v, list) else v for k, v in blob["config"].items()})
    cls = answer_path.CardBypassMini if R.ARMS[blob["arm"]]["bypass"] else PremonitionMini
    # Screen 3: checkpoints written by a variant subclass carry extra tensors; build the recorded class.
    if blob.get("model_class") == "RelationShortcutCardBypassMini" or blob.get("relation_shortcut"):
        import premonition_relation_shortcut as RS
        cls = RS.shortcut_class()
    model = cls(config)
    # Screen 5: the key-pool variant keeps the recorded class but swaps the card writer (extra tensors).
    if blob.get("key_pool"):
        import premonition_key_pool as KP
        KP.apply_key_pool(model)
    model.load_state_dict(blob["state_dict"])
    model.eval()
    return model, blob


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*")
    parser.add_argument("--ckpt-dir", default=None,
                        help="directory holding <name>.pt blobs (default: the overnight exp2 ckpt dir)")
    parser.add_argument("--out", default=None, help="path for the JSON output (default: OUT/first_card_probe.json)")
    parser.add_argument("--extra", action="store_true",
                        help="also record, for every own fetch, the class of the UNGATED top-1 card (what would "
                             "have been fetched if the ASK logit were ignored) and the no-request count, and the "
                             "per-relation one-hop retrieval rate (first own request = the gold card)")
    parser.add_argument("--ladder6", action="store_true",
                        help="screen 4: score against the 6-relation ladder data "
                             "(artifacts/claude-ladder6-20260919/data) instead of the 3-relation default")
    args = parser.parse_args()
    names = args.names or DEFAULT
    L.bootstrap()
    if args.ladder6:
        import premonition_ladder6 as L6
        L6.activate()
    import torch
    torch.set_num_threads(4)
    spec = L.spec()
    items = L.load_split("validation")
    conditions = [("own", 4), ("preload_link", 2), ("preload_link", 3), ("preload_link", 4), ("forced_first", 3),
                  ("forced_first", 4), ("gold_both", 2)]
    started = time.perf_counter()
    out = {"split": "validation", "note": "toy ladder, synthetic vocabulary, eval only; diagnostic, not a verdict",
           "checkpoints": {}}
    for name in names:
        model, blob = load_from(name, args.ckpt_dir)
        before = fingerprint(model)
        report = {}
        order_check = Counter()
        one_hop = {}                       # --extra: relation -> [hits, n] on the FIRST own request
        with torch.no_grad():
            for mode, loops in conditions:
                tally = {}
                for batch, supplied, hops in items:
                    ok, got, own, store, ungated = run(model, batch, hops, mode=mode, loops=loops)
                    held = batch.slices["heldout"]
                    for q in range(len(hops)):
                        if int(hops[q]) != 2:
                            if args.extra and mode == "own" and int(hops[q]) == 1 and own:
                                v1 = int(batch.q_visit[q])
                                rel = int(batch.tokens[v1, int(batch.q_span[q, 1]) - 2])
                                gold_line = int(batch.gold_lines[q, 0])
                                slot = one_hop.setdefault(rel - spec.relation(0), [0, 0])
                                slot[1] += 1
                                slot[0] += int(gold_line >= 0 and gold_line in own[0][q].tolist())
                            continue
                        v = int(batch.q_visit[q])
                        ask_tokens = batch.tokens[v, int(batch.q_span[q, 0]):int(batch.q_span[q, 1])].tolist()
                        a, r = ask_tokens[1] - spec.vocab_size, ask_tokens[3]
                        link_line = int(batch.gold_lines[q, 0])
                        b = int(batch.tokens[v, int(batch.line_start[v, link_line]) + 3]) - spec.vocab_size

                        def kind(line):
                            start = int(batch.line_start[v, line])
                            return classify(batch.tokens[v, start:start + 4].tolist(), a, b, r, spec.link, spec.vocab_size)
                        if mode == "own":
                            order_check[(kind(link_line), kind(int(batch.gold_lines[q, 1])))] += 1
                        g = tally.setdefault("heldout" if bool(held[q]) else "practised", {
                            "n": 0, "correct": 0, "answer_card_fetched": 0, "correct_given_fetched": 0,
                            "correct_given_not_fetched": 0, "fetches": {}})
                        g["n"] += 1
                        g["correct"] += int(ok[q])
                        g["answer_card_fetched"] += int(got[q])
                        g["correct_given_fetched" if bool(got[q]) else "correct_given_not_fetched"] += int(ok[q])
                        for i, cards in enumerate(own):
                            counter = g["fetches"].setdefault(f"own_fetch{i + 1}", Counter())
                            for line in cards[q].tolist():
                                counter["none" if line < 0 or line >= store.lines else kind(line)] += 1
                            if not args.extra:
                                continue
                            # --extra (a): what the model WOULD have fetched with the ASK gate ignored,
                            # and how many of these fetches were "no request" (ASK logit <= 0).
                            ug = g["fetches"].setdefault(f"own_fetch{i + 1}_ungated", Counter())
                            line = int(ungated[i][q, 0])
                            ug["none" if line < 0 or line >= store.lines else kind(line)] += 1
                            nr = g["fetches"].setdefault(f"own_fetch{i + 1}_norequest", Counter())
                            nr["no_request" if int(cards[q, 0]) < 0 else "requested"] += 1
                for g in tally.values():
                    for key, counter in list(g["fetches"].items()):
                        total = sum(counter.values())
                        if key.endswith("_norequest"):
                            g["fetches"][key] = {"classes": dict(counter), "total": total,
                                                 "no_request": counter["no_request"]}
                            continue
                        g["fetches"][key] = {"classes": dict(counter.most_common()), "total": total,
                                             "right_relation": sum(counter[c] for c in RIGHT_REL),
                                             "right_person": sum(counter[c] for c in RIGHT_PERSON),
                                             "right_both": counter["answer"]}
                report[f"{mode}_K{loops}"] = tally
        after = fingerprint(model)
        if before != after:
            raise SystemExit(f"{name}: parameters changed during evaluation")
        report["read_only_fingerprint"] = before
        report["no_step_emb"] = blob.get("no_step_emb")
        report["gold_line_order_check"] = {f"{k[0]}|{k[1]}": v for k, v in order_check.items()}
        if args.extra:
            # --extra (b): one-hop first-own-request gold hit rate, split by relation index.
            report["one_hop_first_request_by_relation"] = {
                str(r): {"gold_first_request": v[0], "n": v[1]} for r, v in sorted(one_hop.items())}
            print("  one-hop first own request = gold card, by relation:",
                  report["one_hop_first_request_by_relation"], flush=True)
        out["checkpoints"][name] = report
        print(f"\n== {name}  (gold order check {report['gold_line_order_check']})", flush=True)
        for cond, tally in report.items():
            if not isinstance(tally, dict) or "practised" not in tally:
                continue
            for group in ("practised", "heldout"):
                g = tally[group]
                first = g["fetches"].get("own_fetch1")
                extra = "" if first is None else (f" | first own fetch: right person+relation {first['right_both']}, "
                                                  f"right relation {first['right_relation']}, right person "
                                                  f"{first['right_person']} of {first['total']}")
                print(f"{cond:16s} {group:9s} correct {g['correct']:3d}/{g['n']}  answer card fetched "
                      f"{g['answer_card_fetched']:3d}  correct|fetched {g['correct_given_fetched']:3d}"
                      f"  correct|not {g['correct_given_not_fetched']:3d}{extra}", flush=True)
    out["seconds"] = round(time.perf_counter() - started, 2)
    out_path = Path(args.out).expanduser() if args.out else (OUT / "first_card_probe.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1))
    print("wrote", out_path)
    print("seconds", out["seconds"])


if __name__ == "__main__":
    main()
