"""Exploratory fresh-eval generation for 9216-update endpoints whose seed-0 parent is a rebased skills checkpoint.
Same as eval_english_9216_v1.py plus --parent0-sha256, which overrides the pinned seed-0 parent sha."""
import argparse
import io
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import english_pilot_runtime_v1 as runtime  # noqa: E402
import eval_english_fresh_windows_v1 as ev  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True)
ap.add_argument('--config', required=True)
ap.add_argument('--config-sha256', required=True)
ap.add_argument('--parent0-sha256', required=True)
a = ap.parse_args()
runtime.PARENT_SHAS[0] = a.parent0_sha256
ev.ENDPOINT_UPDATE = 9216
sys.stdin = io.StringIO(ev.GO_LINE)
sys.exit(ev.run(argparse.Namespace(root=a.root, config=a.config, config_sha256=a.config_sha256,
                                   require_owned_stdin=True, check=False)))
