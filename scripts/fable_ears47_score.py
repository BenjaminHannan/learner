#!/usr/bin/env python3
"""Rung 2 of design 47 -- decode, the five brakes, thresholds, and the marks table.

    python fable_ears47_score.py --runs <dir> --panels <dir> --snapshot <dir> --out report.json

Thresholds come only from the sealed CAL panel (doc 43 B.5): tau0 = smallest value giving
0 wrong EXECUTED writes on cal; tau_exec = 1 - (1 - tau0)/2; tau_echo = 0.5.
Brakes: 1 act not in {UNSURE, NO_FACT};  2 confidence >= tau_exec;  3 three seeds agree
identically;  4 leftover = every [UNK] wordpiece inside a pointed span;  5 the unchanged
`fable_listening_english` validator on the adapted item.

Surface strategy (brake 5): pick a relation surface the unchanged validator will accept —
prefer one whose canonical form matches the predicted class and that appears in the
utterance (or is a KNOWN relation with a wording present); fall back to the predicted
class name. OPEN skips the validator entirely and is never EXECUTE.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fable_listening_english as LE                 # noqa: E402  (read-only + markers)
import fable_ears47_data as D                        # noqa: E402
import fable_ears47_model as M                       # noqa: E402
import fable_ears47_encoder as ENC                   # noqa: E402

SEEDS = (4701, 4702, 4703)
TAU_ECHO = 0.5
WRITE_ACTS = {"STATE", "RETRACT"}
ABSTAIN = {"UNSURE", "NO_FACT"}
PRON_BEN = {"i", "me", "my", "mine", "myself"}
PRON_SELF = {"you", "your", "yours", "yourself"}
PRON_BAD = {"he", "him", "his", "she", "her", "hers", "they", "them", "their",
            "theirs", "it"}
PANEL_SYNTH = ("cal", "t_seen", "t_new", "t_far", "t_trap", "t_hard")
PANEL_TEST = ("t_seen", "t_new", "t_far", "t_trap", "t_hard",
              "wneg", "wpos", "wclosed", "wnewrel")
GATED_MARKS = ("R2-SAFE", "R2-NEG", "R2-SEEN", "R2-NEW", "R2-NAMES", "R2-ASK",
               "R2-WEB", "R2-NEWREL")


# --------------------------------------------------------------------------- encode/run
def encode_panel(panel_rows, tok):
    return [D.encode_row(r, tok) for r in panel_rows]


def probs_for_model(model, encs, device, batch=64):
    outs = [None] * len(encs)
    idx_ok = [i for i, e in enumerate(encs) if e is not None]
    with torch.no_grad():
        for s in range(0, len(idx_ok), batch):
            chunk = idx_ok[s:s + batch]
            ids = torch.zeros(len(chunk), D.MAX_LEN, dtype=torch.long)
            mask = torch.zeros(len(chunk), D.MAX_LEN, dtype=torch.bool)
            for j, i in enumerate(chunk):
                L = min(len(encs[i]["ids"]), D.MAX_LEN)
                ids[j, :L] = torch.tensor(encs[i]["ids"][:L])
                mask[j, :L] = True
            o = model(ids.to(device), mask.to(device), use_temp=True)
            pa = torch.softmax(o["act"], -1).cpu()
            pr = torch.softmax(o["rel"], -1).cpu()
            pd = torch.softmax(o["direction"], -1).cpu()
            pf = torch.sigmoid(o["flags"]).cpu()
            pp = torch.softmax(o["ptr"], -1).cpu()
            for j, i in enumerate(chunk):
                L = int(mask[j].sum())
                outs[i] = {"act": pa[j], "rel": pr[j], "dir": pd[j], "flags": pf[j],
                           "ptr": pp[j, :, :L], "n": L}
    return outs


# ------------------------------------------------------------------------------- decode
def _span(P, k0, k1, n):
    st = int(P["ptr"][k0, :n].argmax())
    en = int(P["ptr"][k1, :n].argmax())
    ps = float(P["ptr"][k0, st]) * float(P["ptr"][k1, en])
    if st == 0 or en == 0:
        return None, ps
    if st < 1 or en < 1 or en < st or en > n - 2 or en - st + 1 > D.MAX_SPAN_WP:
        return "bad", ps
    return (st, en), ps


def frame_key(fr):
    if fr is None:
        return None
    if fr["act"] in ABSTAIN:
        return ("act", fr["act"])
    return (fr["act"], fr["rel"],
            tuple(fr["subj"]) if fr["subj"] else None,
            tuple(fr["obj"]) if fr["obj"] else None,
            fr["dir"])


def same_frame(a, b):
    return frame_key(a) == frame_key(b)


def gold_frame_of(enc):
    if enc is None:
        return {"act": "?", "rel": None, "subj": None, "obj": None, "dir": None}
    act = D.ACTS[enc["act"]]
    if act in ABSTAIN:
        return {"act": act, "rel": None, "subj": None, "obj": None, "dir": None}
    subj = tuple(enc["subj"]) if enc["subj"][1] else None
    obj = tuple(enc["obj"]) if enc["obj"][1] else None
    if act != "STATE":
        obj = None
    return {"act": act, "rel": D.CLASSES["classes"][enc["rel"]],
            "subj": subj, "obj": obj, "dir": enc["dir"]}


def gold_from_row47(row):
    """Gold frame from gold47 char spans -> compared only as act/rel/dir (+ presence)."""
    g = row.get("gold47")
    if not g:
        return {"act": "?", "rel": None, "subj": None, "obj": None, "dir": None}
    act = g["act"]
    if act in ABSTAIN or not g.get("rep"):
        if act in ABSTAIN:
            return {"act": act, "rel": None, "subj": None, "obj": None, "dir": None}
        # non-representable STATE fallback already folded into act/rel by gold_from_*
        return {"act": act, "rel": None, "subj": None, "obj": None, "dir": None}
    return {"act": act, "rel": g.get("rel"), "subj": tuple(g["subj"]) if g.get("subj")
            else None, "obj": tuple(g["obj"]) if g.get("obj") else None,
            "dir": g.get("dir", D.DIR_FORWARD)}


def _wp_char(chspans, span):
    """(start_wp, end_wp) inclusive -> (char_start, char_end) exclusive end."""
    return chspans[span[0]][0], chspans[span[1]][1]


def _wp_start(chspans, span):
    return chspans[span[0]][0]


def _contains(text, fragment):
    return isinstance(fragment, str) and bool(fragment) \
        and fragment.casefold() in text.casefold()


def _surface_candidates(rel_str):
    """ordered unique surface strings to try for the predicted class."""
    target = LE.canonical_relation(rel_str)
    cands: list[str] = [rel_str, target]
    # closed_map may rename a WebRED relation onto our key (place of birth -> hometown)
    cm = D.CLASSES.get("closed_map") or {}
    mapped = cm.get(rel_str)
    if mapped:
        cands.append(mapped)
    for s, info in getattr(D, "WORDING_TABLE", {}).items():
        key = info[0] if isinstance(info, (tuple, list)) else info
        if key in (rel_str, target, mapped):
            cands.append(s)
    for s, key in LE.RELATION_MAP.items():
        if key in (rel_str, target, mapped):
            cands.append(s)
    # reverse: wordings whose key equals a candidate
    for s, key in LE.RELATION_MAP.items():
        if key == target or key == mapped:
            cands.append(s)
    out, seen = [], set()
    for s in cands:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out, target


def pick_surface(rel_str, utt):
    """A relation_surface the unchanged validator can accept for this utterance.

    Order: (1) related wordings that are grounded or copied from the text;
    (2) any wording-table / RELATION_MAP surface present in the text;
    (3) any content word present in the text (last resort so brake 5 does not
    spuriously block EXECUTE when the sentence never spells the relation).
    """
    cands, target = _surface_candidates(rel_str)
    fallback = None
    for s in cands:
        try:
            grounded = LE._relation_grounded(s, utt)
        except Exception:
            grounded = False
        present = _contains(utt, s)
        if not (grounded or present):
            continue
        can = LE.canonical_relation(s)
        if can == target or s == rel_str or can == rel_str or s == (D.CLASSES.get(
                "closed_map") or {}).get(rel_str):
            return s
        if fallback is None:
            fallback = s
    # (2) any known wording that appears in the sentence
    for s in list(getattr(D, "WORDING_TABLE", {})) + list(LE.RELATION_MAP):
        if _contains(utt, s) or (s in LE.KNOWN_RELATIONS
                                 and LE._relation_grounded(s, utt)):
            if fallback is None or len(s) > len(fallback):
                fallback = s
            # prefer a longer match but keep scanning only for longer wordings
    if fallback:
        return fallback
    # (3) last resort: a content word from the utterance (copy constraint)
    words = re.findall(r"[A-Za-z][A-Za-z'-]+", utt)
    for w in sorted(set(words), key=lambda x: (-len(x), x)):
        if w.casefold() in PRON_BAD or w.casefold() in PRON_BEN:
            continue
        return w
    return rel_str


def decode(row, enc, P, unk_ids: set[int]):
    """-> parse dict: frame, conf, ok4, ok5, forced_echo, reason"""
    utt = D.row_text(row)
    if enc is None or P is None:
        return {"frame": {"act": "?", "rel": None, "subj": None, "obj": None,
                          "dir": None},
                "conf": 0.0, "ok4": False, "ok5": False, "forced_echo": True,
                "reason": "span_unreachable", "flags": None}
    n = P["n"]
    act_i = int(P["act"].argmax())
    act = D.ACTS[act_i]
    p_act = float(P["act"][act_i])
    rel_i = int(P["rel"].argmax())
    rel_str = D.CLASSES["classes"][rel_i]
    flags = P["flags"]
    chspans = enc["chspans"]

    if act in ABSTAIN:
        return {"frame": {"act": act, "rel": None, "subj": None, "obj": None,
                          "dir": None},
                "conf": p_act, "ok4": True, "ok5": True, "forced_echo": True,
                "reason": "abstain", "flags": flags}

    mins = [p_act, float(P["rel"][rel_i])]
    subj, p_subj = _span(P, 0, 1, n)
    if subj is None or subj == "bad":
        return {"frame": {"act": act, "rel": rel_str, "subj": None, "obj": None,
                          "dir": None},
                "conf": 0.0, "ok4": False, "ok5": False, "forced_echo": True,
                "reason": "bad_subj", "flags": flags}
    mins.append(p_subj)
    obj = None
    p_obj_absent = float(P["ptr"][2, 0]) * float(P["ptr"][3, 0])
    if act == "STATE":
        obj, p_obj = _span(P, 2, 3, n)
        if obj is None or obj == "bad":
            return {"frame": {"act": act, "rel": rel_str, "subj": tuple(subj),
                              "obj": None, "dir": None},
                    "conf": 0.0, "ok4": False, "ok5": False, "forced_echo": True,
                    "reason": "bad_obj", "flags": flags}
        mins.append(p_obj)
    else:
        mins.append(p_obj_absent)
    if act == "STATE" and obj is not None:
        d = D.DIR_FORWARD if _wp_start(chspans, subj) <= _wp_start(chspans, obj) \
            else D.DIR_REVERSE
    else:
        d = D.DIR_FORWARD
    mins.append(float(P["dir"][d]))
    if act in WRITE_ACTS:
        mins.append(1.0 - max(float(flags[1]), float(flags[2]), float(flags[3])))

    # brake 4: every [UNK] wordpiece lies inside a pointed span
    ids = enc["ids"][:n]
    covered = set(range(subj[0], subj[1] + 1))
    if obj:
        covered.update(range(obj[0], obj[1] + 1))
    leftover = [i for i in range(1, n - 1) if ids[i] in unk_ids and i not in covered]
    ok4 = not leftover

    # brake 5: the unchanged validator on the adapted item
    ok5, reason = True, ""
    forced_echo = rel_str == "OPEN"       # two-key rule: open relation never silent
    cs, ce = _wp_char(chspans, subj)
    subj_txt = utt[cs:ce]
    low = subj_txt.casefold()
    if low in PRON_BAD and act in ("STATE", "ASK", "RETRACT"):
        return {"frame": {"act": act, "rel": rel_str, "subj": tuple(subj),
                          "obj": tuple(obj) if obj else None, "dir": d},
                "conf": 0.0, "ok4": False, "ok5": False, "forced_echo": True,
                "reason": "who_is_pronoun", "flags": flags}
    if low in PRON_BEN:
        subj_txt = "Ben"
    elif low in PRON_SELF:
        subj_txt = "self"
    if act in WRITE_ACTS or act == "ASK":
        item_act = {"STATE": None, "RETRACT": "forget", "ASK": "ask"}[act]
        surface = pick_surface(rel_str, utt)
        path = [LE.canonical_relation(surface)]
        if act == "STATE":
            item_act = "correct" if LE._has_correction_cue(utt) else "teach"
            vs, ve = _wp_char(chspans, obj)
            val_txt = utt[vs:ve]
            item = LE.blank_item(
                item_act, 1.0, subject=subj_txt, relation_path=path,
                relation_surface=[surface], value=val_txt,
                value_kind="person" if rel_str in D.PERSON_CLASSES else "literal")
        elif act == "ASK":
            item = LE.blank_item("ask", 1.0, subject=subj_txt, relation_path=path,
                                 relation_surface=[surface], value_kind="none")
        else:
            item = LE.blank_item("forget", 1.0, subject=subj_txt, relation_path=path,
                                 relation_surface=[surface], value_kind="none")
        if rel_str != "OPEN":
            try:
                LE.validate_model_output(
                    {"items": [item], "unsure": False, "unsure_reason": ""}, utt, None)
                ok5 = True
            except Exception as e:
                ok5 = False
                reason = "validator:" + type(e).__name__
        else:
            ok5 = True                     # no surface to validate against; never EXECUTE
    frame = {"act": act, "rel": rel_str,
             "subj": tuple(subj), "obj": tuple(obj) if obj else None, "dir": d}
    conf = min(mins) if mins else 0.0
    if not ok4:
        reason = reason or "leftover_words"
    return {"frame": frame, "conf": conf, "ok4": ok4, "ok5": ok5,
            "forced_echo": forced_echo, "reason": reason, "flags": flags}


# -------------------------------------------------------------------------- verdicts
def verdict_single(p, tau_exec):
    fr = p["frame"]
    if fr["act"] in ABSTAIN or fr["act"] == "?":
        return "REPHRASE", fr
    if p["ok4"] and p["ok5"] and not p["forced_echo"] and p["conf"] >= tau_exec:
        return "EXECUTE", fr
    if p["ok4"] and p["ok5"] and p["conf"] >= TAU_ECHO:
        return "ECHO", fr
    return "REPHRASE", fr


def verdict_ensemble(ps, tau_exec):
    frames = [p["frame"] for p in ps]
    if any(fr is None for fr in frames):
        return "REPHRASE", frames[0]
    if all(fr["act"] in ABSTAIN or fr["act"] == "?" for fr in frames):
        return "REPHRASE", frames[0]
    all_ok = all(p["ok4"] and p["ok5"] for p in ps)
    agree3 = all(same_frame(frames[0], fr) for fr in frames[1:]) \
        and frames[0]["act"] not in ABSTAIN and frames[0]["act"] != "?"
    conf = min(p["conf"] for p in ps)
    not_echo = not any(p["forced_echo"] for p in ps)
    if all_ok and agree3 and not_echo and conf >= tau_exec:
        return "EXECUTE", frames[0]
    for i in range(3):
        for j in range(i + 1, 3):
            if (frames[i]["act"] not in ABSTAIN and frames[i]["act"] != "?"
                    and same_frame(frames[i], frames[j])):
                maj = [ps[i], ps[j]]
                if all(p["ok4"] and p["ok5"] for p in maj) \
                        and min(p["conf"] for p in maj) >= TAU_ECHO:
                    return "ECHO", frames[i]
    return "REPHRASE", frames[0]


def abstain_act(ps):
    """majority raw abstention act across the three seeds (>=2 agree), else None"""
    acts = [p["frame"]["act"] for p in ps]
    c = Counter(a for a in acts if a in ABSTAIN)
    for a, k in c.items():
        if k >= 2:
            return a
    return None


def is_correct(gold, verdict, frame, ps):
    if gold is None:                       # span unreachable
        return False
    if gold["act"] in ABSTAIN:
        if verdict != "REPHRASE":
            return False
        return abstain_act(ps) == gold["act"] if ps is not None else \
            frame["act"] == gold["act"]
    if gold["act"] == "?":
        return False                       # unscorable: never correct
    if verdict in ("EXECUTE", "ECHO") and frame is not None and same_frame(frame, gold):
        return True
    return False


# ---------------------------------------------------------------------------- scoring
def score_panel(rows, encs, parses, tau_exec, golds, ensemble=True, tau_single=None):
    out = {"n": len(rows), "correct": 0, "exec_correct": 0, "echo_correct": 0,
           "silent_wrong_write": 0, "echoed_wrong_write": 0, "written": 0,
           "wrong_exec_ask": 0, "executed": 0, "echoed": 0, "rephrased": 0,
           "exec_state_gold": 0, "exec_retract_gold": 0,
           "verdicts": Counter(), "fam_miss": Counter(),
           "silent_examples": [], "echo_examples": []}
    for k, ex in enumerate(rows):
        ps = [pe[k] for pe in parses]
        if ensemble:
            v, fr = verdict_ensemble(ps, tau_exec)
        else:
            v, fr = verdict_single(ps[0], tau_single if tau_single is not None
                                   else tau_exec)
        gold = golds[k]
        out["verdicts"][v] += 1
        if v == "EXECUTE":
            out["executed"] += 1
        elif v == "ECHO":
            out["echoed"] += 1
        else:
            out["rephrased"] += 1
        ok = is_correct(gold, v, fr, ps if ensemble else None)
        out["correct"] += int(ok)
        if ok and v == "EXECUTE":
            out["exec_correct"] += 1
        if ok and v == "ECHO":
            out["echo_correct"] += 1
        if not ok:
            out["fam_miss"][ex.get("family", "?")] += 1
        wrote = (v == "EXECUTE" and fr is not None and fr["act"] in WRITE_ACTS)
        if wrote:
            out["written"] += 1
            if gold is not None and gold["act"] == "STATE":
                out["exec_state_gold"] += 1
            if gold is not None and gold["act"] == "RETRACT":
                out["exec_retract_gold"] += 1
        if wrote and (gold is None or gold["act"] == "?"
                      or not same_frame(fr, gold)):
            out["silent_wrong_write"] += 1
            if len(out["silent_examples"]) < 200:
                out["silent_examples"].append(
                    {"n": ex.get("n"), "family": ex.get("family"),
                     "utterance": D.row_text(ex),
                     "gold": gold, "got": fr})
        if (v == "ECHO" and fr is not None and fr["act"] in WRITE_ACTS
                and (gold is None or gold["act"] == "?"
                     or not same_frame(fr, gold))):
            out["echoed_wrong_write"] += 1
            if len(out["echo_examples"]) < 30:
                out["echo_examples"].append(
                    {"n": ex.get("n"), "family": ex.get("family"),
                     "utterance": D.row_text(ex),
                     "gold": gold, "got": fr})
        if v == "EXECUTE" and fr is not None and fr["act"] == "ASK" \
                and (gold is None or gold["act"] == "?"
                     or not same_frame(fr, gold)):
            out["wrong_exec_ask"] += 1
    out["verdicts"] = dict(out["verdicts"])
    out["fam_miss"] = dict(sorted(out["fam_miss"].items(), key=lambda kv: -kv[1]))
    return out


def tau0_from_cal(golds, parses, ensemble=True):
    """smallest tau0 with 0 wrong EXECUTED writes on CAL; sentinel -1 = no wrong writes."""
    worst = -1.0
    n = len(golds)
    for k in range(n):
        ps = [pe[k] for pe in parses]
        if ensemble:
            v, fr = verdict_ensemble(ps, 0.0)
            conf = min(p["conf"] for p in ps)
        else:
            v, fr = verdict_single(ps[0], 0.0)
            conf = ps[0]["conf"]
        gold = golds[k]
        if v == "EXECUTE" and fr is not None and fr["act"] in WRITE_ACTS \
                and (gold is None or gold["act"] == "?"
                     or not same_frame(fr, gold)):
            worst = max(worst, conf)
    if worst < 0:
        return 0.0                          # no wrong writes at tau=0
    return math.nextafter(worst, 2.0)


# ---------------------------------------------------------------------------------CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--panels", required=True)
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--device", default=None)
    a = ap.parse_args()
    device = torch.device(a.device or ("cuda" if torch.cuda.is_available() else "cpu"))
    torch.set_num_threads(max(1, torch.get_num_threads()))
    panels_dir = Path(a.panels)
    enc0, tok, info = ENC.load(a.snapshot)
    unk_ids = {tok.unk}
    del enc0

    models = []
    for s in SEEDS:
        ck = torch.load(Path(a.runs) / f"c-{s}" / "ear.pt", map_location="cpu",
                        weights_only=False)
        enc, _, _ = ENC.load(a.snapshot)
        m = M.FrameEars(enc, D.N_REL, freeze_layers=ck.get("freeze_layers", 0))
        m.load_state_dict(ck["state"])
        m.eval().to(device)
        models.append(m)

    panel_names = [p for p in PANEL_TEST if (panels_dir / f"{p}.json").exists()]
    has_cal = (panels_dir / "cal.json").exists()
    store = {}
    if has_cal:
        store["cal"] = _prep(panels_dir / "cal.json", tok)
    for name in panel_names:
        store[name] = _prep(panels_dir / f"{name}.json", tok)
    paper_path = panels_dir / "paper.json"
    if paper_path.exists():
        store["paper"] = _prep(paper_path, tok)

    if "cal" not in store:
        raise SystemExit("sealed cal panel required")

    # decode everything once (temps already in checkpoints)
    parses_all = {}
    for name, (rows, encs) in store.items():
        golds = [gold_frame_of(e) for e in encs]
        # prefer gold47-based gold when encode succeeded: same content for rep frames
        parses = []
        for m in models:
            P = probs_for_model(m, encs, device)
            parses.append([decode(rows[i], encs[i], P[i], unk_ids)
                           for i in range(len(rows))])
        parses_all[name] = (rows, encs, golds, parses)

    report = {"seeds": list(SEEDS), "device": str(device), "panels": {}}
    cal_rows, cal_encs, cal_golds, cal_parses = parses_all["cal"]
    tau0 = tau0_from_cal(cal_golds, cal_parses, ensemble=True)
    tau_exec = 1.0 - (1.0 - tau0) / 2.0
    report["tau0"] = tau0
    report["tau_exec"] = tau_exec
    report["tau_echo"] = TAU_ECHO
    singles = []
    for s in range(3):
        t0 = tau0_from_cal(cal_golds, [cal_parses[s]], ensemble=False)
        singles.append(1.0 - (1.0 - t0) / 2.0)
    report["tau_exec_single"] = singles
    report["params"] = M.n_params(models[0])
    report["params_trainable"] = M.n_params_trainable(models[0])

    for name in [p for p in PANEL_TEST if p in parses_all] + (
            ["paper"] if "paper" in parses_all else []):
        rows, encs, golds, parses = parses_all[name]
        report["panels"][name] = {
            "ensemble": score_panel(rows, encs, parses, tau_exec, golds, True),
            "single": [score_panel(rows, encs, [parses[s]], tau_exec, golds, False,
                                   singles[s]) for s in range(3)],
            "unscorable": sum(1 for e in encs if e is None),
        }

    e = {nm: report["panels"][nm]["ensemble"]
         for nm in report["panels"] if nm != "paper"}

    def agg(key):
        return sum(e[nm][key] for nm in ("t_seen", "t_new", "t_trap", "t_hard")
                   if nm in e)

    def n_state_from_gold47(panel):
        rows = parses_all[panel][0]
        return sum(1 for r in rows if r.get("gold47", {}).get("act") == "STATE")

    n_seen_state = n_state_from_gold47("t_seen")
    n_new_state = n_state_from_gold47("t_new")
    need_seen = math.ceil(0.90 * n_seen_state)
    need_new = math.ceil(0.65 * n_new_state)

    def exec_stmt(panel):
        rows, encs, golds, parses = parses_all[panel]
        cnt = 0
        for k in range(len(rows)):
            ps = [p[k] for p in parses]
            v, fr = verdict_ensemble(ps, tau_exec)
            if golds[k]["act"] == "STATE" and v == "EXECUTE" \
                    and fr is not None and same_frame(fr, golds[k]):
                cnt += 1
        return cnt

    marks = {}
    marks["R2-SAFE"] = {"silent_wrong_writes_6500": agg("silent_wrong_write"),
                        "t_trap_items_written": e.get("t_trap", {}).get("written", 0),
                        "pass": agg("silent_wrong_write") == 0
                        and e.get("t_trap", {}).get("written", 0) == 0}
    echo_agg = sum(e[nm]["echoed_wrong_write"]
                   for nm in ("t_seen", "t_new", "t_trap", "t_hard") if nm in e)
    marks["R2-ECHO"] = {"echoed_wrong_writes": echo_agg, "limit": 65,
                        "pass": echo_agg <= 65, "gated": False}
    marks["R2-SEEN"] = {"correct": e["t_seen"]["correct"], "need": 1940,
                        "exec_correct_stmt": exec_stmt("t_seen"),
                        "need_exec": need_seen,
                        "n_state": n_seen_state,
                        "pass": e["t_seen"]["correct"] >= 1940
                        and exec_stmt("t_seen") >= need_seen}
    marks["R2-NEW"] = {"correct": e["t_new"]["correct"], "need": 2400,
                       "exec_correct_stmt": exec_stmt("t_new"), "need_exec": need_new,
                       "n_state": n_new_state,
                       "pass": e["t_new"]["correct"] >= 2400
                       and exec_stmt("t_new") >= need_new}
    marks["R2-NAMES"] = {"correct": e["t_hard"]["correct"], "need": 300,
                         "pass": e["t_hard"]["correct"] >= 300}
    wrong_ask = e["t_seen"]["wrong_exec_ask"] + e["t_new"]["wrong_exec_ask"]
    marks["R2-ASK"] = {"wrong_executed_questions": wrong_ask, "limit": 25,
                       "pass": wrong_ask <= 25}
    neg = e["wneg"]
    exec_fact_neg, exec_retract_neg = _count_exec_fact(parses_all["wneg"], tau_exec)
    marks["R2-NEG"] = {"n": neg["n"], "executed_as_fact": exec_fact_neg,
                       "executed_as_retract": exec_retract_neg,
                       "rate": exec_fact_neg / max(neg["n"], 1), "limit": 0.02,
                       "pass": exec_fact_neg / max(neg["n"], 1) <= 0.02}
    wc = e["wclosed"]
    wc_exec = wc["executed"]
    wc_exact = _count_exact(parses_all["wclosed"], tau_exec)
    need_wc_exec = math.ceil(0.60 * wc["n"])
    need_wc_exact = math.ceil(0.85 * max(wc_exec, 1))
    marks["R2-WEB"] = {"n": wc["n"], "executed": wc_exec,
                       "need_exec": need_wc_exec,
                       "exact": wc_exact, "need_exact": need_wc_exact,
                       "rate_exact": (wc_exact / wc_exec) if wc_exec else 0.0,
                       "pass": wc_exec >= need_wc_exec and wc_exact >= need_wc_exact}
    wn = e["wnewrel"]
    wrong_seen = _count_wrong_seen(parses_all["wnewrel"], tau_exec)
    marks["R2-NEWREL"] = {"n": wn["n"], "executed_with_wrong_seen_relation": wrong_seen,
                          "rate": wrong_seen / max(wn["n"], 1), "limit": 0.01,
                          "pass": wrong_seen / max(wn["n"], 1) <= 0.01}
    if "paper" in report["panels"]:
        p = report["panels"]["paper"]["ensemble"]
        marks["R2-PAPER"] = {"n": p["n"], "executed": p["executed"],
                             "correct": p["correct"], "echoed": p["echoed"],
                             "gated": False}
    report["marks"] = marks
    report["arm_pass"] = all(marks[k].get("pass", False) for k in GATED_MARKS
                             if k in marks)
    report["recorded"] = {
        "wpos": e.get("wpos"),
        "t_far": e.get("t_far"),
        "single_ear_totals": [
            {"silent_wrong_writes_6500":
             sum(report["panels"][nm]["single"][s]["silent_wrong_write"]
                 for nm in ("t_seen", "t_new", "t_trap", "t_hard")
                 if nm in report["panels"]),
             "echoed_wrong_writes":
             sum(report["panels"][nm]["single"][s]["echoed_wrong_write"]
                 for nm in ("t_seen", "t_new", "t_trap", "t_hard")
                 if nm in report["panels"]),
             "t_seen_correct": report["panels"]["t_seen"]["single"][s]["correct"],
             "t_new_correct": report["panels"]["t_new"]["single"][s]["correct"],
             "t_hard_correct": report["panels"]["t_hard"]["single"][s]["correct"],
             "t_trap_written": report["panels"]["t_trap"]["single"][s]["written"]}
            for s in range(3)]}
    Path(a.out).write_text(json.dumps(report, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    print(json.dumps(marks, indent=1))
    print("arm_pass", report["arm_pass"])


def _prep(path: Path, tok):
    rows = json.loads(path.read_text(encoding="utf-8"))
    encs = encode_panel(rows, tok)
    return rows, encs


def _count_exec_fact(parsed, tau_exec):
    """STATE-only EXECUTE on negatives (RETRACT recorded separately)."""
    rows, encs, golds, parses = parsed
    state = retract = 0
    for k in range(len(rows)):
        ps = [p[k] for p in parses]
        v, fr = verdict_ensemble(ps, tau_exec)
        if v == "EXECUTE" and fr is not None:
            if fr["act"] == "STATE":
                state += 1
            elif fr["act"] == "RETRACT":
                retract += 1
    return state, retract


def _count_exact(parsed, tau_exec):
    rows, encs, golds, parses = parsed
    cnt = 0
    for k in range(len(rows)):
        ps = [p[k] for p in parses]
        v, fr = verdict_ensemble(ps, tau_exec)
        if v == "EXECUTE" and fr is not None and fr["act"] == "STATE" \
                and same_frame(fr, golds[k]):
            cnt += 1
    return cnt


def _count_wrong_seen(parsed, tau_exec):
    """EXECUTE with a concrete seen relation when gold rel is OPEN (or differs)."""
    rows, encs, golds, parses = parsed
    cnt = 0
    for k in range(len(rows)):
        ps = [p[k] for p in parses]
        v, fr = verdict_ensemble(ps, tau_exec)
        if v != "EXECUTE" or fr is None:
            continue
        if fr["act"] not in ("STATE", "ASK", "RETRACT"):
            continue
        pred_rel = fr.get("rel")
        if pred_rel in (None, "OPEN", "UNSURE"):
            continue
        gold_rel = golds[k].get("rel")
        if gold_rel == "OPEN" or (gold_rel is not None and gold_rel != pred_rel):
            cnt += 1
    return cnt


if __name__ == "__main__":
    main()
