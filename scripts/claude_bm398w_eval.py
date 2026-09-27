#!/usr/bin/env python3
"""bm-398w eval (benchmarks thread, 2026-09-27; DRAFT, not sealed): does a reader adapter trained on RAFT-style
practice (scripts/claude_bm398w_data.py) make the 1B answer better from store B's 20 lines? Plan and marks:
artifacts/claude-bm398w-20260927/PLAN-DRAFT.md. Every LoCoMo number is "after development use". Nothing here trains,
and nothing from LoCoMo, LongMemEval, MMLU or GSM8K is ever trained on. No question, answer, line or reply text is
printed.

Arms (the same lines, layout and prompt; only the weights differ). One process loads the plain MiniCPM5-1B, wraps
q/k/v/o in bm-398i's on/off switch (claude_bm398i_switch) and loads the bm-398w adapter behind it:
  BN  switch off: the plain 1B (bm-398i: off equals the unwrapped model, byte for byte, CPU and GPU)
  BR  switch on:  the 1B with the bm-398w adapter
Panels:
  locomo  LoCoMo conversations 0-9, categories 1-4 with evidence (1,531 questions); store B's first 20 distinct turns
          (rd-378L's ranked_turns.jsonl for 0-4, rd-378u's for 5-9), laid out and prompted as bm-398n and bm-398v did
  panel   the fresh held-out practice panel (claude_bm398w_data.py build --panel, seed 3994), PANEL_N items, its
          file pinned by SEAL-panel.sha256.txt before training; never read by the builder
  general MMLU-Redux-300 and GSM8K-300 (bm-390's sets and prompts): the unwrapped plain 1B (P), then BN and BR
The switch is a hand-given stand-in (disclosed scaffolding): on for memory questions, off for the others, set by the
panel. There is no switch in the build; a switch or MoE in the build needs Ben's yes.
Report only: qwen20 runs a plain model folder (Qwen3.5-2B, only if already on the machine) on the same 20 lines.

  locomo   python -B scripts/claude_bm398w_eval.py locomo --data DATA --ranked-l RL --ranked-u RU --model BASE --adapter A --out OUT [--limit N]
  panel    python -B scripts/claude_bm398w_eval.py panel --panel PANELDIR --model BASE --adapter A --out OUT [--limit N]
  general  python -B scripts/claude_bm398w_eval.py general --data DATA --model BASE --adapter A --out OUT [--limit N]
  qwen20   python -B scripts/claude_bm398w_eval.py qwen20 --data DATA --ranked-l RL --ranked-u RU --model QWEN --out OUT
  score    python -B scripts/claude_bm398w_eval.py score --data DATA --ranked-l RL --ranked-u RU --panel PANELDIR --runs OUT --out S.json
  prep     python -B scripts/claude_bm398w_eval.py prep --data DATA --ranked-l RL --ranked-u RU --panel PANELDIR --runs OUT --work W
  jscore   python -B scripts/claude_bm398w_eval.py jscore --data DATA --work W --score S.json
  selftest python -B scripts/claude_bm398w_eval.py selftest
OUT, W and PANELDIR hold benchmark or panel text: keep them outside the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_bm390 as B  # noqa: E402
import claude_bm398d_evidence as D  # noqa: E402
import claude_bm398n_notes as N  # noqa: E402

EXP = Path(__file__).resolve().parents[1] / "artifacts" / "claude-bm398w-20260927"
RANKED_L_SHA = N.RANKED_SHA                                                          # rd-378L, conversations 0-4
RANKED_U_SHA = "785c9c9adf26071b83716d53465c03663e96f99a517348f4a98f03b792d9ff5e"   # rd-378u, conversations 5-9
N_L, N_U, TURNS = 759, 772, 20
ARMS = ["BN", "BR"]
PANEL_N, PANEL_PICK_SEED = 300, 3995
JUDGE_SEED, BATCH, X1_N = 3996, 50, 60
R1_MIN_GAIN, R2_MIN_GAIN, MAX_P = 30, 15, 0.05     # R1: about 2 points of 1,531, the effect size of +15 of 759
R3_MAX_EXTRA_D, R3_MAX_CAT_DROP = 10, 3
BM398D = {"qwen_whole_chat": 138, "one_b_right_lines": 137, "n": 297}   # bm-398d (56c71354c), other judges


def _jsonl(p, tolerant: bool = False) -> list[dict]:
    """Rows of a JSONL file, split on newlines only (never on other line separators). tolerant: a line that does not
    parse (a reply file cut off by a crash) is skipped; inputs are read strictly."""
    out = []
    for x in Path(p).read_text(encoding="utf-8").split("\n"):
        if not x.strip():
            continue
        try:
            out.append(json.loads(x))
        except json.JSONDecodeError:
            if not tolerant:
                raise
    return out


def _dump(r) -> str:
    return json.dumps(r, ensure_ascii=True)


def _sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _write(path: Path, rows: list[dict]) -> str:
    path.write_text("".join(_dump(r) + "\n" for r in rows), encoding="utf-8", newline="\n")
    return _sha(path)


class Sink:
    """Reply files written row by row and flushed. On a relaunch after a crash, the questions every file already
    holds are kept and skipped; rows of a question only some files hold are dropped and written again."""

    def __init__(self, out: Path, names: list[str]):
        out.mkdir(parents=True, exist_ok=True)
        self.paths = {n: out / f"{n}.jsonl" for n in names}
        have = {n: ({r["qid"]: r for r in _jsonl(p, tolerant=True)} if p.exists() else {})
                for n, p in self.paths.items()}
        self.done = set.intersection(*(set(h) for h in have.values()))
        self.fh = {}
        for n, pth in self.paths.items():
            _write(pth, [r for q, r in have[n].items() if q in self.done])
            self.fh[n] = pth.open("a", encoding="utf-8", newline="\n")

    def write(self, name: str, row: dict) -> None:
        self.fh[name].write(_dump(row) + "\n")
        self.fh[name].flush()

    def close(self) -> None:
        for n, fh in self.fh.items():
            fh.close()
            print(f"wrote {n}.jsonl rows={len(_jsonl(self.paths[n]))} sha256={_sha(self.paths[n])}", flush=True)


# ======================================================================= inputs
def ranked(rl: str, ru: str) -> tuple[list[str], dict]:
    """(qids: rd-378L's 759 then rd-378u's 772, {qid: store B's 20 turns}); refuses any file but the pinned two."""
    qids, rt = [], {}
    for path, want in ((rl, RANKED_L_SHA), (ru, RANKED_U_SHA)):
        if _sha(path) != want:
            raise SystemExit("bm398w: a ranked_turns.jsonl is not the pinned file")
        for r in _jsonl(path):
            if r["arm"] != "B":
                continue
            if r["qid"] in rt:
                raise SystemExit("bm398w: a question appears twice")
            qids.append(r["qid"])
            rt[r["qid"]] = list(r["turns"])
    return qids, rt


def check(qids: list[str], rt: dict, info: dict) -> None:
    if len(qids) != N_L + N_U:
        raise SystemExit(f"bm398w: expected {N_L + N_U} questions")
    for q in qids:
        conv, _i, qa, gold = info[q]
        n = len(D.items_of(conv))
        t = rt[q]
        if qa["category"] not in (1, 2, 3, 4) or not gold:
            raise SystemExit("bm398w: a question outside categories 1-4 or without evidence")
        if len(t) != TURNS or len(set(t)) != TURNS or not all(0 <= p < n for p in t):
            raise SystemExit("bm398w: bad turn list")


def panel_rows(pdir: str, seal: str = "") -> list[dict]:
    """The sealed panel file (its sha256 must be listed in SEAL-panel.sha256.txt), PANEL_N items by a fixed draw.
    --panel-seal names another list, for a smoke on a stub panel only."""
    f = Path(pdir) / "panel.jsonl"
    seal = Path(seal) if seal else EXP / "SEAL-panel.sha256.txt"
    listed = {x.split()[0] for x in seal.read_text(encoding="utf-8").splitlines() if x.strip()} if seal.exists() else set()
    if _sha(f) not in listed:
        raise SystemExit("bm398w: panel.jsonl is not the sealed panel")
    rows = _jsonl(f)
    if any(not r["id"].startswith("w3994-") for r in rows):
        raise SystemExit("bm398w: a panel item is not from the panel seed")
    return pick_panel(rows)


def pick_panel(rows: list[dict]) -> list[dict]:
    rows = sorted(rows, key=lambda r: r["id"])
    if len(rows) <= PANEL_N:
        return rows
    keep = set(random.Random(PANEL_PICK_SEED).sample([r["id"] for r in rows], PANEL_N))
    return [r for r in rows if r["id"] in keep]


# ======================================================================= replies (BensPC)
def load(model_dir: str, adapter: str) -> dict:
    import claude_bm398i_switch as SW
    _tok, model, dev, _ = B.plain_model(model_dir)
    res = {"device": dev, "wrapped": SW.wrap(model), **SW.load_adapter(model, adapter),
           "adapter_file_sha256": _sha(adapter)}
    res["adapter_state_sha256"] = SW.adapter_sha(model)
    model.eval()
    return res


def set_arm(model_dir: str, arm: str) -> None:
    import claude_bm398i_switch as SW
    SW.set_on(B.plain_model(model_dir)[1], arm == "BR")


def _answer_both(model_dir: str, system: str, user: str, max_new: int) -> dict:
    out = {}
    for arm in ARMS:
        set_arm(model_dir, arm)
        t0 = time.time()
        reply, ntok = B.generate(model_dir, system, user, max_new)
        out[arm] = {"reply": reply, "ms": round((time.time() - t0) * 1000, 1), "prompt_tokens": ntok}
    set_arm(model_dir, "BN")
    return out


def locomo_user(conv: dict, i: int, qa: dict, keep: list[int]) -> str:
    return D.context(conv, D.items_of(conv), keep) + "\n\n" + B.QA_PROMPT.format(
        B.question_text(conv["sample_id"], i, qa))


def run_locomo(a) -> int:
    qids, rt = ranked(a.ranked_l, a.ranked_u)
    _kept, info = D.sample(Path(a.data))
    check(qids, rt, info)
    res = load(a.model, a.adapter)
    sink = Sink(Path(a.out), [f"locomo_{arm}" for arm in ARMS])
    t_all, todo = time.time(), [q for q in qids[: a.limit or None] if q not in sink.done]
    res["resumed_questions"] = len(sink.done)
    for n, q in enumerate(todo):
        conv, i, qa, _gold = info[q]
        both = _answer_both(a.model, B.LOCOMO_SYSTEM, locomo_user(conv, i, qa, rt[q]), B.ANS_TOKENS)
        for arm in ARMS:
            sink.write(f"locomo_{arm}", {"qid": q, "category": qa["category"], "turns": rt[q], **both[arm]})
        if (n + 1) % 100 == 0:
            print(f"[bm398w] locomo {n + 1}/{len(todo)} seconds={time.time() - t_all:.0f}", flush=True)
    sink.close()
    print(json.dumps(res | {"questions_run": len(todo), "seconds": round(time.time() - t_all)}), flush=True)
    return 0


def run_panel(a) -> int:
    items = panel_rows(a.panel, a.panel_seal)[: a.limit or None]
    res = load(a.model, a.adapter)
    sink = Sink(Path(a.out), [f"panel_{arm}" for arm in ARMS])
    t_all, todo = time.time(), [r for r in items if r["id"] not in sink.done]
    res["resumed_items"] = len(sink.done)
    for r in todo:
        both = _answer_both(a.model, r["system"], r["user"], B.ANS_TOKENS)
        for arm in ARMS:
            sink.write(f"panel_{arm}", {"qid": r["id"], "category": r["category"], **both[arm]})
    sink.close()
    print(json.dumps(res | {"panel_sha256": _sha(Path(a.panel) / "panel.jsonl"), "items": len(items),
                            "items_run": len(todo), "seconds": round(time.time() - t_all)}), flush=True)
    return 0


def run_general(a) -> int:
    """P (the unwrapped plain 1B) for both tasks first, then wrap: BN (off) and BR (on). R4 compares P and BN.
    A relaunch skips what each file already holds (P always runs before the switch is added)."""
    tasks = ("mmlu", "gsm8k")
    its = {t: _jsonl(Path(a.data) / f"{t}300.jsonl")[: a.limit or None] for t in tasks}
    t_all, ran = time.time(), {}

    def one_pass(name: str) -> None:
        for t in tasks:
            sink = Sink(Path(a.out), [f"{t}_{name}"])
            todo = [it for it in its[t] if it["qid"] not in sink.done]
            for it in todo:
                t0 = time.time()
                reply, _ = B.generate(a.model, B.GENERAL_SYSTEM, B.general_prompt(t, it), B.MAX_NEW[t])
                sink.write(f"{t}_{name}", {"qid": it["qid"], "reply": reply, "ms": round((time.time() - t0) * 1000, 1)})
            sink.close()
            ran[f"{t}_{name}"] = len(todo)

    one_pass("P")
    res = load(a.model, a.adapter)
    for arm in ARMS:
        set_arm(a.model, arm)
        one_pass(arm)
    set_arm(a.model, "BN")
    print(json.dumps(res | {"items_run": ran, "seconds": round(time.time() - t_all)}), flush=True)
    return 0


def run_qwen20(a) -> int:
    """Report only: a plain model folder on the same 20 lines (no switch, no adapter). F1 only, never judged."""
    qids, rt = ranked(a.ranked_l, a.ranked_u)
    _kept, info = D.sample(Path(a.data))
    check(qids, rt, info)
    sink = Sink(Path(a.out), ["locomo_Q20"])
    t_all, todo = time.time(), [q for q in qids[: a.limit or None] if q not in sink.done]
    for q in todo:
        conv, i, qa, _gold = info[q]
        t0 = time.time()
        reply, ntok = B.generate(a.model, B.LOCOMO_SYSTEM, locomo_user(conv, i, qa, rt[q]), B.ANS_TOKENS)
        sink.write("locomo_Q20", {"qid": q, "category": qa["category"], "reply": reply, "turns": rt[q],
                                  "ms": round((time.time() - t0) * 1000, 1), "prompt_tokens": ntok})
    sink.close()
    print(json.dumps({"questions_run": len(todo), "seconds": round(time.time() - t_all)}), flush=True)
    return 0


# ======================================================================= score (F1, general accuracy, R4)
def _replies(runs: Path, prefix: str, ids: list[str]) -> dict:
    out = {}
    for arm in ARMS:
        rows = {r["qid"]: r for r in _jsonl(runs / f"{prefix}_{arm}.jsonl")}
        if sorted(rows) != sorted(ids):
            raise SystemExit(f"bm398w: {prefix}_{arm} does not cover its panel")
        out[arm] = rows
    return out


def r4(runs: Path, data: Path, n_items: int = 300) -> dict:
    """R4: on each task, P, BN and BR each hold all n_items questions; every BN reply equals P's; equal right counts.
    BR (the adapter always on) is reported, never marked."""
    import claude_bm390_score as SC
    res = {}
    for t in ("mmlu", "gsm8k"):
        rows = {x: {r["qid"]: r for r in _jsonl(runs / f"{t}_{x}.jsonl")} for x in ("P", "BN", "BR")}
        res[t] = {x: SC.score_general(data, t, list(rows[x].values()))["summary"]["right"] for x in rows}
        res[t]["rows"] = {x: len(rows[x]) for x in rows}
        res[t]["BN_replies_equal_P"] = sum(rows["BN"].get(q, {}).get("reply") == r["reply"] for q, r in rows["P"].items())
    res["R4"] = all(set(res[t]["rows"].values()) == {n_items} and res[t]["BN_replies_equal_P"] == n_items
                    and res[t]["BN"] == res[t]["P"] for t in ("mmlu", "gsm8k"))
    return res


def score(a) -> int:
    import claude_bm390_score as SC
    runs = Path(a.runs)
    qids, rt = ranked(a.ranked_l, a.ranked_u)
    _kept, info = D.sample(Path(a.data))
    rep = _replies(runs, "locomo", qids)
    res = {"n": len(qids)}
    arms = list(ARMS)
    if (runs / "locomo_Q20.jsonl").exists():                  # report only, and only when it covers every question
        q20 = {r["qid"]: r for r in _jsonl(runs / "locomo_Q20.jsonl", tolerant=True)}
        if set(q20) >= set(qids):
            rep["Q20"], arms = q20, arms + ["Q20"]
        else:
            res["Q20_partial_rows"] = len(q20)
    for arm in arms:
        s = SC.score_locomo(Path(a.data), [rep[arm][q] for q in qids])["summary"]
        res[arm] = {k: s[k] for k in ("cat1to4_n", "cat1to4_f1", "cat1to4_abstain", "cat1to4_confident_wrong",
                                      "cat1to4_half_right", "cat1_f1", "cat2_f1", "cat3_f1", "cat4_f1")}
    res["BR_minus_BN_f1"] = round(res["BR"]["cat1to4_f1"] - res["BN"]["cat1to4_f1"], 2)
    res["evidence_among_the_20"] = sum(bool(set(info[q][3]) & set(rt[q])) for q in qids)
    res["general"] = r4(runs, Path(a.data)) if (runs / "gsm8k_BR.jsonl").exists() else None
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))
    return 0


