#!/usr/bin/env python3
"""CPU tests for scripts/claude_k1h_cre.py (no model needed). Run: python -B scripts/claude_k1h_test.py"""
from __future__ import annotations

import functools
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_chat338_agent as C38  # noqa: E402
import claude_cre333_agent as C  # noqa: E402
import claude_cre333d_agent as CD  # noqa: E402
import claude_k1a_test as T1A  # noqa: E402
import claude_k1f_cre as K1F  # noqa: E402
import claude_k1f_score as K1FS  # noqa: E402
import claude_k1f_test as TF  # noqa: E402
import claude_k1h_cre as K  # noqa: E402


def fake_adapter(d: str, body: bytes = b"lora weights") -> str:
    Path(d, K.ADAPTER_FILE).write_bytes(body)
    return K.sha256_file(Path(d, K.ADAPTER_FILE))


class Merged:
    def __init__(self, base):
        self.base, self.evaled = base, False
        self.config = base.config

    def eval(self):
        self.evaled = True
        return self


class Peft:
    def __init__(self, base, d):
        self.base, self.d = base, d

    def merge_and_unload(self):
        return Merged(self.base)


def main():
    C._facts = lambda loop: []                      # no notebook in these tests
    ok = 0
    req = "can you give me some ideas for names for it?"
    good = ["Here are five: Crumb Club, Flour Power, Rise Up, Knead Speed and Batter Days."]
    hist = [{"role": "user", "content": "we're starting a bread club at work"},
            {"role": "assistant", "content": "Nice, that sounds fun!"}]
    with tempfile.TemporaryDirectory() as ad:
        sha = fake_adapter(ad)
        # 1. the adapter must be named and match its sha256, else nothing loads
        for env in ({}, {K.ADAPTER_ENV: ad}, {K.SHA_ENV: sha}):
            os.environ.pop(K.ADAPTER_ENV, None)
            os.environ.pop(K.SHA_ENV, None)
            os.environ.update(env)
            try:
                K.adapter_checked()
                raise AssertionError("adapter_checked ran without both env settings")
            except SystemExit as e:
                assert K.ADAPTER_ENV in str(e)
        os.environ[K.ADAPTER_ENV], os.environ[K.SHA_ENV] = ad, "0" * 64
        try:
            K.adapter_checked()
            raise AssertionError("a wrong sha was accepted")
        except RuntimeError as e:
            assert "refusing to load" in str(e)
        os.environ[K.SHA_ENV] = sha.upper()
        assert K.adapter_checked() == (ad, sha)
        ok += 1
        # 2. the adapter is merged into the LFM writer once per process, with k1f's Gen338 sampling
        os.environ[K1F.WRITER_ENV] = TF.LFM
        K1F._GEN.clear()
        seen = []

        def peft_load(model, d):
            seen.append(d)
            return Peft(model, d)
        load = functools.partial(K.load_adapted, base=TF.One, peft_load=peft_load)
        g1, g2 = K1F.writer_gen(load), K1F.writer_gen(load)
        assert g1 is g2 and seen == [ad] and isinstance(g1, C38.Gen338)
        assert (g1.max_new, g1.t, g1.p) == (200, 0.7, 0.9) and g1.g.k1h_adapter == sha
        assert isinstance(g1.g.model, Merged) and g1.g.model.evaled and g1.g.d == TF.LFM
        assert K.writer_name() == f"lfm2 @0f604ada + adapter {sha[:8]}"
        ok += 1
        # 3. the one change on k1f: same messages, n, reply, counters and WORK entry given the same drafts
        for h in (None, hist):
            with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
                runs = []
                for inst, d in ((K1F.install_creative_k1f, a), (K.install_creative_k1h, b)):
                    w = TF.with_writer(good)
                    if h is not None:
                        (Path(d) / C38.STATE_NAME338).write_text(json.dumps({"history": h}), encoding="utf-8")
                    lp, mini = T1A.Loop(d), T1A.Gen(["should never be used"])
                    inst(lp, mini)
                    runs.append((lp, w, lp.turn(req), mini))
                (l0, w0, r0, m0), (l1, w1, r1, m1) = runs
                assert r0 == r1 == good and w0.calls == w1.calls and m0.calls == m1.calls == []
                assert l0.cre333_stats == l1.cre333_stats and l0.experience == l1.experience
                assert l1.k1h_writer == f"lfm2 @0f604ada + adapter {sha[:8]}"
        w = TF.with_writer(["I'm sorry, but I can't help with that."])
        with tempfile.TemporaryDirectory() as d:
            lp = T1A.Loop(d)
            K.install_creative_k1h(lp, None)
            assert lp.turn(req) == [C.FALLBACK] and lp.cre333_stats["G5"] == 1
            assert lp.turn("my sister lives in Brackenford") == ["(inner)"] and len(w.calls) == 1
        ok += 1
        # 4. build_null_k1h swaps install_creative333d in, restores it, renames the layer and prints once
        import claude_mu402 as MU
        TF.with_writer(good)
        real = MU.build_null02c
        got = {}

        def fake(state_dir, args):
            got["fn"] = CD.install_creative333d
            o = type("L", (), {})()
            o.layers330c = ["330a_334", "cre333d", "seed402"]
            return o
        MU.build_null02c = fake
        K._PRINTED.clear()
        buf = io.StringIO()
        try:
            before = CD.install_creative333d
            with redirect_stdout(buf):
                out = K.build_null_k1h("x", None)
                K.build_null_k1h("y", None)
            assert got["fn"] is K.install_creative_k1h and CD.install_creative333d is before
            assert out.layers330c == ["330a_334", "cre_k1h", "seed402"]
            assert buf.getvalue().splitlines() == [
                f"k1h: creative writer = install_creative_k1h; writer = lfm2 @0f604ada + adapter {sha[:8]}; "
                "layers = ['330a_334', 'cre_k1h', 'seed402']"], buf.getvalue()
        finally:
            MU.build_null02c = real
        ok += 1
    # 5. the prompt log is a pass-through on k1f's own build; it records the writer's exact messages per state folder
    import claude_mu402 as MU
    real_b, real_l = MU.build_null02c, K1F._logged
    outs = ["I'm sorry, but I can't help with that.", good[0]]

    def fake_b(state_dir, args):
        lp = T1A.Loop(state_dir)
        lp.layers330c = ["330a_334", "cre333d", "seed402"]
        CD.install_creative333d(lp, T1A.Gen(["unused"]))
        return lp
    MU.build_null02c = fake_b
    try:
        os.environ.pop(K.PROMPTS_ENV, None)
        try:
            K.build_null_k1f_prompts("x", None)
            raise AssertionError("prompt build ran without K1H_PROMPTS")
        except SystemExit:
            pass
        replies = {}
        with tempfile.TemporaryDirectory() as t:
            log = Path(t) / "prompts.jsonl"
            items = Path(t) / "items.jsonl"
            items.write_text(json.dumps({"item_id": "kh-0001", "kind": "idea", "turns": ["x"], "last": req,
                                         "facts": []}) + "\n", encoding="utf-8")
            for logged in (False, True):
                w = TF.with_writer(outs)
                with tempfile.TemporaryDirectory() as d:
                    (Path(d) / C38.STATE_NAME338).write_text(json.dumps({"history": hist}), encoding="utf-8")
                    K1F._PRINTED.clear()
                    K._PRINTED.clear()
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        if logged:
                            os.environ[K.PROMPTS_ENV] = str(log)
                            lp = K.build_null_k1f_prompts(d, None)
                        else:
                            lp = K1F.build_null_k1f(d, None)
                    replies[logged] = (lp.turn(req), w.calls)
                    lines = buf.getvalue().splitlines()
                    assert lines[0].startswith("k1f: creative writer = install_creative_k1f; writer = lfm2 @0f604ada")
                    assert lines[1:] == (["k1h-prompts: the k1f build, writer prompts logged to prompts.jsonl"]
                                         if logged else [])
                    assert K1F._logged is real_l
                    if logged:
                        rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
                        assert len(rows) == 1 and rows[0]["dir"] == Path(d).name and rows[0]["request"] == req
                        assert rows[0]["msgs"] == w.calls[0][0] and rows[0]["msgs"][1:3] == hist
                        assert K1FS._last_records(str(items), log)["kh-0001"]["msgs"] == rows[0]["msgs"]
            assert replies[True] == replies[False] and replies[True][0] == good
    finally:
        MU.build_null02c = real_b
        os.environ.pop(K.PROMPTS_ENV, None)
    ok += 1
    print(f"k1h tests: {ok}/5 OK")


if __name__ == "__main__":
    main()
