#!/usr/bin/env python3
"""Fable ledger audit 82: static parser for artifacts/fable-predictions-ledger.md.

Read-only on the ledger. Prints every prediction id with p, outcome, experiment;
duplicates; stale opens; per-experiment + overall Brier; experiment verdicts;
order violations. Includes --selftest on a synthetic ledger.

Usage:
  python -B scripts/fable_ledger82_check.py --ledger artifacts/fable-predictions-ledger.md \
      --out artifacts/fable-ledger82-20260921/ledger_status.json
  python -B scripts/fable_ledger82_check.py --selftest
"""

import argparse
import json
import re
import sys

ID_RE = re.compile(r"\b(?:R\d+-)?P\d+(?:\.\d+)?\b")
RANGE_RE = re.compile(r"\bP(\d+)\s*[–—-]\s*P?(\d+)\b")
PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
EXP_RE = re.compile(r"(?:experiment|redteam|exp)\s+(\d+[a-z]*)", re.I)
HEADING_RE = re.compile(r"^#{1,3}\s*(.*)")
OUTCOME_WORD_RE = re.compile(r"NOT SCORABLE|VOID|TRUE|FALSE|\(open\)", re.I)
VERDICT_RE = re.compile(
    r"SCORE (?:registered FAIL|PASS|FAIL)|registered FAIL|final verdict \S+|"
    r"SCORE PASS|Brier:[^.\n]*|(\d+/\d+ (?:TRUE|PASS))", re.I)


def outcome_of_text(t):
    u = t.upper()
    if re.search(r"\bNOT SCORABLE\b", u):
        return "NOT_SCORABLE"
    if re.search(r"\bVOID\b", u):
        return "VOID"
    if re.search(r"\bTRUE\b", u):
        return "TRUE"
    if re.search(r"\bFALSE\b", u):
        return "FALSE"
    if "(OPEN)" in u:
        return "OPEN"
    return None


def expand_range(a, b):
    a, b = int(a), int(b)
    if b < a or b - a > 500:
        return []
    return ["P%d" % i for i in range(a, b + 1)]


