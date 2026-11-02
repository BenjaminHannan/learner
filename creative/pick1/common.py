"""Shared bits for Pick-1 (see PREREG.md): load Guess-1 helpers, judge prompt, small utils."""
import importlib.util, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
G1 = os.path.join(os.path.dirname(HERE), "guess1")
DEFAULT_RESULTS = "/mnt/project-files/creative/guess1/out-seed2/guess1-seed2/run"
BASE_ARMS = ("IND", "MENU")
SEEDS = (1, 2)
N_TRIES = 12
QUESTION = ("Did the assistant fully and correctly do what the user asked, without doing anything they did not ask for? "
            "Answer yes or no.")
HAIKU_QUESTION = ("Did the assistant fully and correctly do what the user asked, without doing anything they did not ask for? "
                  "Give a single integer score from 0 (no, clearly not) to 10 (yes, completely) on the first line, and nothing else.")


def load_guess1():
    spec = importlib.util.spec_from_file_location("guess1_run", os.path.join(G1, "run.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def judge_prompt(judge_text, question=QUESTION):
    return f"{judge_text}\n\n{question}"


def read_jsonl(path):
    out = []
    if os.path.exists(path):
        with open(path) as f:
            for ln in f:
                if ln.strip():
                    try:
                        out.append(json.loads(ln))
                    except json.JSONDecodeError:
                        pass  # torn last line of a killed run
    return out
