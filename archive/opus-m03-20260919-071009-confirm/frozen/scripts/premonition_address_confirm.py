"""Milestone-3 continuation 4: bounded confirmation of the address-key result on FRESH examples (no training).

Fresh examples from the EXISTING task family (synthetic-vocabulary toy ladder; the same generator, spec and label-free
rule; supplied privileged cards) -- not evidence of general language ability. full_verdict: false; H1 OFF; defaults
unchanged; checkpoints loaded read-only and never modified; shared ledger (amended cap 2,100 s; no extension).

Checkpoints: answer-address-s{0,1} vs their compatible pooled controls answer-original-s{0,1}, on EXACTLY the same
examples, card orders and conditions.

Fresh data (generated and saved by `data` before any model is loaded; overlap-checked):
  ladder    16 batches x 16 visits, generator seed 4404 (validation-like: held-out 2-hop relation included)
  triplets  32 batches x 8 verified triplets (x; u irrelevant change; v relevant change), seeds 4505/4506/4507
Conditions (predeclared): O original; N consistent person renaming (one permutation of the 16 person ids per batch,
seed 5500 + batch, applied to every visit/sibling: answers and evidence access preserved and re-verified); P card
order changed (fresh order seeds); NP both. Orders: ladder all-cards O/N 6100 + batch, P/NP 6600 + batch; triplets
O/N 8100 + batch, P/NP 8600 + batch. Gold-only reading uses the unshuffled gold cards (O and N).

    PY -B scripts/premonition_address_confirm.py freeze | dry | check --tests ... | data | run | compare
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
M3 = "m03-20260919-071009"
M3_OUT = ROOT / "artifacts" / f"opus-{M3}"
OUT = M3_OUT / "confirm"
ARCHIVE = ROOT / "archive" / f"opus-{M3}-confirm"
SELF = "scripts/premonition_address_confirm.py"
PAIRS = {0: ("answer-address-s0", "answer-original-s0"), 1: ("answer-address-s1", "answer-original-s1")}
SEEDS = {"ladder": 4404, "triplets": 4505, "rename": 5500, "ladder_order": (6100, 6600),
         "triplet_order": (8100, 8600)}
LADDER_BATCHES, VISITS, TRIPLET_BATCHES, PER_BATCH = 16, 16, 32, 8
TRAIN_BATCHES_USED = 2000                     # answer_loop steps of every compared checkpoint (stream seed 1101)
CONDITIONS = ("O", "N", "P", "NP")
RESERVE = 30.0
A = D = H = L = None


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=str))


def freeze() -> None:
    (ARCHIVE / "frozen" / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / SELF, ARCHIVE / "frozen" / SELF)
    (ARCHIVE / "FROZEN.SHA256SUMS").write_text(f"{sha256(ARCHIVE / 'frozen' / SELF)}  ./{SELF}\n")
    write_json(ARCHIVE / "FROZEN-NOTES.json", {"imports": f"archive/opus-{M3}-address/frozen (via "
                                                          "premonition_address_keys.bootstrap)", "added": [SELF]})
    print("frozen", SELF)


def bootstrap() -> None:
    global A, D, H, L
    frozen = ARCHIVE / "frozen" / SELF
    if sha256(frozen) != (ARCHIVE / "FROZEN.SHA256SUMS").read_text().split()[0] or sha256(ROOT / SELF) != sha256(frozen):
        raise SystemExit("live confirmation harness differs from its frozen copy: re-freeze (and journal it) first")
    sys.path.insert(0, str(ROOT / "scripts"))
    import premonition_address_keys as address
    address.bootstrap()                        # address snapshot, reused harness identities, sealed ledger prefix
    A, D, H, L = address, address.D, address.H, address.L


def charge(kind: str, name: str, seconds: float, **extra) -> None:
    H.ledger_add(f"confirm-{kind}", name, seconds, continuation="address-confirm", **extra)


def left() -> float:
    return A.CAP_SECONDS - H.ledger_seconds()


# ----------------------------------------------------------------------------- data (no model)
def rename_lines(lines, perm, spec):
    """Consistent person renaming of rendered lines: every person token, entity tuple and entity answer mapped by
    `perm`; value words, relations, layout and line indices unchanged."""
    from dataclasses import replace
    from premonition.toy_ladder import N_ENT
    low, high = spec.vocab_size, spec.vocab_size + N_ENT
    token = lambda t: low + perm[t - low] if low <= t < high else t
    return [replace(line, tokens=[token(t) for t in line.tokens], ents=tuple(perm[e] for e in line.ents),
                    answer=None if line.answer is None else [token(t) for t in line.answer]) for line in lines]


def rename_world(world, perm):
    from premonition.toy_ladder import World
    return World([perm[e] for e in world.ents], {(perm[e], r): v for (e, r), v in world.attr.items()},
                 {perm[e]: perm[f] for e, f in world.friend.items()})


def permutation(batch: int) -> list:
    from premonition.toy_ladder import N_ENT
    rng = random.Random(SEEDS["rename"] + batch)
    while True:
        perm = list(range(N_ENT))
        rng.shuffle(perm)
        if all(perm[e] != e for e in range(N_ENT)):          # every person gets a different id
            return perm


def facts_of_tokens(tokens, spec) -> tuple:
    """World fingerprint from rendered text: the sorted attribute and link facts of a visit's fact lines."""
    from premonition.toy_ladder import NEWLINE, WORLD
    facts, line = [], []
    for t in tokens:
        line.append(t)
        if t == NEWLINE:
            if len(line) >= 4 and line[0] == WORLD and line[1] >= spec.vocab_size:
                if line[2] == spec.link:
                    facts.append(("link", line[1], line[3]))
                elif spec.relation(0) <= line[2] < spec.relation(0) + spec.relations:
                    facts.append(("attr", line[1], line[2], line[3]))
            line = []
    return tuple(sorted(facts))