# ======================================================================= blind judging
def latin(qids: list[str], rng: random.Random) -> dict[str, list[tuple[str, str]]]:
    groups = {f"L{g}": [(q, ARMS[(n + g) % 2]) for n, q in enumerate(qids)] for g in range(2)}
    groups["X1"] = sorted(rng.sample(groups["L0"], X1_N))
    for g in groups:
        rng.shuffle(groups[g])
    return groups


def prep(a) -> int:
    import claude_bm397_judge as J
    runs, work = Path(a.runs), Path(a.work)
    qids, rt = ranked(a.ranked_l, a.ranked_u)
    kept, info = D.sample(Path(a.data))
    lrep = _replies(runs, "locomo", qids)
    prow = {r["id"]: r for r in panel_rows(a.panel, a.panel_seal)}
    pids = sorted(prow)
    prep_ = _replies(runs, "panel", pids)
    chats = {c["sample_id"]: c for c in json.loads((Path(a.panel) / "chats.json").read_text(encoding="utf-8"))}
    (work / "batches").mkdir(parents=True, exist_ok=True)
    (work / "labels").mkdir(parents=True, exist_ok=True)
    rep = {arm: lrep[arm] | prep_[arm] for arm in ARMS}

    def item(q: str, arm: str) -> dict:
        if q in prow:
            r = prow[q]
            conv = chats[q.split("#")[0]]
            items = D.items_of(conv)
            pos = D.evidence(conv, {"evidence": r["evidence"]})
            return {"question": r["question"], "gold_answer": r["gold"], "reply": rep[arm][q]["reply"],
                    "evidence": "\n".join(f"[{items[p][1]}] " + B.turn_text(items[p][2]) for p in pos)}
        conv, _i, qa, gold = info[q]
        items = D.items_of(conv)
        return {"question": qa["question"], "gold_answer": J._gold(qa), "reply": rep[arm][q]["reply"],
                "evidence": "\n".join(f"[{items[p][1]}] " + B.turn_text(items[p][2]) for p in gold)}

    allq = qids + pids
    key, batches, counter = {}, [], 0
    for g, pairs in latin(allq, random.Random(JUDGE_SEED)).items():
        its = []
        for q, arm in pairs:
            counter += 1
            iid = f"w{counter:05d}"
            key[iid] = {"qid": q, "arm": arm}
            its.append({"item": iid} | item(q, arm))
        size = BATCH if g.startswith("L") else len(its)
        for k in range(0, len(its), size):
            name = f"{g}{k // size + 1:02d}"
            _write(work / "batches" / f"{name}.jsonl", its[k:k + size])
            batches.append(name)
    same = [q for q in allq if rep["BN"][q]["reply"] == rep["BR"][q]["reply"]]
    meta = {q: {"panel": "panel", "category": prow[q]["category"]} for q in pids} | {
        q: {"panel": "locomo", "category": info[q][2]["category"], "conv": info[q][0]["sample_id"],
            "in20": bool(set(info[q][3]) & set(rt[q])), "bm398d": q in set(kept)} for q in qids}
    (work / "key.json").write_text(json.dumps({"qids": allq, "items": key, "same": same, "meta": meta}),
                                   encoding="utf-8")
    print(json.dumps({"questions": len(allq), "locomo": len(qids), "panel": len(pids), "items": len(key),
                      "batches": len(batches), "identical": len(same),
                      "bm398d_sample_inside": sum(q in set(qids) for q in kept)}))
    return 0


