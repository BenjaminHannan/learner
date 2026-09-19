"""Simple-English text from the teacher model (language only; never a fact target).

Resumable: each request id is written once to data/english/raw/<writer>.jsonl.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOPICS = (
    "a rainy day", "baking bread", "a lost glove", "feeding ducks", "a new puppy", "planting seeds", "a trip to the market",
    "building a sandcastle", "a broken toy", "a birthday", "the first snow", "a sleepy cat", "washing the dishes", "a kite",
    "a visit to grandma", "a thunderstorm", "a picnic", "learning to swim", "a lost key", "sharing lunch", "a noisy morning",
    "the moon", "a garden", "a school day", "fixing a bike", "a friendly neighbour", "a tall tree", "a busy bakery", "a river",
    "the seasons", "counting apples", "a treasure hunt", "a quiet library", "a farm", "a train ride", "a painted fence",
    "a big box", "a lost sheep", "making soup", "the wind", "a bridge", "a small boat", "a hungry bird", "a warm fire",
    "a muddy path", "cleaning a room", "a surprise", "a game of hide and seek", "a race", "an old clock", "a basket of eggs",
    "the night sky", "a stubborn goat", "a well", "a windmill", "carrying water", "a candle", "a snowman", "a lamp",
    "tidying toys", "a broken cup", "trading marbles", "a map", "a mirror", "a song", "a rope swing", "the sun", "a pond",
    "an apple tree", "a lost shoe", "a helpful robot", "a shy mouse", "a long walk", "a secret door", "a sore knee",
)
FORMS = (
    "a short story", "a short dialogue between two people", "a simple explanation of how something works",
    "a short description", "a short story with a small problem that gets solved", "simple step-by-step instructions",
)
PROMPT = (
    "Write {form} about {topic} for a five-year-old reader. Use short sentences and simple, common words. "
    "About 120 to 200 words. Plain text only: no title, no lists, no markdown."
)


def requests(n: int) -> list[dict]:
    out = []
    for i in range(n):
        topic, form = TOPICS[i % len(TOPICS)], FORMS[(i // len(TOPICS)) % len(FORMS)]
        rid = hashlib.sha256(f"{i}|{topic}|{form}".encode()).hexdigest()[:16]
        out.append({"id": rid, "index": i, "topic": topic, "form": form, "prompt": PROMPT.format(form=form, topic=topic)})
    return out


def call(url: str, model: str, prompt: str, seed: int) -> tuple[str, int]:
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.9, "top_p": 0.95,
            "max_tokens": 450, "seed": seed, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=600) as response:
                data = json.load(response)
            return data["choices"][0]["message"]["content"].strip(), data["usage"]["completion_tokens"]
        except Exception:
            if attempt == 2:
                raise
            time.sleep(10 * (attempt + 1))
    raise AssertionError


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18081")
    parser.add_argument("--model", default="qwen3.8-27b")
    parser.add_argument("--writer", default="qwen3.8-27b")
    parser.add_argument("--requests", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    out = ROOT / "data" / "english" / "raw" / f"{args.writer}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(line)["id"] for line in out.read_text().splitlines() if line.strip()}
    todo = [r for r in requests(args.requests) if r["id"] not in done]
    lock = threading.Lock()
    start, tokens = time.time(), 0

    def run(r: dict) -> None:
        nonlocal tokens
        t = time.time()
        text, n = call(args.url, args.model, r["prompt"], r["index"])
        record = {**r, "writer": args.writer, "text": text, "tokens": n, "seconds": round(time.time() - t, 2)}
        with lock:
            with out.open("a") as handle:
                handle.write(json.dumps(record) + "\n")
            tokens += n
            print(f"{len(done)} done, {tokens / (time.time() - start):.1f} tok/s", flush=True)
            done.add(r["id"])

    with cf.ThreadPoolExecutor(args.workers) as pool:
        for future in cf.as_completed([pool.submit(run, r) for r in todo]):
            future.result()


if __name__ == "__main__":
    main()
