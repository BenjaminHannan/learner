#!/usr/bin/env python3
"""k1h teacher jobs through GPT-6 Luna (Ben's Codex plan) instead of GLM (Creative answers in chat thread,
2026-09-27; k1h ADDENDUM-5). New file; the sealed scripts/claude_k1h_glm.py runs unchanged through it.

The one change is the teacher: claude_k1h_glm's calls go to scripts/claude_luna_codex.py call() (the Director's
helper, sha 342a0fb7..., model gpt-6-luna, selftest passed on the Mac 09-27). Same prompts (ANSWER with SYSTEM333D;
T.WRITE for chats), parsing, resume, failure stop and outputs; rows record model "gpt-6-luna". The helper refuses an
empty or error-like reply (looks_like_error: 3 tries, then RuntimeError); claude_k1h_glm then writes an empty row with
the error's type only (answer), or keeps nothing from the call (chats). An empty row is a route loss, not a grade.
No key and nothing under ~/.codex is read here.
Additions, all outside the prompts and parsing:
- --cap-minutes N (required for answer and chats): after N minutes no new Luna try starts (a try already running may
  add up to its timeout: 300 s for an answer, 600 s for a 20-chat call). answer's --max-minutes is set to N if absent.
- --workers: 1 unless given, at most 4 (claude_k1h_glm's own limit).
- one stderr line per Luna try, counts and labels only (never prompt, reply or error text):
    [k1h-luna-try] n=<start order> start=<UTC hh:mm:ss> secs=<s> kind=<ok|timeout|exit|errlike|capped|raised|other>
    code=<exit code or -> prompt_chars=<n>
- chats needs --chunk X (one lowercase letter): ids kh-NNNN become kl-XNNNN, so chunks run as separate commands never
  share an id, and each row gets "chat_writer": "luna". The other chats' writers are fixed by id prefix (WRITERS):
  kt- = GLM in k1e, kh- = GLM in k1h-glm2, kl- = Luna.
Offline modes (no network; fixed before any Luna answer is read):
  pilot-items  --items K1E_ITEMS --out P.jsonl
      40 of the k1e practice chats: sort the ids, shuffle with seed 4614, take the first 40.
  pilot-packet --items P.jsonl --answers FILTERED.jsonl --out DIR [--dev DEV_ITEMS]
      P1 (items with a non-empty answer after the route filter, need 36 of 40); P2 (answers the build's trim and
      guard333d keep, claude_k1h_train.filter_reason, need 34 of 40; check's DEV near-copy drop is a fact about the
      chat, not the answer, so it is counted beside P2, not in it); and the blind packet of every non-empty answer
      (DIR/pilot_packet.jsonl, ids L0000..., seed 4615; the same fields as gate 2's packet) with its key
      (DIR/pilot_key.json). Prints counts only.
  pilot-score  --items P.jsonl --key DIR/pilot_key.json --judges J1,J2[,J3] [--splits-out S.json]
      P3: useful on at least 32 of 40 and made_up_user_facts >= 1 on at most 2 of 40; an item with no packet line
      counts as not useful and not made up. Judge 3 decides the lines 1 and 2 split on, as in gate 2.
  split        --kept KEPT.jsonl [--key gate2_key.json --judges J1,J2,J3]
      gates 1 and 2 by chat writer (report only, the Thread manager 03:52 UTC).
  selftest
    python3 -B scripts/claude_k1h_luna.py answer --items P.jsonl --out DIR --cap-minutes 45 [--workers 1]
    python3 -B scripts/claude_k1h_luna.py chats --existing K1E_ITEMS --out DIR --calls 2 --chunk p --cap-minutes 20
"""
from __future__ import annotations

import json
import random
import re
import sys
import threading
import time
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_k1h_glm as K          # noqa: E402  (stdlib-only at import)
import claude_luna_codex as L       # noqa: E402  (stdlib-only at import; no call is made at import)

MAX_WORKERS = 4
TIMEOUTS = {"answer": 300, "chats": 600}
CAP_FLAG = "--cap-minutes"
WRITERS = {"kt-": "glm-k1e", "kh-": "glm-k1h", "kl-": "luna"}
PILOT_SEED, PILOT_N, PACKET_SEED = 4614, 40, 4615
P1_MIN, P2_MIN, P3_USEFUL, P3_MADEUP = 36, 34, 32, 2


class _State:
    deadline = None
    n = 0
    timeout = 300
    lock = threading.Lock()


