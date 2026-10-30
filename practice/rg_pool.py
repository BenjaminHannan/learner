"""Practice-2 puzzle source: Reasoning Gym (pip reasoning-gym==0.1.25), procedurally generated puzzles with built-in checkers (score_answer == 1.0 is correct).
Puzzle dicts match the Practice-1 format (id, prompt, answer, answer_type, kind) plus src="rg" and the dataset entry (JSON round-tripped) for re-grading.
Seeds: reasoning_gym derives entry i from Random(seed + i), so consecutive seeds (1001, 1002) share almost all puzzles. The `seed` argument here is a label (PREREG-2:
1000+day, 9999 test, 100 stage 0); the dataset seed is label * SEED_STRIDE, so different labels never overlap (at most MAX_PER_SEED puzzles per label)."""
import json

CANDIDATES = ["countdown", "cryptarithm", "knights_knaves", "zebra_puzzles", "mini_sudoku", "futoshiki", "word_ladder", "family_relationships"]
SEED_STRIDE, MAX_PER_SEED = 100003, 5000   # word_ladder refuses very large dataset sizes
TEST_SEED, STAGE0_SEED, DAY_SEED0 = 9999, 100, 1000
_DS = {}


def _ds(task, seed=0, size=1):
    import reasoning_gym as rg
    return rg.create_dataset(task, size=size, seed=seed)


def _scorer(task):
    if task not in _DS:
        _DS[task] = _ds(task)
    return _DS[task]


def _entries(task, seed):
    """Endless (index, entry) for the label `seed`; entries are JSON round-tripped so that grading sees exactly what is stored."""
    ds, i = _ds(task, seed * SEED_STRIDE, MAX_PER_SEED), 0
    while i < MAX_PER_SEED:
        yield i, json.loads(json.dumps(ds[i]))
        i += 1


def _puzzle(task, seed, i, e):
    return {"id": f"rg-{task}-{seed}-{i}", "prompt": e["question"], "answer": e["answer"], "answer_type": "str", "kind": task, "src": "rg", "source": "rg", "entry": e}


def make_puzzles(task, n, seed):
    out = []
    for i, e in _entries(task, seed):
        if i >= n:
            break
        out.append(_puzzle(task, seed, i, e))
    return out


def grade(puzzle, answer_text):
    """True iff the dataset's score_answer gives 1.0 (accepts any valid solution for countdown, word_ladder, cryptarithm)."""
    if answer_text is None:
        return False
    try:
        return float(_scorer(puzzle["kind"]).score_answer(str(answer_text).strip(), puzzle["entry"])) == 1.0
    except Exception:  # noqa: BLE001  (a malformed answer must score 0, not crash a rollout)
        return False


def test_set(task, n=300, seed=TEST_SEED, exclude=()):
    """First n puzzles of label `seed` whose question text is not in `exclude` (practice questions) and not repeated inside the set."""
    seen, out = set(exclude), []
    for i, e in _entries(task, seed):
        if e["question"] in seen:
            continue
        seen.add(e["question"])
        out.append(_puzzle(task, seed, i, e))
        if len(out) >= n:
            break
    return out


def pick_skills(scores, k=2, target=0.30, lo=0.10, hi=0.60):
    """PREREG-2 stage 0: the k skills closest to `target` among those with lo <= score <= hi; if fewer qualify, the nearest others fill up (and the note says so).
    scores: {skill: base accuracy 0..1}. Returns (picked, note)."""
    order = {s: i for i, s in enumerate(scores)}
    near = sorted(scores, key=lambda s: (abs(scores[s] - target), order[s]))
    ok = [s for s in near if lo <= scores[s] <= hi]
    picked = ok[:k]
    note = ""
    if len(picked) < k:
        picked += [s for s in near if s not in picked][: k - len(picked)]
        note = f"only {len(ok)} skill(s) between {lo:.0%} and {hi:.0%}; filled with the nearest to {target:.0%}"
    return picked, note
