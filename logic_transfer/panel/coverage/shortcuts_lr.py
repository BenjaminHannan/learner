"""Task 3 (part 2): cross-fitted hashed bag-of-words / char-n-gram softmax regression (own numpy implementation, no sklearn).
Usage: python3 -B shortcuts_lr.py [N_TRAIN=30000] [SETS=comma list] [logic_train|placebo_train]
Trains on the first N_TRAIN rows of logic_train / placebo_train (never more than 50k rows in memory), reports
 (a) 5-fold out-of-fold accuracy inside the train sample, (b) accuracy of the full-sample fit on every eval file.
Feature sets: words (uni+bigrams of the prompt incl. options suffix), chars (char 1-5grams of the prompt incl. suffix),
delex (entity/predicate words replaced by E/P, uni-tri-grams of the body), tids (template-id bag), suffix (options order only),
counts (binned sentence-role counts, negation-cue count, length), all (union)."""
from common import *
import numpy as np, zlib, sys, time

B = 1 << 18
LAB = {"true": 0, "false": 1, "unknown": 2}
NEG = re.compile(r"\bnot\b|n't|\bnever\b|non-", re.I)
TOK = re.compile(r"[a-z]+|'t|[.?:,()/!-]")

def h(s): return zlib.crc32(s.encode()) % B

def pad(lists, F=None):
    F = F or max(len(x) for x in lists)
    M = np.full((len(lists), F), B, dtype=np.int32)
    for i, x in enumerate(lists):
        x = x[:F]; M[i, :len(x)] = x
    return M

def f_words(rows):
    out = []
    for r in rows:
        t = TOK.findall(r["prompt"].lower())
        out.append([h("w|" + a) for a in t] + [h("b|" + a + " " + b) for a, b in zip(t, t[1:])])
    return pad(out)

def f_chars(rows, nmax=5):
    L = 208
    X = np.zeros((len(rows), L), dtype=np.int64)
    for i, r in enumerate(rows):
        p = r["prompt"][:L]; X[i, :len(p)] = np.frombuffer(p.encode("latin1", "replace"), dtype=np.uint8)
    parts = []
    for n in range(1, nmax + 1):
        w = L - n + 1
        hh = np.zeros((len(rows), w), dtype=np.int64); valid = np.ones((len(rows), w), dtype=bool)
        for k in range(n):
            c = X[:, k:k + w]
            hh = (hh * 257 + c) % (1 << 40); valid &= c > 0
        hh = (hh * 2654435761 + n * 40503) % (1 << 40)
        idx = ((hh ^ (hh >> 13)) % B).astype(np.int32); idx[~valid] = B
        parts.append(idx)
    return np.concatenate(parts, axis=1)

def f_delex(rows):
    out = []
    for r in rows:
        m = r["meta"]; body, _ = split_prompt(r["prompt"])
        facts, rules, query = ck.parse_program(m["program"])
        ents = {f[2] for f in facts} | {ru.ent for ru in rules if ru.ent} | {query[2]}
        preds = {f[1] for f in facts} | {p for ru in rules for _, p in ru.lhs + (ru.rhs,)} | {query[1]}
        toks = []
        for t in TOK.findall(body.lower()):
            toks.append("E" if t in ents else "P" if t in preds else t)
        feats = [h("d1|" + a) for a in toks] + [h("d2|" + a + " " + b) for a, b in zip(toks, toks[1:])] + \
                [h("d3|" + a + " " + b + " " + c) for a, b, c in zip(toks, toks[1:], toks[2:])]
        out.append(feats)
    return pad(out)

def f_tids(rows):
    out = []
    for r in rows:
        t = r["meta"]["template_ids"]; k = [x.split(":")[0] for x in t]
        out.append([h("t|" + x) for x in t] + [h("k2|" + a + b) for a, b in zip(k, k[1:])] + [h("n|%d" % len(t))])
    return pad(out)

def f_suffix(rows):
    out = []
    for r in rows:
        _, o = split_prompt(r["prompt"])
        out.append([h("perm|" + "/".join(o))] + [h("slot%d|%s" % (i, w)) for i, w in enumerate(o)])
    return pad(out)

