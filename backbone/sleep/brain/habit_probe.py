"""Stage 1 of PREREG-habit1.md: does the model answer the habit spotter's question well? No training.

  build  (needs sleepb's imports):  python habit_probe.py build --week data/week2.json --items results_a12/result_q36_q4.json --out probe.jsonl
  ask    (stdlib only; any OpenAI-compatible chat server, e.g. mlx_lm.server with Qwen3.6, thinking off):
         python habit_probe.py ask --in probe.jsonl --url http://127.0.0.1:8080/v1/chat/completions --model <name> --out replies.jsonl
  score:  python habit_probe.py score --in replies.jsonl --out score.json

Questions (all in the spotter's exact wording, habit.habit_user):
  R2   each of the 20 routines, shown its first 2 days only (what the spotter sees the first night it can ask);
  Rall each routine, shown all its days (up to HABIT_CTX_DAYS);
  N    every other pair the spotter would ask over the week, with the run's own items standing in for the notes (as many nights as asked);
  F    up to 40 fact pairs (C2 / C4, 2+ days together) that are NOT habits: false-habit stress, never asked in a real run (their items exist).
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import habit as H  # noqa: E402


def build(a):
    import sleepb as S
    w = json.loads(Path(a.week).read_text())
    dia = S.Diary(w)
    items = {}
    if a.items:
        for it in json.loads(Path(a.items).read_text())["items"]:
            k = (S.norm(it["subj"]), S.norm(it["obj"]))
            items[k] = S.Item(k, it["subj"], it["rel"], it["obj"], 1, dead=it["dead"])
    gt = {}
    for g in w["items"]:
        gt[tuple(sorted((S.norm(g["a"]), S.norm(g["b"]))))] = g
    v = S.name_vocab(dia, 7)
    pt = H.pair_days(dia, 7, v, S.pat)
    rows = []

    def add(kind, p, idx, extra=None):
        days = sorted({dia.turns[i]["day"] for i in idx})
        last = {dia.turns[i]["day"]: i for i in sorted(idx)}
        ctx = [last[x] for x in days][-H.HABIT_CTX_DAYS:]
        a_, b_ = v[p[0]], v[p[1]]
        rows.append({"kind": kind, "pair": [a_, b_], "n_days": len(days), "system": H.HABIT_SYS,
                     "user": H.habit_user(dia.label(ctx, 400), a_, b_, len(days)), **(extra or {})})
    for p, g in gt.items():
        if g["kind"] != "routine":
            continue
        idx = pt.get(p, [])
        d2 = sorted({dia.turns[i]["day"] for i in idx})[:2]
        add("R2", p, [i for i in idx if dia.turns[i]["day"] in d2], {"activity": g["activity"]})
        add("Rall", p, idx, {"activity": g["activity"]})
    asked = {}
    for d in range(1, 8):  # the spotter's nightly questions, with the run's items as the notes
        vd = S.name_vocab(dia, d)
        ptd = H.pair_days(dia, d, vd, S.pat)
        for p, ctx in H.candidates(dia, ptd, items, set(), asked):
            asked[p] = len({dia.turns[i]["day"] for i in ptd[p]})
            g = gt.get(tuple(sorted(p)))
            if not g or g["kind"] != "routine":
                add("N", p, ptd[p], {"night": d, "gt_kind": g["kind"] if g else None})
    facts = [p for p, g in gt.items() if g["kind"] == "fact" and len({dia.turns[i]["day"] for i in pt.get(p, [])}) >= 2]
    for p in facts[:40]:
        add("F", p, pt[p], {"gt_kind": gt[p].get("class")})
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in rows))
    print({k: sum(r["kind"] == k for r in rows) for k in ("R2", "Rall", "N", "F")})


def ask(a):
    rows = [json.loads(x) for x in Path(a.inp).read_text().splitlines() if x.strip()]
    out = []
    t0 = time.time()
    for r in rows:
        body = {"model": a.model, "messages": [{"role": "system", "content": r["system"]}, {"role": "user", "content": r["user"]}],
                "max_tokens": 48, "temperature": 0.0, "chat_template_kwargs": {"enable_thinking": False}}
        req = urllib.request.Request(a.url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as f:
            txt = json.loads(f.read())["choices"][0]["message"]["content"]
        out.append({**r, "reply": txt})
    Path(a.out).write_text("".join(json.dumps(r) + "\n" for r in out))
    print(f"{len(out)} replies in {time.time() - t0:.0f} s")


def score(a):
    rows = [json.loads(x) for x in Path(a.inp).read_text().splitlines() if x.strip()]
    res = {}
    for k in ("R2", "Rall", "N", "F"):
        rs = [r for r in rows if r["kind"] == k]
        yes = [r for r in rs if H.parse_habit(r["reply"], *r["pair"])]
        res[k] = {"n": len(rs), "yes": len(yes), "rate": round(len(yes) / len(rs), 3) if rs else None}
        if k.startswith("R"):  # does the sentence name the activity? (any word of 4+ letters of the activity)
            act = [r for r in yes if any(x in r["reply"].lower() for x in r["activity"].lower().split() if len(x) >= 4)]
            res[k]["yes_with_activity"] = len(act)
    res["pass_S1"] = res["Rall"]["yes"] >= 16 and (res["F"]["rate"] or 0) <= 0.30
    res["samples"] = [{"kind": r["kind"], "pair": r["pair"], "reply": r["reply"][:160]} for r in rows[:6]]
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "samples"}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("build", "ask", "score"))
    ap.add_argument("--week")
    ap.add_argument("--items")
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--out", required=True)
    ap.add_argument("--url", default="http://127.0.0.1:8080/v1/chat/completions")
    ap.add_argument("--model", default="default")
    a = ap.parse_args()
    {"build": build, "ask": ask, "score": score}[a.cmd](a)
