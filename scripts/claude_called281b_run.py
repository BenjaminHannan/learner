#!/usr/bin/env python3
"""Exp 281b dev runner: run dev dialogs through an agent daemon.

  dev <agent.py> <config> <workdir> <devcases.json> <out.json>
Fresh daemon per case. Daemon handling (Runner/send/trip) is reused
read-only from scripts/claude_openers260_run.py so both arms run
identically. Never scores.
"""

import json
import sys

sys.path.insert(0, "scripts")
import claude_openers260_run as R260  # noqa: E402 (read-only driver)


def main(argv):
    mode, agent, config, work, src, dst = argv[1:7]
    assert mode == "dev"
    r = R260.Runner(agent, config, work)
    cases = json.load(open(src))
    out = R260.run_dev(r, cases)
    json.dump(out, open(dst, "w"), indent=1)
    print(f"done {len(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
