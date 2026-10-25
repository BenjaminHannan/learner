"""D2 "Slot Laps" at init on frozen Qwen3.5-0.8B (CPU, no training, no LoRA = zero-init think/task LoRA).

Sequence per question: [context + question] [16 slots] [" [answer]"] [answer + eos]; CE on answer tokens only.
  A      : no slots ([ctx+q][" [answer]"][answer]), the stage-1 format.
  P      : slots = 16 ordinary token embeddings run once through all layers (pause tokens, "R=0").
  laps   : slots go through [0,a) once (Z0), then R laps of band [a,b) over slots only, prompt band state restored
           each lap, then the final Z goes through [b,L); tail+answer read everything through the cache.
  variants: d2_bi   alpha=0.5, norm held to rms(Z0), slots see all slots in band full-attention (D2 as written)
            d2_ca   same, causal among slots
            bslot   alpha=1, no norm hold, causal (= arm B's operation restricted to slots); R=1 must equal P.
"""
import copy, json, math, random, sys, time
import torch, torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache

torch.set_num_threads(4)
MID = sys.argv[1]; DATA = sys.argv[2]; N = int(sys.argv[3]); OUT = sys.argv[4]; SHOTS = int(sys.argv[5]) if len(sys.argv) > 5 else 0; TRAIN = sys.argv[6] if len(sys.argv) > 6 else None
A_, B_ = 8, 12
RS = [1, 2, 4, 8, 12]
tok = AutoTokenizer.from_pretrained(MID)
lm = AutoModelForCausalLM.from_pretrained(MID, dtype=torch.float32).eval()
m, cfg = lm.model, lm.config
L = cfg.num_hidden_layers
types = cfg.layer_types


def ids(s):
    return tok(s, add_special_tokens=False)["input_ids"]


def mask4(past, n, bidir=False):
    q = torch.arange(n)[:, None] + past
    k = torch.arange(past + n)[None, :]
    allow = k <= q
    if bidir:
        allow = allow | (k >= past)
    out = torch.zeros(n, past + n)
    out[~allow] = float("-inf")
    return out[None, None]


def run(x, start_pos, cache, layer_ids, bidir=False):
    n = x.shape[1]
    pos = torch.arange(start_pos, start_pos + n)[None]
    pe = m.rotary_emb(x, pos[None].expand(3, *pos.shape))
    mk = mask4(start_pos, n, bidir)
    for i in layer_ids:
        x = m.layers[i](x, position_embeddings=pe, attention_mask=mk if types[i] == "full_attention" else None,
                        position_ids=pos, past_key_values=cache, use_cache=True)
    return x


def ce_from(h_last, h_rest, ans):
    h = torch.cat([h_last, h_rest], 1)[:, :len(ans)]
    logits = lm.lm_head(m.norm(h)).float()[0]
    return F.cross_entropy(logits, torch.tensor(ans), reduction="mean").item()


rms = lambda z: z.pow(2).mean(-1, keepdim=True).sqrt()
rows = [json.loads(l) for l in open(DATA)]
random.Random(0).shuffle(rows)
rows = [r for r in rows if len(r["context"]) < 4500][:N]
slot_ids = ids(" Let me work out where each thing was, step by step, before I answer the question now")[:16]
assert len(slot_ids) == 16
tail = ids(" [answer]")
prefix = []
if SHOTS:
    tr = [json.loads(l) for _, l in zip(range(4000), open(TRAIN))]
    tr = [t for t in tr if len(t["context"]) < 1400][:SHOTS]
    for t in tr:
        prefix += ids(t["context"] + "\n" + t["question"]) + tail + ids(" " + t["answer"]) + ids("\n\n")
res = []
t0 = time.time()
with torch.no_grad():
    for qi, r in enumerate(rows):
        p = prefix + ids(r["context"] + "\n" + r["question"])
        ans = ids(" " + r["answer"]) + [tok.eos_token_id]
        P = len(p)
        cache = DynamicCache(config=cfg)
        hp = run(m.embed_tokens(torch.tensor([p])), 0, cache, range(L))
        rec = dict(id=r["id"], depth=r["depth"], P=P)
        # A: no slots
        c = copy.deepcopy(cache)
        ta = tail + ans[:-1]
        h = run(m.embed_tokens(torch.tensor([ta])), P, c, range(L))
        rec["A"] = ce_from(h[:, len(tail) - 1:len(tail)], h[:, len(tail):], ans)
        # slots through [0,a): Z0 (cached in [0,a))
        z0 = run(m.embed_tokens(torch.tensor([slot_ids])), P, cache, range(A_))
        snap_band = {i: copy.deepcopy(cache.layers[i]) for i in range(A_, B_)}
        s0 = rms(z0)

        def readout(zR, band_state, tagname):
            c = copy.deepcopy(cache)
            for i in range(A_, B_):
                c.layers[i] = copy.deepcopy(band_state[i])
            run(zR, P, c, range(B_, L))  # board enters upper stack
            h = run(m.embed_tokens(torch.tensor([ta])), P + 16, c, range(L))
            rec[tagname] = ce_from(h[:, len(tail) - 1:len(tail)], h[:, len(tail):], ans)

        # P: plain pass (slots as ordinary tokens)
        c = copy.deepcopy(cache)
        run(z0, P, c, range(A_, L))
        h = run(m.embed_tokens(torch.tensor([ta])), P + 16, c, range(L))
        rec["P"] = ce_from(h[:, len(tail) - 1:len(tail)], h[:, len(tail):], ans)
        for var, alpha, hold, bidir in [("d2_bi", 0.5, True, True), ("d2_ca", 0.5, True, False), ("bslot", 1.0, False, False)]:
            z = z0.clone()
            deltas = []
            for lap in range(1, max(RS) + 1):
                for i in range(A_, B_):
                    cache.layers[i] = copy.deepcopy(snap_band[i])
                y = run(z, P, cache, range(A_, B_), bidir=bidir)
                if lap == 1:
                    rec["rms_ratio_hb_over_ha"] = (rms(y) / s0).mean().item()
                zn = z + alpha * (y - z)
                if hold:
                    zn = zn * s0 / rms(zn)
                deltas.append(((zn - z).norm() / z0.norm()).item())
                z = zn
                if lap in RS:
                    readout(z, {i: cache.layers[i] for i in range(A_, B_)}, f"{var}_R{lap}")
            rec[f"{var}_delta"] = deltas
            rec[f"{var}_cos_z_z0"] = F.cosine_similarity(z.flatten(), z0.flatten(), 0).item()
        for i in range(A_, B_):
            cache.layers[i] = copy.deepcopy(snap_band[i])
        res.append(rec)
        print(qi, f"{time.time() - t0:.0f}s", json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec.items() if not isinstance(v, list)}), flush=True)
json.dump(res, open(OUT, "w"))