def batch_worlds(item, spec) -> list:
    batch = item[0]
    return [facts_of_tokens(batch.tokens[v, :int(batch.lengths[v])].tolist(), spec) for v in range(batch.tokens.shape[0])]


def fresh_ladder(spec):
    """(O items, N items, raw rows): the same fresh visits, original and consistently renamed."""
    from premonition.toy_ladder import assemble, visit
    rng = random.Random(SEEDS["ladder"])
    original, renamed = [], []
    for b in range(LADDER_BATCHES):
        rows = [visit(spec, rng, training=False)[0] for _ in range(VISITS)]
        serial = rng.randrange(1 << 30)
        perm = permutation(b)
        original.append(L.label_free_item(assemble(spec, rows, prefix=f"fresh-{serial}")))
        renamed.append(L.label_free_item(assemble(spec, [rename_lines(r, perm, spec) for r in rows],
                                                  prefix=f"fresh-{serial}-renamed")))
    return original, renamed


def fresh_triplets(spec):
    """(O, N): verified fresh triplets, original and consistently renamed (same row permutation, re-verified)."""
    from dataclasses import replace
    from premonition import ladder_triplets as T
    rng, edit = random.Random(SEEDS["triplets"]), random.Random(SEEDS["triplets"] + 1)
    original, renamed = [], []
    for b in range(TRIPLET_BATCHES):
        ts = [T.make_triplet(spec, rng, edit, training=False) for _ in range(PER_BATCH)]
        perm = permutation(100 + b)
        rs = []
        for t in ts:
            key = lambda k: (perm[k[0]], k[1])
            r = replace(t, x=rename_lines(t.x, perm, spec), u=rename_lines(t.u, perm, spec),
                        v=rename_lines(t.v, perm, spec), changed_u=tuple(key(k) for k in t.changed_u),
                        changed_v=tuple(key(k) for k in t.changed_v),
                        worlds=tuple(rename_world(w, perm) for w in t.worlds))
            T.verify(spec, r)                                   # answers and evidence preserved under renaming
            rs.append(r)
        seed = SEEDS["triplets"] + 2 + 1000 * b                 # the same visit-row permutation for O and N
        for group, out in ((ts, original), (rs, renamed)):
            item, meta = T.assemble_triplets(spec, group, random.Random(seed), prefix=f"fresh-t{b}")
            out.append((L.label_free_item(item), meta))
    return original, renamed


def training_worlds(spec, batches: int) -> set:
    """World fingerprints of the training visits the compared checkpoints consumed (L.train_stream replayed with
    toy_ladder.visit: make() = 16 visits, then one serial draw)."""
    from premonition.toy_ladder import visit
    rng = random.Random(L.SEEDS["train"])
    worlds = set()
    for _ in range(batches):
        for _ in range(L.VISITS):
            lines, _, _ = visit(spec, rng, training=True)
            worlds.add(facts_of_tokens([t for line in lines for t in line.tokens], spec))
        rng.randrange(1 << 30)
    return worlds