def parse_ledger(text):
    lines = text.splitlines()
    recs = {}  # id -> {p:[], pred_lines:[], outcome_lines:[], outcomes:[], exp}
    exp_of_line = {}
    cur_exp = "early"
    cur_date = None
    line_date = {}
    line_exp = {}
    for i, ln in enumerate(lines, start=1):
        m = DATE_RE.search(ln[:120] if ln.startswith("#") else ln if ln.startswith("#") else "")
        if ln.startswith("#"):
            dm = DATE_RE.search(ln)
            if dm:
                cur_date = dm.group(1)
            em = EXP_RE.search(ln)
            if em:
                cur_exp = em.group(1)
            elif "ledger note" in ln.lower() or "earlier forecasts" in ln.lower():
                pass
        # inline experiment hints update only for outcome grouping, keep heading exp
        line_date[i] = cur_date
        line_exp[i] = cur_exp
        exp_of_line[i] = cur_exp

    in_outcomes = False
    for i, ln in enumerate(lines, start=1):
        exp = exp_of_line[i]
        stripped = ln.strip()
        # Continuation of a wrapped "Outcomes ...:" block: lines that do not
        # start a new bullet/table/heading but carry "Pxxx TRUE/FALSE" pairs.
        cont_handled = False
        if in_outcomes and not stripped.startswith(("#", "|", "-", "*")) and stripped:
            cont_ids = ID_RE.findall(ln)
            if cont_ids and outcome_of_text_bullet(ln):
                all_ids = cont_ids
                refs_only = set()
                cont_handled = True
            else:
                for r_id in ID_RE.findall(ln):
                    r = recs.setdefault(r_id, {"p": None, "p_line": None, "pred_lines": [],
                                               "outcome_lines": [], "outcomes": [], "exps": set()})
                    r["exps"].add(exp + ":ref")
                continue
        elif stripped.startswith("|"):
            in_outcomes = False
        # Decide which ids this line DEFINES (pred/outcome attribution):
        # - table rows: only the first-cell id(s); other ids are references.
        # - bullet "Outcomes ...:" lines: ids after the colon.
        # - bullet prediction lines "- P187: ...": subject ids before colon.
        # All other id mentions (e.g. "same statement as P102", "(see P104)",
        # "(e.g. P60.1)") are references and get no pred/outcome attribution.
        refs_only = set()
        if cont_handled:
            pass  # all_ids/refs_only already set by continuation branch
        elif stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 1 and ("forecast | p |" in ln or "| id |" in ln):
                continue  # header row
            first_ids = ID_RE.findall(cells[0]) if cells else []
            first_extra = []
            for a, b in RANGE_RE.findall(cells[0] if cells else ""):
                first_extra.extend(expand_range(a, b))
            attr_ids = list(dict.fromkeys(first_ids + [e for e in first_extra if e not in first_ids]))
            ref_ids = [x for x in ID_RE.findall(ln) if x not in attr_ids]
            refs_only.update(ref_ids)
            all_ids = attr_ids
        else:
            m = re.match(r"\s*[-*]\s*([^:]+):", ln)
            if m:
                subject = m.group(1)
                rest = ln[m.end():]
                if re.search(r"[Oo]utcomes?", subject):
                    in_outcomes = True
                    all_ids = list(dict.fromkeys(
                        ID_RE.findall(subject) + ID_RE.findall(rest)))
                    # range in subject, e.g. "P145-P151 outcomes"
                    for a, b in RANGE_RE.findall(subject):
                        for e in expand_range(a, b):
                            if e not in all_ids:
                                all_ids.append(e)
                    # subject tokens are labels, keep only rest+range members
                    rest_ids = ID_RE.findall(rest)
                    range_ids = []
                    for a, b in RANGE_RE.findall(subject):
                        range_ids.extend(expand_range(a, b))
                    all_ids = list(dict.fromkeys(rest_ids + [e for e in range_ids if e not in rest_ids]))
                else:
                    in_outcomes = False
                    all_ids = ID_RE.findall(subject)
                    for a, b in RANGE_RE.findall(subject):
                        for e in expand_range(a, b):
                            if e not in all_ids:
                                all_ids.append(e)
                    refs_only.update(x for x in ID_RE.findall(rest) if x not in all_ids)
            else:
                in_outcomes = False
                all_ids = []
                refs_only.update(ID_RE.findall(ln))
        for r_id in refs_only:
            r = recs.setdefault(r_id, {"p": None, "p_line": None, "pred_lines": [],
                                       "outcome_lines": [], "outcomes": [], "exps": set()})
            r["exps"].add(exp + ":ref")
        if not all_ids:
            continue
        # stated probability for this line
        p = None
        stripped = ln.strip()
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            # standard table: id|hashed|setting|forecast|p|falsified|outcome|brier
            if len(cells) >= 8:
                pc = cells[4]
                if re.fullmatch(r"\d*\.?\d+", pc):
                    v = float(pc)
                    if 0.0 <= v <= 1.0:
                        p = v
        if p is None and re.search(r"^[\s\-*|]*P\d", ln) is None:
            pass
        if p is None:
            # bullet prediction lines "- P187: ... 75%." : take LAST % on line as p
            # but avoid taking Brier-list lines as predictions (they have no P-colon def)
            if re.search(r"-\s*(?:Outcomes|P\d)", ln) and "%" in ln:
                pcts = PCT_RE.findall(ln)
                if pcts and re.match(r"\s*[-*|]\s*(P\d|R\d)", stripped):
                    # outcome-summary lines also carry % rarely; only treat as
                    # prediction if line defines predictions (contains ':' after id)
                    if re.search(r"P\d[\d.]*\s*:", ln):
                        p = float(pcts[-1]) / 100.0
        # outcome signal on this line (bullets: case-sensitive; tables: cell-based below)
        oc = outcome_of_text_bullet(ln) if not stripped.startswith("|") else outcome_of_text(ln)
        # table outcome cell more precise
        if stripped.startswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 8:
                co = outcome_of_text(cells[6])
                # outcomes-summary rows put verdicts in a later cell
                if co is None:
                    co = outcome_of_text(" ".join(cells[6:]))
                # empty outcome cell -> MISSING (not OPEN) unless (open) elsewhere
                if co is None:
                    if cells[6] == "" and "open" not in ln.lower():
                        co = "MISSING"
                oc = co if co else ("MISSING" if cells[6] == "" else oc)
        for pid in all_ids:
            # skip header-ish tokens like the range label itself being outcome word; keep all
            r = recs.setdefault(pid, {"p": None, "p_line": None, "pred_lines": [],
                                      "outcome_lines": [], "outcomes": [], "exps": set()})
            r["exps"].add(exp)
            # prediction if this line states p AND (defines with colon OR table row with p col)
            is_pred = p is not None and (
                stripped.startswith("|") or bool(re.search(re.escape(pid) + r"\s*:", ln)))
            # table header rows: no
            if "forecast | p |" in ln or "| id |" in ln:
                is_pred = False
            if is_pred:
                r["pred_lines"].append(i)
                if r["p"] is None:
                    r["p"] = p
                    r["p_line"] = i
                else:
                    # second distinct stated p -> keep first, record dup later
                    r.setdefault("p_dup", []).append({"line": i, "p": p})
            if oc and not is_pred_only(ln, pid):
                # outcome mentions: line asserts TRUE/FALSE/etc about this id,
                # or summary "P187 FALSE" pattern
                st = None if stripped.startswith("|") else status_for(ln, pid)
                if st is None:
                    st = oc
                if mentions_outcome_for(ln, pid) and st in (
                        "TRUE", "FALSE", "VOID", "NOT_SCORABLE", "OPEN"):
                    r["outcome_lines"].append(i)
                    r["outcomes"].append({"line": i, "status": st, "exp": exp})
            elif oc and is_pred and outcome_of_text(ln):
                # same-line table row carrying both prediction and outcome
                r["outcome_lines"].append(i)
                r["outcomes"].append({"line": i, "status": oc, "exp": exp})
    return recs, lines, line_date, line_exp


