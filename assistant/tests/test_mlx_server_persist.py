"""Tests for mlx_server_persist.py. mlx is mocked; the real-mlx test skips where mlx is missing."""
import http.client
import json
import sys
import tempfile
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import mlx_server_persist as P  # noqa: E402

KEY = ("mlx-community/fake", None, None)


class FakeCache:
    def __init__(self, n=100):
        self.nbytes = n


class FakeEntry:
    def __init__(self, cache, cache_type):
        self.prompt_cache, self.cache_type = cache, cache_type
        self.nbytes = sum(c.nbytes for c in cache)


class FakeLRU:
    """Just the attributes of mlx_lm's LRUPromptCache that the wrapper touches."""

    def __init__(self):
        self._lru = types.SimpleNamespace(_lrus={"assistant": [], "user": [], "system": []})
        self.entries = {}
        self._trie = types.SimpleNamespace(get=lambda m, t: self.entries[(m, tuple(t))])

    def insert_cache(self, model, tokens, prompt_cache, *, cache_type="assistant"):
        self.entries[(model, tuple(tokens))] = FakeEntry(prompt_cache, cache_type)
        self._lru._lrus[cache_type].append((model, tokens))


class FakeDisk:
    """save_fn/load_fn that keep caches in a dict keyed by path, plus an empty marker file."""

    def __init__(self):
        self.blobs = {}

    def save(self, path, cache, metadata):
        # the store writes <base>.tmp.safetensors then renames it to <base>.safetensors
        self.blobs[path.replace(".tmp.safetensors", ".safetensors")] = (cache, dict(metadata))
        Path(path).write_text("x")

    def load(self, path):
        if not Path(path).exists():
            raise FileNotFoundError(path)
        return self.blobs[path]


def make_store(tmp, disk=None):
    disk = disk or FakeDisk()
    return P.PrefixStore(tmp, disk.save, disk.load), disk


