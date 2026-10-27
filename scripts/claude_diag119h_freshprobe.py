"""Director fresh probe for 119h (descriptive; inference only; no training, no tuning).
Scores the sealed fresh119h.json (sha256 230d8135...) on the 119g checkpoints (before) and the 119h checkpoints (after).
Per seed and group: occupation offered in the K=3 read-outs, occupation exact (subject + any listed job/alt), first job
exact, occupation rank buckets, oracle-relation (forced occupation) read-out exact, and false occupation reads on group C.
Metric code written 2026-09-22 before any 119h model existed; only the checkpoint paths may be adjusted after the build."""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import torch
import fable_ears47_data as D
import fable_ears119_data as D119  # noqa: F401  (MAX_LEN override)
import fable_ears47_encoder as ENC
import fable_ears47_score as S47
import fable_ears119g_score as G
import fable_ears119g_model as M119g
import fable_read106_score as R106
HERE = Path(__file__).resolve().parent
RUNS = {"119g": Path(r"C:\Users\benja\ears119g\runs"), "119h": Path(r"C:\Users\benja\ears119h\runs")}
SNAP = r"C:\Users\benja\.cache\huggingface\hub\models--allenai--scibert_scivocab_uncased\snapshots\24f92d32b1bfb0bcaf9ab193ff3ad01e87732fc1"
K, FLOOR = 3, 0.10
CLS = D.CLASSES["classes"]
OCC = CLS.index("occupation")
N = R106.norm
dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
enc0, tok, _ = ENC.load(SNAP); del enc0
unk = {tok.unk}
probe = json.loads((HERE / "fresh119h.json").read_text(encoding="utf-8"))["rows"]
rows = [{"text": r["text"], "gold47": {"act": "NO_FACT", "rel": "UNSURE", "subj": None, "obj": None, "dir": 0, "rep": False}}
        for r in probe]
encs = [D.encode_row(r, tok) for r in rows]


def rank_of(relp, r):
    order = sorted(range(len(relp)), key=lambda k: -float(relp[k]))
    return order.index(r) + 1


def bucket_rank(k):
    return "1" if k == 1 else "2-3" if k <= 3 else "4-10" if k <= 10 else "11+"


def occ_triples(frames, i):
    out = []
    for p in frames:
        f = p.get("frame") or {}
        if f.get("rel") != "occupation":
            continue
        t = R106.r2_triple_of(f, rows[i]["text"], encs[i]["chspans"])
        if t is not None:
            out.append(t)
    return out


def hit(ts, r, first_only=False):
    if not r["subj"]:
        return False
    objs = [r["jobs"][0]] if first_only else list(r["jobs"])
    objs += r["alt"]
    good = {("occupation", N(r["subj"]), N(o)) for o in objs}
    return any(t in good for t in ts)


out = {"probe_sha_prefix": "230d8135", "K": K, "FLOOR": FLOOR}
for tag, runs in RUNS.items():
    for s in (11911, 11912, 11913):
        if not (runs / f"w-{s}" / "ear.pt").exists():
            out[f"{tag}-{s}"] = "missing checkpoint"; continue
        model, _ = G.load_model_g(runs, s, SNAP, dev)
        P = S47.probs_for_model(model, encs, dev, batch=64)
        multi = G.decode_all_multi(model, rows, encs, dev, unk, K, FLOOR)
        forced = []
        for i in range(len(rows)):
            if D.ACTS[int(P[i]["act"].argmax())] != "STATE":
                forced.append([]); continue
            n = int(P[i]["n"])
            ids = torch.tensor([encs[i]["ids"][:n]]); mask = torch.ones(1, n, dtype=torch.bool)
            pp = M119g.conditioned_ptr_probs(model, ids.to(dev), mask.to(dev), torch.tensor([OCC]).to(dev))
            fo = G.decode_forced_rel(rows[i], encs[i], P[i], pp[0, :, :n].cpu(), OCC, float(P[i]["rel"][OCC]), unk)
            forced.append([fo] if fo else [])
        res = {}
        for g in ("A", "B", "C"):
            idx = [i for i, r in enumerate(probe) if r["id"][0] == g]
            c = collections.Counter()
            ranks = collections.Counter()
            for i in idx:
                r = probe[i]
                ts = occ_triples(multi[i], i)
                ranks[bucket_rank(rank_of(P[i]["rel"], OCC))] += 1
                c["act_STATE"] += D.ACTS[int(P[i]["act"].argmax())] == "STATE"
                if g == "C":
                    c["false_occ_read"] += bool(ts)
                    continue
                c["occ_offered"] += bool(ts)
                c["occ_exact"] += hit(ts, r)
                c["occ_first_exact"] += hit(ts, r, first_only=True)
                c["forced_occ_exact"] += hit(occ_triples(forced[i], i), r)
            res[g] = {"n": len(idx), **dict(c), "occ_rank": dict(ranks)}
        # per-sentence detail (director's own probe, not a panel): top-3 relations and occupation read-outs
        res["detail"] = [{"id": probe[i]["id"],
                          "top3": [(CLS[k], round(float(P[i]["rel"][k]), 3)) for k in
                                   sorted(range(len(P[i]["rel"])), key=lambda k: -float(P[i]["rel"][k]))[:3]],
                          "occ_reads": occ_triples(multi[i], i),
                          "forced": occ_triples(forced[i], i)} for i in range(len(rows))]
        out[f"{tag}-{s}"] = res
        del model
        torch.cuda.empty_cache()
(HERE / "diag119h.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
print("DIAG119H DONE")
