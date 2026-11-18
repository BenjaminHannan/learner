"""Probe-4 keep rules (PREREG.md "New jobs"): a generated task is kept only if (1) every check passes the sandbox validator, (2) its reference plan replayed in the sandbox passes all its checks,
(3) for a trap, the literal "just do it" plan written by the same call fails at least one check. Also dropped: malformed fields, duplicates (of each other or of the 420 existing tasks).
Survivors beyond --max are cut (traps keep ~40%); ids are renamed p4_001...; the result is written to tasks_new.jsonl and its sha256 printed (goes in RESULTS).
Usage: validate_tasks.py [--raw tasks_raw.jsonl] [--out tasks_new.jsonl] [--report validation_report.json] [--min 80] [--max 120]"""
import argparse, copy, json, os, re, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p4common as P
import replay as R
from p4common import World, validate_check, run_checks

KEYS = ("scenario", "state", "user", "checks", "reference", "reference_reply", "rubric")
STATE_TYPES = dict(files=dict, emails=list, sent=list, drafts=list, calendar=list, notes=dict, reminders=list)
TOOL_NAMES = {t["function"]["name"] for t in P.TOOLS}


def words(s):
    return set(re.findall(r"\w+", str(s).lower()))


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


def plan_ok(plan):
    return isinstance(plan, list) and all(isinstance(c, dict) and c.get("name") in TOOL_NAMES and isinstance(c.get("arguments"), dict) for c in plan)


def mail_ok(box):
    return all(isinstance(m, dict) and all(k in m for k in ("from", "to", "subject", "body")) for m in box)


def check_task(t, others=(), near=0.8):
    """-> (reasons it must be dropped, notes). others: user texts already kept / existing (exact or Jaccard >= near is a duplicate)."""
    why, notes = [], []
    if not isinstance(t, dict) or any(k not in t for k in KEYS):
        return ["missing_fields"], notes
    if not (isinstance(t["scenario"], str) and t["scenario"].strip() and isinstance(t["user"], str) and t["user"].strip() and isinstance(t["reference_reply"], str) and isinstance(t["rubric"], str)):
        return ["bad_field_types"], notes
    st = t["state"]
    if not isinstance(st, dict) or any(k in st and not isinstance(st[k], ty) for k, ty in STATE_TYPES.items()) or not all(isinstance(v, str) for v in st.get("files", {}).values()) \
            or not isinstance(st.get("today", ""), str) or not all(isinstance(v, str) for v in st.get("notes", {}).values()):
        return ["bad_state"], notes
    if not (mail_ok(st.get("emails", [])) and mail_ok(st.get("sent", [])) and mail_ok(st.get("drafts", []))) or \
            not all(isinstance(e, dict) and all(k in e for k in ("title", "date", "start")) for e in st.get("calendar", [])) or \
            not all(isinstance(r, dict) and "text" in r and "when" in r for r in st.get("reminders", [])):
        return ["bad_state"], notes
    try:
        World.from_json(st)
    except Exception:  # noqa
        return ["bad_state"], notes
    if not isinstance(t["checks"], list) or not t["checks"] or not all(validate_check(c) for c in t["checks"]):     # rule 1
        return ["invalid_check"], notes
    trap = t.get("trap")
    if not isinstance(trap, bool):
        return ["bad_trap_flag"], notes
    if not plan_ok(t["reference"]) or not t["reference"]:
        return ["bad_reference"], notes
    task = dict(t)
    w, reply = R.replay_reference(task)                                                                              # rule 2
    if not R.success_of(task, w, reply):
        why.append("reference_fails_checks")
    if trap:                                                                                                         # rule 3
        lp = t.get("literal_plan")
        if not plan_ok(lp) or not lp or not isinstance(t.get("literal_reply", ""), str):
            why.append("trap_without_literal_plan")
        else:
            w2, r2 = R.apply_calls(task, [(c["name"], c["arguments"]) for c in lp], t.get("literal_reply") or "")
            if R.success_of(task, w2, r2):
                why.append("literal_plan_passes")
    else:
        w0 = World.from_json(st)
        if all(run_checks(task, w0, "")):
            notes.append("passes_without_doing_anything")
    u = words(t["user"])
    for o in others:
        if o == t["user"].strip().lower() or jaccard(u, words(o)) >= near:
            why.append("duplicate")
            break
    ref_err = sum(str(r).startswith("error:") for r in (lambda w_: [w_.call(c["name"], c["arguments"]) for c in t["reference"]])(World.from_json(st)))
    if ref_err:
        notes.append(f"reference_has_{ref_err}_error_results")
    return why, notes


def select(kept, lo, hi, trap_share=0.4):
    """Survivors in generation order -> at most hi, traps ~ trap_share (take the first traps / plain jobs up to their quota, then fill)."""
    if len(kept) <= hi:
        return kept
    nt = round(hi * trap_share)
    traps, plain = [t for t in kept if t["trap"]], [t for t in kept if not t["trap"]]
    take = traps[:nt] + plain[:hi - nt]
    if len(take) < hi:
        rest = [t for t in kept if t not in take]
        take += rest[:hi - len(take)]
    ids = {id(t) for t in take}
    return [t for t in kept if id(t) in ids]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(P.HERE, "tasks_raw.jsonl"))
    ap.add_argument("--out", default=P.TASKS_NEW)
    ap.add_argument("--report", default=os.path.join(P.HERE, "validation_report.json"))
    ap.add_argument("--min", type=int, default=80)
    ap.add_argument("--max", type=int, default=120)
    a = ap.parse_args()
    old = P.load_old_tasks()
    seen = [t["user"].strip().lower() for t in old]
    raw = [json.loads(l) for l in open(a.raw) if l.strip()]
    kept, drops, notes_c = [], Counter(), Counter()
    for t in raw:
        why, notes = check_task(t, seen)
        notes_c.update(notes)
        if why:
            drops.update(why[:1])
            continue
        kept.append(t)
        seen.append(t["user"].strip().lower())
    final = select(kept, a.min, a.max)
    out = []
    for i, t in enumerate(final, 1):
        t = {k: copy.deepcopy(v) for k, v in t.items() if k != "_src"}
        t["state"].setdefault("today", "2026-10-24")
        out.append(dict(id=f"p4_{i:03d}", **t))
    with open(a.out, "w") as f:
        f.writelines(json.dumps(t, ensure_ascii=False) + "\n" for t in out)
    new_scen = sum(t["scenario"] in {x["scenario"] for x in old} for t in out)
    rep = dict(raw=len(raw), kept_before_cap=len(kept), written=len(out), traps=sum(t["trap"] for t in out), drops=dict(drops), notes=dict(notes_c), scenarios_reusing_existing_names=new_scen,
               n_scenarios=len({t["scenario"] for t in out}), sha256=P.sha256(a.out), enough=len(out) >= a.min)
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps(rep, indent=1))
    if len(out) < a.min:
        print(f"ONLY {len(out)} tasks survive (< {a.min}): run gen_tasks.py --phase submit again (a new round), collect, and rerun this script.")
        sys.exit(3)


if __name__ == "__main__":
    main()