class HelperTests(unittest.TestCase):
    def test_split_args(self):
        d, rest = P.split_args(["--model", "m", "--cache-dir", "/x", "--port", "1"])
        self.assertEqual((d, rest), ("/x", ["--model", "m", "--port", "1"]))
        d, rest = P.split_args(["--cache-dir=/y", "--port", "1"])
        self.assertEqual((d, rest), ("/y", ["--port", "1"]))
        self.assertEqual(P.split_args(["--port", "1"]), (None, ["--port", "1"]))

    def test_version_check(self):
        self.assertTrue(P.check_version("0.32.2"))
        self.assertFalse(P.check_version("0.32.3"))
        self.assertFalse(P.check_version(None))

    def test_pick_longest_system_entry_for_this_model_only(self):
        lru = FakeLRU()
        lru.insert_cache(KEY, [1, 2, 3], [FakeCache()], cache_type="system")
        lru.insert_cache(KEY, [1, 2, 3, 4, 5], [FakeCache()], cache_type="system")
        lru.insert_cache(("other", None, None), list(range(50)), [FakeCache()], cache_type="system")
        lru.insert_cache(KEY, list(range(99)), [FakeCache()], cache_type="user")
        tokens, entry = P.pick_system_entry(lru, KEY)
        self.assertEqual(tokens, [1, 2, 3, 4, 5])
        self.assertEqual(entry.cache_type, "system")
        self.assertIsNone(P.pick_system_entry(lru, KEY, min_tokens=10))
        self.assertIsNone(P.pick_system_entry(FakeLRU(), KEY))


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_roundtrip_restore_inserts_system_entry(self):
        store, disk = make_store(self.tmp.name)
        self.assertEqual(store.save(KEY, [5, 6, 7], [FakeCache(10), FakeCache(20)]), "saved")
        store2, _ = make_store(self.tmp.name, disk)  # "restart": new store, same disk
        lru = FakeLRU()
        self.assertEqual(P.restore(lru, KEY, store2), 3)
        e = lru.entries[(KEY, (5, 6, 7))]
        self.assertEqual((e.cache_type, e.nbytes), ("system", 30))

    def test_unchanged_prefix_is_not_resaved(self):
        store, disk = make_store(self.tmp.name)
        self.assertEqual(store.save(KEY, [1, 2], [FakeCache()]), "saved")
        self.assertEqual(store.save(KEY, [1, 2], [FakeCache()]), "unchanged")
        self.assertEqual(store.save(KEY, [1, 2, 3], [FakeCache()]), "saved")

    def test_other_model_key_or_version_not_restored(self):
        store, disk = make_store(self.tmp.name)
        store.save(KEY, [1, 2], [FakeCache()])
        self.assertIsNone(make_store(self.tmp.name, disk)[0].load(("other", None, None)))
        side = next(Path(self.tmp.name).glob("*.json"))
        d = json.loads(side.read_text())
        d["mlx_lm"] = "0.1.0"
        side.write_text(json.dumps(d))
        self.assertIsNone(make_store(self.tmp.name, disk)[0].load(KEY))

    def test_id_mismatch_and_corrupt_files_start_cold(self):
        store, disk = make_store(self.tmp.name)
        store.save(KEY, [1, 2], [FakeCache()])
        side = next(Path(self.tmp.name).glob("*.json"))
        d = json.loads(side.read_text())
        d["id"] = "different"
        side.write_text(json.dumps(d))
        self.assertIsNone(make_store(self.tmp.name, disk)[0].load(KEY))
        side.write_text("{not json")
        self.assertIsNone(make_store(self.tmp.name, disk)[0].load(KEY))
        self.assertEqual(P.restore(FakeLRU(), KEY, make_store(self.tmp.name, disk)[0]), 0)

    def test_empty_dir_is_cold_start(self):
        self.assertEqual(P.restore(FakeLRU(), KEY, make_store(self.tmp.name)[0]), 0)

    def test_save_current_reports(self):
        store, _ = make_store(self.tmp.name)
        lru = FakeLRU()
        self.assertFalse(P.save_current(lru, KEY, store)["saved"])  # nothing cached yet
        self.assertFalse(P.save_current(lru, None, store)["saved"])  # model not loaded
        lru.insert_cache(KEY, [1, 2, 3], [FakeCache(40)], cache_type="system")
        r = P.save_current(lru, KEY, store)
        self.assertEqual((r["saved"], r["tokens"], r["bytes"]), (True, 3, 40))
        self.assertTrue(P.save_current(lru, KEY, store)["unchanged"])


# ---- a fake mlx_lm.server module, to test the patching itself

def make_fake_server_module():
    S = types.ModuleType("fake_mlx_lm_server")
    S.calls = []

    class ModelProvider:
        def __init__(self):
            self.model_key = None

        def _load(self, *a):
            S.calls.append("orig_load")
            self.model_key = KEY

    class ResponseGenerator:
        def __init__(self, model_provider, prompt_cache):
            self.model_provider, self.prompt_cache = model_provider, prompt_cache
            self.ready = threading.Event()
            self._stop = False
            self.thread = threading.Thread(target=self._gen, daemon=True)
            self.thread.start()  # like the real one: starts in __init__

        def _gen(self):
            self.model_provider._load()
            self.ready.set()
            while not self._stop:
                self._next_request(0.01)

        def _next_request(self, timeout=None):
            threading.Event().wait(timeout or 0)
            return None

        def generation_available(self):
            return self.thread.is_alive()

    class APIHandler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _set_completion_headers(self, code=200):
            self.send_response(code)
            self.send_header("Content-type", "application/json")

        def do_POST(self):
            data = b"stock"
            self._set_completion_headers(404)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    S.ModelProvider, S.ResponseGenerator, S.APIHandler = ModelProvider, ResponseGenerator, APIHandler
    S.LRUPromptCache = FakeLRU

    def run(host, port, model_provider, server_class=None, handler_class=APIHandler):
        S.run_handler = handler_class
        lru = FakeLRU()
        S.rg = ResponseGenerator(model_provider, lru)
        S.lru = lru

    S.run = run
    return S


class PatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.disk = FakeDisk()

    def start(self, preload=False):
        store, _ = make_store(self.tmp.name, self.disk)
        if preload:
            store.save(KEY, [9, 8, 7, 6], [FakeCache(64)])
            store = make_store(self.tmp.name, self.disk)[0]
        S = make_fake_server_module()
        self.assertEqual(P.missing_hooks(S), [])
        handler = P.install(S, store)
        S.run("h", 0, S.ModelProvider())
        S.rg.ready.wait(5)
        self.addCleanup(lambda: setattr(S.rg, "_stop", True))
        return S, handler

    def test_missing_hooks_detected(self):
        S = make_fake_server_module()
        del S.ResponseGenerator._next_request
        self.assertEqual(P.missing_hooks(S), ["ResponseGenerator._next_request"])

    def test_restore_happens_after_load_before_requests(self):
        S, _ = self.start(preload=True)
        self.assertIn("orig_load", S.calls)
        e = S.lru.entries[(KEY, (9, 8, 7, 6))]
        self.assertEqual(e.cache_type, "system")

    def test_cold_start_still_works(self):
        S, _ = self.start()
        self.assertEqual(S.lru.entries, {})

    def test_save_endpoint_runs_in_generation_thread_and_other_paths_stay_stock(self):
        S, handler = self.start()
        S.lru.insert_cache(KEY, [1, 2, 3], [FakeCache(5)], cache_type="system")
        srv = ThreadingHTTPServer(("127.0.0.1", 0),
                                  lambda *a, **k: self._make(handler, S.rg, *a, **k))
        srv.daemon_threads = True
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)

        def post(path, body=b"{}"):
            c = http.client.HTTPConnection("127.0.0.1", srv.server_port, timeout=10)
            c.request("POST", path, body, {"Content-Type": "application/json"})
            r = c.getresponse()
            out = (r.status, r.read())
            c.close()
            return out

        st, data = post(P.SAVE_PATH)
        self.assertEqual(st, 200)
        self.assertEqual(json.loads(data)["tokens"], 3)
        self.assertTrue(list(Path(self.tmp.name).glob("prefix-*.json")))
        st, data = post(P.SAVE_PATH, b'{"min_tokens": 99}')
        self.assertEqual((st, json.loads(data)["saved"]), (200, False))
        self.assertEqual(post(P.SAVE_PATH, b"nope")[0], 400)
        self.assertEqual(post("/v1/chat/completions"), (404, b"stock"))

    @staticmethod
    def _make(handler, rg, *a, **k):
        h = handler.__new__(handler)
        h.response_generator = rg
        handler.__init__(h, *a, **k)
        return h


@unittest.skipUnless(
    __import__("importlib").util.find_spec("mlx") and __import__("importlib").util.find_spec("mlx_lm"),
    "mlx / mlx_lm not installed")
class RealMlxTests(unittest.TestCase):
    def test_version_and_hooks_and_cache_roundtrip(self):
        import mlx.core as mx
        import mlx_lm
        import mlx_lm.server as S
        from mlx_lm.models.cache import KVCache, load_prompt_cache, save_prompt_cache
        if not P.check_version(mlx_lm.__version__):
            self.skipTest("mlx_lm %s is not %s" % (mlx_lm.__version__, P.SUPPORTED_VERSION))
        self.assertEqual(P.missing_hooks(S), [])
        c = KVCache()
        c.update_and_fetch(mx.ones((1, 2, 4, 8)), mx.ones((1, 2, 4, 8)))
        with tempfile.TemporaryDirectory() as d:
            store = P.PrefixStore(d, save_prompt_cache,
                                  lambda p: load_prompt_cache(p, return_metadata=True))
            store.save(KEY, [1, 2, 3], [c])
            tokens, cache = P.PrefixStore(
                d, save_prompt_cache, lambda p: load_prompt_cache(p, return_metadata=True)).load(KEY)
            self.assertEqual(tokens, [1, 2, 3])
            self.assertEqual(cache[0].nbytes, c.nbytes)


if __name__ == "__main__":
    unittest.main()
