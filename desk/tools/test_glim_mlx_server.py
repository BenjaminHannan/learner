"""Tests for glim_mlx_server.py (no model, no MLX needed: a fake mx). Run: python -m pytest -q desk/tools/test_glim_mlx_server.py"""
import json
import os
import sys
import tempfile
import types

sys.path.insert(0, os.path.dirname(__file__))
import glim_mlx_server as W  # noqa: E402

GB = 1 << 30


class FakeMx:
    float32 = "f32"

    def __init__(self, max_rec=30 * GB):
        self.wired, self.cache, self.cleared, self.allocs = 0, None, 0, []
        self.max_rec = max_rec

    def device_info(self):
        return {"max_recommended_working_set_size": self.max_rec}

    def set_wired_limit(self, n):
        prev, self.wired = self.wired, n
        return prev

    def set_cache_limit(self, n):
        prev, self.cache = self.cache, n
        return prev

    def clear_cache(self):
        self.cleared += 1

    def zeros(self, shape, dtype=None):
        self.allocs.append(shape[0] * 4)
        return object()

    def eval(self, *a):
        pass


def test_setting_defaults_off_and_reads_settings_json():
    assert W.setting_on(None, None) is False
    assert W.setting_on("/nope/settings.json", None) is False
    d = tempfile.mkdtemp()
    p = os.path.join(d, "settings.json")
    open(p, "w").write("{bad json")
    assert W.setting_on(p, None) is False, "unreadable settings: off"
    json.dump({"keepBrainInMemory": "yes"}, open(p, "w"))
    assert W.setting_on(p, None) is False, "only a real true turns it on"
    json.dump({"keepBrainInMemory": True}, open(p, "w"))
    assert W.setting_on(p, None) is True
    assert W.setting_on(p, "off") is False, "the explicit flag wins"
    assert W.setting_on(None, "on") is True


def test_plan_caps_at_recommended():
    assert W.plan(4 * GB, 2 * GB, 30 * GB) == (6 * GB + W.MARGIN, False)
    assert W.plan(29 * GB, 2 * GB, 30 * GB) == (30 * GB, True)


def test_flags_are_removed_before_mlx_lm_sees_them():
    argv = ["x", "--model", "m", "--keep-in-memory", "on", "--kv-buffer", "1GB", "--port", "1"]
    assert W.pop_flag(argv, "--keep-in-memory") == "on"
    assert W.pop_flag(argv, "--kv-buffer") == "1GB"
    assert argv == ["x", "--model", "m", "--port", "1"]
    assert W.parse_size("2GB") == 2 * GB and W.parse_size("512MB") == 512 << 20 and W.parse_size("123") == 123


def test_install_keep_fixes_the_limit_pool_and_clear_cache():
    mx = FakeMx()
    mods = [types.SimpleNamespace(maybe_set_recommended_wired_limit=lambda: None) for _ in range(3)]
    info = W.install_keep(mx, mods, 4 * GB, 2 * GB, log=lambda s: None)
    want = 6 * GB + W.MARGIN
    assert mx.wired == want and mx.cache == 2 * GB and info["capped"] is False
    assert mx.allocs == [2 * GB], "the buffer is pre-touched once"
    # mlx_lm's own 'set recommended' calls (server start, each generate / BatchGenerator) now set OUR limit and return the previous
    mx.wired = 123
    assert mods[1].maybe_set_recommended_wired_limit() == 123 and mx.wired == want
    mx.clear_cache()
    assert mx.cleared == 0, "the pool is not emptied between requests"


def test_install_keep_reports_cap_and_never_sudo():
    mx, lines = FakeMx(max_rec=5 * GB), []
    info = W.install_keep(mx, [], 4 * GB, 2 * GB, log=lines.append)
    assert info["capped"] and mx.wired == 5 * GB
    assert "sudo sysctl iogpu.wired_limit_mb" in lines[0] and "not done" in lines[0]


def test_weight_bytes_sums_safetensors():
    d = tempfile.mkdtemp()
    open(os.path.join(d, "a.safetensors"), "wb").write(b"x" * 10)
    open(os.path.join(d, "b.safetensors"), "wb").write(b"x" * 5)
    open(os.path.join(d, "tokenizer.json"), "wb").write(b"x" * 99)
    assert W.weight_bytes(d) == 15 and W.weight_bytes("/nope") == 0


def test_idle_touch_runs_only_when_idle_and_at_its_pace():
    calls = {"eval": 0}

    class Arr:
        itemsize = 4
        def reshape(self, *a): return self
        def __getitem__(self, k): return self
        def sum(self): return 0

    class Model:
        def parameters(self): return {"w": Arr(), "b": Arr()}

    class RG:
        def __init__(self): self.model_provider = types.SimpleNamespace(model=Model()); self.q = []
        def _next_request(self, timeout=None): return self.q.pop() if self.q else None

    mx = types.SimpleNamespace(eval=lambda xs: calls.__setitem__("eval", calls["eval"] + 1))
    S = types.SimpleNamespace(ResponseGenerator=RG)
    t = {"now": 0.0}
    st = W.install_touch(S, mx, 10, clock=lambda: t["now"], log=lambda s: None)
    g = RG()
    t["now"] = 5; g._next_request(0.1); assert calls["eval"] == 0, "not yet due"
    t["now"] = 11; g.q.append("req"); assert g._next_request(0.1) == "req"; assert calls["eval"] == 0, "a request came: no touch"
    t["now"] = 12; g._next_request(None); assert calls["eval"] == 0, "decoding a batch (no timeout): no touch"
    g._next_request(0.1); assert calls["eval"] == 1 and st["count"] == 1
    t["now"] = 15; g._next_request(0.1); assert calls["eval"] == 1, "every 10 s only"
    t["now"] = 23; g._next_request(0.1); assert calls["eval"] == 2
