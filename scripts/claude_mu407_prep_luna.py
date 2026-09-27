#!/usr/bin/env python3
"""mu-407 prep with GPT-6 Luna as the writer ("Making things up about you", 2026-09-27; ADDENDUM-1).
New file. It imports claude_mu407_prep unchanged and swaps only its module-level caller (`call_low`) for
claude_luna_codex.call. Every prompt, check and subcommand is claude_mu407_prep's. Standard library only.

  facts | frames | write | select | selftest     exactly as claude_mu407_prep.py, with Luna as the caller
  smokefacts --facts F --out S                   the 3 smoke rows of F only (pilot input for `write`)
  pilot --frames FR --raw RAW                    ADDENDUM-1's pilot gate; prints JSON, exit 0 on pass, 1 on fail
  scan  --frames FR --raw RAW                    pre-SEAL-data scan: pilot strings in every kept text, and any user
                                                 message repeated across 3 or more chats; prints JSON counts
  selftest-luna                                  offline checks of the swap, pilot and scan (no network)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import claude_mu407_prep as P  # noqa: E402

SCAN = ("usage limit", "rate limit", "error:", "as an ai", "openai", "codex", "i can't help with")
PILOT_MIN_SMOKE = 2
REPEAT_MIN = 3


def luna_call(text: str) -> str:
    import claude_luna_codex as L
    return L.call(text) or ""


P.call_low = luna_call


def texts_of(frames: dict, raw: list[dict]) -> list[str]:
    out = [str(v) for v in frames.values()]
    for r in raw:
        if r.get("ok"):
            out += [t["text"] for t in r["session1"]] + [t["text"] for t in r["session2"]]
    return out


def scan_hits(texts: list[str]) -> dict:
    return {s: sum(1 for t in texts if s in t.lower()) for s in SCAN}


def repeats(raw: list[dict]) -> dict:
    """User messages (exact, case-folded, stripped) that appear in REPEAT_MIN or more different chats."""
    where = Counter()
    for r in raw:
        if r.get("ok"):
            for t in {x["text"].strip().lower() for x in r["session1"] + r["session2"]}:
                where[t] += 1
    return {t: n for t, n in where.items() if n >= REPEAT_MIN}


def pilot(frames_path: str, raw_path: str) -> dict:
    fr_ok, frames = False, {}
    try:
        frames = P.check_frames(json.loads(Path(frames_path).read_text(encoding="utf-8")))
        fr_ok = True
    except Exception:  # noqa: BLE001  (missing or failing frames fail the pilot)
        pass
    raw = list(map(json.loads, Path(raw_path).read_text(encoding="utf-8").splitlines())) \
        if Path(raw_path).exists() else []
    smoke_ok = sum(1 for r in raw if r.get("ok"))
    hits = scan_hits(texts_of(frames, raw))
    res = {"frames_ok": fr_ok, "smoke_rows": len(raw), "smoke_ok": smoke_ok, "scan_hits": hits,
           "pass": fr_ok and smoke_ok >= PILOT_MIN_SMOKE and not any(hits.values())}
    return res


def scan(frames_path: str, raw_path: str) -> dict:
    frames = json.loads(Path(frames_path).read_text(encoding="utf-8"))
    raw = list(map(json.loads, Path(raw_path).read_text(encoding="utf-8").splitlines()))
    rep = repeats(raw)
    return {"kept_chats": sum(1 for r in raw if r.get("ok")), "scan_hits": scan_hits(texts_of(frames, raw)),
            "repeated_messages": len(rep), "max_repeat": max(rep.values(), default=0)}


def selftest_luna() -> None:
    ok = 0
    assert P.call_low is luna_call; ok += 1
    fr = {"system": "Be kind.", "memory_header": "Before:", "line_prefix": "They said", "current_label": "Now:"}
    good = {"item_id": "s1", "ok": True, "session1": [{"text": "my dog Biscuit"}], "session2": [
        {"kind": k, "text": f"hi {k}"} for k in P.KINDS2]}
    assert not any(scan_hits(texts_of(fr, [good])).values()); ok += 1
    bad = dict(good, session1=[{"text": "Error: usage limit exceeded"}])
    h = scan_hits(texts_of(fr, [bad]))
    assert h["usage limit"] == 1 and h["error:"] == 1; ok += 1
    rows = [dict(good, item_id=f"c{i}", session2=[{"kind": "smalltalk", "text": "Hey again!"}]) for i in range(3)]
    assert repeats(rows) == {"hey again!": 3, "my dog biscuit": 3}; ok += 1
    assert repeats(rows[:2]) == {}; ok += 1
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        fp, rp = Path(td) / "fr.json", Path(td) / "raw.jsonl"
        fp.write_text(json.dumps(fr), encoding="utf-8")
        rp.write_text("".join(json.dumps(r) + "\n" for r in [good, dict(good, item_id="s2"),
                                                            {"item_id": "s3", "ok": False}]), encoding="utf-8")
        assert pilot(str(fp), str(rp))["pass"]; ok += 1
        rp.write_text("".join(json.dumps(r) + "\n" for r in [good, {"item_id": "s2", "ok": False},
                                                            {"item_id": "s3", "ok": False}]), encoding="utf-8")
        assert not pilot(str(fp), str(rp))["pass"]; ok += 1
        fp.write_text(json.dumps(dict(fr, current_label="")), encoding="utf-8")
        rp.write_text("".join(json.dumps(r) + "\n" for r in [good, dict(good, item_id="s2")]), encoding="utf-8")
        assert not pilot(str(fp), str(rp))["pass"]; ok += 1
    print(f"mu407 prep-luna selftest {ok}/8 ok")


def arg(name: str) -> str:
    return sys.argv[sys.argv.index(name) + 1]


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "selftest-luna":
        return selftest_luna()
    if cmd == "smokefacts":
        rows = [r for r in map(json.loads, Path(arg("--facts")).read_text(encoding="utf-8").splitlines())
                if r["smoke"]]
        Path(arg("--out")).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                      encoding="utf-8")
        print(json.dumps({"smoke_rows": len(rows)}))
        return
    if cmd == "pilot":
        res = pilot(arg("--frames"), arg("--raw"))
        print(json.dumps(res))
        raise SystemExit(0 if res["pass"] else 1)
    if cmd == "scan":
        print(json.dumps(scan(arg("--frames"), arg("--raw"))))
        return
    P.main()


if __name__ == "__main__":
    main()
