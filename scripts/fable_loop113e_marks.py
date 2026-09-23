#!/usr/bin/env python3
"""Experiment 113e marks: P2 + P3 + P4 vs loop113e (113d-harness reuse).

Reuse of scripts/fable_loop113d_marks.py by import with class swap (as the
exp-113e brief allows): the agent module (L113D -> loop113e), the spawned
agent script path (PY113D -> fable_loop113e_agent.py), and the artifact
directory (ART -> the exp-113e regression dir). Report filenames and the
hardcoded "loop113d" mark labels are renamed to loop113e after the run
(own artifact dir). KNOWN LIMITATION (documented, not edited: the 113d file
is read-only): run_p2's kill-9 burst spawns its daemon from an inline
hardcoded `SCRIPTS / "fable_loop113d_agent.py"` path, so that one spawned
process is loop113d, not loop113e; every in-process daemon (P2 cases, P4,
P3 via PY113D swap) is loop113e. The registered E4 bar itself is measured
with scripts/fable_marks123_all.py --agent/--config (see PASSMARKS.md); this
harness is supplementary comparability with exp 113d's D2.

Run (Mac CPU, offline; only AFTER PASSMARKS are sealed):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    python -B scripts/fable_loop113e_marks.py --mark all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_loop113d_marks as M113D  # noqa: E402 (harness, read-only)
import fable_loop113e_agent as L113E  # noqa: E402 (this experiment's agent)

ROOT = SCRIPTS.parent
ART = ROOT / "artifacts" / "fable-bench113e-20260922" / "regression"

# The class swap. Note the 113d harness looks up Loop113dDaemon /
# build_agent113d / DEFAULT_CONFIG113D on the (swapped) agent module, so
# compatibility aliases point at the 113e objects (this wrapper only; the
# agent module itself keeps clean 113e names).
L113E.Loop113dDaemon = L113E.Loop113eDaemon
L113E.build_agent113d = L113E.build_agent113e
L113E.DEFAULT_CONFIG113D = copy.deepcopy(L113E.DEFAULT_CONFIG113E)
M113D.L113D = L113E
M113D.PY113D = [sys.executable, "-B",
                str(SCRIPTS / "fable_loop113e_agent.py")]
M113D.ART = ART


def _relabel_tree(root: Path) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix == ".json":
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, ValueError):
                continue
            new = (text.replace("loop113d", "loop113e")
                       .replace("Loop113d", "Loop113e")
                       .replace("fable_loop113d_", "fable_loop113e_")
                       .replace("fable_bench113d_", "fable_bench113e_"))
            if new != text:
                path.write_text(new, encoding="utf-8")
    for path in sorted(root.rglob("*113d*")):
        target = Path(str(path).replace("113d", "113e"))
        if path != target and not target.exists():
            path.rename(target)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exp 113e marks vs loop113e")
    parser.add_argument("--mark", default="all",
                        choices=("p2", "p3", "l1", "l2", "l3", "l4", "l5z1",
                                 "l5z2", "l6", "p4", "all"))
    parser.add_argument("--out", default=str(ART))
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ret = M113D.main(["--mark", args.mark, "--out", str(out)])
    _relabel_tree(out)
    print(f"reports under {out} relabelled loop113d->loop113e")
    return ret


if __name__ == "__main__":
    sys.exit(main())
