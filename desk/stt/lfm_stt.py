"""Local speech-to-text for Premonition Desk: LiquidAI LFM3-Audio-2B (MLX 8-bit) behind a tiny localhost HTTP server.

stdout: one line {"port": N} when listening. POST /transcribe: raw little-endian int16 16 kHz mono PCM -> {"text": "..."}.
GET /health -> {"ok": true}. POST /warm loads the model. Exits when stdin closes (so it dies with Desk). Nothing leaves this Mac.
"""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = os.environ.get("PREMONITION_STT_MODEL", "LiquidAI/LFM3-Audio-2B-MLX-8bit")
MAX_BYTES = 16000 * 2 * 60  # one minute of audio
MIN_SAMPLES = 1600          # shorter than 0.1 s is not speech


class MlxModel:
    """Loads lazily on first use."""

    def __init__(self, model_id=MODEL):
        self.model_id = model_id
        self.model = self.proc = None

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


def make_handler(model, lock, to_float=pcm_to_float):
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
                self._json(200, {"text": text})
            except Exception as e:  # report, keep serving
                self._json(500, {"error": "%s: %s" % (type(e).__name__, e)})

    return H


def make_server(model, port=0):
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(model, threading.Lock()))


def main():
    srv = make_server(MlxModel())
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
