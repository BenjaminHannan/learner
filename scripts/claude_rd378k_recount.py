"""rd-378k blind recount of a label gate (Trustworthy notes thread, 2026-09-27). New file.

Recounts the sealed rows of PASSMARKS-E/F/K from a gate folder's labels.jsonl, labels_passA.jsonl and failures.jsonl
against the blind judges' verdicts, with code written apart from claude_rd378k_teacher.py agree. Prints counts only,
never a note, a turn or a raw answer.
usage: claude_rd378k_recount.py GATE_DIR [--rem R] [--judge-in F] [--judge-out F]
"""
import argparse, hashlib, json, re
from pathlib import Path

D = "artifacts/claude-rd371b-20260926/data/"
LOSS = re.compile(r"usage limit|rate limit|quota", re.I)


def rows(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


def rem3(i):
    return int(hashlib.sha256(i.encode()).hexdigest(), 16) % 3


def compare(lab, ver):
    got = {(r["dialog"], int(r["t"])): r["verdicts"] for r in lab}
    want = {(r["dialog"], int(r["t"])): r["verdicts"] for r in ver}
    tt = to = oo = ag = un = un_ok = n = 0
    for k, vs in got.items():
        js = want.get(k)
        if js is None or len(js) != len(vs):
            continue
        for x, y in zip(vs, js):
            n += 1
            a, b = x == "ok", y == "ok"
            tt += a; oo += b; ag += a == b; to += a and b
            if y == "unsupported":
                un += 1; un_ok += a
    pa, pb = tt / max(1, n), oo / max(1, n)
    pe = pa * pb + (1 - pa) * (1 - pb)
    kap = (ag / max(1, n) - pe) / (1 - pe) if pe < 1 else 0.0
    return {"compared": n, "agree": ag, "agree_pct": round(100 * ag / max(1, n), 1), "kappa": round(kap, 3),
            "judges_unsupported": un, "judges_unsupported_teacher_ok": un_ok,
            "untrue_pct": round(100 * un_ok / max(1, un), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gate")
    ap.add_argument("--judge-in", default=D + "judge_train_in.jsonl")
    ap.add_argument("--judge-out", default=D + "judge_train_out.jsonl")
    ap.add_argument("--rem", type=int, default=1, help="sha256(id) %% 3 of the gate's dialogs (1 = the gate's 38)")
    a = ap.parse_args()
    g = Path(a.gate)
    picked = {d["dialog"]: d["kind"] for d in rows(a.judge_in) if rem3(d["dialog"]) == a.rem}
    kinds = {k: sum(v == k for v in picked.values()) for k in sorted(set(picked.values()))}
    ver = rows(a.judge_out)
    lab = rows(g / "labels.jsonl")
    lab_a = rows(g / "labels_passA.jsonl") if (g / "labels_passA.jsonl").exists() else []
    fails = rows(g / "failures.jsonl") if (g / "failures.jsonl").exists() else []
    used = {r["dialog"] for r in lab}
    usable = {k: sum(picked.get(i) == k for i in used) for k in kinds}
    loss = [f for f in fails if not (f.get("raw") or "").strip() or LOSS.search(f.get("raw") or "")]
    bad = set(picked) - used
    loss_dialogs = sum(1 for i in bad if any(f["dialog"] == i for f in fails)
                       and all(f in loss for f in fails if f["dialog"] == i))
    full, pa = compare(lab, ver), compare(lab_a, ver)
    rep = {"picked": len(picked), "picked_by_kind": kinds, "label_dialogs_outside_picked": len(used - set(picked)),
           "usable_by_kind": usable, "overall": full, "passA": pa,
           "failed_tries": len(fails), "route_loss_tries": len(loss), "route_loss_dialogs": loss_dialogs,
           "missed_unknown_turns": sum(int(r.get("missed", 0)) == -1 for r in lab)}
    rep["rows"] = {
        "overall": full["agree"] >= 0.85 * full["compared"] and full["compared"] > 0 and full["kappa"] >= 0.5,
        "untrue": full["judges_unsupported_teacher_ok"] <= 0.15 * full["judges_unsupported"],
        "coverage_chat": usable.get("chat", 0) >= 21, "coverage_overheard": usable.get("overheard", 0) >= 14}
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
