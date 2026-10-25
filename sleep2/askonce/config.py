"""Constants for the Ask-once test harness. No torch, no network. Everything that must be identical across arms lives here."""
import hashlib
import json
import math
import os
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("ASKONCE_DATA", ROOT / "data"))
MODEL_ID = "IFM/K2-Horizon-3.7B"
SONNET = "claude-sonnet-5-5"
HAIKU = "claude-haiku-5-5"
KEY_ENV = "LEARNER_ANTHROPIC_API_KEY"
# $ per million tokens, standard price; Batches API is 50% of this (claude-api skill table, 2026-10)
PRICES = {SONNET: (2.0, 10.0), HAIKU: (0.10, 0.50)}
BATCH_DISCOUNT = 0.5

# --- world size (prereg). ASKONCE_SCALE shrinks every day, split and eval set by the same factor in every arm.
DAYS_TRAIN = 5
PER_DAY = 40
N_SLOTS = 60
N_FACTS = 40
KINDS = {"contact": 22, "meeting": 10, "duration": 6, "file": 12, "mode": 10}
SPLIT_NEW = {"contact": 7, "meeting": 3, "duration": 2, "file": 4, "mode": 4}  # 20 held-out new-ambiguity slots
SILENT_N = 5  # training slots that sim-Ben never corrects
EVAL_H = {"H_know": 80, "H_new": 80, "H_full": 40}
EVAL_R = {"R_new": 30, "R_know": 70, "R_full": 100}
N_SILENT_ITEMS = 20
N_GENERAL = 100
N_ANCHOR = 100
N_ARC = 500
SEED_WORLD = 20260925  # world / data generation seed (fixed; not the arm seeds)


def scale():
    return float(os.environ.get("ASKONCE_SCALE", "1.0"))


def shrink(items, scale_=None):
    """Keep the first ceil(scale*n) items of an already stratified/shuffled list (same factor for every arm)."""
    s = scale() if scale_ is None else scale_
    if s >= 0.999:
        return list(items)
    return list(items)[: max(1, math.ceil(len(items) * s))]


def night_scale():
    """Shrinks the nightly training data (shared part, tagged events and therefore the slice) by the same factor in EVERY arm: the prereg's
    'cut dream and re-read counts equally if a night takes more than 9 min'. Applied by build_night_data."""
    return float(os.environ.get("ASKONCE_NIGHT_SCALE", "1.0"))


def n_nights():
    return int(os.environ.get("ASKONCE_NIGHTS", DAYS_TRAIN))


# --- prompts (fixed strings; served identically in every arm)
RULE = "If a required detail is missing and not in memory, ask one short question naming it."
SYSTEM = (
    "You are Ben's email, calendar and files assistant. Reply with exactly one line, either\n"
    "ACT {\"tool\": NAME, \"args\": {...}}   to run a tool, or\n"
    "ASK <one short question>   to ask Ben.\n"
    "Tools: send_email(to), draft_email(to), create_event(attendees, duration_min), move_event(event_id), "
    "open_file(path), share_file(path, with). attendees is a list; duration_min is a number; all other args are strings.\n"
    "Rule: " + RULE + "\n"
    "Example: Request: Email Dr Wu at wu@clinic.example the test results.\n"
    "ACT {\"tool\": \"send_email\", \"args\": {\"to\": \"wu@clinic.example\"}}\n"
    "Example: Request: Open the budget sheet. [Lookup: 1) /docs/budget_2025.xlsx 2) /docs/budget_old.xlsx; memory empty]\n"
    "ASK Which budget sheet do you mean: /docs/budget_2025.xlsx or /docs/budget_old.xlsx?"
)
GENERAL_SYSTEM = "You are a helpful assistant. " + RULE
ANNOY_PREFIX = ["Obviously. ", "I already told you. ", "Just do it. "]
FULLSPEC_REPLY = ["It is right there in my message: {lits}. Just do it.", "Obviously {lits}, I wrote it in the request.", "It is in my request already ({lits}). Just do it."]
CORR_PREFIX = ["No, ", "That's wrong. ", "Not that one. ", "", ""]
MEM_MAX_TOKENS = 150
MEM_TOPK = 3
FACT_Q_MAX_NEW = 16
ACT_MAX_NEW = 72
SPLIT_FOR_DAY = {"train": None, "H_know": 6, "H_new": 6, "H_full": 6, "R_new": 7, "R_know": 7, "R_full": 7, "silent": 7}

# --- night training (shared by all trained arms)
LORA_R = 16
LORA_ALPHA = 32
LORA_TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
BETA = 0.1
LR = float(os.environ.get("ASKONCE_LR", "1e-4"))
ANCHOR_W = 0.1
SLICE_FRAC = 0.15
LEDGER_TOL = 0.05
# askonce-v2: share of ASK among the shared night's action examples (ASK + corrected ACT + correct ACT-on-known). Base model K2 asked on 14/80 H_new (17.5%) and 20% of knowable items.
ASK_SHARE = 0.20
MAX_SEQ = 1024
CHUNK = 512


def night_opt_steps():
    return int(os.environ.get("ASKONCE_OPT_STEPS", "30"))


def norm(s):
    return unicodedata.normalize("NFKC", str(s)).strip().lower()


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def jl_read(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def jl_write(p, rows):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")


def jdump(p, o):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(o, ensure_ascii=False, indent=1, sort_keys=True))


def jload(p):
    return json.loads(Path(p).read_text())