def writer_of(item_id: str) -> str:
    return next((w for p, w in WRITERS.items() if item_id.startswith(p)), "unknown")


def load(p) -> list:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]


# ------------------------------------------------------------------ the Luna route: cap and per-try log
def _kind(reply, err: str) -> tuple:
    if reply is not None:
        return "ok", "0"
    if err.startswith("k1h cap reached"):
        return "capped", "-"
    if err.startswith("timeout"):
        return "timeout", "-"
    m = re.match(r"exit (-?\d+):", err)
    if m:
        return "exit", m.group(1)
    if err.startswith("error-like"):
        return "errlike", "0"
    return "other", "-"


def _log(n, start, secs, kind, code, chars, stream=None) -> None:
    stamp = time.strftime("%H:%M:%S", time.gmtime(start))
    print(f"[k1h-luna-try] n={n} start={stamp} secs={secs:.1f} kind={kind} code={code} prompt_chars={chars}",
          file=stream or sys.stderr, flush=True)


def wrap_once(orig, stream=None):
    """Wrap the helper's _once(text, model, timeout) -> (reply | None, err): cap and log each try."""
    def once(text, model, timeout):
        with _State.lock:
            _State.n += 1
            n = _State.n
        start, chars = time.time(), len(text)
        if _State.deadline is not None and start > _State.deadline:
            _log(n, start, 0.0, "capped", "-", chars, stream)
            return None, "k1h cap reached"
        try:
            reply, err = orig(text, model, timeout)
        except Exception:
            _log(n, start, time.time() - start, "raised", "-", chars, stream)
            raise
        kind, code = _kind(reply, err or "")
        _log(n, start, time.time() - start, kind, code, chars, stream)
        return reply, err
    return once


def luna_call(text: str) -> str:
    return L.call(text, model=L.MODEL, timeout=_State.timeout)


def take_flag(argv: list, flag: str) -> tuple:
    """Remove `flag VALUE` from argv; return (argv, value or None)."""
    if flag not in argv:
        return argv, None
    i = argv.index(flag)
    return argv[:i] + argv[i + 2:], argv[i + 1]


def rename_luna_chats(out_dir, chunk: str) -> int:
    p = Path(out_dir) / "chats.jsonl"
    if not p.exists():
        return 0
    rows = load(p)
    for r in rows:
        if r["item_id"].startswith("kh-"):
            r["item_id"] = f"kl-{chunk}" + r["item_id"][3:]
        r["chat_writer"] = "luna"
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return len(rows)


def run_route(argv: list) -> None:
    mode = argv[1]
    argv, cap = take_flag(argv, CAP_FLAG)
    argv, chunk = take_flag(argv, "--chunk")
    if cap is None:
        raise SystemExit(f"k1h-luna: {mode} needs --cap-minutes")
    if mode == "chats" and not (chunk and re.fullmatch(r"[a-z]", chunk)):
        raise SystemExit("k1h-luna: chats needs --chunk X (one lowercase letter)")
    minutes = float(cap)
    if minutes <= 0:
        raise SystemExit("k1h-luna: --cap-minutes must be above 0")
    if "--workers" in argv:
        if int(argv[argv.index("--workers") + 1]) > MAX_WORKERS:
            raise SystemExit(f"k1h-luna: at most {MAX_WORKERS} calls at once")
    else:
        argv += ["--workers", "1"]
    if mode == "answer" and "--max-minutes" not in argv:
        argv += ["--max-minutes", str(minutes)]
    _State.deadline = time.time() + 60 * minutes
    _State.timeout = TIMEOUTS[mode]
    L._once = wrap_once(L._once)
    K.MODEL = L.MODEL
    K._call = luna_call
    print(f"[k1h-luna] mode={mode} model={L.MODEL} cap_minutes={minutes} try_timeout={_State.timeout} "
          f"workers={argv[argv.index('--workers') + 1]}", file=sys.stderr, flush=True)
    sys.argv = argv
    K.main()
    if mode == "chats":
        n = rename_luna_chats(argv[argv.index("--out") + 1], chunk)
        print(json.dumps({"luna_chats_renamed": n}), flush=True)


