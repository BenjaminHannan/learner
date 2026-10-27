#!/usr/bin/env python3
"""Rung 1 of design 43 -- decoder (B.4), five brakes (B.5), thresholds and the marks table.

    python fable_ears45_score.py --arm tape --runs <dir> --panels <dir> --out <file.json>

Thresholds come only from the CALIBRATION panel.  No test panel is read before the marks
are computed, and no number from a test panel feeds any choice.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_listening_english as LE                 # noqa: E402  (read-only)
import fable_ears45_data as D                        # noqa: E402
import fable_ears45_model as M                       # noqa: E402
import fable_ears45_train as T                       # noqa: E402

SEEDS = (4301, 4302, 4303)
TAU_ECHO = 0.5
MAX_SPAN_TOKENS = 4
PRON_BEN = {"i", "me", "my", "mine", "myself"}
PRON_SELF = {"you", "your", "yours", "yourself"}
PRON_BAD = {"he", "him", "his", "she", "her", "hers", "they", "them", "their", "theirs", "it"}
NO_ITEM_ACTS = {"unsure", "smalltalk", "multi", "dontknow"}
PENDING_ACTS = {"yes", "no", "pick", "undo"}


# ---------------------------------------------------------------------------------------
# probabilities for one panel, one ear
# ---------------------------------------------------------------------------------------

def run_ear(model, packs, n_hops_run=D.MAX_HOPS):
    """-> {panel index: dict of per-example probability lists}"""
    res = {}
    g = torch.Generator()
    with torch.no_grad():
        for pack in packs:
            n = pack["ids"].shape[0]
            for s in range(0, n, 256):
                idx = torch.arange(s, min(s + 256, n))
                b = T.batch_from(pack, idx, g, train=False)
                o = model(b["ids"], b["feats"], b["pending"], b["mask"],
                          n_hops_run=n_hops_run, use_temp=True)
                p_act = torch.softmax(o["act"], -1)
                p_items = torch.softmax(o["items"], -1)
                p_flags = torch.sigmoid(o["flags"])
                p_slot = torch.softmax(o["slot"], -1)
                p_hs = torch.softmax(o["hop_start"], -1)
                p_he = torch.softmax(o["hop_end"], -1)
                p_stop = torch.sigmoid(o["stop"])
                p_key = torch.softmax(o["relkey"], -1)
                p_typ = torch.softmax(o["reltype"], -1)
                for i, j in enumerate(idx.tolist()):
                    e = pack["rows"][j]
                    res[e["idx"]] = {
                        "act": p_act[i], "items": p_items[i], "flags": p_flags[i],
                        "slot": p_slot[i], "hs": p_hs[i], "he": p_he[i],
                        "stop": p_stop[i], "key": p_key[i], "typ": p_typ[i],
                        "n": e["n"],
                    }
    return res


# ---------------------------------------------------------------------------------------
# B.4 decoder
# ---------------------------------------------------------------------------------------

def _span_text(utt, toks, a, b):
    return utt[toks[a - 1].start:toks[b - 1].end]


def decode(ex, enc, P):
    """-> parse dict: item (or None), conf, ok145, forced_echo, reason, act"""
    utt = ex["utterance"]
    toks = D.tokenise(utt)
    n = enc["n"]
    act = int(P["act"].argmax())
    act_name = D.ACTS15[act]
    p_act = float(P["act"][act])
    n_items = int(P["items"].argmax())
    fl = P["flags"]
    mins = [p_act]
    used = []          # (start_tok, end_tok) of every pointed span
    bad = None

    def take(slot):
        si = D.SLOT_IDX[slot]
        st = int(P["slot"][si, 0, :n].argmax())
        en = int(P["slot"][si, 1, :n].argmax())
        ps = float(P["slot"][si, 0, st]) * float(P["slot"][si, 1, en])
        if st == 0 or en == 0:
            return None, ps
        if st > n - 2 or en > n - 2:        # EOS is not a token -> invalid span
            return "bad", ps
        return (st, en), ps

    def reject(reason):
        return {"item": None, "conf": 0.0, "ok145": False, "forced_echo": True,
                "reason": reason, "act": act_name, "n_items": n_items}

    if act_name in NO_ITEM_ACTS:
        return {"item": None, "conf": p_act, "ok145": False, "forced_echo": True,
                "reason": "not_sure" if act_name != "smalltalk" else "smalltalk",
                "act": act_name, "n_items": n_items}
    if n_items > 1:
        return reject("one_thing_at_a_time")
    if act_name in PENDING_ACTS:                 # rung 1 never has a pending state
        return reject("not_sure")
    if act_name == "quote":
        item = LE.blank_item("quote", 1.0, text=utt, value_kind="none")
        doc = {"items": [item], "unsure": False, "unsure_reason": ""}
        try:
            LE.validate_model_output(doc, utt, None)
            ok = True
        except Exception:
            ok = False
        return {"item": item, "conf": p_act, "ok145": ok, "forced_echo": True,
                "reason": "quote", "act": act_name, "n_items": n_items}

    # ---- hops --------------------------------------------------------------------
    need_hops = {"teach": (1, 1), "correct": (1, 1), "forget": (1, 1), "ask": (1, 8)}
    hops = []
    if act_name in need_hops:
        for j in range(D.MAX_HOPS):
            pstop = float(P["stop"][j])
            if pstop > 0.5:
                mins.append(pstop)
                break
            st = int(P["hs"][j, :n].argmax())
            en = int(P["he"][j, :n].argmax())
            pp = float(P["hs"][j, st]) * float(P["he"][j, en]) * (1.0 - pstop)
            if st == 0 or en == 0 or st > n - 2 or en > n - 2 or en < st \
                    or en - st + 1 > MAX_SPAN_TOKENS:
                return reject("not_sure")
            ki = int(P["key"][j].argmax())
            hops.append({"span": (st, en), "p": pp, "key": ki,
                         "pkey": float(P["key"][j, ki]),
                         "type": int(P["typ"][j].argmax())})
            mins.append(pp)
            mins.append(float(P["key"][j, ki]))
        else:
            return reject("not_sure")
        lo, hi = need_hops[act_name]
        if not (lo <= len(hops) <= hi):
            return reject("not_sure")
    else:
        mins.append(float(P["stop"][0]))

    # ---- slots -------------------------------------------------------------------
    slots = {}
    want = {"teach": ["SUBJ", "VAL"], "correct": ["SUBJ", "VAL"], "ask": ["SUBJ"],
            "forget": ["SUBJ"], "person": ["SUBJ"], "alias": ["ALIAS", "CANON"]}
    for s in want.get(act_name, []):
        sp, pp = take(s)
        if sp is None or sp == "bad":
            return reject("not_sure")
        if sp[1] < sp[0] or sp[1] - sp[0] + 1 > MAX_SPAN_TOKENS:
            return reject("not_sure")
        slots[s] = sp
        mins.append(pp)
    used = list(slots.values()) + [h["span"] for h in hops]
    for i in range(len(used)):
        for j in range(i + 1, len(used)):
            a, b = used[i], used[j]
            if not (a[1] < b[0] or b[1] < a[0]):
                return reject("not_sure")

    # ---- strings (byte-exact copies) ---------------------------------------------
    def text(sp):
        return _span_text(utt, toks, sp[0], sp[1])

    subject = None
    if "SUBJ" in slots:
        raw = text(slots["SUBJ"])
        low = raw.casefold()
        if low in PRON_BAD:
            return reject("who_is_pronoun")
        subject = "Ben" if low in PRON_BEN else ("self" if low in PRON_SELF else raw)

    forced_echo = False
    path, surface, types = [], [], []
    for h in hops:
        surf = text(h["span"])
        tab = D.WORDING_TABLE.get(surf.casefold().strip(" .,:;!?"))
        head = None if h["key"] == D.OPEN_INDEX else D.ALL_KEYS[h["key"]]
        if tab is not None:
            if head == tab:
                key = tab
            else:
                key, forced_echo = tab, True
        else:
            if head is not None:
                key, forced_echo = head, True
            else:
                key, forced_echo = LE._snake(surf), True
        path.append(key)
        surface.append(surf)
        types.append("verb" if h["type"] == 1 else "noun")

    if act_name in ("teach", "correct"):
        vk = "person" if path[0] in D.PERSON_KEYS else "literal"
        item = LE.blank_item(act_name, 1.0, subject=subject, relation_path=path,
                             relation_surface=surface, value=text(slots["VAL"]),
                             value_kind=vk)
    elif act_name == "ask":
        item = LE.blank_item("ask", 1.0, subject=subject, relation_path=path,
                             relation_surface=surface, value_kind="none")
    elif act_name == "forget":
        item = LE.blank_item("forget", 1.0, subject=subject, relation_path=path,
                             relation_surface=surface, value_kind="none")
    elif act_name == "person":
        item = LE.blank_item("person", 1.0, subject=subject, value_kind="none")
    elif act_name == "alias":
        item = LE.blank_item("alias", 1.0, alias=text(slots["ALIAS"]),
                             canonical=text(slots["CANON"]), value_kind="none")
        forced_echo = True                      # existing policy: aliases always ECHO
    else:
        return reject("not_sure")

    # ---- touching names ----------------------------------------------------------
    for i in range(len(used)):
        for j in range(len(used)):
            if i == j:
                continue
            a, b = used[i], used[j]
            if a[1] + 1 != b[0]:
                continue
            if enc["opaque"][a[1]] and enc["opaque"][b[0]]:
                if not (enc["feats"][a[1]][7] or enc["feats"][b[0]][7]):
                    forced_echo = True

    # ---- brake 4: leftover opaque tokens -----------------------------------------
    covered = set()
    for a, b in used:
        covered.update(range(a, b + 1))
    leftover = [i for i in range(1, n - 1) if enc["opaque"][i] and i not in covered]
    ok4 = not leftover

    # ---- brake 5: the existing validator -----------------------------------------
    doc = {"items": [item], "unsure": False, "unsure_reason": ""}
    try:
        LE.validate_model_output(doc, utt, None)
        ok5 = True
    except Exception:
        ok5 = False

    if act_name in LE.WRITE_ACTS:
        mins.append(1.0 - max(float(fl[1]), float(fl[2]), float(fl[3])))
    conf = min(mins) if mins else 0.0
    return {"item": item, "conf": conf, "ok145": ok4 and ok5, "forced_echo": forced_echo,
            "reason": "leftover_words" if not ok4 else ("" if ok5 else "not_sure"),
            "act": act_name, "n_items": n_items}


def same_item(a, b):
    if a is None or b is None:
        return a is None and b is None
    ks = [k for k in a if k != "confidence"]
    return all(a[k] == b.get(k) for k in ks)


def verdict_single(p, tau_exec):
    if p["item"] is None:
        return "REPHRASE", None
    if p["ok145"] and not p["forced_echo"] and p["conf"] >= tau_exec:
        return "EXECUTE", p["item"]
    if p["ok145"] and p["conf"] >= TAU_ECHO:
        return "ECHO", p["item"]
    return "REPHRASE", None


def verdict_ensemble(ps, tau_exec):
    items = [p["item"] for p in ps]
    all_ok = all(p["ok145"] for p in ps)
    agree3 = all(same_item(items[0], it) for it in items[1:]) and items[0] is not None
    conf = min(p["conf"] for p in ps)
    if all_ok and agree3 and not any(p["forced_echo"] for p in ps) and conf >= tau_exec:
        return "EXECUTE", items[0]
    # majority of 2
    for i in range(3):
        for j in range(i + 1, 3):
            if items[i] is not None and same_item(items[i], items[j]):
                maj = [ps[i], ps[j]]
                if all(p["ok145"] for p in maj) and min(p["conf"] for p in maj) >= TAU_ECHO:
                    return "ECHO", items[i]
    return "REPHRASE", None


# ---------------------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------------------

def gold_of(ex):
    return ex["item"]


def is_correct(ex, verdict, item):
    g = gold_of(ex)
    if g is None:
        return item is None or (item.get("act") in NO_ITEM_ACTS)
    if verdict == "REPHRASE" or item is None:
        return False
    return same_item(item, g)


def score_panel(rows, encs, parses_by_ear, tau_exec, ensemble=True, tau_single=None):
    out = {"n": len(rows), "correct": 0, "exec_correct": 0, "echo_correct": 0,
           "silent_wrong_write": 0, "echoed_wrong_write": 0, "written": 0,
           "wrong_exec_ask": 0, "verdicts": Counter(), "fam_miss": Counter(),
           "silent_examples": [], "echo_examples": []}
    for k, ex in enumerate(rows):
        ps = [pe[k] for pe in parses_by_ear]
        if ensemble:
            v, item = verdict_ensemble(ps, tau_exec)
        else:
            v, item = verdict_single(ps[0], tau_single if tau_single is not None else tau_exec)
        out["verdicts"][v] += 1
        ok = is_correct(ex, v, item)
        out["correct"] += int(ok)
        if ok and v == "EXECUTE":
            out["exec_correct"] += 1
        if ok and v == "ECHO":
            out["echo_correct"] += 1
        if not ok:
            out["fam_miss"][ex["family"]] += 1
        wrote = (v == "EXECUTE" and item is not None and item["act"] in LE.WRITE_ACTS)
        if wrote:
            out["written"] += 1
        if wrote and not same_item(item, gold_of(ex)):
            out["silent_wrong_write"] += 1
            if len(out["silent_examples"]) < 200:
                out["silent_examples"].append(
                    {"n": ex["n"], "family": ex["family"], "utterance": ex["utterance"],
                     "gold": gold_of(ex), "got": item})
        if (v == "ECHO" and item is not None and item["act"] in LE.WRITE_ACTS
                and not same_item(item, gold_of(ex))):
            out["echoed_wrong_write"] += 1
            if len(out["echo_examples"]) < 30:
                out["echo_examples"].append(
                    {"n": ex["n"], "family": ex["family"], "utterance": ex["utterance"],
                     "gold": gold_of(ex), "got": item})
        if v == "EXECUTE" and item is not None and item["act"] == "ask" \
                and not same_item(item, gold_of(ex)):
            out["wrong_exec_ask"] += 1
    out["verdicts"] = dict(out["verdicts"])
    out["fam_miss"] = dict(sorted(out["fam_miss"].items(), key=lambda kv: -kv[1]))
    return out


def tau0_from_cal(rows, parses_by_ear, ensemble=True):
    """smallest tau with 0 wrong EXECUTED writes on CAL (B.5)"""
    worst = 0.0
    for k, ex in enumerate(rows):
        ps = [pe[k] for pe in parses_by_ear]
        if ensemble:
            v, item = verdict_ensemble(ps, 0.0)
            conf = min(p["conf"] for p in ps)
        else:
            v, item = verdict_single(ps[0], 0.0)
            conf = ps[0]["conf"]
        if v == "EXECUTE" and item is not None and item["act"] in LE.WRITE_ACTS \
                and not same_item(item, gold_of(ex)):
            worst = max(worst, conf)
    return math.nextafter(worst, 2.0) if worst > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--panels", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    torch.set_num_threads(1)
    panels_dir = Path(a.panels)
    split, pools, lex, gen = D.load_all()

    models = []
    for s in SEEDS:
        ck = torch.load(Path(a.runs) / f"{a.arm}-{s}" / "ear.pt", weights_only=False)
        m = M.Ears(ck["vocab"], a.arm)
        m.load_state_dict(ck["state"])
        m.eval()
        models.append(m)

    report = {"arm": a.arm, "seeds": list(SEEDS),
              "params": M.n_params(models[0]), "panels": {}}
    gates = torch.sigmoid(10 * torch.tanh(models[0].trunk.G)).tolist() \
        if a.arm != "bigru" else None
    report["router_gates"] = gates

    panel_names = ["cal", "t_seen", "t_new", "t_far", "t_trap", "t_hard"]
    store = {}
    for name in panel_names:
        rows = json.loads((panels_dir / f"{name}.json").read_text())
        rng = random.Random(9000 + D.PANEL_SEEDS[name])
        encs = []
        keep = []
        for i, ex in enumerate(rows):
            e = D.encode(ex, lex, rng, False, hash_names=(a.arm == "names"))
            if e is None:
                continue
            e["idx"] = len(encs)
            encs.append(e)
            keep.append(ex)
        packs = T.to_tensors(encs)
        parses = []
        for m in models:
            probs = run_ear(m, packs)
            parses.append([decode(keep[i], encs[i], probs[i]) for i in range(len(encs))])
        store[name] = (keep, encs, parses)

    cal_rows, _, cal_parses = store["cal"]
    tau0 = tau0_from_cal(cal_rows, cal_parses, ensemble=True)
    tau_exec = 1.0 - (1.0 - tau0) / 2.0
    report["tau0"] = tau0
    report["tau_exec"] = tau_exec
    report["tau_echo"] = TAU_ECHO
    singles = []
    for s in range(3):
        t0 = tau0_from_cal(cal_rows, [cal_parses[s]], ensemble=False)
        singles.append(1.0 - (1.0 - t0) / 2.0)
    report["tau_exec_single"] = singles

    for name in panel_names[1:]:
        rows, encs, parses = store[name]
        report["panels"][name] = {
            "ensemble": score_panel(rows, encs, parses, tau_exec, True),
            "single": [score_panel(rows, encs, [parses[s]], tau_exec, False, singles[s])
                       for s in range(3)],
        }

    def agg(which, key, sel=None):
        tot = 0
        for nm in ("t_seen", "t_new", "t_trap", "t_hard"):
            tot += report["panels"][nm][which][key] if sel is None \
                else report["panels"][nm][which][sel][key]
        return tot

    marks = {}
    e = {nm: report["panels"][nm]["ensemble"] for nm in panel_names[1:]}
    marks["R1-SAFE"] = {"silent_wrong_writes_6500": agg("ensemble", "silent_wrong_write"),
                        "t_trap_items_written": e["t_trap"]["written"],
                        "pass": agg("ensemble", "silent_wrong_write") == 0
                        and e["t_trap"]["written"] == 0}
    marks["R1-ECHO"] = {"echoed_wrong_writes": agg("ensemble", "echoed_wrong_write"),
                        "limit": 65,
                        "pass": agg("ensemble", "echoed_wrong_write") <= 65}
    marks["R1-SEEN"] = {"correct": e["t_seen"]["correct"], "need": 1940,
                        "exec_correct": e["t_seen"]["exec_correct"], "need_exec": 1800,
                        "pass": e["t_seen"]["correct"] >= 1940
                        and e["t_seen"]["exec_correct"] >= 1800}
    marks["R1-NEW"] = {"correct": e["t_new"]["correct"], "need": 2400,
                       "exec_correct": e["t_new"]["exec_correct"], "need_exec": 1950,
                       "pass": e["t_new"]["correct"] >= 2400
                       and e["t_new"]["exec_correct"] >= 1950}
    marks["R1-NAMES"] = {"correct": e["t_hard"]["correct"], "need": 300,
                         "pass": e["t_hard"]["correct"] >= 300}
    wrong_ask = e["t_seen"]["wrong_exec_ask"] + e["t_new"]["wrong_exec_ask"]
    marks["R1-ASK"] = {"wrong_executed_questions": wrong_ask, "limit": 25,
                       "pass": wrong_ask <= 25}
    report["marks"] = marks
    report["recorded"] = {"t_far": e["t_far"],
                          "four_hop_questions": 0,
                          "single_ear_totals": [
                              {"silent_wrong_writes_6500":
                               sum(report["panels"][nm]["single"][s]["silent_wrong_write"]
                                   for nm in ("t_seen", "t_new", "t_trap", "t_hard")),
                               "t_seen_correct": report["panels"]["t_seen"]["single"][s]["correct"],
                               "t_new_correct": report["panels"]["t_new"]["single"][s]["correct"],
                               "t_hard_correct": report["panels"]["t_hard"]["single"][s]["correct"],
                               "t_trap_written": report["panels"]["t_trap"]["single"][s]["written"],
                               "echoed_wrong_writes":
                               sum(report["panels"][nm]["single"][s]["echoed_wrong_write"]
                                   for nm in ("t_seen", "t_new", "t_trap", "t_hard"))}
                              for s in range(3)]}
    Path(a.out).write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps(marks, indent=1))


if __name__ == "__main__":
    main()