def compare(by: dict, qs: list[str], same: set, first: dict) -> tuple[dict, dict]:
    """BN against BR on questions qs. same: byte-identical replies count as one answer (both arms take group L0's
    label, the arm L0 holds, which is ARMS[first[q] % 2]), so the question is a tie."""
    full = [q for q in qs if set(by.get(q, {})) == set(ARMS)]
    agree = sum(by[q]["BN"] == by[q]["BR"] for q in full if q in same)
    lab = {q: ({arm: by[q][ARMS[first[q] % 2]] for arm in ARMS} if q in same else by[q]) for q in full}
    res = {"n": len(qs), "fully_judged": len(full), "identical": sum(q in same for q in full),
           "identical_judges_agree": agree}
    for arm in ARMS:
        c = Counter(lab[q][arm] for q in full)
        res[arm] = {"A": c["A"], "D": c["D"], "E": c["E"], "labels": dict(sorted(c.items()))}
    diff = {q: int(lab[q]["BR"] == "A") - int(lab[q]["BN"] == "A") for q in full}
    g, lo = sum(v > 0 for v in diff.values()), sum(v < 0 for v in diff.values())
    res["BR-BN"] = {"A": res["BR"]["A"] - res["BN"]["A"], "gained": g, "lost": lo,
                    "mcnemar_p": round(N.mcnemar_p(g, lo), 5),
                    "ci95_by_chat_report_only": N._boot(full, diff) if full else None}
    res["table_BN_to_BR"] = dict(sorted(Counter(f"{lab[q]['BN']}->{lab[q]['BR']}" for q in full).items()))
    return res, lab