def is_pred_only(ln, pid):
    # bullet prediction def "- P187: ... 75%." with no TRUE/FALSE word -> pred only
    m = re.search(re.escape(pid) + r"\s*:", ln)
    if m and not outcome_of_text_bullet(ln):
        return True
    return False


def outcome_of_text_bullet(t):
    """Case-sensitive variant for bullet lines: prose contains lowercase
    'true' (e.g. '(true by fallback construction)') which must NOT count."""
    if re.search(r"NOT SCORABLE", t):
        return "NOT_SCORABLE"
    if re.search(r"\bVOID\b", t):
        return "VOID"
    if re.search(r"\bTRUE\b", t):
        return "TRUE"
    if re.search(r"\bFALSE\b", t):
        return "FALSE"
    if "(open)" in t:
        return "OPEN"
    return None


def status_for(ln, pid):
    """Outcome status scoped to one id: first outcome word after the id's
    occurrence, up to the next id (or 120 chars). Falls back to the whole
    line only when the line carries exactly one outcome word."""
    spans = [(m.group(0), m.start(), m.end()) for m in ID_RE.finditer(ln)]
    hits = [s for s in spans if s[0] == pid]
    if not hits:
        return outcome_of_text_bullet(ln)
    words = re.findall(r"NOT SCORABLE|\bVOID\b|\bTRUE\b|\bFALSE\b|\(open\)", ln)
    for _, s, e in hits:
        nxt = min([s2 for _, s2, _ in spans if s2 > s] + [e + 120])
        w = outcome_of_text_bullet(ln[e:nxt])
        if w:
            return w
    if len(words) == 1:
        return outcome_of_text_bullet(ln)
    return None


def mentions_outcome_for(ln, pid):
    # outcome if TRUE/FALSE/VOID/NOT SCORABLE/(open) on line AND id within
    # a few dozen chars of the word, or table row, or Outcomes line
    if ln.strip().startswith("|"):
        return True
    if re.search(r"[Oo]utcomes?", ln):
        return True
    # bullet "- P187 FALSE ..." pattern
    if re.search(re.escape(pid) + r"\b[^\n]{0,60}(TRUE|FALSE|VOID|NOT SCORABLE|\(open\))", ln):
        return True
    if outcome_of_text_bullet(ln):
        return True
    return False


def final_status(r):
    if not r["outcomes"]:
        return "MISSING"
    return r["outcomes"][-1]["status"]


