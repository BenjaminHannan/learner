#!/usr/bin/env python3
"""rd-378g: write again, through Ben's opencode route, the practice batches that OpenRouter's 402s lost (Trustworthy
notes thread, 2026-09-26). New file; claude_rd378g_teacher.py stays and is imported unchanged.

rd378g-teacher (COMMIT 854f21660) wrote 90 dialogs (15 of 40 batches). Batches 7, 8, 11 and 14 failed the script's own
code checks three times (kept skipped, as the sealed script would); batches 18-20 and 22-39 were lost to "HTTP Error 402:
Payment Required" (the OpenRouter account ran out of funds). This script runs the SAME per-batch step as
claude_rd378g_teacher.writenotes (same WRITE prompt, area, speaker letters, check_batch, repeat check against every
first turn already written, to_rows) for the named batches only, with each call sent through
scripts/claude_glm_opencode.py (the Director's helper; the route sets no temperature, the sealed run asked for 0.9).
New dialogs get ids after the existing ones (kg-091...). Output = the existing dialogs, unchanged, then the new ones.

python -B scripts/claude_rd378g_writemore_oc.py write --have glm/notes_w1.jsonl --batches 18-20,22-39 --out DIR
    writes DIR/notes_w1.jsonl; prints one JSON line of counts
python -B scripts/claude_rd378g_writemore_oc.py selftest   (no network)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_rd378g_teacher as G  # noqa: E402


def oc_call(text):
    import claude_glm_opencode as OC
    try:
        return OC.call(text) or ""
    except Exception as e:                            # a failed call counts as a failed try, never guessed
        print(f"[rd378g-writemore] call failed: {type(e).__name__} {str(e)[:120]}", flush=True)
        return ""


def batches(spec):
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += list(range(int(a), int(b or a) + 1))
    return out


def one_batch(b, seen, call):
    """The loop body of claude_rd378g_teacher.writenotes for batch b; returns the checked rows or None."""
    letters = ", ".join(G.LETTERS[(3 * b + j) % len(G.LETTERS)] for j in range(3))
    for t in range(3):
        txt = call(G.WRITE.replace("{area}", G.AREAS[b]).replace("{letters}", letters))
        rows = G.json_list(txt)
        bad = G.check_batch(rows)
        firsts = None if bad else {r["turns"][0]["text"].strip().lower() for r in rows}
        if bad is None and not firsts & seen:
            return rows
        print(f"[rd378g-writemore] batch {b} try {t + 1}: {bad or 'repeats an earlier dialog'}", flush=True)
    return None


def write(a, call=oc_call):
    items = [json.loads(x) for x in Path(a.have).read_text(encoding="utf-8").splitlines() if x.strip()]
    have = len(items)
    seen = {x["turns"][0]["text"].strip().lower() for x in items}
    skipped = []
    for b in batches(a.batches):
        rows = one_batch(b, seen, call)
        if rows is None:
            skipped.append(b)
            print(f"[rd378g-writemore] batch {b} skipped after 3 tries", flush=True)
            continue
        seen |= {r["turns"][0]["text"].strip().lower() for r in rows}
        items += G.to_rows(rows, len(items))
        print(f"[rd378g-writemore] batch {b} ok ({len(items)} dialogs)", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "notes_w1.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items),
                                        encoding="utf-8")
    new = items[have:]
    tn = [t for x in new for t in x["turns"] if "notes" in t]
    rep = {"dialogs": len(items), "kept_from_before": have, "new_dialogs": len(new),
           "new_by_kind": {k: sum(x["kind"] == k for x in new) for k in ("chat", "overheard")},
           "batches_skipped": skipped, "new_turns": len(tn), "new_notes": sum(len(t["notes"]) for t in tn),
           "new_empty_turns": sum(not t["notes"] for t in tn)}
    print(json.dumps(rep))
    return rep


def selftest():
    import tempfile
    assert batches("18-20,22-24") == [18, 19, 20, 22, 23, 24]

    def turns(kind, sp, n):
        return [{"speaker": sp[k % 2], "text": f"we got a dog last May {kind} {n}" if k == 0 else "ok",
                 "notes": [] if (kind == "chat" and k % 2) else ([{"text": "The user got a dog.", "cites": [0],
                                                                    "when": "last May"}] if k == 0 else [])}
                for k in range(12)]
    calls = {"n": 0}

    def fake(_text):
        calls["n"] += 1
        if calls["n"] == 1:
            return "not json"
        n = calls["n"]
        return json.dumps([{"kind": "chat", "speakers": ["user", "assistant"], "date": "8 May 2023",
                            "turns": turns("chat", ["user", "assistant"], f"{n}-{i}")} for i in range(3)] +
                          [{"kind": "overheard", "speakers": ["Wren", "Tobin"], "date": "14 June 2022",
                            "turns": turns("overheard", ["Wren", "Tobin"], f"{n}-{i}")} for i in range(3)])
    with tempfile.TemporaryDirectory() as d:
        have = Path(d) / "have.jsonl"
        have.write_text(json.dumps({"dialog": "kg-001", "kind": "chat", "speakers": ["user", "assistant"],
                                    "date": "8 May 2023", "turns": [{"t": 1, "speaker": "user", "text": "hi",
                                                                     "notes": []}]}) + "\n", encoding="utf-8")
        rep = write(argparse.Namespace(have=str(have), batches="3-4", out=d), call=fake)
        rows = [json.loads(x) for x in (Path(d) / "notes_w1.jsonl").read_text().splitlines()]
    ok = (rep["kept_from_before"] == 1 and rep["new_dialogs"] == 12 and rows[0]["dialog"] == "kg-001"
          and rows[1]["dialog"] == "kg-002" and rows[-1]["dialog"] == "kg-013" and calls["n"] == 3)
    print("rd378g writemore selftest " + ("1/1 ok" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["write", "selftest"])
    ap.add_argument("--have", default="")
    ap.add_argument("--batches", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.mode == "selftest":
        sys.exit(selftest())
    write(a)


if __name__ == "__main__":
    main()
