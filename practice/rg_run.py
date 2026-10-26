"""Practice-2 driver (PREREG-2): stage 0 (pick the skills) and the main run (per skill: A0, then 3 x (day -> night) for arms P and C, evals).
  python -m practice.job --stage0 --out $OUT
  python -m practice.job --rg-skills auto --out $OUT      (or --rg-skills countdown,zebra_puzzles)
Layout: <out>/stage0.json, <out>/stage0/<skill>/..., <out>/<skill>/rgdata/{day1..N,test}.jsonl, <out>/<skill>/{P,C}/ (results/, day/, eval/, adapters/, lane.log).
Re-running with the same --out resumes: a finished phase (its results/*.json exists) is skipped; a half-finished day or eval restarts. Practice days use fresh puzzles
(label 1000+day), each seen once. Evals: A0 and P1, P3 on the 300-puzzle test (2 tries), C3 only (S2 needs only C3), sealed test100 at A0 (first skill only, it is the
same base model) and P3. Night size: P = shortest win per solved puzzle (cap RG_N_SFT) x EPOCHS + one DPO pair per puzzle (cap RG_N_PAIRS), steps scale with that
count; C gets exactly the same item counts and steps."""
import argparse
import json
from pathlib import Path

from . import rg_pool as R
from .lessons import RG_N_PAIRS, RG_N_SFT


def jload(p):
    return json.loads(Path(p).read_text())


def jsave(p, o):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(o, indent=1))


def lane_args(a, out, arm, skill, **kw):
    d = dict(vars(a), out=str(out), arm=arm, rg_skill=skill, arc_n=0, deadline_s=1e9, **kw)
    d["tries"] = a.tries or 4
    return argparse.Namespace(**d)


def write_sets(sdir, skill, a, days):
    rd = Path(sdir) / "rgdata"
    questions = set()
    for d in range(1, days + 1):
        ps = R.make_puzzles(skill, a.rg_day_n, R.DAY_SEED0 + d)
        questions |= {p["prompt"] for p in ps}
        if not (rd / f"day{d}.jsonl").exists():
            (rd).mkdir(parents=True, exist_ok=True)
            (rd / f"day{d}.jsonl").write_text("".join(json.dumps(p) + "\n" for p in ps))
    if not (rd / "test.jsonl").exists():
        ts = R.test_set(skill, a.rg_test_n, R.TEST_SEED, questions)
        (rd / "test.jsonl").write_text("".join(json.dumps(p) + "\n" for p in ts))
    return rd


def stage0(a):
    from .job import Lane
    root = Path(a.out)
    if (root / "stage0.json").exists():
        print("stage0.json exists, skipping", flush=True)
        return jload(root / "stage0.json")
    scores = {}
    for skill in R.CANDIDATES:
        sdir = root / "stage0" / skill
        rd = sdir / "rgdata"
        rd.mkdir(parents=True, exist_ok=True)
        if not (rd / "stage0.jsonl").exists():
            (rd / "stage0.jsonl").write_text("".join(json.dumps(p) + "\n" for p in R.make_puzzles(skill, a.stage0_n, R.STAGE0_SEED)))
        res_path = sdir / "S0" / "results" / "S0.json"
        if not res_path.exists():
            lane = Lane(lane_args(a, sdir, "S0", skill, rg_test="stage0"))
            lane.phase("eval", "eval_S0", tag="S0", seed=a.seed or 1, tries_map={"test": 1})
        scores[skill] = jload(res_path)["test"]["acc"]
        print(f"stage0 {skill}: {scores[skill]}", flush=True)
    picked, note = R.pick_skills(scores)
    out = {"n_puzzles": a.stage0_n, "tries": 1, "seed": R.STAGE0_SEED, "scores": scores, "picked": picked, "note": note}
    jsave(root / "stage0.json", out)
    print("stage0 picked", picked, note, flush=True)
    return out


def run_skill(a, skill, k):
    from .job import Lane
    root = Path(a.out)
    sdir = root / skill
    write_sets(sdir, skill, a, a.nights)
    seed = a.seed or 1
    P, C = (Lane(lane_args(a, sdir, arm, skill)) for arm in ("P", "C"))
    ev_nights = {int(x) for x in str(a.eval_nights).split(",") if x}
    last = a.nights
    TT = a.test_tries

    def once(lane, key, fn):
        path = lane.out / "results" / f"{key}.json"
        if path.exists():
            lane.log(f"resume: {key} already done")
            return jload(path)
        return fn()

    def ev(lane, tag, seed_, sib):
        tm = {"test": TT, **({"sibling": TT} if sib else {})}
        return once(lane, tag, lambda: lane.phase("eval", f"eval_{tag}", tag=tag, seed=seed_, tries_map=tm))

    ev(P, "A0", seed, sib=(k == 0))
    for n in range(1, a.nights + 1):
        pz = str(sdir / "rgdata" / f"day{n}.jsonl")
        for lane in (P, C):
            once(lane, f"day{n}", lambda lane=lane: lane.day(n, seed * 100 + n, None, puzzles=pz))
        st = once(P, f"night{n}", lambda: P.night(n, seed, auto_steps=True, dedup=True, n_sft=RG_N_SFT, n_pairs=RG_N_PAIRS))
        kw = dict(steps=st["steps"], n_sft=max(1, st.get("sft_unique", 0)), n_pairs=st.get("pairs", 0), dedup=True)
        stc = once(C, f"night{n}", lambda: C.night(n, seed, **kw))
        for lane, s_ in ((P, st), (C, stc)):
            ad = lane.out / "adapters" / f"night{n}"
            lane.adapter = str(ad) if ad.exists() else s_.get("adapter")
        if n in ev_nights or n == last:
            if n == last:
                ev(P, f"P{n}", seed * 100 + n, sib=True)
                ev(C, f"C{n}", seed * 100 + n, sib=False)
            else:
                ev(P, f"P{n}", seed * 100 + n, sib=False)


def main(a):
    a.tries = a.tries or 4
    a.seed = a.seed or 1
    root = Path(a.out)
    root.mkdir(parents=True, exist_ok=True)
    jsave(root / "rg_config.json", {k: v for k, v in vars(a).items() if isinstance(v, (int, float, str, bool, type(None)))})
    if a.stage0:
        stage0(a)
        if not a.rg_skills:
            return
    skills = a.rg_skills
    if skills == "auto":
        if not (root / "stage0.json").exists():
            raise SystemExit("--rg-skills auto needs <out>/stage0.json (run --stage0 first)")
        skills = jload(root / "stage0.json")["picked"]
    else:
        skills = skills.split(",")
    for s in skills:
        if s not in R.CANDIDATES:
            raise SystemExit(f"unknown skill {s}; candidates: {R.CANDIDATES}")
    for k, s in enumerate(skills):
        run_skill(a, s, k)
