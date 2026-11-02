"""Anchor set: first 100 alpaca instructions, answered once by the BASE model (greedy, <=200 tokens) through the running vLLM server.
Usage: anchors.py TOKENIZER_DIR OUT_JSONL"""
import json, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from render import load_tok, render_chat


def prompts():
    try:
        from huggingface_hub import snapshot_download
        import pyarrow.parquet as pq, glob
        d = snapshot_download("tatsu-lab/alpaca", repo_type="dataset", allow_patterns=["*.parquet"])
        t = pq.read_table(glob.glob(d + "/**/*.parquet", recursive=True)[0]).to_pylist()[:100]
        return [(r["instruction"] + ("\n\n" + r["input"] if r.get("input") else "")) for r in t]
    except Exception as e:
        print("alpaca download failed, using inline prompts:", type(e).__name__, str(e)[:100])
        topics = ["the water cycle", "photosynthesis", "the French Revolution", "how vaccines work", "compound interest", "the Pythagorean theorem",
                  "black holes", "recycling", "the printing press", "supply and demand", "volcanoes", "the immune system", "renewable energy",
                  "the Roman Empire", "machine learning", "sleep", "bridges", "honeybees", "the internet", "tides"]
        forms = ["Explain {} in two sentences.", "Give three facts about {}.", "Write a short poem about {}.",
                 "What is a common misconception about {}?", "Describe {} to a ten year old."]
        return [f.format(t) for t in topics for f in forms]


def ask(p):
    body = {"model": "m", "messages": [{"role": "user", "content": p}], "max_tokens": 200, "temperature": 0}
    r = json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:8000/v1/chat/completions", json.dumps(body).encode(),
                                                                 {"Content-Type": "application/json"}), timeout=600).read())["choices"][0]
    return r["message"]["content"] or "", r["finish_reason"] == "length"


if __name__ == "__main__":
    tok = load_tok(sys.argv[1]); ps = prompts()
    with ThreadPoolExecutor(16) as ex:
        outs = list(ex.map(ask, ps))
    with open(sys.argv[2], "w") as f:
        for p, (reply, cut) in zip(ps, outs):
            if reply.strip():
                ids, mask = render_chat(tok, p, reply, truncated=cut); f.write(json.dumps({"prompt": p, "ids": ids, "mask": mask}) + "\n")
    print("anchors written:", len(ps))