# ------------------------------------------------------------------ offline: the pilot and the split report
def pilot_items(items_path: str, out: str) -> list:
    rows = load(items_path)
    by_id = {r["item_id"]: r for r in rows}
    if len(by_id) != len(rows):
        raise SystemExit("k1h-luna: duplicate item ids")
    ids = sorted(by_id)
    random.Random(PILOT_SEED).shuffle(ids)
    pick = ids[:PILOT_N]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("".join(json.dumps(by_id[i], ensure_ascii=False) + "\n" for i in pick), encoding="utf-8")
    print(json.dumps({"from": len(rows), "picked": len(pick), "seed": PILOT_SEED}))
    return pick


def last_answers(answers_path: str) -> dict:
    ans = {}
    for r in load(answers_path):
        if r.get("answer"):
            ans[r["item_id"]] = r["answer"]              # as in check: the last non-empty answer wins
    return ans


def pilot_packet(items_path: str, answers_path: str, out: str, dev_path: str = "") -> dict:
    import claude_k1h_train as TR
    items = {r["item_id"]: r for r in load(items_path)}
    ans = {i: a for i, a in last_answers(answers_path).items() if i in items and a.strip()}
    why = Counter(TR.filter_reason(ans.get(i, ""), items[i]) or "kept" for i in sorted(items))
    dev_reqs = [r["last"] for r in load(dev_path)] if dev_path else []
    near = sum(1 for it in items.values() if dev_reqs and TR.near_copy(it["last"], dev_reqs))
    ids = sorted(ans)
    random.Random(PACKET_SEED).shuffle(ids)
    d = Path(out)
    d.mkdir(parents=True, exist_ok=True)
    key = {}
    with open(d / "pilot_packet.jsonl", "w", encoding="utf-8") as fh:
        for n, iid in enumerate(ids):
            it = items[iid]
            key[f"L{n:04d}"] = iid
            fh.write(json.dumps({"id": f"L{n:04d}", "chat": it["turns"], "request": it["last"],
                                 "reply": ans[iid].strip()}, ensure_ascii=False) + "\n")
    (d / "pilot_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    res = {"items": len(items), "nonempty_items": len(ans), "p1_need": P1_MIN,
           "p1_pass": len(items) == PILOT_N and len(ans) >= P1_MIN, "p2_kept": why["kept"], "p2_need": P2_MIN,
           "p2_pass": len(items) == PILOT_N and why["kept"] >= P2_MIN, "p2_reasons": dict(why),
           "near_copy_dev_chats": near if dev_path else None, "packet_lines": len(key)}
    print(json.dumps(res))
    return res


def _verdicts(key: dict, judges: str, splits_out: str = ""):
    """Per line (useful, made_up>=1), judge 3 on the lines judges 1 and 2 split on; None if judge 3 is still needed."""
    import claude_k1c_score as KC
    js = KC._judges(judges)
    j1, j2 = js[0], js[1]
    if any(c not in j1 or c not in j2 for c in key):
        raise SystemExit("k1h-luna: ids missing from judge 1 or 2")
    split = sorted(c for c in key if KC.yes(j1[c]["useful"]) != KC.yes(j2[c]["useful"])
                   or KC.madeup(j1[c]) != KC.madeup(j2[c]))
    if len(js) < 3:
        if splits_out:
            Path(splits_out).write_text(json.dumps(split), encoding="utf-8")
        return None, split
    j3 = js[2]
    if any(c not in j3 for c in split):
        raise SystemExit("k1h-luna: split ids missing from judge 3")
    out = {}
    for c in key:
        u1, u2, m1, m2 = KC.yes(j1[c]["useful"]), KC.yes(j2[c]["useful"]), KC.madeup(j1[c]), KC.madeup(j2[c])
        out[c] = (bool(u1 if u1 == u2 else KC.yes(j3[c]["useful"])), bool(m1 if m1 == m2 else KC.madeup(j3[c])))
    return out, split


def pilot_score(items_path: str, key_path: str, judges: str, splits_out: str = "") -> dict | None:
    n_items = len(load(items_path))
    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    v, split = _verdicts(key, judges, splits_out)
    if v is None:
        print(json.dumps({"lines": len(key), "need_third": len(split)}))
        return None
    u = sum(1 for c in key if v[c][0])
    m = sum(1 for c in key if v[c][1])
    res = {"items": n_items, "lines": len(key), "third_judged": len(split), "useful": u, "madeup": m,
           "need_useful": P3_USEFUL, "max_madeup": P3_MADEUP,
           "pass": n_items == PILOT_N and u >= P3_USEFUL and m <= P3_MADEUP}
    print(json.dumps(res))
    return res


