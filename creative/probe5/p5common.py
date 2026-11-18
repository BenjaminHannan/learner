"""Shared bits for Probe-5 (PREREG.md): path setup so the Probe-4 / Probe-3 / Probe-1 modules can be imported, server arguments, pause flag, seeds.
Nothing here needs torch, mlx or a model."""
import os, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
CREATIVE = os.path.dirname(HERE)
P4DIR = os.path.join(CREATIVE, "probe4")
for _p in (HERE, P4DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import p4common as P  # noqa: E402  (also puts probe1 and probe3/mlx on sys.path)

EXIT_PAUSED = 75                      # "paused, rerun the same command to resume" (same code as Probe-3 / Probe-4)
DEFAULT_URL = "http://127.0.0.1:8080"
LORA_ID = 0                           # the one adapter given to llama-server with --lora
TASKS = P.TASKS_NEW                   # the 96 frozen tasks
SAMPLING = dict(P.SAMPLING)           # T 0.7, top_p 0.95, max_tokens 512 (as Probe-4)
TEST_SAMPLING = dict(temperature=0.7, top_p=0.95, max_tokens=768)   # write_probes / gen_mlx settings
N_SAMPLES = 4


def seed_for(*parts):
    """Deterministic per-request seed (a resumed run asks the server for the same randomness)."""
    return zlib.crc32(("probe5|" + "|".join(str(p) for p in parts)).encode()) % 2**31


def flag_path():
    return os.environ.get("ASSISTANT_FLAG") or os.path.join(os.path.expanduser("~"), "learner-ops", "ASSISTANT_RUNNING")


def assistant_running():
    """The assistant (Ben's daily-driver model server) needs the RAM: a file ~/learner-ops/ASSISTANT_RUNNING exists."""
    return os.path.exists(flag_path())


def add_server_args(ap):
    ap.add_argument("--url", default=os.environ.get("LLAMA_URL", DEFAULT_URL), help="llama-server base URL")
    ap.add_argument("--parallel", type=int, default=4, help="requests in flight (match llama-server -np)")
    ap.add_argument("--timeout", type=float, default=900.0)
    ap.add_argument("--no-pause-flag", action="store_true", help="ignore ASSISTANT_RUNNING")


def make_client(a):
    from llm_server import LlamaServer
    return LlamaServer(a.url, timeout=a.timeout, lora_id=LORA_ID)


def read_jsonl(path):
    return P.read_jsonl(path) if os.path.exists(path) else []


def atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)
