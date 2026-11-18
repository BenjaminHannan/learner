"""Exploratory rescore generation for the 9216-update English endpoints (fast lane, not a sealed claim).
Runs the unchanged pilot eval generator on real fresh inputs; only ENDPOINT_UPDATE is changed to 9216."""
import argparse
import io
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eval_english_fresh_windows_v1 as ev  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--root', required=True)
ap.add_argument('--config', required=True)
ap.add_argument('--config-sha256', required=True)
a = ap.parse_args()
ev.ENDPOINT_UPDATE = 9216
sys.stdin = io.StringIO(ev.GO_LINE)
sys.exit(ev.run(argparse.Namespace(root=a.root, config=a.config, config_sha256=a.config_sha256,
                                   require_owned_stdin=True, check=False)))
