"""I1b real check: Glim's eyes through the gateway on :8090 (MARKS-eyes-gateway-v1.md). Grading is fixed here, before the run.

usage: python check.py <engine-label> <png dir> <out.json> <big-server pid>
Text checks always; picture checks send image_features parts (built with glim_eyes.py) through the gateway.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

sys.path.insert(0, os.path.expanduser("~/learner-ops/assistant/glim"))
import glim_eyes as E  # noqa: E402

GW = "http://127.0.0.1:8090/v1/chat/completions"
PICS = ["1-weather", "2-shop", "3-dog", "4-map", "5-chart"]
# Visible things per picture (a thing counts when any of its words is in the reply). Lists are disjoint across pictures.
THINGS = {
    "1-weather": {"sun": ["sun", "sunny", "sunshine"], "temperature": ["75", "degree", "degrees", "temperature", "fahrenheit"],
                  "weather": ["weather", "forecast"], "sky": ["sky"]},
    "2-shop": {"apple": ["apple", "apples"], "banana": ["banana", "bananas"], "fruit": ["fruit", "fruits"],
               "price": ["price", "prices", "1.99", "0.99", "dollar", "dollars"], "cart": ["cart", "shop", "shopping", "store", "market"]},
    "3-dog": {"dog": ["dog", "dogs", "puppy", "puppies", "pup"], "adopt": ["adopt", "adoption", "shelter"], "max": ["max"],
              "paws": ["paw", "paws"]},
    "4-map": {"map": ["map", "maps"], "pin": ["pin", "marker", "location"],
              "route": ["route", "road", "roads", "street", "streets", "path", "directions", "navigation"], "lake": ["lake", "water"]},
    "5-chart": {"chart": ["chart", "graph", "bar", "bars"], "sales": ["sales"],
                "months": ["jan", "feb", "mar", "apr", "january", "february", "march", "april", "month", "monthly"]},
}
SHUFFLE = {i: (i + 2) % 5 for i in range(5)}   # control: picture i's question with picture (i+2)'s features, graded against i
TEXT = ["Name three colours of the rainbow.", "What is 12 + 7? Answer with just the number.", "Say hello in French."]


def matched(reply, things):
    t = reply.lower()
    return sorted(k for k, words in things.items()
                  if any(re.search(r"(?<![a-z0-9])" + re.escape(w) + r"(?![a-z0-9])", t) for w in words))


def chat(model, content, max_tokens, temperature=0.0):
    body = {"model": model, "messages": [{"role": "user", "content": content}], "max_tokens": max_tokens,
            "temperature": temperature, "stream": False}
    t0 = time.time()
    r = urllib.request.urlopen(urllib.request.Request(GW, json.dumps(body).encode(), {"content-type": "application/json"}),
                               timeout=600)
    j = json.loads(r.read())
    m = j["choices"][0]["message"]
    return {"status": r.status, "content": m.get("content") or "", "reasoning": m.get("reasoning_content") or m.get("reasoning") or "",
            "s": round(time.time() - t0, 2), "usage": j.get("usage")}


def footprint_mb(pid):
    try:
        out = subprocess.run(["/usr/bin/footprint", "-p", str(pid)], capture_output=True, text=True, timeout=20).stdout
        m = re.search(r"Footprint:\s*([\d.]+)\s*([KMG]B)", out)
        if m:
            return round(float(m.group(1)) * {"KB": 1 / 1024, "MB": 1, "GB": 1024}[m.group(2)], 1)
    except Exception:  # noqa: BLE001
        pass
    return None


def rss_mb(pid):
    try:
        return round(int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(pid)]).strip()) / 1024, 1)
    except Exception:  # noqa: BLE001
        return None


def main():
    label, pngdir, out_path, pid = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    out = {"engine": label, "text": [], "pictures": [], "control": [], "mem": {}}
    peak = {"rss": 0.0, "footprint": 0.0}
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            r, f = rss_mb(pid), footprint_mb(pid)
            peak["rss"] = max(peak["rss"], r or 0)
            peak["footprint"] = max(peak["footprint"], f or 0)
            stop.wait(2)
    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    out["mem"]["idle_rss_mb"], out["mem"]["idle_footprint_mb"] = rss_mb(pid), footprint_mb(pid)

    for q in TEXT:
        out["text"].append(dict(chat("lfm3-fast", q, 40), q=q))
    think = chat("lfm3", "Why is the sky blue? One sentence.", 400)
    out["text_thinking"] = think

    from PIL import Image
    enc = E.load_vision()
    feats = []
    for n in PICS:
        t0 = time.time()
        f = E.encode(enc, [Image.open(os.path.join(pngdir, n + ".png")).convert("RGB")])[0]
        feats.append({"type": "image_features", "image_features": {"f16": E.f16_b64(f), "shape": [64, 768], "eye": E.EYE_ID},
                      "_ms": round((time.time() - t0) * 1000, 1)})
    del enc

    def ask(feat):
        part = {k: v for k, v in feat.items() if not k.startswith("_")}
        return chat("lfm3-fast", [part, {"type": "text", "text": "\nDescribe this image."}], 120)

    for i, n in enumerate(PICS):
        r = ask(feats[i])
        m = matched(r["content"], THINGS[n])
        out["pictures"].append(dict(r, pic=n, eyes_ms=feats[i]["_ms"], things=m, ok=len(m) >= 2))
    for i, n in enumerate(PICS):
        j = SHUFFLE[i]
        r = ask(feats[j])
        m = matched(r["content"], THINGS[n])
        out["control"].append(dict(r, pic=n, features_of=PICS[j], things=m, ok=len(m) >= 2))
    stop.set()
    th.join(5)
    out["mem"]["peak_rss_mb"], out["mem"]["peak_footprint_mb"] = peak["rss"], peak["footprint"]
    out["summary"] = {"pictures_ok": sum(p["ok"] for p in out["pictures"]), "control_ok": sum(p["ok"] for p in out["control"]),
                      "text_nonempty": sum(bool(t["content"].strip()) for t in out["text"]),
                      "thinking_ok": think["status"] == 200 and bool((think["content"] + think["reasoning"]).strip())}
    json.dump(out, open(out_path, "w"), indent=1)
    print(json.dumps(out["summary"]))


if __name__ == "__main__":
    main()
