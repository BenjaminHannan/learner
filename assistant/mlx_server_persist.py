#!/usr/bin/env python3
"""mlx_lm.server with an on-disk copy of the system-prompt KV cache.

Usage (same arguments as `python -m mlx_lm.server`, plus one):

    python assistant/mlx_server_persist.py --model ... --port 18080 --cache-dir DIR

Why: Qwen3.6 is a hybrid (Gated DeltaNet + full attention) model, so its prompt caches
cannot be trimmed, and the ~12k-token system+tools prefix takes ~50-60 s to prefill on an M1.
mlx_lm keeps it only in memory, so every server restart loses it.

What this does (patched against mlx-lm 0.32.2 only; any other version runs stock):
  * after the model loads (in mlx_lm's generation thread, before any request is served) it loads
    DIR/prefix-<hash>.safetensors + .json when their model key matches, and inserts the cache
    into the server's LRUPromptCache as a "system" entry under the saved token list;
  * POST /v1/internal/save_prefix saves the longest "system" entry of the LRU cache for the
    loaded model. The save runs in the generation thread (MLX streams are per thread).
    The gateway calls it after a successful warm. Body (optional JSON): {"min_tokens": N}.

The patches are small wrappers: ModelProvider._load, ResponseGenerator.__init__,
ResponseGenerator._next_request, and a handler subclass passed to run(). Stdlib only here;
mlx is imported lazily, so the helpers can be unit-tested without it.
"""
import hashlib
import json
import logging
import os
import queue
import sys
import threading
import time
import uuid

SUPPORTED_VERSION = "0.32.2"
SAVE_PATH = "/v1/internal/save_prefix"
SAVE_TIMEOUT_S = 300
PREFIX = "prefix-"

log = logging.getLogger("mlx_server_persist")


def say(msg):
    """Always visible, even before/without logging.basicConfig."""
    print("persist: " + msg, file=sys.stderr, flush=True)


# ------------------------------------------------------------------ pure helpers

def split_args(argv):
    """Remove --cache-dir DIR / --cache-dir=DIR from argv -> (cache_dir or None, remaining argv)."""
    rest, cache_dir, i = [], None, 0
    while i < len(argv):
        a = argv[i]
        if a == "--cache-dir" and i + 1 < len(argv):
            cache_dir = argv[i + 1]
            i += 2
            continue
        if a.startswith("--cache-dir="):
            cache_dir = a.split("=", 1)[1]
        else:
            rest.append(a)
        i += 1
    return cache_dir, rest


def key_json(model_key):
    """Stable string for a ModelProvider.model_key tuple (model_path, adapter_path, draft_path)."""
    return json.dumps(list(model_key), sort_keys=True)


def tokens_digest(tokens):
    return hashlib.sha1(json.dumps(list(tokens)).encode()).hexdigest()


def pick_system_entry(lru, model_key, min_tokens=1):
    """Longest 'system' entry for model_key -> (tokens, CacheEntry) or None.

    lru is mlx_lm's LRUPromptCache. Reads _lru._lrus["system"] (deque of (model, tokens)) and
    _trie.get(model, tokens). Called from the generation thread, so nothing mutates under us.
    """
    best = None
    for model, tokens in list(lru._lru._lrus.get("system", ())):
        if model != model_key or len(tokens) < min_tokens:
            continue
        if best is None or len(tokens) > len(best):
            best = tokens
    if best is None:
        return None
    return list(best), lru._trie.get(model_key, best)


