r"""Build sense sleep's fixed seat test for the eye projector (track I1): pooled SigLIP2 features + captions + fixed candidates.

    python build_vision_seat.py --userdata ~/Library/Application\ Support/Premonition --from-jsonl items.jsonl   # {"path", "caption"} per line
    python build_vision_seat.py --userdata ... --from-html ~/learner-ops/premonition-projectors/results/vision_captions.html   # interim

Writes userData/sense-sleep/seat/vision_seat.safetensors ("features": N x 64 x 768 float16) and vision_seat.json
({"eye", "captions", "cands", "source", "n"}): each item's true caption first, then 9 others (seed 0). Public held-out images only
(never Ben's screen). The seat items must stay apart from any morning-report items.
Interim source: the 50 held-out ReCap thumbnails (160 px) in premonition-projectors' vision_captions.html, captions cut to 300 chars.
The real seat should be 150+ full-size images from ReCap shard 25 (never trained on), built where that shard is (the PC).
"""
import argparse
import base64
import io
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import glim_eyes as E  # noqa: E402


def from_html(path):
    from PIL import Image
    s = open(path, encoding="utf-8").read()
    imgs = re.findall(r"data:image/jpeg;base64,([A-Za-z0-9+/=]+)", s)
    caps = json.load(open(os.path.join(os.path.dirname(path), "vision_captions.json")))
    n = min(len(imgs), len(caps))
    return [(Image.open(io.BytesIO(base64.b64decode(imgs[i]))), caps[i]["reference"][:300]) for i in range(n)]


def from_jsonl(path):
    from PIL import Image
    out = []
    for line in open(path, encoding="utf-8"):
        if line.strip():
            j = json.loads(line)
            out.append((Image.open(j["path"]), str(j["caption"])[:600]))
    return out


def cands_for(n, k=10, seed=0):
    rng = random.Random(seed)
    out = []
    for i in range(n):
        o = [j for j in range(n) if j != i]
        rng.shuffle(o)
        out.append([i] + o[:k - 1])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--userdata", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-html")
    g.add_argument("--from-jsonl")
    a = ap.parse_args(argv)
    import mlx.core as mx
    import numpy as np
    items = from_html(a.from_html) if a.from_html else from_jsonl(a.from_jsonl)
    m = E.load_vision()
    feats = np.concatenate([E.encode(m, [im]) for im, _ in items])
    d = os.path.join(os.path.expanduser(a.userdata), "sense-sleep", "seat")
    os.makedirs(d, exist_ok=True)
    mx.save_safetensors(os.path.join(d, "vision_seat.safetensors"), {"features": mx.array(feats).astype(mx.float16)})
    json.dump({"eye": E.EYE_ID, "captions": [c for _, c in items], "cands": cands_for(len(items)), "n": len(items),
               "source": a.from_html or a.from_jsonl}, open(os.path.join(d, "vision_seat.json"), "w"), indent=1)
    print(json.dumps({"seat": d, "n": len(items)}))


if __name__ == "__main__":
    main()
