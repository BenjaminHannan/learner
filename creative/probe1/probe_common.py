"""Shared bits for Probe-1 (see PREREG.md): paths, Pick-1 module loader, sandbox imports, task loader."""
import importlib.util, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CREATIVE = os.path.dirname(HERE)
P1, RL = os.path.join(CREATIVE, "pick1"), os.path.join(CREATIVE, "reach1", "rlaif_copy")
if RL not in sys.path:
    sys.path.insert(0, RL)
from sandbox import World, TOOLS  # noqa: E402
from checks import CHECK_KEYS, validate_check, run_check, run_checks  # noqa: E402

MNT = "/mnt/project-files/creative/"
DEFAULT_RESULTS = MNT + "guess1/out-seed2/guess1-seed2/run"   # holds IND/MENU and IND.s2/MENU.s2, as Pick-1 used
DEFAULT_POOLS = MNT + "pick1/pools.jsonl"
DEFAULT_K2 = MNT + "pick1/out/pick1/k2_scores.jsonl"
ARMS = ("IND", "IND.s2", "MENU", "MENU.s2")
N_TRIES, N_SAMPLES, TEMPERATURE, TOP_P = 12, 4, 0.7, 0.95
GATE = 0.99


def load_pick1(name):
    """Import creative/pick1/<name>.py under a private module name (its own `from common import *` finds pick1's common)."""
    sys.path.insert(0, P1)
    try:
        spec = importlib.util.spec_from_file_location(f"pick1_{name}", os.path.join(P1, name + ".py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    finally:
        sys.path.remove(P1)
        sys.modules.pop("common", None)
    return m


read_jsonl = load_pick1("common").read_jsonl


def load_tasks():
    d = os.path.join(RL, "data")
    return [json.loads(l) for f in ("tasks_train.jsonl", "tasks_heldout.jsonl") for l in open(os.path.join(d, f)) if l.strip()]


def target_ids(results_dir):
    return json.load(open(os.path.join(results_dir, "target.json")))["T"]