def brier(p, status):
    if status == "TRUE":
        return (1.0 - p) ** 2
    if status == "FALSE":
        return p ** 2
    return None


def analyze(text):
    recs, lines, line_date, line_exp = parse_ledger(text)
    # duplicates: same id with >=2 pred_lines, or pred in >=2 exps
    duplicates = {}
    for pid, r in recs.items():
        n_pred = len(r["pred_lines"])
        if n_pred >= 2 or (len(r.get("p_dup", [])) > 0):
            duplicates[pid] = {"pred_lines": r["pred_lines"],
                               "p": r["p"],
                               "extra_p": r.get("p_dup", []),
                               "exps": sorted(r["exps"])}
    # order violations: first outcome line < first pred line
    order_violations = []
    for pid, r in recs.items():
        if r["pred_lines"] and r["outcome_lines"]:
            if min(r["outcome_lines"]) < min(r["pred_lines"]):
                order_violations.append({"id": pid,
                                         "first_outcome": min(r["outcome_lines"]),
                                         "first_pred": min(r["pred_lines"])})
    order_violations.sort(key=lambda d: d["first_outcome"])
    # stale opens: MISSING or OPEN and section date older than file max date
    dates = [d for d in line_date.values() if d]
    max_date = max(dates) if dates else None
    stale = []
    for pid, r in sorted(recs.items()):
        st = final_status(r)
        if st in ("MISSING", "OPEN"):
            pl = r["p_line"] or (r["pred_lines"][0] if r["pred_lines"] else None)
            # ids only seen in outcome summaries without own pred line: use first outcome line
            ref = pl or (r["outcome_lines"][0] if r["outcome_lines"] else 1)
            d = line_date.get(ref)
            if max_date and d and d < max_date:
                stale.append(pid)
            elif max_date and d == max_date and st == "MISSING" and r["p"] is None:
                pass  # fresh undefined tokens, not stale
    # Brier per experiment (by prediction experiment = exp at p_line)
    per_exp = {}
    overall_n = 0
    overall_sum = 0.0
    for pid, r in recs.items():
        st = final_status(r)
        if r["p"] is None:
            continue
        # P82 self-audit predictions have no outcomes yet -> skip
        b = brier(r["p"], st)
        if b is None:
            continue
        pl = r["p_line"] or 1
        exp = line_exp.get(pl, "?")
        # normalize redteam labels
        e = per_exp.setdefault(exp, {"n": 0, "sum": 0.0})
        e["n"] += 1
        e["sum"] += b
        overall_n += 1
        overall_sum += b
    for e in per_exp.values():
        e["mean"] = e["sum"] / e["n"] if e["n"] else None
    overall = overall_sum / overall_n if overall_n else None
    # experiment verdicts: last verdict-like match per heading section
    exps_seen = []
    verdicts = {}
    cur = "early"
    for i, ln in enumerate(lines, start=1):
        if ln.startswith("#"):
            em = EXP_RE.search(ln)
            if em:
                cur = em.group(1)
                if cur not in exps_seen:
                    exps_seen.append(cur)
        vm = VERDICT_RE.search(ln)
        if vm and cur:
            verdicts[cur] = {"verdict": vm.group(0).strip()[:120], "line": i}
    for exp in per_exp:
        if exp not in exps_seen:
            exps_seen.append(exp)
    counts = {
        "n_ids": len(recs),
        "n_with_p": sum(1 for r in recs.values() if r["p"] is not None),
        "n_true": sum(1 for r in recs.values() if final_status(r) == "TRUE"),
        "n_false": sum(1 for r in recs.values() if final_status(r) == "FALSE"),
        "n_void": sum(1 for r in recs.values() if final_status(r) == "VOID"),
        "n_not_scorable": sum(1 for r in recs.values() if final_status(r) == "NOT_SCORABLE"),
        "n_open": sum(1 for r in recs.values() if final_status(r) == "OPEN"),
        "n_missing": sum(1 for r in recs.values() if final_status(r) == "MISSING"),
        "n_duplicates": len(duplicates),
        "n_stale_open": len(stale),
        "n_order_violations": len(order_violations),
        "n_scored_brier": overall_n,
    }
    detail = {}
    for pid in sorted(recs, key=lambda x: (len(x), x)):
        r = recs[pid]
        detail[pid] = {"p": r["p"], "p_line": r["p_line"],
                       "status": final_status(r),
                       "outcome_lines": r["outcome_lines"],
                       "exps": sorted(r["exps"])}
    return {"counts": counts, "duplicates": duplicates, "stale_open": stale,
            "order_violations": order_violations, "per_experiment_brier": per_exp,
            "overall_brier": {"n": overall_n, "mean": overall},
            "experiments": exps_seen, "verdicts": verdicts, "predictions": detail,
            "max_date": max_date}