class PrefixStore:
    """One saved prefix per model key: DIR/prefix-<hash>.safetensors + DIR/prefix-<hash>.json.

    save_fn(path, cache, metadata) / load_fn(path) -> (cache, metadata) are mlx_lm's
    save_prompt_cache / load_prompt_cache (injected so tests can fake them).
    The .json holds the token list; both files carry the same random id, checked on load.
    """

    def __init__(self, cache_dir, save_fn, load_fn):
        self.dir = cache_dir
        self.save_fn = save_fn
        self.load_fn = load_fn
        self._last_saved = {}  # key_json -> tokens_digest, skips re-saving an unchanged prefix

    def _base(self, model_key):
        h = hashlib.sha1(key_json(model_key).encode()).hexdigest()[:12]
        return os.path.join(self.dir, PREFIX + h)

    def save(self, model_key, tokens, prompt_cache):
        """-> 'saved' | 'unchanged'. Writes the cache first, the token sidecar last (atomic renames)."""
        kj, digest = key_json(model_key), tokens_digest(tokens)
        base = self._base(model_key)
        if self._last_saved.get(kj) == digest and os.path.exists(base + ".json"):
            return "unchanged"
        os.makedirs(self.dir, exist_ok=True)
        rid = uuid.uuid4().hex
        tmp_st = base + ".tmp.safetensors"
        self.save_fn(tmp_st, prompt_cache, {"id": rid, "model_key": kj})
        os.replace(tmp_st, base + ".safetensors")
        tmp_js = base + ".json.tmp"
        with open(tmp_js, "w") as f:
            json.dump({"id": rid, "model_key": kj, "mlx_lm": SUPPORTED_VERSION,
                       "saved_at": time.time(), "tokens": list(tokens)}, f)
        os.replace(tmp_js, base + ".json")
        self._last_saved[kj] = digest
        return "saved"

    def load(self, model_key):
        """-> (tokens, prompt_cache) or None when missing / mismatched / unreadable."""
        base = self._base(model_key)
        try:
            with open(base + ".json") as f:
                side = json.load(f)
            if side.get("model_key") != key_json(model_key) or side.get("mlx_lm") != SUPPORTED_VERSION:
                return None
            cache, meta = self.load_fn(base + ".safetensors")
            if meta.get("id") != side.get("id") or meta.get("model_key") != side["model_key"]:
                say("cache files do not belong together (id mismatch); ignoring them")
                return None
            tokens = side["tokens"]
            if not tokens or not all(isinstance(t, int) for t in tokens):
                return None
            self._last_saved[side["model_key"]] = tokens_digest(tokens)
            return tokens, cache
        except FileNotFoundError:
            return None
        except Exception as e:  # corrupt file, format change, ...: start cold instead of dying
            say("could not load saved cache: %r" % (e,))
            return None


def restore(lru, model_key, store, eval_fn=None):
    """Insert the saved prefix for model_key into lru. -> token count restored (0 = nothing)."""
    t0 = time.time()
    got = store.load(model_key)
    if got is None:
        say("no saved prefix cache for this model in %s (cold start)" % store.dir)
        return 0
    tokens, cache = got
    if eval_fn:
        eval_fn(cache)
    lru.insert_cache(model_key, tokens, cache, cache_type="system")
    say("restored system prefix: %d tokens, %.2f GB in %.1fs" % (
        len(tokens), sum(c.nbytes for c in cache) / 1e9, time.time() - t0))
    return len(tokens)


def save_current(lru, model_key, store, min_tokens=1):
    """Save the longest system entry. -> result dict for the HTTP reply."""
    t0 = time.time()
    if model_key is None:
        return {"saved": False, "reason": "model not loaded"}
    picked = pick_system_entry(lru, model_key, min_tokens)
    if picked is None:
        return {"saved": False, "reason": "no system entry in the prompt cache yet"}
    tokens, entry = picked
    status = store.save(model_key, tokens, entry.prompt_cache)
    secs = time.time() - t0
    if status == "saved":
        say("saved system prefix: %d tokens, %.2f GB in %.1fs" % (len(tokens), entry.nbytes / 1e9, secs))
    return {"saved": status == "saved", "unchanged": status == "unchanged",
            "tokens": len(tokens), "bytes": entry.nbytes, "seconds": round(secs, 2)}


# ------------------------------------------------------------------ patching mlx_lm.server

def check_version(version):
    return version == SUPPORTED_VERSION


def missing_hooks(S):
    """Names the patches rely on that this mlx_lm.server lacks (empty list = safe to patch)."""
    need = [("ModelProvider", "_load"), ("ResponseGenerator", "__init__"),
            ("ResponseGenerator", "_next_request"), ("APIHandler", "do_POST"),
            ("APIHandler", "_set_completion_headers"), ("LRUPromptCache", "insert_cache")]
    out = ["%s.%s" % n for n in need if not hasattr(getattr(S, n[0], None), n[1])]
    if not callable(getattr(S, "run", None)):
        out.append("run")
    return out