def verdict(by: dict, meta: dict, qids: list[str], same: set, general: dict | None) -> dict:
    first = {q: n for n, q in enumerate(qids)}
    loc = [q for q in qids if meta[q]["panel"] == "locomo"]
    pan = [q for q in qids if meta[q]["panel"] == "panel"]
    res = {}
    res["locomo"], lab = compare(by, loc, same, first)
    res["panel"], plab = compare(by, pan, same, first)
    L, P = res["locomo"], res["panel"]
    L["A_by_category"] = {str(c): {arm: sum(lab[q][arm] == "A" for q in lab if meta[q]["category"] == c)
                                   for arm in ARMS} | {"n": sum(meta[q]["category"] == c for q in lab)}
                          for c in (1, 2, 3, 4)}
    L["by_evidence_among_20_report_only"] = {k: {"n": sum(meta[q]["in20"] == v for q in lab)} | {
        arm: {x: sum(lab[q][arm] == x for q in lab if meta[q]["in20"] == v) for x in "ADE"} for arm in ARMS}
        for k, v in (("in", True), ("out", False))}
    L["bm398d_sample_report_only"] = {"n": sum(meta[q]["bm398d"] for q in lab)} | {
        arm: sum(lab[q][arm] == "A" for q in lab if meta[q]["bm398d"]) for arm in ARMS} | {"bm398d": BM398D}
    P["A_by_kind_report_only"] = {str(c): {arm: sum(plab[q][arm] == "A" for q in plab if meta[q]["category"] == c)
                                           for arm in ARMS} for c in (1, 2, 4)}
    res["R1"] = (L["BR-BN"]["A"] >= R1_MIN_GAIN and L["BR-BN"]["gained"] > L["BR-BN"]["lost"]
                 and L["BR-BN"]["mcnemar_p"] < MAX_P)
    res["R2"] = (P["BR-BN"]["A"] >= R2_MIN_GAIN and P["BR-BN"]["gained"] > P["BR-BN"]["lost"]
                 and P["BR-BN"]["mcnemar_p"] < MAX_P)
    res["R3"] = L["BR"]["D"] <= L["BN"]["D"] + R3_MAX_EXTRA_D and all(
        v["BN"] - v["BR"] <= max(R3_MAX_CAT_DROP, round(R3_MAX_CAT_DROP * v["n"] / 100))
        for v in L["A_by_category"].values())
    res["R4"] = bool(general and general.get("R4"))
    res["proved_wrong"] = ((P["BR-BN"]["A"] >= R2_MIN_GAIN and L["BR-BN"]["A"] <= 0)
                           or (P["BR-BN"]["A"] <= 0 and L["BR-BN"]["A"] <= 0))
    res["verdict"] = "PASS" if res["R1"] and res["R2"] and res["R3"] and res["R4"] else "FAIL"
    res["R4_is"] = "hand-given stand-in switch (disclosed scaffolding)"
    res["a_PASS_reads"] = "the reader gains, given a switch (not: no harm)"
    return res


