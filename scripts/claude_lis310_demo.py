#!/usr/bin/env python3
"""lis-310 chat demo: talk to the 310 agent (291 + listener) via a mailbox.

A copy of how scripts/claude_chatdemo_server.py builds its agent
(load_agent -> base config -> make_daemon -> process_file over
inbox/mNNNN.txt -> outbox/mNNNN.txt), pointed at build_agent310
(scripts/claude_lis310_agent.py) with a model-dir argument for the real
lis-300 weights. Give --reader-stub for a weight-free smoke run.

  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/claude_lis310_demo.py --model ~/premonition-models/lis300-merged \
    --state /tmp/lis310demo --once "My sister is Mira."

New file only; the server itself is not edited.
"""

from __future__ import annotations

import argparse
import copy
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

AGENT_FILE = str(HERE / "claude_lis310_agent.py")
_DEPS = Path(tempfile.gettempdir()) / "lis310deps"


def ensure_deps() -> None:
    """Copies of frozen lis-300 modules (local git objects only, no network;
    never checks out, merges or pushes any branch)."""
    if str(_DEPS / "scripts") in sys.path:
        return
    (_DEPS / "scripts").mkdir(parents=True, exist_ok=True)
    (_DEPS / "design" / "v3" / "60-listener").mkdir(parents=True,
                                                   exist_ok=True)
    jobs = {"scripts/claude_lis300_common.py":
            _DEPS / "scripts" / "claude_lis300_common.py",
            "scripts/claude_lis300_compiler.py":
            _DEPS / "scripts" / "claude_lis300_compiler.py",
            "design/v3/60-listener/relation-names.txt":
            _DEPS / "design" / "v3" / "60-listener" / "relation-names.txt"}
    for src, dst in jobs.items():
        if not dst.exists():
            r = subprocess.run(["git", "-C", str(WORKTREE), "show",
                                "origin/main:" + src],
                               capture_output=True, timeout=60)
            if r.returncode != 0:
                raise RuntimeError("cannot extract " + src)
            dst.write_bytes(r.stdout)
    sys.path.insert(0, str(_DEPS / "scripts"))


def build_demo(model_dir=None, reader=None, state_dir=None, threshold=0.99):
    """Server-style build: load_agent(AGENT) + base config + make_daemon."""
    ensure_deps()
    import fable_marks123_all as M  # noqa: E402

    _mod, dcls, _build_fn, default_cfg = M.load_agent(AGENT_FILE)
    base = copy.deepcopy(default_cfg)
    base["lis310"] = {"model_dir": model_dir, "threshold": threshold,
                      "reader": reader}
    root = Path(state_dir or tempfile.mkdtemp(prefix="lis310demo_"))
    return M.make_daemon(dcls, base, root)


def do_turn(daemon, root, text: str) -> str:
    n = 0
    for sub in ("inbox", "outbox", "done"):
        for p in (Path(root) / sub).glob("m*.txt"):
            try:
                n = max(n, int(p.stem[1:]) + 1)
            except ValueError:
                pass
    name = "m%04d.txt" % n
    ipath = Path(root) / "inbox" / name
    ipath.parent.mkdir(parents=True, exist_ok=True)
    ipath.write_text(text, encoding="utf-8")
    daemon.process_file(ipath)
    return (Path(root) / "outbox" / name).read_text(
        encoding="utf-8").strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="lis-310 chat demo (mailbox)")
    ap.add_argument("--model", default=None,
                    help="lis-300 merged model dir (real weights)")
    ap.add_argument("--state", default=None)
    ap.add_argument("--threshold", type=float, default=0.99)
    ap.add_argument("--once", default=None)
    ap.add_argument("--reader-stub", action="store_true",
                    help="weight-free smoke run (CHAT everything)")
    args = ap.parse_args(argv)
    reader = None
    if args.reader_stub:
        class _Stub:
            def read(self, turn, prev_reply=""):
                return ({"act": "CHAT", "facts": [], "ask": None}, [],
                        "stub", 0.0)

        reader = _Stub()
    if args.model is None and reader is None:
        ap.error("--model DIR or --reader-stub is required")
    daemon = build_demo(model_dir=args.model, reader=reader,
                        state_dir=args.state, threshold=args.threshold)
    root = daemon.dir if hasattr(daemon, "dir") else Path(args.state)
    if args.once is not None:
        print(do_turn(daemon, root, args.once), flush=True)
        return 0
    print("lis-310 demo ready (state %s). Ctrl-D to stop." % root,
          flush=True)
    for line in sys.stdin:
        line = line.strip()
        if line:
            print(do_turn(daemon, root, line), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