def install(S, store, eval_fn=None):
    """Patch the mlx_lm.server module object S in place. Call only after check_version()."""

    orig_load = S.ModelProvider._load
    orig_rg_init = S.ResponseGenerator.__init__
    orig_next = S.ResponseGenerator._next_request
    orig_run = S.run

    def _load(self, *a, **kw):
        out = orig_load(self, *a, **kw)  # sets self.model_key last
        lru = getattr(self, "_persist_lru", None)
        if lru is not None:
            try:
                restore(lru, self.model_key, store, eval_fn)
            except Exception as e:
                say("restore failed, continuing cold: %r" % (e,))
        return out

    def rg_init(self, model_provider, prompt_cache):
        # Runs before the generation thread starts: hand it the LRU and a job queue.
        model_provider._persist_lru = prompt_cache
        self._persist_jobs = queue.Queue()
        orig_rg_init(self, model_provider, prompt_cache)

    def _next_request(self, *a, **kw):
        # The generation thread calls this every loop (<= 0.1 s idle). Run save jobs here so
        # MLX work stays on that thread and never races with cache mutation.
        jobs = getattr(self, "_persist_jobs", None)
        while jobs is not None and not jobs.empty():
            fn, done, box = jobs.get_nowait()
            try:
                box["result"] = fn()
            except Exception as e:
                logging.exception("persist job failed")
                box["result"] = {"saved": False, "reason": "error: %r" % (e,)}
            done.set()
        return orig_next(self, *a, **kw)

    class PersistHandler(S.APIHandler):
        def do_POST(self):
            if self.path != SAVE_PATH:
                return super().do_POST()
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}") if n else {}
                min_tokens = int(body.get("min_tokens", 1)) if isinstance(body, dict) else 1
            except (ValueError, TypeError):
                return self._reply(400, {"error": "bad request body"})
            rg = self.response_generator
            if not rg.generation_available():
                return self._reply(503, {"error": "generation thread not running"})
            done, box = threading.Event(), {}
            rg._persist_jobs.put((
                lambda: save_current(rg.prompt_cache, rg.model_provider.model_key, store, min_tokens),
                done, box))
            if not done.wait(SAVE_TIMEOUT_S):
                return self._reply(504, {"error": "save timed out"})
            self._reply(200, box["result"])

        def _reply(self, code, obj):
            data = json.dumps(obj).encode()
            self._set_completion_headers(code)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def run(host, port, model_provider, *a, **kw):
        kw.setdefault("handler_class", PersistHandler)
        return orig_run(host, port, model_provider, *a, **kw)

    S.ModelProvider._load = _load
    S.ResponseGenerator.__init__ = rg_init
    S.ResponseGenerator._next_request = _next_request
    S.run = run  # main() looks run() up in the module globals at call time
    return PersistHandler


def mlx_eval(cache):
    """Force lazily loaded cache arrays into memory so the first request does not pay for disk."""
    import mlx.core as mx
    from mlx.utils import tree_flatten
    arrays = [v for _, v in tree_flatten([c.state for c in cache]) if isinstance(v, mx.array)]
    mx.eval(arrays)


def main(argv=None):
    cache_dir, rest = split_args(list(sys.argv[1:] if argv is None else argv))
    try:
        import mlx_lm
        import mlx_lm.server as S
    except ImportError as e:
        say("cannot import mlx_lm (%s); this wrapper needs the Mac venv" % e)
        return 1
    sys.argv = [sys.argv[0]] + rest

    version = getattr(mlx_lm, "__version__", None)
    if not cache_dir:
        say("no --cache-dir given: running stock mlx_lm.server")
    elif not check_version(version):
        say("REFUSING to patch: mlx_lm %s != %s; running stock mlx_lm.server without "
            "cache persistence" % (version, SUPPORTED_VERSION))
    elif missing_hooks(S):
        say("REFUSING to patch: mlx_lm.server lacks %s; running stock" % ", ".join(missing_hooks(S)))
    else:
        from mlx_lm.models.cache import load_prompt_cache, save_prompt_cache
        cache_dir = os.path.expanduser(cache_dir)
        store = PrefixStore(
            cache_dir, save_prompt_cache,
            lambda p: load_prompt_cache(p, return_metadata=True))
        install(S, store, mlx_eval)
        say("mlx_lm %s patched; cache dir %s; save endpoint POST %s" % (version, cache_dir, SAVE_PATH))
    S.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
