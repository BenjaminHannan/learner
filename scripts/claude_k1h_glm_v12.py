#!/usr/bin/env python3
"""k1h teacher jobs through GLM helper v1.1 with a time cap and a per-try log (Creative answers in chat thread,
2026-09-26; for k1h's resume job, sealed in a k1h addendum before any run uses it).

scripts/claude_k1h_glm_v11.py's route (the sealed scripts/claude_k1h_glm.py unchanged, its calls through
scripts/claude_glm_opencode_v11.py, at most 2 at once, 600 s a try) with two additions, both outside the prompts,
parsing and outputs:
- --cap-minutes N (required for chats): once N minutes have passed since this script started, no new opencode try
  starts; a call that would start one fails at once (run_chats keeps nothing from a failed call; run_answer writes an
  empty row that a later resume asks again). A try already running may still take up to 600 s, so the step ends at
  most about 10 minutes after its cap. run_chats has no time limit of its own (the Thread manager, 20:37 UTC: a 9 h
  worst case with no cap is not acceptable for a $0 Mac job that other jobs queue behind).
- one log line per opencode try on stderr, counts and labels only (never prompt or reply text):
    [k1h-try] n=<start order> start=<UTC hh:mm:ss> secs=<s> code=<exit code> kind=<ok|empty|exit-build|timeout|
    exit-other|capped> prompt_chars=<n>
  kind exit-build = a nonzero exit whose stderr holds opencode's "> build" line (lis-320 pilot 3's failure).
Session list and delete commands pass through unchanged and are not logged.
  python3 -B scripts/claude_k1h_glm_v12.py chats|answer ... --cap-minutes N   (claude_k1h_glm.py's other arguments)
  python3 -B scripts/claude_k1h_glm_v12.py selftest
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_k1h_glm as K          # noqa: E402
import claude_k1h_glm_v11 as W11    # noqa: E402

MAX_WORKERS = W11.MAX_WORKERS
TIMEOUT = W11.TIMEOUT
CAP_FLAG = "--cap-minutes"


class _State:
    deadline = None
    n = 0
    lock = threading.Lock()


def _kind(code, out, err, strip) -> str:
    if code == 0:
        return "ok" if strip(out) else "empty"
    if code == 124:
        return "timeout"
    return "exit-build" if "> build" in strip(err) else "exit-other"


def _log(n, start, secs, code, kind, chars, stream=None) -> None:
    stamp = time.strftime("%H:%M:%S", time.gmtime(start))
    print(f"[k1h-try] n={n} start={stamp} secs={secs:.1f} code={code} kind={kind} prompt_chars={chars}",
          file=stream or sys.stderr, flush=True)


def wrap_run(orig, strip, stream=None):
    """Wrap helper v1.1's _run_opencode: cap and log 'run' tries; pass other commands through."""
    def run(args, cwd, stdin_devnull=True, timeout=300):
        if not args or args[0] != "run":
            return orig(args, cwd, stdin_devnull=stdin_devnull, timeout=timeout)
        with _State.lock:
            _State.n += 1
            n = _State.n
        start, chars = time.time(), len(args[-1])
        if _State.deadline is not None and start > _State.deadline:
            _log(n, start, 0.0, 1, "capped", chars, stream)
            return 1, "", "k1h cap reached"
        code, out, err = orig(args, cwd, stdin_devnull=stdin_devnull, timeout=timeout)
        _log(n, start, time.time() - start, code, _kind(code, out, err, strip), chars, stream)
        return code, out, err
    return run


def take_cap(argv: list) -> tuple:
    """Remove --cap-minutes N from argv; return (argv, minutes or None)."""
    if CAP_FLAG not in argv:
        return argv, None
    i = argv.index(CAP_FLAG)
    minutes = float(argv[i + 1])
    if minutes <= 0:
        raise SystemExit("k1h-glm v1.2: --cap-minutes must be above 0")
    return argv[:i] + argv[i + 2:], minutes


def selftest() -> None:
    import io
    ok = 0
    strip = lambda s: (s or "").strip()                    # noqa: E731
    calls = []

    def fake(args, cwd, stdin_devnull=True, timeout=300):
        calls.append(args[0])
        if args[0] != "run":
            return 0, "[]", ""
        return {"a": (0, "Hello there.", ""), "b": (1, "", "> build · glm-5.3-flash"), "c": (124, "", "TIMEOUT"),
                "d": (0, "  ", ""), "e": (2, "", "other")}[args[-1]]
    buf = io.StringIO()
    run = wrap_run(fake, strip, buf)
    _State.deadline, _State.n = None, 0
    got = [run(["run", "--model", "m", p], cwd=".")[0] for p in "abcde"]
    assert got == [0, 1, 124, 0, 2], got
    kinds = [ln.split("kind=")[1].split()[0] for ln in buf.getvalue().splitlines()]
    assert kinds == ["ok", "exit-build", "timeout", "empty", "exit-other"], kinds
    assert "Hello" not in buf.getvalue() and "glm-5.3" not in buf.getvalue(), "log must hold no text"
    ok += 1
    buf2 = io.StringIO()
    run2 = wrap_run(fake, strip, buf2)
    n_before = len(calls)
    assert run2(["session", "list"], cwd=".")[0] == 0 and buf2.getvalue() == "", "session commands pass unlogged"
    _State.deadline = time.time() - 1
    assert run2(["run", "--model", "m", "a"], cwd=".") == (1, "", "k1h cap reached")
    assert calls[n_before:] == ["session"], "a capped try must not reach opencode"
    assert "kind=capped" in buf2.getvalue()
    _State.deadline = None
    ok += 1
    argv, m = take_cap(["x.py", "chats", "--out", "O", "--cap-minutes", "90", "--calls", "36"])
    assert argv == ["x.py", "chats", "--out", "O", "--calls", "36"] and m == 90.0, (argv, m)
    assert take_cap(["x.py", "answer"]) == (["x.py", "answer"], None)
    ok += 1
    print(f"k1h glm v1.2 selftest {ok}/3 ok")


def main() -> None:
    argv, minutes = take_cap(list(sys.argv))
    mode = argv[1:2]
    if mode == ["selftest"]:
        selftest()
        sys.argv = [argv[0], "selftest"]
        return W11.main()
    if mode == ["chats"] and minutes is None:
        raise SystemExit("k1h-glm v1.2: chats needs --cap-minutes (run_chats has no time limit of its own)")
    import claude_glm_opencode_v11 as G11
    if minutes is not None:
        _State.deadline = time.time() + 60 * minutes
    G11._run_opencode = wrap_run(G11._run_opencode, G11._strip_chrome)
    sys.argv = argv
    print(f"[k1h-glm v1.2] cap_minutes={minutes} workers<={MAX_WORKERS} try_timeout={TIMEOUT}", file=sys.stderr,
          flush=True)
    W11.main()


if __name__ == "__main__":
    main()
