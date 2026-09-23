"""Milestone-3 continuation 2: what the four answer-only checkpoints respond to (read-only probe; no training).

EXPLORATORY SYNTHETIC-VOCABULARY EVIDENCE. Toy ladder, legacy toy label-free rule, supplied gold-evidence cards
(privileged), nothink+qread decode, model defaults unchanged, H1 OFF, full_verdict: false.

Checkpoints (all existing, loaded read-only): answer-original-s{0,1} (pooled cards) and answer-direct-s{0,1} (direct
contextual-state reader). Data: the frozen milestone-3 validation triplets (triplets-validation.pt): per triplet the
original world x, an irrelevant change u (answer kept) and a relevant change v (answer changed; swaps keep the word
inventory). Card orders exactly as milestone 3's triplet readout (shared per triplet, seed 9100 + batch).

Memory conditions, all derived from ONE starting state per batch (same reader pass, same store, same insertion):
  full         the model's normal decoder memory
  no_evidence  the inserted evidence rows (pooled card rows; direct: token rows) masked out; entity slots kept bound
  no_slots     entity-slot rows restored to their pre-insertion values (unbound); evidence rows kept
  neither      both; must reproduce the no-card decode exactly (faithfulness check)
Recorded: actual greedy answers (full token sequences) of every question under every condition; for x/u/v of each
triplet, which supplied card's value was answered; decoder cross-attention at the first answer position (full
memory; reconstructed from the decoder's own weights and checked against its forward pass) by row type.

    PY -B scripts/premonition_binding_probe.py freeze
    PY -B scripts/premonition_binding_probe.py check --tests tests.test_premonition_binding_probe
    PY -B scripts/premonition_binding_probe.py dry
    PY -B scripts/premonition_binding_probe.py run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
M3 = "m03-20260919-071009"
M3_OUT = ROOT / "artifacts" / f"opus-{M3}"
OUT = M3_OUT / "probe"
ARCHIVE = ROOT / "archive" / f"opus-{M3}-probe"
SELF = "scripts/premonition_binding_probe.py"
CKPTS = ("answer-original-s0", "answer-original-s1", "answer-direct-s0", "answer-direct-s1")
CONDITIONS = ("full", "no_evidence", "no_slots", "neither")
CARD_TYPES = ("gold", "same_person", "same_relation", "other")        # supplied columns 0..3 of a 1-hop question
ROLES = ("marker", "person", "relation", "value", "rest")             # token rank within an attribute line
BATCHES_ALL, BATCHES_FALLBACK = 32, 16
EXAMPLES = {"per_kind": 2, "checkpoints": ("answer-original-s0", "answer-direct-s0")}
RESERVE = 30.0
D = H = L = None


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, default=str))


def freeze() -> None:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    (ARCHIVE / "frozen" / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / SELF, ARCHIVE / "frozen" / SELF)
    (ARCHIVE / "FROZEN.SHA256SUMS").write_text(f"{sha256(ARCHIVE / 'frozen' / SELF)}  ./{SELF}\n")
    write_json(ARCHIVE / "FROZEN-NOTES.json", {
        "imports": f"archive/opus-{M3}-direct/frozen (verified by premonition_direct_reader.bootstrap)",
        "added": [SELF], "note": "the probe adds no importable module; model code is the direct-reader snapshot"})
    print("frozen", SELF)


def bootstrap() -> None:
    global D, H, L
    frozen = ARCHIVE / "frozen" / SELF
    if sha256(frozen) != (ARCHIVE / "FROZEN.SHA256SUMS").read_text().split()[0] or sha256(ROOT / SELF) != sha256(frozen):
        raise SystemExit("live probe differs from its frozen copy: re-freeze (and journal it) first")
    sys.path.insert(0, str(ROOT / "scripts"))
    import premonition_direct_reader as direct
    direct.bootstrap()                       # verifies the direct snapshot, harness identities, sealed ledger prefix
    D, H, L = direct, direct.H, direct.L


def charge(kind: str, name: str, seconds: float, **extra) -> None:
    H.ledger_add(f"probe-{kind}", name, seconds, continuation="binding-probe", **extra)


def left() -> float:
    return H.CAP_SECONDS - H.ledger_seconds()


# ----------------------------------------------------------------------------- mechanics
def regions(model, rows_before: int, rows_after: int) -> dict:
    c = model.config
    return {"question": (0, c.question_rows), "slots": (c.question_rows, c.question_rows + c.slots),
            "cards": (model._card_base, model._card_base + c.cards),
            "registers": (model._register_base, model._register_base + c.registers),
            "tokens": (rows_before, rows_after)}


def start_state(model, item, order):
    """ONE starting state: reader pass, store, episode before insertion (copied), episode after insertion."""
    import torch
    batch, supplied, hops = item
    hidden = model.read(batch)
    store = model.build_store(hidden, batch)
    mentions = model._mentions(batch)
    ep = model._start(batch, hidden, store, mentions)
    pre_x, pre_valid = ep.x.clone(), ep.valid.clone()
    chosen = supplied.gather(1, order)
    model._insert(ep, store, torch.arange(len(hops)), chosen)
    return ep, pre_x, pre_valid, mentions, chosen


def memories(model, ep, pre_x, pre_valid) -> tuple[dict, dict]:
    """Condition -> (x, valid), plus faithfulness facts about what insertion changed."""
    import torch
    rows = pre_x.shape[1]
    reg = regions(model, rows, ep.x.shape[1])
    changed = (ep.x[:, :rows] != pre_x).any(-1).any(0)
    valid_changed = (ep.valid[:, :rows] != pre_valid).any(0)
    allowed = torch.zeros(rows, dtype=torch.bool)
    for name in ("slots", "cards"):
        allowed[slice(*reg[name])] = True
    facts = {"x_changed_outside_slots_cards": int((changed & ~allowed).sum()),
             "valid_changed_outside_cards": int((valid_changed & ~allowed).sum()),
             "slot_rows_changed": int(changed[slice(*reg["slots"])].sum()),
             "slot_valid_changed": int(valid_changed[slice(*reg["slots"])].sum())}
    evidence = torch.zeros(ep.x.shape[1], dtype=torch.bool)
    evidence[slice(*reg["cards"])] = True
    evidence[slice(*reg["tokens"])] = True
    unbound = ep.x.clone()
    unbound[:, slice(*reg["slots"])] = pre_x[:, slice(*reg["slots"])]
    masked = ep.valid & ~evidence
    return {"full": (ep.x, ep.valid), "no_evidence": (ep.x, masked), "no_slots": (unbound, ep.valid),
            "neither": (unbound, masked)}, facts


def decode(model, batch, mentions, x, valid):
    tokens, lengths = model._greedy(batch, SimpleNamespace(x=x, valid=valid), mentions, None)
    return [tokens[q, :int(lengths[q])].tolist() for q in range(tokens.shape[0])]


def cross_attention(model, x, valid, prefix):
    """Decoder cross-attention weights [Q, heads, rows] at the last prefix position (the first answer prediction),
    recomputed from the decoder's own weights, plus the max error of (a) the attended values against SDPA and
    (b) the final decoder state against model._decode_logits."""
    import torch
    import torch.nn.functional as F
    from premonition.model import _norm, rope
    dec = model.decoder
    h = model.embed(prefix)
    n, length, width = h.shape
    heads = dec.heads
    q, k, v = dec.qkv(dec.norm1(h)).view(n, length, 3, heads, -1).permute(2, 0, 3, 1, 4)
    positions = torch.arange(length)
    q, k = rope(q, positions, dec.base), rope(k, positions, dec.base)
    h = h + dec.proj(F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(n, length, width))
    cq = dec.cross_q(dec.norm2(h)).view(n, length, heads, -1).transpose(1, 2)
    ck, cv = dec.cross_kv(_norm(x)).view(n, x.shape[1], 2, heads, -1).permute(2, 0, 3, 1, 4)
    scores = (cq @ ck.transpose(-1, -2)) / math.sqrt(cq.shape[-1])
    weights = scores.masked_fill(~valid[:, None, None, :], -math.inf).softmax(-1)
    mine = weights @ cv
    ref = F.scaled_dot_product_attention(cq, ck, cv, attn_mask=valid[:, None, None, :])
    h2 = h + dec.cross_proj(mine.transpose(1, 2).reshape(n, length, width))
    out = dec.norm(h2 + dec.mlp(dec.norm3(h2)))
    full = model._decode_logits(x, valid, prefix)
    return weights[:, :, -1], float((mine - ref).abs().max()), float((out - full).abs().max())


def card_values(batch, supplied, q) -> list:
    """Value token of each supplied card column 0..3 of question q (line layout [WORLD, ENT, REL, VAL, ...])."""
    v = int(batch.q_visit[q])
    return [int(batch.tokens[v, int(batch.line_start[v, int(supplied[q, c])]) + 3]) for c in range(4)]


def source(token, values) -> str:
    hits = [CARD_TYPES[c] for c in range(4) if values[c] == token]
    return hits[0] if len(hits) == 1 else ("not_on_cards" if not hits else "ambiguous")


def attention_by_type(model, weights, q, chosen, order, rows_before, longest, e, other) -> dict:
    """Head-averaged attention mass of question row q by row type (supplied-card types, token roles, slots)."""
    w = weights[q].mean(0)
    c = model.config
    out = {"question": float(w[:c.question_rows].sum()),
           "slot_question_person": float(w[c.question_rows + e]),
           "slot_other_person": float(w[c.question_rows + other]),
           "slots_rest": float(w[c.question_rows:c.question_rows + c.slots].sum() - w[c.question_rows + e]
                               - w[c.question_rows + other]),
           "registers": float(w[model._register_base:model._register_base + c.registers].sum())}
    for name in CARD_TYPES:
        out[f"card_{name}"] = 0.0
    for role in ROLES:
        out[f"role_{role}"] = 0.0
    real = 0
    for k in range(chosen.shape[1]):
        if int(chosen[q, k]) < 0:
            continue
        kind = CARD_TYPES[int(order[q, k])]
        if longest:                                     # direct: token rows of this card
            block = w[rows_before + k * longest:rows_before + (k + 1) * longest]
            out[f"card_{kind}"] += float(block.sum())
            for j in range(longest):
                out[f"role_{ROLES[min(j, 4)]}"] += float(block[j])
        else:
            out[f"card_{kind}"] += float(w[model._card_base + real])
        real += 1
    return out


def probe_checkpoint(name: str, batches: int, *, examples: bool) -> dict:
    import torch
    from learnlab.core import IGNORE_INDEX
    from learnlab.readonly import read_only
    from premonition.ladder_triplets import shared_order
    from premonition.ovn_qread import question_prefix
    model, info = D.load_any(name)
    triplets = H.load_triplets("validation")[:batches]
    spec = L.spec()
    records, faith = [], {"insertion": [], "attention_error": 0.0, "decoder_error": 0.0, "neither_equals_none": True,
                          "full_equals_saved_bits": None}
    with read_only(model):
        for j, (item, meta) in enumerate(triplets):
            batch, supplied, hops = item
            order = shared_order(meta, len(hops), torch.Generator().manual_seed(9100 + j))
            ep, pre_x, pre_valid, mentions, chosen = start_state(model, item, order)
            mems, facts = memories(model, ep, pre_x, pre_valid)
            faith["insertion"].append(facts)
            answers = {cond: decode(model, batch, mentions, *mems[cond]) for cond in CONDITIONS}
            none = decode(model, batch, mentions, pre_x, pre_valid)
            faith["neither_equals_none"] &= answers["neither"] == none
            prefix = question_prefix(batch, model.config.pad_id)
            weights, err_att, err_dec = cross_attention(model, *mems["full"], prefix)
            faith["attention_error"] = max(faith["attention_error"], err_att)
            faith["decoder_error"] = max(faith["decoder_error"], err_dec)
            rows_before = pre_x.shape[1]
            longest = (ep.x.shape[1] - rows_before) // chosen.shape[1] if ep.x.shape[1] > rows_before else 0
            for t in range(len(meta.a)):
                rec = {"batch": j, "t": t, "kind_u": meta.kind_u[t], "kind_v": meta.kind_v[t],
                       "a": int(meta.a[t]), "b": int(meta.b[t])}
                for role, qs in (("x", meta.x_q), ("u", meta.u_q), ("v", meta.v_q)):
                    q = int(qs[t])
                    vis = int(batch.q_visit[q])
                    end = int(batch.q_span[q, 1])
                    e = int(batch.tokens[vis, end - 3]) - spec.vocab_size
                    values = card_values(batch, supplied, q)
                    x_line = int(supplied[q, 2])
                    other = int(batch.tokens[vis, int(batch.line_start[vis, x_line]) + 1]) - spec.vocab_size
                    target = batch.answer[q][batch.answer[q] != IGNORE_INDEX].tolist()
                    rec[role] = {"q": q, "person": e, "relation": int(batch.tokens[vis, end - 2]) - spec.relation(0),
                                 "other_person": other, "card_values": values, "target": target,
                                 "answers": {cond: answers[cond][q] for cond in CONDITIONS},
                                 "source": {cond: source(answers[cond][q][0] if answers[cond][q] else -1, values)
                                            for cond in CONDITIONS},
                                 "attention": attention_by_type(model, weights, q, chosen, order, rows_before,
                                                                longest, e, other)}
                records.append(rec)
    return {"ckpt": name, **info, "records": records, "faith": faith}


def saved_bits_match(result: dict) -> bool:
    """The full-memory first answers reproduce the saved triplet correctness bits of the same checkpoint."""
    name = result["ckpt"]
    path = (D.OUT / "eval" / f"{name}.json") if "direct" in name else (M3_OUT / "eval" / f"{name}.json")
    saved = json.loads(path.read_text())["scores"]["triplets"]
    n = len(result["records"])
    for role in ("x", "u", "v"):
        want = saved[f"{role}_correct"]["bits"][:n]
        got = "".join("1" if (r[role]["answers"]["full"][:1] == [r["a"] if role != "v" else r["b"]]) else "0"
                      for r in result["records"])
        if got != want:
            return False
    return True


# ----------------------------------------------------------------------------- summaries
def summarize(result: dict) -> dict:
    import torch
    recs = result["records"]
    n = len(recs)
    ids = torch.arange(n)
    boot = lambda bits: H.cluster_bootstrap(torch.tensor(bits, dtype=torch.float64), ids, resamples=10000, alpha=0.01)
    pboot = lambda a, b: H.paired_bootstrap(torch.tensor(a, dtype=torch.float64), torch.tensor(b, dtype=torch.float64),
                                            ids, resamples=10000, alpha=0.01)
    first = lambda r, role, cond: r[role]["answers"][cond][:1]
    out = {"triplets": n, "conditions": {}}
    for cond in CONDITIONS:
        x_ok = [first(r, "x", cond) == [r["a"]] for r in recs]
        u_ok = [first(r, "u", cond) == [r["a"]] for r in recs]
        v_ok = [first(r, "v", cond) == [r["b"]] for r in recs]
        entry = {"x_correct": sum(x_ok), "u_correct": sum(u_ok), "v_correct": sum(v_ok),
                 "invariant_both": sum(a and b for a, b in zip(x_ok, u_ok)),
                 "relevant_both": sum(a and b for a, b in zip(x_ok, v_ok)),
                 "full_sequence_x_correct": sum(r["x"]["answers"][cond] == r["x"]["target"] for r in recs),
                 "answer_changed_on_relevant": sum(r["x"]["answers"][cond] != r["v"]["answers"][cond] for r in recs),
                 "answer_kept_on_irrelevant": sum(r["x"]["answers"][cond] == r["u"]["answers"][cond] for r in recs),
                 "x_correct_bounds": boot(x_ok)}
        for role in ("x", "v"):
            counts = {}
            for r in recs:
                counts[r[role]["source"][cond]] = counts.get(r[role]["source"][cond], 0) + 1
            entry[f"{role}_answer_source"] = dict(sorted(counts.items()))
        # v: after the swap the gold card holds b and the partner card holds a
        entry["v_tracks_card"] = sum(first(r, "v", cond) == [r["b"]] for r in recs)
        entry["v_tracks_value"] = sum(first(r, "v", cond) == [r["a"]] for r in recs)
        if cond != "full":
            changed = [r["x"]["answers"][cond] != r["x"]["answers"]["full"] for r in recs]
            full_ok = [first(r, "x", "full") == [r["a"]] for r in recs]
            entry["x_answer_changed_vs_full"] = sum(changed)
            entry["x_correct_minus_full"] = pboot(x_ok, full_ok)
        out["conditions"][cond] = entry
    for kind in ("subject_swap", "relation_swap"):
        sub = [r for r in recs if r["kind_v"] == kind]
        out[f"v_{kind}"] = {"n": len(sub),
                            "tracks_card": sum(first(r, "v", "full") == [r["b"]] for r in sub),
                            "tracks_value": sum(first(r, "v", "full") == [r["a"]] for r in sub),
                            "x_correct": sum(first(r, "x", "full") == [r["a"]] for r in sub)}
    att = {}
    for role in ("x", "v"):
        keys = recs[0][role]["attention"].keys()
        att[role] = {k: round(sum(r[role]["attention"][k] for r in recs) / n, 4) for k in keys}
    correct = [r for r in recs if first(r, "x", "full") == [r["a"]]]
    wrong = [r for r in recs if first(r, "x", "full") != [r["a"]]]
    for label, sub in (("x_when_correct", correct), ("x_when_wrong", wrong)):
        if sub:
            att[label] = {k: round(sum(r["x"]["attention"][k] for r in sub) / len(sub), 4)
                          for k in recs[0]["x"]["attention"]}
    out["attention_full_memory"] = att
    return out


def example_lines(result: dict, count: int) -> list:
    spec = L.spec()
    tok = lambda t: (f"V{t - spec.value(0)}" if spec.value(0) <= t < spec.value(0) + spec.values else
                     "<eos>" if t == 2 else f"t{t}")
    lines = []
    picked = []
    for kind in ("subject_swap", "relation_swap"):
        picked += [r for r in result["records"] if r["kind_v"] == kind][:count]
    for r in picked:
        x, u, v = r["x"], r["u"], r["v"]
        names = lambda vals: ", ".join(f"{CARD_TYPES[c]}=V{vals[c] - spec.value(0)}" for c in range(4))
        lines.append(f"- triplet {r['batch']}.{r['t']} — question: person P{x['person']}, relation R{x['relation']} "
                     f"(other person P{x['other_person']}); relevant change {r['kind_v']}, irrelevant change "
                     f"{r['kind_u']}")
        lines.append(f"  - cards x: {names(x['card_values'])} | u: {names(u['card_values'])} | "
                     f"v: {names(v['card_values'])}; right answers x/u V{r['a'] - spec.value(0)}, "
                     f"v V{r['b'] - spec.value(0)}")
        for cond in CONDITIONS:
            ans = " / ".join(" ".join(tok(t) for t in s["answers"][cond]) for s in (x, u, v))
            src = " / ".join(s["source"][cond] for s in (x, u, v))
            lines.append(f"  - {cond:11} answers x/u/v: {ans}   (card answered: {src})")
        att = lambda s: ", ".join(f"{t} {s['attention'][f'card_{t}']:.2f}" for t in CARD_TYPES)
        lines.append(f"  - attention (full): x [{att(x)}; slot P{x['person']} "
                     f"{x['attention']['slot_question_person']:.2f}] | v [{att(v)}]")
    return lines


# ----------------------------------------------------------------------------- commands
def cmd_check(args) -> None:
    import os
    import subprocess
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


def cmd_dry(args) -> None:
    """Time ONE triplet batch on ONE pooled and ONE direct checkpoint (outputs discarded, not inspected) and write
    the complete-diagnostic estimate; the subset follows the predeclared fallback rule."""
    H.require(20, reserve=RESERVE)
    started = time.perf_counter()
    try:
        per = {}
        for name in ("answer-original-s0", "answer-direct-s0"):
            t0 = time.perf_counter()
            probe_checkpoint(name, 1, examples=False)
            per[name] = time.perf_counter() - t0
    except BaseException as error:
        charge("failed-dry", "one-batch timing", time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    load_overhead = 1.0
    per_batch = max(per.values())
    estimate = {b: round((4 * (per_batch * b + load_overhead)) * 1.25 + 5.0 + RESERVE, 1)
                for b in (BATCHES_ALL, BATCHES_FALLBACK)}
    remaining = left() - seconds
    batches = BATCHES_ALL if estimate[BATCHES_ALL] <= remaining else (
        BATCHES_FALLBACK if estimate[BATCHES_FALLBACK] <= remaining else 0)
    report = {"seconds_one_batch": {k: round(v, 2) for k, v in per.items()}, "estimate_with_reserve": estimate,
              "left_after_dry": round(remaining, 1), "batches": batches, "dry_seconds": round(seconds, 2)}
    write_json(OUT / "dry.json", report)
    charge("dry", "one-batch timing (outputs discarded)", seconds, batches=batches)
    print(json.dumps(report, indent=1))


def cmd_run(args) -> None:
    dry = json.loads((OUT / "dry.json").read_text())
    batches = dry["batches"]
    if not batches:
        raise SystemExit("the diagnostic does not fit the remaining allowance: not run")
    if (OUT / "summary.json").exists():
        raise SystemExit("already run; never rerun")
    need = dry["estimate_with_reserve"][str(batches)] - RESERVE
    if left() - RESERVE < need:
        raise SystemExit(f"refused: needs ~{need:.0f} s, {left():.1f} s left with a {RESERVE:.0f} s reserve")
    started = time.perf_counter()
    summary = {"label": "exploratory synthetic-vocabulary evidence; full_verdict: false", "batches": batches,
               "triplets_file": str((M3_OUT / "data" / "triplets-validation.pt").relative_to(ROOT)),
               "triplets_sha256": sha256(M3_OUT / "data" / "triplets-validation.pt"), "checkpoints": {}}
    examples = ["# Worked examples (predeclared: first 2 triplets of each relevant-change kind, seed-0 checkpoints)",
                "", "V = value word, P = person, R = relation (synthetic vocabulary). Card types are relative to the "
                "question: gold = (P, R), same_person = (P, other R), same_relation = (other P, R), other = (other P, "
                "other R).", ""]
    try:
        for name in CKPTS:
            t0 = time.perf_counter()
            result = probe_checkpoint(name, batches, examples=name in EXAMPLES["checkpoints"])
            faith = result.pop("faith")
            ins = faith.pop("insertion")
            faith["insertion_x_changed_outside_slots_cards"] = sum(f["x_changed_outside_slots_cards"] for f in ins)
            faith["insertion_valid_changed_outside_cards"] = sum(f["valid_changed_outside_cards"] for f in ins)
            faith["slot_rows_changed_by_binding"] = sum(f["slot_rows_changed"] for f in ins)
            faith["slot_valid_changed_by_binding"] = sum(f["slot_valid_changed"] for f in ins)
            faith["full_equals_saved_bits"] = saved_bits_match(result)
            faith["isolation_ok"] = bool(faith["neither_equals_none"] and faith["full_equals_saved_bits"]
                                         and faith["insertion_x_changed_outside_slots_cards"] == 0
                                         and faith["insertion_valid_changed_outside_cards"] == 0
                                         and faith["slot_valid_changed_by_binding"] == 0
                                         and faith["attention_error"] < 1e-4 and faith["decoder_error"] < 1e-4)
            summary["checkpoints"][name] = {"reader": result["reader"], "sha256": result["sha256"],
                                            "faithfulness": faith, **summarize(result),
                                            "seconds": round(time.perf_counter() - t0, 2)}
            write_json(OUT / "records" / f"{name}.json", result)
            if name in EXAMPLES["checkpoints"]:
                examples += [f"## {name} ({result['reader']} reader)", ""] + example_lines(result, EXAMPLES["per_kind"]) \
                    + [""]
    except BaseException as error:
        charge("failed-run", "probe", time.perf_counter() - started, error=repr(error)[:300])
        raise
    seconds = time.perf_counter() - started
    summary["seconds"] = round(seconds, 2)
    write_json(OUT / "summary.json", summary)
    (OUT / "examples.md").write_text("\n".join(examples) + "\n")
    charge("run", f"{len(CKPTS)} checkpoints x {batches} triplet batches x {len(CONDITIONS)} conditions (+none)",
           seconds, isolation_ok={k: v["faithfulness"]["isolation_ok"] for k, v in summary["checkpoints"].items()})
    for name, s in summary["checkpoints"].items():
        print(f"== {name}: isolation_ok {s['faithfulness']['isolation_ok']} ({s['seconds']} s)")
        for cond, c in s["conditions"].items():
            print(f"  {cond:11} x {c['x_correct']:3} u {c['u_correct']:3} v {c['v_correct']:3} inv {c['invariant_both']:3}"
                  f" rel {c['relevant_both']:3} changed_rel {c['answer_changed_on_relevant']:3} "
                  f"v card/value {c['v_tracks_card']}/{c['v_tracks_value']}  x src {c['x_answer_source']}"
                  + (f"  changed_vs_full {c['x_answer_changed_vs_full']}" if cond != "full" else ""))
    print(f"({seconds:.1f} s)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("freeze")
    check = sub.add_parser("check")
    check.add_argument("--tests", nargs="+", required=True)
    sub.add_parser("dry")
    sub.add_parser("run")
    args = parser.parse_args()
    if args.command == "freeze":
        return freeze()
    bootstrap()
    {"check": cmd_check, "dry": cmd_dry, "run": cmd_run}[args.command](args)


if __name__ == "__main__":
    main()