def jscore(a) -> int:
    work = Path(a.work)
    k = json.loads((work / "key.json").read_text(encoding="utf-8"))
    main, rel = {}, {}
    for f in sorted((work / "labels").glob("*.jsonl")):
        sink = rel if f.stem.startswith("X") else main
        for r in _jsonl(f):
            lab = str(r["label"]).strip().upper()[:1]
            if not lab or lab not in "ABCDE":
                raise SystemExit(f"bm398w jscore: bad label in {f.name}")
            sink[r["item"]] = lab
    by = defaultdict(dict)
    for iid, lab in main.items():
        m = k["items"][iid]
        by[m["qid"]][m["arm"]] = lab
    general = json.loads(Path(a.score).read_text(encoding="utf-8"))["general"] if a.score else None
    res = verdict(by, k["meta"], k["qids"], set(k["same"]), general)
    res["general"] = general
    mk = {(k["items"][i]["qid"], k["items"][i]["arm"]): lab for i, lab in main.items()}
    pr = [(mk.get((k["items"][i]["qid"], k["items"][i]["arm"])), lab) for i, lab in rel.items()]
    pr = [p for p in pr if p[0] is not None]
    res["relabel_agree"] = f"{sum(x == y for x, y in pr)}/{len(pr)}"
    print(json.dumps(res))
    return 0