def split_report(kept_path: str, key_path: str = "", judges: str = "") -> dict:
    import claude_k1h_train as TR
    kept = load(kept_path)
    by_w: dict = {}
    for k in kept:
        by_w.setdefault(writer_of(k["item_id"]), []).append(k["answer"])
    res = {"gate1_by_writer": {w: {kk: g[kk] for kk in ("answers", "top_opening_share", "top_sentence_count",
                                                        "top_sentence_share", "pass")}
                               for w, g in ((w, TR.gate1(a)) for w, a in sorted(by_w.items()))}}
    if key_path and judges:
        key = json.loads(Path(key_path).read_text(encoding="utf-8"))
        v, _ = _verdicts(key, judges)
        if v is not None:
            g2: dict = {}
            for c, iid in key.items():
                s = g2.setdefault(writer_of(iid), Counter())
                s["lines"] += 1
                s["useful"] += v[c][0]
                s["madeup"] += v[c][1]
            res["gate2_by_writer"] = {w: dict(s) for w, s in sorted(g2.items())}
    print(json.dumps(res))
    return res


# ------------------------------------------------------------------ selftest (no network)
def selftest() -> None:
    import argparse
    import io
    import tempfile
    ok = 0
    # 1. labels, no text in the log
    buf = io.StringIO()
    fakes = {"a": ("A toast to Wren!", ""), "b": (None, "timeout after 300s"), "c": (None, "exit 1: SECRETSTDERR"),
             "d": (None, "error-like or empty reply: 'Usage limit HIDDENREPLY'"), "e": (None, "weird")}

    def fake_once(text, model, timeout):
        if text == "boom":
            raise OSError("no codex")
        return fakes[text]
    once = wrap_once(fake_once, buf)
    _State.deadline, _State.n = None, 0
    got = [once(t, "gpt-6-luna", 300)[0] for t in "abcde"]
    assert got == ["A toast to Wren!", None, None, None, None], got
    try:
        once("boom", "m", 1)
        raise AssertionError("an exception must pass through")
    except OSError:
        pass
    lines = buf.getvalue().splitlines()
    kinds = [ln.split("kind=")[1].split()[0] for ln in lines]
    codes = [ln.split("code=")[1].split()[0] for ln in lines]
    assert kinds == ["ok", "timeout", "exit", "errlike", "other", "raised"], kinds
    assert codes == ["0", "-", "1", "0", "-", "-"], codes
    for bad in ("Wren", "SECRET", "HIDDEN", "Usage", "codex"):
        assert bad not in buf.getvalue(), f"log must hold no text ({bad})"
    ok += 1
    # 2. the cap: a capped try never reaches the route, and call() raises after 3 capped tries
    reached = []

    def fake_once2(text, model, timeout):
        reached.append(text)
        return "Here you go.", ""
    buf2 = io.StringIO()
    real_once = L._once
    L._once = wrap_once(fake_once2, buf2)
    try:
        _State.deadline = None
        assert L.call("x") == "Here you go." and reached == ["x"]
        _State.deadline = time.time() - 1
        try:
            L.call("y")
            raise AssertionError("a capped call must raise")
        except RuntimeError:
            pass
        assert reached == ["x"], "a capped try must not reach the route"
        assert buf2.getvalue().count("kind=capped") == 3
    finally:
        L._once = real_once
        _State.deadline = None
    ok += 1
    # 3. answer through the sealed run_answer: model id, a refused call is an empty row with the type only
    with tempfile.TemporaryDirectory() as d:
        it = {"item_id": "kt-001", "kind": "uses_facts", "turns": ["My sister Wren loves sailing."],
              "last": "a card for her?", "facts": []}
        src = Path(d) / "p.jsonl"
        src.write_text("".join(json.dumps(dict(it, item_id=f"kt-00{i}")) + "\n" for i in range(3)), encoding="utf-8")
        n_calls = []

        def fake_once3(text, model, timeout):
            n_calls.append(model)
            if len(n_calls) in (2, 3, 4):
                return None, "error-like or empty reply: 'quota exceeded HIDDENREPLY'"
            return "Fair winds, Wren! Happy sailing.", ""
        buf3 = io.StringIO()
        real_once, real_model, real_call = L._once, K.MODEL, K._call
        L._once, K.MODEL, K._call = wrap_once(fake_once3, buf3), L.MODEL, luna_call
        try:
            s = K.run_answer(argparse.Namespace(items=[str(src)], out=d, workers=1, max_minutes=5))
        finally:
            L._once, K.MODEL, K._call = real_once, real_model, real_call
        rows = load(Path(d) / "answers.jsonl")
        assert s["answered"] == 2 and s["failed"] == 1, s
        assert all(r["model"] == "gpt-6-luna" for r in rows) and set(n_calls) == {"gpt-6-luna"}
        assert [r.get("error") for r in rows if not r["answer"]] == ["RuntimeError"]
        assert "HIDDEN" not in (Path(d) / "answers.jsonl").read_text() + buf3.getvalue()
        ok += 1
        # 4. chats: the sealed run_chats, then kh- -> kl- and chat_writer
        good = {"kind": "idea", "turns": [], "last": "3 names for a book club?", "facts": []}
        real_call = K._call
        K._call = lambda t: json.dumps([good])
        try:
            K.run_chats(argparse.Namespace(existing=None, out=d, calls=1, workers=1))
        finally:
            K._call = real_call
        assert rename_luna_chats(d, "p") == 1
        c = load(Path(d) / "chats.jsonl")[0]
        assert c["item_id"] == "kl-p0001" and c["chat_writer"] == "luna" and writer_of(c["item_id"]) == "luna"
        assert writer_of("kt-001") == "glm-k1e" and writer_of("kh-0001") == "glm-k1h" and writer_of("x") == "unknown"
        ok += 1
        # 5. pilot items: the rule, and deterministic
        allp = Path(d) / "all.jsonl"
        allp.write_text("".join(json.dumps(dict(it, item_id=f"kt-{i:03d}")) + "\n" for i in range(240, 0, -1)),
                        encoding="utf-8")
        pick = pilot_items(str(allp), str(Path(d) / "pi.jsonl"))
        ids = sorted(f"kt-{i:03d}" for i in range(1, 241))
        random.Random(4614).shuffle(ids)
        assert pick == ids[:40] and len(set(pick)) == 40
        assert [r["item_id"] for r in load(Path(d) / "pi.jsonl")] == pick
        ok += 1
        # 6. pilot packet and score: empty answers count as not useful; judge 3 on splits
        pi = str(Path(d) / "pi.jsonl")
        ans = [{"item_id": i, "answer": ("" if n < 3 else f"Reply {n}.")} for n, i in enumerate(pick)]
        ans.append({"item_id": pick[0], "answer": "A later reply."})     # a resumed item: the last non-empty wins
        ap_ = Path(d) / "ans.jsonl"
        ap_.write_text("".join(json.dumps(r) + "\n" for r in ans), encoding="utf-8")
        r = pilot_packet(pi, str(ap_), str(Path(d) / "pk"))
        assert r["nonempty_items"] == 38 and r["packet_lines"] == 38 and r["p1_pass"], r
        assert r["p2_kept"] == 38 and r["p2_reasons"] == {"kept": 38, "empty": 2} and r["p2_pass"], r
        ap2 = Path(d) / "ans2.jsonl"                     # text after the last end mark -> trim changes it -> dropped
        ap2.write_text("".join(json.dumps({"item_id": i, "answer": "Reply. And" if n < 5 else "Reply."}) + "\n"
                               for n, i in enumerate(pick)), encoding="utf-8")
        devp = Path(d) / "dev.jsonl"
        devp.write_text(json.dumps({"last": it["last"]}) + "\n", encoding="utf-8")
        r2 = pilot_packet(pi, str(ap2), str(Path(d) / "pk2"), str(devp))
        assert r2["p2_kept"] == 35 and r2["p2_reasons"].get("trim") == 5 and r2["p2_pass"], r2
        assert r2["near_copy_dev_chats"] == 40 and r2["p1_pass"], r2
        key = json.loads((Path(d) / "pk" / "pilot_key.json").read_text())
        pk = load(Path(d) / "pk" / "pilot_packet.jsonl")
        assert sorted(key.values()) == sorted(set(pick) - {pick[1], pick[2]})
        assert set(pk[0]) == {"id", "chat", "request", "reply"} and "Reply" not in json.dumps(r)
        lines = sorted(key)
        j1 = [{"id": c, "useful": "yes", "made_up_user_facts": 0} for c in lines]
        j2 = [dict(x) for x in j1]
        for x in j2[:5]:
            x["useful"] = "no"                                           # 5 split lines
        j2[5]["made_up_user_facts"] = 2                                  # 1 split line
        j3 = [{"id": c, "useful": "no", "made_up_user_facts": 1} for c in lines[:6]]
        for n_, rows_ in (("j1", j1), ("j2", j2), ("j3", j3)):
            (Path(d) / f"{n_}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows_), encoding="utf-8")
        J = lambda *n: ",".join(str(Path(d) / f"{x}.jsonl") for x in n)   # noqa: E731
        assert pilot_score(pi, str(Path(d) / "pk" / "pilot_key.json"), J("j1", "j2")) is None
        s = pilot_score(pi, str(Path(d) / "pk" / "pilot_key.json"), J("j1", "j2", "j3"))
        # 38 lines: 5 split on useful (judge 3: no), 1 split on made-up (judge 3: yes); 2 empty items not useful
        assert s["useful"] == 33 and s["madeup"] == 1 and s["third_judged"] == 6 and s["pass"], s
        j3b = [dict(x, useful="no") for x in j1[:6]] + [{"id": lines[6], "useful": "no", "made_up_user_facts": 0}]
        j2b = [dict(x, useful="no") if i < 7 else x for i, x in enumerate(j1)]
        for n_, rows_ in (("j2b", j2b), ("j3b", j3b)):
            (Path(d) / f"{n_}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows_), encoding="utf-8")
        s = pilot_score(pi, str(Path(d) / "pk" / "pilot_key.json"), J("j1", "j2b", "j3b"))
        assert s["useful"] == 31 and s["madeup"] == 0 and not s["pass"], s          # 31 of 40 fails P3
        ok += 1
        # 7. the split report by chat writer
        kept = Path(d) / "kept.jsonl"
        kept.write_text("".join(json.dumps({"item_id": iid, "answer": a}) + "\n" for iid, a in
                                (("kt-001", "Nice one."), ("kl-0001", "Great idea."), ("kl-0002", "Great idea."))),
                        encoding="utf-8")
        g2key = Path(d) / "g2key.json"
        g2key.write_text(json.dumps({lines[0]: "kt-001", lines[1]: "kl-0001"}), encoding="utf-8")
        rep = split_report(str(kept), str(g2key), J("j1", "j2", "j3"))
        assert rep["gate1_by_writer"]["luna"]["answers"] == 2 and rep["gate1_by_writer"]["glm-k1e"]["answers"] == 1
        assert rep["gate2_by_writer"] == {"glm-k1e": {"lines": 1, "useful": 0, "madeup": 0},
                                          "luna": {"lines": 1, "useful": 0, "madeup": 0}}, rep
        ok += 1
    # 8. argument handling
    a, v = take_flag(["x.py", "answer", "--cap-minutes", "45", "--out", "O"], CAP_FLAG)
    assert a == ["x.py", "answer", "--out", "O"] and v == "45"
    try:
        run_route(["x.py", "answer", "--out", "O"])
        raise AssertionError("answer must need --cap-minutes")
    except SystemExit as e:
        assert "cap-minutes" in str(e)
    try:
        run_route(["x.py", "answer", "--out", "O", "--cap-minutes", "5", "--workers", "5"])
        raise AssertionError("more than 4 workers must be refused")
    except SystemExit as e:
        assert "at most" in str(e)
    try:
        run_route(["x.py", "chats", "--out", "O", "--cap-minutes", "5"])
        raise AssertionError("chats must need --chunk")
    except SystemExit as e:
        assert "--chunk" in str(e)
    assert L._once is real_once, "a refused run must not patch the route"
    ok += 1
    print(f"k1h luna selftest {ok}/8 ok")


def main() -> None:
    argv = list(sys.argv)
    mode = argv[1] if len(argv) > 1 else ""
    if mode in ("answer", "chats"):
        return run_route(argv)
    if mode == "selftest":
        return selftest()
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["pilot-items", "pilot-packet", "pilot-score", "split"])
    ap.add_argument("--items")
    ap.add_argument("--answers")
    ap.add_argument("--out")
    ap.add_argument("--key", default="")
    ap.add_argument("--judges", default="")
    ap.add_argument("--splits-out", default="")
    ap.add_argument("--kept")
    ap.add_argument("--dev", default="")
    a = ap.parse_args()
    if a.mode == "pilot-items":
        pilot_items(a.items, a.out)
    elif a.mode == "pilot-packet":
        pilot_packet(a.items, a.answers, a.out, a.dev)
    elif a.mode == "pilot-score":
        pilot_score(a.items, a.key, a.judges, a.splits_out)
    else:
        split_report(a.kept, a.key, a.judges)


if __name__ == "__main__":
    main()
