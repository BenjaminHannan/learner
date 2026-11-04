"""Tests for sense_night (track I1): pending manifests, the published projector is never written, no seat set -> no training,
crash-safety, benFirst mid-training stop, and (MLX) a real projector night on a tiny random 8-bit Nanbeige: gradients flow through
the quantized model, a good night is kept and a poisoned one is rolled back byte for byte. No real model is loaded."""
import json
import os
import struct
import tempfile
import unittest
from pathlib import Path

from sleepmlx import sense_night as SN

try:
    import mlx.core as mx
    import mlx.nn as nn
    HAVE_MLX = True
except Exception:  # noqa: BLE001
    HAVE_MLX = False

ENC, D = 8, 64


def write_day(d: Path, day: str, vecs):
    off, out = 0, []
    with open(d / f"features-{day}.bin", "ab") as f:
        for v in vecs:
            b = struct.pack(f"<{len(v)}e", *v)
            f.write(b)
            out.append({"day": day, "off": off, "len": len(v), "shape": [len(v) // ENC, ENC]})
            off += len(b)
    return out


def setup_userdata(n_nights=1, labels=("a b c", "d e f")):
    ud = Path(tempfile.mkdtemp())
    sd = ud / "sense-sleep"
    sd.mkdir()
    import random
    rng = random.Random(0)
    for k in range(n_nights):
        day = "2026-11-0%d" % (4 + k)
        vecs = [[rng.uniform(-1, 1) for _ in range(4 * ENC)] for _ in labels]
        ents = [dict(e, label=l, kind="reading", from_="text", encoder=SN.EYE_ID) for e, l in zip(write_day(sd, day, vecs), labels)]
        (sd / f"practice-{day}.json").write_text(json.dumps({"night": day, "dtype": "float16", "featureDir": str(sd), "eye": ents, "ear": []}))
    return ud


def published_file(d: Path):
    p = d / "published.safetensors"
    if HAVE_MLX:
        mx.random.seed(1)
        mx.save_safetensors(str(p), {"fc1.weight": (mx.random.normal((D, ENC)) * 0.2).astype(mx.bfloat16), "fc1.bias": mx.zeros((D,), mx.bfloat16),
                                     "fc2.weight": (mx.random.normal((D, D)) * 0.05).astype(mx.bfloat16), "fc2.bias": mx.zeros((D,), mx.bfloat16)})
    else:
        p.write_bytes(b"PUBLISHED" * 10)
    return p


class FakeTok:
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True, enable_thinking=False):
        return "<u>" + messages[0]["content"] + "|<a>"

    def encode(self, s, add_special_tokens=False):
        return [2 + (ord(c) % 50) for c in s]

    def convert_tokens_to_ids(self, t):
        return 1


def tiny_q8_lm():
    from mlx_lm.models import nanbeige as NB
    import sys
    sys.path.insert(0, str(Path(SN.__file__).resolve().parent.parent / "desk" / "tools"))
    import glim_mlx_server as W
    args = NB.ModelArgs(model_type="nanbeige", hidden_size=D, num_hidden_layers=2, intermediate_size=128, num_attention_heads=4,
                        num_key_value_heads=2, rms_norm_eps=1e-5, vocab_size=64, head_dim=16, num_loops=2, tie_word_embeddings=False,
                        max_position_embeddings=512, rope_theta=10000.0)
    mx.random.seed(0)
    m = NB.Model(args)
    nn.quantize(m, group_size=32, bits=8)
    mx.eval(m.parameters())
    W.make_seeing(m)
    return SN.LM(m, FakeTok())


class SenseNightPlain(unittest.TestCase):
    def test_off_by_default(self):
        self.assertFalse(SN.enabled({}))
        self.assertFalse(SN.enabled({"SLEEPMLX_SENSE_SLEEP": "0"}))
        self.assertTrue(SN.enabled({"SLEEPMLX_SENSE_SLEEP": "1"}))

    def test_no_seat_set_means_no_training_and_published_file_untouched(self):
        ud = setup_userdata()
        pub = published_file(ud)
        before = pub.read_bytes()
        called = []
        r = SN.run_all(str(ud), lm_factory=lambda: called.append(1), published=str(pub))
        self.assertIn("no seat set", r["skipped"])
        self.assertEqual(called, [])
        self.assertEqual(pub.read_bytes(), before)
        self.assertEqual(len(SN.pending_manifests(ud)), 1)

    def test_nothing_pending_and_quarantined_or_slept_nights_are_skipped(self):
        ud = setup_userdata(n_nights=3)
        sd = ud / "sense-sleep"
        (sd / "practice-2026-11-04.json").rename(sd / "practice-2026-11-04.quarantined.json")
        (sd / "nights.jsonl").write_text(json.dumps({"night": "2026-11-05", "kept": True}) + "\n")
        self.assertEqual([p.name for p in SN.pending_manifests(ud)], ["practice-2026-11-06.json"])
        self.assertEqual(SN.run_all(str(Path(tempfile.mkdtemp())))["skipped"], "nothing to practise")

    def test_run_safely_never_raises(self):
        ud = setup_userdata()
        def boom():
            raise MemoryError("no room for the model")
        r = SN.run_safely(str(ud), lm_factory=boom, seat=([[0.0]], ["x"], [[0]]), published=str(published_file(ud)), log=lambda s: None)
        self.assertIn("MemoryError", r["skipped"])
        self.assertEqual(r["nights"], [])

    def test_worker_sense_step_is_off_and_crash_safe(self):
        from sleepmlx import worker as Wk

        class G:
            def reason(self):
                return None
        out = {}
        Wk._sense_step({}, type("P", (), {"userdata_dir": Path(tempfile.mkdtemp())})(), out, G(), print, False)
        self.assertNotIn("sense_sleep", out)

        class BadPaths:
            @property
            def userdata_dir(self):
                raise OSError("disk gone")
        out = {}
        Wk._sense_step({"SLEEPMLX_SENSE_SLEEP": "1"}, BadPaths(), out, G(), print, False)
        self.assertIn("error", out["sense_sleep"]["skipped"])


@unittest.skipUnless(HAVE_MLX, "MLX not installed")
class SenseNightMLX(unittest.TestCase):
    def seat(self, lm, n=4):
        import numpy as np
        rng = np.random.default_rng(3)
        feats = rng.uniform(-1, 1, (n, 4, ENC)).astype("float32")
        caps = ["a b c", "d e f", "g h i", "j k l"][:n]
        cands = [[i] + [j for j in range(n) if j != i] for i in range(n)]
        return feats, caps, cands

    def test_q8_gradients_reach_the_projector_and_loss_falls(self):
        lm = tiny_q8_lm()
        ud = setup_userdata()
        w = SN.projector_copy(ud, str(published_file(ud)))
        p, _ = SN.load_projector_module(w)
        x = mx.random.uniform(-1, 1, (4, ENC))
        ids = lm.caption_ids("a b c")

        def loss(model):
            return -lm.caption_logprob(model(x), ids)
        l0 = float(loss(p))
        _, g = nn.value_and_grad(p, loss)(p)
        from mlx.utils import tree_flatten
        gn = sum(float((v * v).sum()) for _, v in tree_flatten(g))
        self.assertGreater(gn, 0.0)
        tonight = [(list(map(float, x.reshape(-1).tolist())), [4, ENC], "a b c")]
        SN.make_train_fn(lm, steps=25, batch=2, lr=3e-3, log=lambda s: None)(str(w), tonight, [])
        p2, dt = SN.load_projector_module(w)
        self.assertLess(float(loss(p2)), l0)
        self.assertEqual(str(dt["fc1.weight"]), str(mx.bfloat16), "written back in bf16")

    def test_cached_candidate_scores_equal_full_forwards(self):
        lm = tiny_q8_lm()
        media = mx.random.normal((4, D)) * 0.1
        caps = [lm.caption_ids(c) for c in ("a b c", "hello there", "x")]
        cached = lm.score_candidates(media, caps)
        full = [float(lm.caption_logprob(media, c)) for c in caps]
        for a, b in zip(cached, full):
            self.assertAlmostEqual(a, b, delta=1e-2 * max(1.0, abs(b)))

    def test_full_night_kept_then_poisoned_night_rolled_back_exactly(self):
        ud = setup_userdata(n_nights=2)
        pub = published_file(ud)
        lm = tiny_q8_lm()
        seat = self.seat(lm)
        logs = []
        pub_bytes = pub.read_bytes()
        r = SN.run_all(str(ud), lm_factory=lambda: lm, published=str(pub), seat=seat, train_kw={"steps": 3, "batch": 2, "lr": 1e-4},
                       log=logs.append)
        self.assertEqual(len(r["nights"]), 2)
        self.assertIsNotNone(r["nights"][0]["before"])
        self.assertEqual(pub.read_bytes(), pub_bytes, "the published projector is never written")
        self.assertTrue((ud / "sense-sleep" / "vision_projector.safetensors").exists())
        lines = [json.loads(l) for l in (ud / "sense-sleep" / "nights.jsonl").read_text().splitlines()]
        self.assertEqual([l["night"] for l in lines], ["2026-11-04", "2026-11-05"])
        # poisoned: a huge learning rate on a fresh night; the seatbelt must restore the exact bytes (or keep if nothing dropped)
        ud2 = setup_userdata()
        w = SN.projector_copy(ud2, str(pub))
        b0 = w.read_bytes()
        bad_eval = iter([{"V1": 75.0}, {"V1": 25.0}])
        orig = SN.make_eval_fn
        SN.make_eval_fn = lambda *a, **k: (lambda path: next(bad_eval))
        try:
            r2 = SN.run_all(str(ud2), lm_factory=lambda: lm, published=str(pub), seat=seat, train_kw={"steps": 2, "batch": 2, "lr": 1.0})
        finally:
            SN.make_eval_fn = orig
        self.assertFalse(r2["nights"][0]["kept"])
        self.assertTrue(r2["nights"][0]["quarantined"])
        self.assertEqual(w.read_bytes(), b0)

    def test_ben_comes_back_mid_training_rolls_back(self):
        ud = setup_userdata()
        pub = published_file(ud)
        lm = tiny_q8_lm()
        calls = {"n": 0}

        def stop():
            calls["n"] += 1
            return calls["n"] > 3   # before-training checks pass, then Ben is back at a training step
        w = SN.projector_copy(ud, str(pub))
        b0 = w.read_bytes()
        r = SN.run_all(str(ud), lm_factory=lambda: lm, published=str(pub), seat=self.seat(lm), should_stop=stop,
                       train_kw={"steps": 10, "batch": 2})
        self.assertFalse(r["nights"][0]["kept"])
        self.assertIn("Stopped", r["nights"][0]["reason"])
        self.assertEqual(w.read_bytes(), b0)


if __name__ == "__main__":
    unittest.main()