# ======================================================================= selftest
def selftest(a) -> int:
    ok = {}
    loc = [f"conv-{c}#{i}" for c in (1, 2, 3) for i in range(60)]
    pan = [f"w3994-{c:04d}#{i}" for c in range(6) for i in range(10)]
    qids = loc + pan
    groups = latin(qids, random.Random(JUDGE_SEED))
    ok["each group holds every question once, arms balanced"] = all(
        sorted(q for q, _ in groups[g]) == sorted(qids) and Counter(x for _, x in groups[g]) == Counter(
            {"BN": 120, "BR": 120}) for g in ("L0", "L1"))
    ok["a question's two arms are in different groups"] = all(dict(groups["L0"])[q] != dict(groups["L1"])[q]
                                                              for q in qids)
    ok["X1 re-asks 60 of L0's items with L0's arms"] = len(groups["X1"]) == X1_N and set(groups["X1"]) <= set(
        groups["L0"])
    meta = {q: {"panel": "locomo", "category": 1 + n % 4, "in20": n % 5 != 0, "bm398d": n % 3 == 0}
            for n, q in enumerate(loc)} | {q: {"panel": "panel", "category": (1, 2, 4)[n % 3]} for n, q in enumerate(pan)}
    gen_ok = {"R4": True}

    def lab(f):
        return {q: f(n, q) for n, q in enumerate(qids)}

    def gain(n, q):
        return {"BN": "D" if n % 6 == 0 or (q in pan and n % 3 == 0) else "A", "BR": "A"}

    v1 = verdict(lab(gain), meta, qids, set(), gen_ok)
    ok["gains on both panels pass"] = (v1["verdict"] == "PASS" and v1["locomo"]["BR-BN"]["A"] == 30
                                       and v1["panel"]["BR-BN"]["A"] == 20 and not v1["proved_wrong"])
    v2 = verdict(lab(lambda n, q: {"BN": "A", "BR": "A"}), meta, qids, set(), gen_ok)
    ok["no gain anywhere fails and is proved wrong"] = v2["verdict"] == "FAIL" and v2["proved_wrong"]
    v3 = verdict(lab(lambda n, q: {"BN": "D", "BR": "A"} if q in pan else {"BN": "A", "BR": "A"}), meta, qids, set(),
                 gen_ok)
    ok["a practice-only gain is proved wrong"] = v3["R2"] and not v3["R1"] and v3["proved_wrong"]
    v4 = verdict(lab(lambda n, q: {"BN": "E" if n % 3 else "A", "BR": "A" if n % 3 else "D"}), meta, qids, set(),
                 gen_ok)
    ok["more wrong answers fail R3"] = v4["R1"] and not v4["R3"] and v4["verdict"] == "FAIL"
    v5 = verdict(lab(lambda n, q: ({"BN": "A", "BR": "D"} if meta[q]["category"] == 3 and q in loc
                                   else {"BN": "D", "BR": "A"})), meta, qids, set(), gen_ok)
    ok["a category drop fails R3"] = v5["R1"] and not v5["R3"]
    v6 = verdict(lab(gain), meta, qids, set(), {"R4": False})
    ok["R4 failing fails the verdict"] = v6["R1"] and v6["R2"] and v6["R3"] and v6["verdict"] == "FAIL"
    alt = lab(lambda n, q: {"BN": "A", "BR": "D"} if n % 2 else {"BN": "D", "BR": "A"})
    v7 = verdict(alt, meta, qids, set(qids), gen_ok)
    want = sum(alt[q][ARMS[n % 2]] == "A" for n, q in enumerate(loc))
    ok["identical replies are ties with L0's label"] = (v7["locomo"]["BR-BN"]["gained"] == 0
                                                       and v7["locomo"]["BR"]["A"] == v7["locomo"]["BN"]["A"] == want)
    rows = [{"id": f"w3994-{c:04d}#{i}"} for c in range(30) for i in range(18)]
    p1, p2 = pick_panel(rows), pick_panel(list(reversed(rows)))
    ok["the no-evidence split reports A, D and E per arm"] = set(
        v1["locomo"]["by_evidence_among_20_report_only"]["out"]["BR"]) == set("ADE") and v1["locomo"][
        "by_evidence_among_20_report_only"]["out"]["n"] == sum(not meta[q]["in20"] for q in loc)
    ok["the panel draw is fixed and PANEL_N long"] = len(p1) == PANEL_N and [r["id"] for r in p1] == [r["id"] for r in p2]
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        sk = Sink(td, ["x_BN", "x_BR"])
        for q in ("q1", "q2"):
            sk.write("x_BN", {"qid": q, "reply": "r\u2028" + q})
            sk.write("x_BR", {"qid": q, "reply": "s" + q})
        sk.write("x_BN", {"qid": "q3", "reply": "r"})
        sk.fh["x_BR"].write('{"qid": "q3", "rep')                # a crash mid-line
        sk.fh["x_BR"].flush()
        sk2 = Sink(td, ["x_BN", "x_BR"])
        ok["a relaunch keeps questions both files hold and drops the rest"] = (
            sk2.done == {"q1", "q2"} and [r["qid"] for r in _jsonl(td / "x_BN.jsonl")] == ["q1", "q2"]
            and _jsonl(td / "x_BN.jsonl")[0]["reply"] == "r\u2028q1")
        for n in sk2.fh.values():
            n.close()
        data = td / "data"
        data.mkdir()
        _write(data / "mmlu300.jsonl", [{"qid": f"m{i}", "gold": "A"} for i in range(3)])
        _write(data / "gsm8k300.jsonl", [{"qid": f"g{i}", "gold": "3"} for i in range(3)])
        runs = td / "runs"
        runs.mkdir()
        for x in ("P", "BN", "BR"):
            _write(runs / f"mmlu_{x}.jsonl", [{"qid": f"m{i}", "reply": "A"} for i in range(3)])
            _write(runs / f"gsm8k_{x}.jsonl", [{"qid": f"g{i}", "reply": "#### 3"} for i in range(3)])
        ok["R4 holds when all items match"] = r4(runs, data, 3)["R4"]
        _write(runs / "gsm8k_BN.jsonl", [{"qid": f"g{i}", "reply": "#### 3"} for i in range(2)])
        _write(runs / "gsm8k_P.jsonl", [{"qid": f"g{i}", "reply": "#### 3"} for i in range(2)])
        ok["R4 fails on a short file"] = not r4(runs, data, 3)["R4"]
    for k2, v in ok.items():
        print(("PASS " if v else "FAIL ") + k2)
    print("BM398W-EVAL-SELFTEST " + ("PASS" if all(ok.values()) else "FAIL") + f" {sum(ok.values())}/{len(ok)}")
    return 0 if all(ok.values()) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["locomo", "panel", "general", "qwen20", "score", "prep", "jscore", "selftest"])
    for x in ("data", "ranked_l", "ranked_u", "panel", "panel_seal", "model", "adapter", "out", "runs", "work",
              "score"):
        ap.add_argument("--" + x.replace("_", "-"), dest=x, default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    return {"locomo": run_locomo, "panel": run_panel, "general": run_general, "qwen20": run_qwen20, "score": score,
            "prep": prep, "jscore": jscore, "selftest": selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
