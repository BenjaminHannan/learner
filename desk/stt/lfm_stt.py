"""Local speech-to-text for Premonition Desk: LiquidAI LFM3-Audio-2B (MLX 4-bit) behind a tiny localhost HTTP server.

stdout: one line {"port": N} when listening. POST /transcribe: raw little-endian int16 16 kHz mono PCM -> {"text": "..."}.
GET /health -> {"ok": true}. POST /warm loads the model. Exits when stdin closes (so it dies with Desk). Nothing leaves this Mac.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.environ.get("PREMONITION_STT_MODEL", "LiquidAI/LFM3-Audio-2B-MLX-4bit")
MAX_BYTES = 16000 * 2 * 60  # one minute of audio
MIN_SAMPLES = 1600          # shorter than 0.1 s is not speech
IDLE_S = float(os.environ.get("PREMONITION_STT_IDLE_S", "300"))  # unload after this long unused, to give the memory back


class MlxModel:
    """Loads lazily on first use; unload() frees it again (the idle timer in main calls it)."""

    def __init__(self, model_id=MODEL):
        self.model_id = model_id
        self.model = self.proc = None

    def unload(self):
        if self.model is None:
            return
        self.model = self.proc = None
        import gc
        gc.collect()
        try:
            import mlx.core as mx
            mx.clear_cache()
        except Exception:
            pass

    def _load(self):
        if self.model is None:
            from mlx_vlm import load
            self.model, self.proc = load(self.model_id)

    def warm(self):
        self._load()

    def transcribe(self, samples):
        self._load()
        from mlx_vlm import generate
        msgs = [{"role": "system", "content": "Perform ASR in English."}, {"role": "user", "content": "<|audio|>"}]
        prompt = self.proc.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        out = generate(self.model, self.proc, prompt, audio=[samples], temperature=0.0, max_tokens=200, verbose=False)
        return (getattr(out, "text", out) or "").strip()


def pcm_to_float(body):
    import numpy as np
    return np.frombuffer(body[: len(body) // 2 * 2], dtype="<i2").astype("float32") / 32768.0


def make_handler(model, lock, to_float=pcm_to_float, touch=None):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._json(200, {"ok": True}) if self.path == "/health" else self._json(404, {"error": "not found"})

        def do_POST(self):
            if touch:
                touch()
            try:
                n = int(self.headers.get("Content-Length") or 0)
                if self.path == "/warm":
                    self.rfile.read(n)
                    with lock:
                        model.warm()
                    return self._json(200, {"ok": True})
                if self.path != "/transcribe":
                    return self._json(404, {"error": "not found"})
                if n > MAX_BYTES:
                    if n <= 8 * MAX_BYTES:  # drain so the client sees the reply, not a broken pipe
                        while n > 0:
                            n -= len(self.rfile.read(min(n, 65536)) or b"\0" * n)
                    return self._json(413, {"error": "audio too long"})
                body = self.rfile.read(n)
                if len(body) // 2 < MIN_SAMPLES:
                    return self._json(200, {"text": ""})
                samples = to_float(body)
                with lock:
                    text = model.transcribe(samples)
                if touch:
                    touch()  # a long first load must not count as idle time
                self._json(200, {"text": text})
            except Exception as e:  # report, keep serving
                self._json(500, {"error": "%s: %s" % (type(e).__name__, e)})

    return H


def make_server(model, port=0):
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(model, threading.Lock()))


def idle_unloader(model, lock, last, idle_s=IDLE_S, every=15):
    """Every `every` s: if no request for idle_s, unload the model (the next request loads it again, about 5 s)."""
    import time
    while True:
        time.sleep(every)
        if idle_s > 0 and model.model is not None and time.time() - last[0] > idle_s:
            with lock:
                if time.time() - last[0] > idle_s:
                    model.unload()


def main():
    import time
    model, lock, last = MlxModel(), threading.Lock(), [time.time()]
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(model, lock, touch=lambda: last.__setitem__(0, time.time())))
    threading.Thread(target=idle_unloader, args=(model, lock, last), daemon=True).start()
    print(json.dumps({"port": srv.server_address[1]}), flush=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        while sys.stdin.read(4096):
            pass
    except Exception:
        pass
    os._exit(0)


if __name__ == "__main__":
    main()