def selftest():
    syn = """# ledger
## 2026-09-20 — Experiment 9 (demo), written before the run
- P9.1: thing happens. 75%.
- P9.2: other thing. 50%.
## 2026-09-22 — Experiment 10 (demo), written before the run
- P9.1: redefined thing. 60%.
| id | hashed in | setting | forecast | p | falsified by | outcome | Brier |
| P10 | x | s | f | 0.25 | y | FALSE | 0.0625 |
| P11 | x | s | f | 0.50 | y | (open) | |
- Outcomes 9: P9.1 TRUE. P9.2 FALSE.
- Outcomes 10: P10 FALSE.
"""
    a = analyze(syn)
    assert a["predictions"]["P10"]["p"] == 0.25, a["predictions"]["P10"]
    assert a["predictions"]["P10"]["status"] == "FALSE"
    assert abs(a["overall_brier"]["mean"] - (((0.25) ** 2 + (0.5) ** 2 + (1 - 0.75) ** 2) / 3)) < 1e-9, a["overall_brier"]
    assert "P9.1" in a["duplicates"], a["duplicates"]
    assert a["predictions"]["P11"]["status"] == "OPEN", a["predictions"]["P11"]
    # order violation synthetic
    syn2 = "- Outcomes 7: P7.1 TRUE.\n- P7.1: pred. 80%.\n"
    a2 = analyze(syn2)
    assert len(a2["order_violations"]) == 1 and a2["order_violations"][0]["id"] == "P7.1", a2["order_violations"]
    # Brier spot check: 75% TRUE -> 0.0625
    assert abs(brier(0.75, "TRUE") - 0.0625) < 1e-12
    assert abs(brier(0.75, "FALSE") - 0.5625) < 1e-12
    print("SELFTEST PASS: brier/duplicates/order/open all green")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default="artifacts/fable-predictions-ledger.md")
    ap.add_argument("--out", default="artifacts/fable-ledger82-20260921/ledger_status.json")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    with open(args.ledger, encoding="utf-8") as f:
        text = f.read()
    a = analyze(text)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(a, f, indent=2, sort_keys=False)
    c = a["counts"]
    print("ids=%d with_p=%d TRUE=%d FALSE=%d VOID=%d NOTSCOR=%d OPEN=%d MISSING=%d scored=%d" % (
        c["n_ids"], c["n_with_p"], c["n_true"], c["n_false"], c["n_void"],
        c["n_not_scorable"], c["n_open"], c["n_missing"], c["n_scored_brier"]))
    ob = a["overall_brier"]
    print("overall Brier n=%d mean=%.4f" % (ob["n"], ob["mean"] if ob["mean"] is not None else float("nan")))
    for exp in sorted(a["per_experiment_brier"]):
        e = a["per_experiment_brier"][exp]
        print("exp %s: n=%d mean=%.4f" % (exp, e["n"], e["mean"]))
    print("duplicates (%d): %s" % (len(a["duplicates"]), ", ".join(sorted(a["duplicates"]))[:2000]))
    print("stale_open (%d): %s" % (len(a["stale_open"]), ", ".join(a["stale_open"])[:2000]))
    print("order_violations (%d): %s" % (
        len(a["order_violations"]),
        "; ".join("%s outcome@%d pred@%d" % (d["id"], d["first_outcome"], d["first_pred"])
                  for d in a["order_violations"])[:2000]))
    print("experiments: %s" % (", ".join(a["experiments"])[:2000]))
    for exp in a["experiments"]:
        v = a["verdicts"].get(exp)
        print("verdict %s: %s" % (exp, (v["verdict"] + " @%d" % v["line"]) if v else "none found"))


if __name__ == "__main__":
    main()