def cmd_data(args) -> None:
    import torch
    if (OUT / "data" / "manifest.json").exists():
        raise SystemExit("fresh data already frozen; never regenerated")
    A.require(40, reserve=RESERVE)
    started = time.perf_counter()
    try:
        spec = L.spec()
        ladder_o, ladder_n = fresh_ladder(spec)
        trip_o, trip_n = fresh_triplets(spec)
        existing = {"training_worlds_2000_batches": training_worlds(spec, TRAIN_BATCHES_USED)}
        for split in ("validation", "test"):
            existing[f"ladder_{split}"] = {w for item in L.load_split(split) for w in batch_worlds(item, spec)}
            existing[f"triplets_{split}"] = {w for item, _ in H.load_triplets(split) for w in batch_worlds(item, spec)}
        existing["overnight_paired_two_hop"] = {w for kind in L.paired_two_hop(256).values() for a, b, _ in kind
                                                for w in batch_worlds(a, spec) + batch_worlds(b, spec)}
        fresh = {"ladder_O": {w for it in ladder_o for w in batch_worlds(it, spec)},
                 "ladder_N": {w for it in ladder_n for w in batch_worlds(it, spec)},
                 "triplets_O": {w for it, _ in trip_o for w in batch_worlds(it, spec)},
                 "triplets_N": {w for it, _ in trip_n for w in batch_worlds(it, spec)}}
        overlap = {f: {e: len(fw & ew) for e, ew in existing.items()} for f, fw in fresh.items()}
        prints_existing = {p for split in ("validation", "test") for it in L.load_split(split) for p in L.prints(it)}
        prints_existing |= {p for split in ("validation", "test") for it, _ in H.load_triplets(split) for p in L.prints(it)}
        prints_fresh = {p for it in ladder_o + ladder_n for p in L.prints(it)} | \
                       {p for it, _ in trip_o + trip_n for p in L.prints(it)}
        answers_equal = all(torch.equal(a[0].answer, b[0].answer) and torch.equal(a[1], b[1]) and torch.equal(a[2], b[2])
                            for a, b in zip(ladder_o, ladder_n))
        meta_equal = all(all(torch.equal(getattr(ma, f), getattr(mb, f)) for f in ("x_q", "u_q", "v_q", "a", "b", "rows"))
                         for (_, ma), (_, mb) in zip(trip_o, trip_n))
        out = OUT / "data"
        out.mkdir(parents=True, exist_ok=True)
        files = {}
        for name, value in (("ladder-O", ladder_o), ("ladder-N", ladder_n), ("triplets-O", trip_o),
                            ("triplets-N", trip_n)):
            path = out / f"{name}.pt"
            torch.save(value, path)
            files[name] = {"file": str(path.relative_to(ROOT)), "sha256": sha256(path)}
    except BaseException as error:
        charge("failed-data", "fresh data + overlap", time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    manifest = {"label": "fresh examples from the existing task family (not general-language evidence)",
                "seeds": SEEDS, "ladder": {"batches": LADDER_BATCHES, "visits": LADDER_BATCHES * VISITS,
                                           "questions": sum(len(it[2]) for it in ladder_o)},
                "triplets": {"batches": TRIPLET_BATCHES, "triplets": TRIPLET_BATCHES * PER_BATCH},
                "renaming": "one fixed-point-free permutation of the 16 person ids per batch (seed 5500 + batch; "
                            "triplets 5600 + batch); answers identical, triplets re-verified by the oracle",
                "answers_identical_under_renaming": answers_equal, "triplet_meta_identical_under_renaming": meta_equal,
                "world_overlap": overlap, "existing_world_counts": {k: len(v) for k, v in existing.items()},
                "fresh_world_counts": {k: len(v) for k, v in fresh.items()},
                "exact_visit_overlap_with_saved_heldout_sets": len(prints_fresh & prints_existing),
                "files": files, "model_loaded": False, "seconds": round(seconds, 2)}
    write_json(out / "manifest.json", manifest)
    charge("data", "fresh ladder + triplets (O, N) + overlap checks; no model loaded", seconds,
           overlap_total=sum(sum(v.values()) for v in overlap.values()))
    print(json.dumps({k: v for k, v in manifest.items() if k != "files"}, indent=1))


# ----------------------------------------------------------------------------- evaluation
def greedy(model, item, cards: str, order):
    import torch
    batch, supplied, hops = item
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    ep = model._start(batch, hidden, store, mentions)
    if cards == "all":
        model._insert(ep, store, torch.arange(len(hops)), supplied.gather(1, order))
    else:
        gold = torch.where(torch.arange(supplied.shape[1]) < hops.unsqueeze(1), supplied,
                           torch.full_like(supplied, -1))[:, :2]
        model._insert(ep, store, torch.arange(len(hops)), gold)
    tokens, lengths = model._greedy(batch, ep, mentions, None)
    return [tokens[q, :int(lengths[q])].tolist() for q in range(tokens.shape[0])]


def ladder_order(item, b: int, condition: str):
    import torch
    seed = SEEDS["ladder_order"][condition in ("P", "NP")] + b
    return torch.rand(item[1].shape, generator=torch.Generator().manual_seed(seed)).argsort(1)


def evaluate(model, data) -> dict:
    """Actual answer sequences for every question, per condition."""
    import torch
    from learnlab.core import IGNORE_INDEX
    from premonition.ladder_triplets import shared_order
    out = {"ladder": {}, "triplets": {}}
    for condition in CONDITIONS:
        items = data["ladder-N" if "N" in condition else "ladder-O"]
        seqs = {"all": [], "gold": []}
        for b, item in enumerate(items):
            seqs["all"] += greedy(model, item, "all", ladder_order(item, b, condition))
            if condition in ("O", "N"):
                seqs["gold"] += greedy(model, item, "gold", None)
        out["ladder"][condition] = {k: v for k, v in seqs.items() if v}
        trips = data["triplets-N" if "N" in condition else "triplets-O"]
        rec = []
        for j, (item, meta) in enumerate(trips):
            seed = SEEDS["triplet_order"][condition in ("P", "NP")] + j
            order = shared_order(meta, len(item[2]), torch.Generator().manual_seed(seed))
            seq = greedy(model, item, "all", order)
            for t in range(len(meta.a)):
                rec.append({role: seq[int(getattr(meta, f"{role}_q")[t])] for role in ("x", "u", "v")})
        out["triplets"][condition] = rec
    targets = [row[row != IGNORE_INDEX].tolist() for item in data["ladder-O"] for row in item[0].answer]
    out["ladder_targets"] = targets
    return out


def cmd_dry(args) -> None:
    """Complete-cost estimate BEFORE any fresh data exists and without loading any model: times the replay of 12
    training batches (the overlap check's main cost) and prices decoding from timings already in the ledger."""
    A.require(10, reserve=RESERVE)
    started = time.perf_counter()
    try:
        spec = L.spec()
        t0 = time.perf_counter()
        training_worlds(spec, 12)
        per_train_batch = (time.perf_counter() - t0) / 12
    except BaseException as error:
        charge("failed-dry", "timing", time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    rows = H.ledger_rows()
    pooled_outputs = next(r for r in rows if r["kind"] == "direct-eval" and r["name"] == "answer-original-s0")
    probe = next(r for r in rows if r["kind"] == "probe-run")
    ladder_decode = pooled_outputs["seconds"] / (3 * 16) * 1.10       # per 16-visit batch decode; address x1.10
    triplet_decode = probe["seconds"] / (4 * 32 * 5)                  # per 8-triplet batch decode (probe incl. extras)
    per_ckpt = LADDER_BATCHES * 6 * ladder_decode + TRIPLET_BATCHES * 4 * triplet_decode + 1.0
    package = {"data_and_overlap": (TRAIN_BATCHES_USED * per_train_batch + 8.0) * 1.3, "tests": 5.0,
               "run_4_checkpoints": 4 * per_ckpt * 1.5, "compare": 4.0, "final_verification": 1.0,
               "saving_reserve": RESERVE}
    need = sum(package.values())
    remaining = left() - seconds
    report = {"per_train_batch_replay": round(per_train_batch, 4),
              "decode_prices_from_ledger": {"ladder_batch": round(ladder_decode, 4), "triplet_batch": round(triplet_decode, 4),
                                            "sources": [f"{pooled_outputs['kind']} {pooled_outputs['name']} {pooled_outputs['at']}",
                                                        f"{probe['kind']} {probe['at']}"]},
              "package": {k: round(v, 1) for k, v in package.items()}, "total_needed": round(need, 1),
              "left_after_dry": round(remaining, 1), "fits": bool(need <= remaining), "model_loaded": False,
              "dry_seconds": round(seconds, 2)}
    write_json(OUT / "dry.json", report)
    charge("dry", "cost estimate (training-world replay timing + ledger decode prices; no model, no fresh data)", seconds,
           fits=report["fits"], needed=round(need, 1))
    print(json.dumps(report, indent=1))


def cmd_check(args) -> None:
    started = time.perf_counter()
    run = subprocess.run([sys.executable, "-B", "-m", "unittest", *args.tests], cwd=ROOT,
                         env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), capture_output=True, text=True)
    seconds = time.perf_counter() - started
    log = OUT / "checks" / f"{time.strftime('%H%M%S')}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"$ unittest {' '.join(args.tests)}\n{run.stdout}{run.stderr}")
    tail = (run.stdout + run.stderr).strip().splitlines()[-3:]
    charge("check", " ".join(args.tests), seconds, returncode=run.returncode, log=str(log.relative_to(ROOT)),
           result=" | ".join(tail))
    print(f"{seconds:.1f} s", "\n".join(tail))
    if run.returncode:
        print(run.stdout[-4000:], run.stderr[-4000:])
        raise SystemExit(run.returncode)


def cmd_run(args) -> None:
    import torch
    from learnlab.readonly import read_only
    if (OUT / "answers.json").exists():
        raise SystemExit("already evaluated; never re-run")
    dry = json.loads((OUT / "dry.json").read_text())
    manifest = json.loads((OUT / "data" / "manifest.json").read_text())
    need = dry["package"]["run_4_checkpoints"]
    if left() - RESERVE < need:
        raise SystemExit(f"refused: run needs ~{need:.0f} s; {left():.1f} s left with the reserve")
    data = {}
    for name, info in manifest["files"].items():
        path = ROOT / info["file"]
        if sha256(path) != info["sha256"]:
            raise SystemExit(f"{path} changed since it was frozen")
        data[name] = torch.load(path, weights_only=False)
    started = time.perf_counter()
    answers = {}
    try:
        for seed, names in PAIRS.items():
            for name in names:
                model, info = A.load_address(name) if "address" in name else H.load(name)
                with read_only(model):
                    answers[name] = {"sha256": info["sha256"], **evaluate(model, data)}
    except BaseException as error:
        charge("failed-run", "4 checkpoints on fresh data", time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    write_json(OUT / "answers.json", answers)
    charge("run", "4 checkpoints x fresh ladder + triplets x O/N/P/NP (read-only)", seconds)
    print(f"evaluated {len(answers)} checkpoints in {seconds:.1f} s")


def scores(ans, data) -> dict:
    """Per-question correctness bits (ladder slices; triplet pair metrics) per condition."""
    import torch
    hops = torch.cat([it[2] for it in data["ladder-O"]])
    held = torch.cat([it[0].slices["heldout"] for it in data["ladder-O"]])
    targets = ans["ladder_targets"]
    out = {}
    for condition in CONDITIONS:
        lad = ans["ladder"][condition]
        ok_all = torch.tensor([s == t for s, t in zip(lad["all"], targets)])
        entry = {"choose:one_hop": ok_all[hops == 1], "combine:two_hop_trained_rel": ok_all[(hops == 2) & ~held],
                 "combine:two_hop_heldout_rel": ok_all[(hops == 2) & held]}
        if "gold" in lad:
            ok_gold = torch.tensor([s == t for s, t in zip(lad["gold"], targets)])
            entry["read:one_hop"] = ok_gold[hops == 1]
        trips = data["triplets-N" if "N" in condition else "triplets-O"]
        a = torch.cat([m.a for _, m in trips]).tolist()
        b = torch.cat([m.b for _, m in trips]).tolist()
        rec = ans["triplets"][condition]
        x = torch.tensor([r["x"][:1] == [ai] for r, ai in zip(rec, a)])
        u = torch.tensor([r["u"][:1] == [ai] for r, ai in zip(rec, a)])
        v = torch.tensor([r["v"][:1] == [bi] for r, bi in zip(rec, b)])
        entry.update({"triplets/x_correct": x, "triplets/invariant_both_correct": x & u,
                      "triplets/relevant_both_correct": x & v})
        out[condition] = entry
    return out


def cmd_compare(args) -> None:
    """Paired address - pooled per seed and condition; predeclared confirmation rule; answer invariance."""
    import torch
    A.require(5, reserve=5)
    started = time.perf_counter()
    manifest = json.loads((OUT / "data" / "manifest.json").read_text())
    data = {name: torch.load(ROOT / info["file"], weights_only=False) for name, info in manifest["files"].items()}
    answers = json.loads((OUT / "answers.json").read_text())
    visits = torch.cat([it[0].q_visit + i * VISITS for i, it in enumerate(data["ladder-O"])])
    hops = torch.cat([it[2] for it in data["ladder-O"]])
    held = torch.cat([it[0].slices["heldout"] for it in data["ladder-O"]])
    clusters = {"choose:one_hop": visits[hops == 1], "read:one_hop": visits[hops == 1],
                "combine:two_hop_trained_rel": visits[(hops == 2) & ~held],
                "combine:two_hop_heldout_rel": visits[(hops == 2) & held]}
    rows, table = [], {}
    for seed, (mine, ctrl) in PAIRS.items():
        sa, sc = scores(answers[mine], data), scores(answers[ctrl], data)
        for condition in CONDITIONS:
            for metric, bits in sa[condition].items():
                other = sc[condition][metric]
                group = clusters.get(metric, torch.arange(len(bits)))
                boot = H.paired_bootstrap(bits.float(), other.float(), group, resamples=10000, alpha=0.01)
                rows.append({"seed": seed, "condition": condition, "metric": metric, "address": int(bits.sum()),
                             "pooled": int(other.sum()), "n": len(bits), **boot})
    rule = ("confirmed iff, in EVERY condition (O, N, P, NP) and on BOTH seeds, the paired lower bound of (address - "
            "pooled) is > 0 for choose:one_hop AND triplets/relevant_both_correct; not confirmed iff any such upper "
            "bound < 0; else partly confirmed")
    key = [r for r in rows if r["metric"] in ("choose:one_hop", "triplets/relevant_both_correct")]
    verdict = ("confirmed" if all(r["lower"] > 0 for r in key) else
               "not confirmed" if any(r["upper"] < 0 for r in key) else "partly confirmed")
    invariance = {}
    for name, ans in answers.items():
        lad = ans["ladder"]
        invariance[name] = {
            "ladder_all_same_answer_O_vs_N": sum(a == b for a, b in zip(lad["O"]["all"], lad["N"]["all"])),
            "ladder_all_same_answer_O_vs_P": sum(a == b for a, b in zip(lad["O"]["all"], lad["P"]["all"])),
            "ladder_questions": len(lad["O"]["all"]),
            "triplet_x_same_answer_O_vs_NP": sum(a["x"] == b["x"] for a, b in zip(ans["triplets"]["O"],
                                                                              ans["triplets"]["NP"]))}
    result = {"label": manifest["label"], "rule": rule, "verdict": verdict, "rows": rows, "invariance": invariance,
              "data_manifest_sha256": sha256(OUT / "data" / "manifest.json"),
              "answers_sha256": sha256(OUT / "answers.json")}
    seconds = time.perf_counter() - started
    write_json(OUT / "compare.json", result)
    charge("analysis", "paired address - pooled on fresh data, rule, invariance", seconds)
    print("VERDICT:", verdict)
    for r in rows:
        print(f"s{r['seed']} {r['condition']:2} {r['metric']:32} {r['address']:4} {r['pooled']:4} /{r['n']:3} "
              f"{r['point']:+.4f} [{r['lower']:+.4f}, {r['upper']:+.4f}]")
    print(json.dumps(invariance, indent=1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("freeze")
    for name in ("dry", "data", "run", "compare"):
        sub.add_parser(name)
    check = sub.add_parser("check")
    check.add_argument("--tests", nargs="+", required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        return freeze()
    bootstrap()
    {"dry": cmd_dry, "check": cmd_check, "data": cmd_data, "run": cmd_run, "compare": cmd_compare}[args.command](args)


if __name__ == "__main__":
    main()