def f_counts(rows):
    out = []
    for r in rows:
        m = r["meta"]; body, _ = split_prompt(r["prompt"]); tl = m["template_ids"]; k = [x.split(":")[0] for x in tl]
        f = ["nsent=%d" % len(tl), "neg=%d" % min(len(NEG.findall(body)), 8), "chars=%d" % (len(r["prompt"]) // 10), "words=%d" % len(r["prompt"].split()),
             "Q=%s" % tl[-1]] + ["n%s=%d" % (x, k.count(x)) for x in ["FP", "FN", "R1", "R2", "R3", "R4", "R5"]]
        f += ["nrule=%d" % sum(x.startswith("R") for x in k), "nfact=%d" % sum(x.startswith("F") for x in k)]
        out.append([h("c|" + a) for a in f])
    return pad(out)

FSETS = dict(words=f_words, chars=f_chars, delex=f_delex, tids=f_tids, suffix=f_suffix, counts=f_counts)

def f_all(rows):
    return np.concatenate([FSETS[k](rows) for k in ["words", "delex", "tids", "suffix", "counts"]], axis=1)

class LR:
    def __init__(self, l2=1e-4, epochs=6, lr=0.03, bs=256, seed=0):
        self.l2, self.epochs, self.lr, self.bs, self.seed = l2, epochs, lr, bs, seed
    def logits(self, idx):
        sc = 1.0 / np.sqrt(np.maximum(1, (idx != B).sum(1)))
        out = np.zeros((idx.shape[0], 3), dtype=np.float64)
        for s in range(0, idx.shape[0], 512):
            out[s:s + 512] = self.W[idx[s:s + 512]].sum(1) * sc[s:s + 512, None]
        return out + self.b
    def fit(self, idx, y):
        rng = np.random.RandomState(self.seed)
        self.W = np.zeros((B + 1, 3)); self.b = np.zeros(3)
        mW = np.zeros_like(self.W); vW = np.zeros_like(self.W); t = 0
        n = len(y)
        for ep in range(self.epochs):
            perm = rng.permutation(n)
            for s in range(0, n, self.bs):
                bi = perm[s:s + self.bs]; ix = idx[bi]; yy = y[bi]
                sc = 1.0 / np.sqrt(np.maximum(1, (ix != B).sum(1)))
                z = self.W[ix].sum(1) * sc[:, None] + self.b
                z -= z.max(1, keepdims=True); p = np.exp(z); p /= p.sum(1, keepdims=True)
                p[np.arange(len(yy)), yy] -= 1; p /= len(yy)
                g = np.zeros_like(self.W)
                flat = ix.ravel()
                for c in range(3):
                    g[:, c] = np.bincount(flat, weights=np.repeat(p[:, c] * sc, ix.shape[1]), minlength=B + 1)
                g += self.l2 * self.W
                t += 1
                mW = 0.9 * mW + 0.1 * g; vW = 0.999 * vW + 0.001 * g * g
                self.W -= self.lr * (mW / (1 - 0.9 ** t)) / (np.sqrt(vW / (1 - 0.999 ** t)) + 1e-8)
                self.W[B] = 0
                self.b -= self.lr * p.sum(0)
        return self
    def predict(self, idx): return self.logits(idx).argmax(1)
    def logloss(self, idx, y):
        z = self.logits(idx); z -= z.max(1, keepdims=True); lp = z - np.log(np.exp(z).sum(1, keepdims=True))
        return float(-lp[np.arange(len(y)), y].mean())

def ylab(rows): return np.array([LAB[r["answer"]] for r in rows])

if __name__ == "__main__":
    NTR = int(sys.argv[1]) if len(sys.argv) > 1 else 30000
    sets = (sys.argv[2].split(",") if len(sys.argv) > 2 else ["words", "chars", "delex", "tids", "suffix", "counts", "all"])
    out = {"n_train": NTR, "sets": sets, "results": {}}
    evrows = {k: read_jsonl(p) for k, p in EVAL.items()}
    trlist = [sys.argv[3]] if len(sys.argv) > 3 else ["logic_train", "placebo_train"]
    for trname in trlist:
        rows = read_jsonl(TRAIN[trname], NTR); y = ylab(rows)
        evs = [k for k in EVAL if k.startswith(trname.split("_")[0])]
        out["results"][trname] = {}
        for sname in sets:
            fn = f_all if sname == "all" else FSETS[sname]
            t0 = time.time()
            X = fn(rows)
            folds = np.arange(len(rows)) % 5
            oof = np.zeros(len(rows), dtype=int); ll = []
            for f in range(5):
                tr, te = folds != f, folds == f
                m = LR().fit(X[tr], y[tr]); oof[te] = m.predict(X[te]); ll.append(m.logloss(X[te], y[te]))
            res = dict(oof_acc=round(100 * float((oof == y).mean()), 2), oof_logloss=round(float(np.mean(ll)), 4),
                       majority=round(100 * float(np.bincount(y).max() / len(y)), 2), eval={})
            m = LR().fit(X, y)
            for ek in evs:
                Xe = fn(evrows[ek]); ye = ylab(evrows[ek]); pe = m.predict(Xe)
                d = dict(acc=round(100 * float((pe == ye).mean()), 2), n=len(ye), logloss=round(m.logloss(Xe, ye), 4))
                lv = np.array([r["level"] for r in evrows[ek]])
                d["pred_share_true_false_unknown"] = [round(float((pe == c).mean()), 3) for c in range(3)]
                if ek.startswith("logic") and ek != "logic_test_sampler":
                    d["by_depth"] = {str(dd): round(100 * float((pe[lv == dd] == ye[lv == dd]).mean()), 1) for dd in sorted(set(lv.tolist()))}
                res["eval"][ek] = d
            res["secs"] = round(time.time() - t0, 1)
            out["results"][trname][sname] = res
            print(trname, sname, "OOF", res["oof_acc"], "eval", {k: v["acc"] for k, v in res["eval"].items()}, "secs", res["secs"], flush=True)
            del X
            json.dump(out, open(OUT + "/shortcuts_lr_%s.json" % ("_".join(trlist)), "w"), indent=1)
