import json
import os
import unittest
from pathlib import Path

from sleepmode import mlx_worker as mw
from sleepmode.tests.helpers import TmpCase


def rec(conv, n, reply="ok", status=200):
    return {"ts": "t", "conv_id": conv, "status": status,
            "messages": [{"role": "system", "content": {"$blob": "h"}},
                         {"role": "user", "content": [{"type": "text", "text": "q%d" % n}]}],
            "response": {"content": reply, "tool_calls": []}}


class DataTest(TmpCase):
    def make_diary(self, n_conv=60):
        d = Path(self.root, "diary")
        d.mkdir()
        with open(str(d / "2026-10-25.jsonl"), "w") as f:
            for c in range(n_conv):
                for t in range(2):
                    f.write(json.dumps(rec("c%d" % c, t, "answer %d" % t)) + "\n")
            f.write(json.dumps(rec("bad", 0, "", 200)) + "\n")       # empty reply
            f.write(json.dumps(rec("err", 0, "x", 500)) + "\n")      # failed call
            f.write("not json\n")
        return str(d)

    def test_record_to_example(self):
        ex = mw.record_to_example(rec("c", 1, "hi"))
        self.assertEqual([m["role"] for m in ex["messages"]], ["user", "assistant"])
        self.assertEqual(ex["messages"][0]["content"], "q1")

    def test_read_diary_skips_bad(self):
        ex = mw.read_diary(self.make_diary())
        self.assertEqual(len(ex), 120)

    def test_build_data_freezes_quiz(self):
        diary = self.make_diary()
        wd, data = Path(self.root, "w"), Path(self.root, "w", "data")
        c1 = mw.build_data(diary, [], wd, data)
        self.assertGreaterEqual(c1["quiz"], 20)
        self.assertEqual(c1["train"] + c1["quiz"], 120)
        q1 = (wd / "quiz.jsonl").read_text()
        for name in ("train", "valid", "test"):
            row = json.loads((data / (name + ".jsonl")).read_text().splitlines()[0])
            self.assertEqual(list(row), ["messages"])
        # new diary data arrives: quiz stays frozen, new data only goes to train
        with open(os.path.join(diary, "2026-10-26.jsonl"), "w") as f:
            for c in range(100, 120):
                f.write(json.dumps(rec("c%d" % c, 0)) + "\n")
        c2 = mw.build_data(diary, [], wd, data)
        self.assertEqual((wd / "quiz.jsonl").read_text(), q1)
        self.assertEqual(c2["quiz"], c1["quiz"])
        self.assertEqual(c2["train"], c1["train"] + 20)

    def test_quiz_conversations_never_in_train(self):
        ex = mw.read_diary(self.make_diary())
        train, quiz = mw.split_quiz(ex)
        self.assertFalse({e["conv_id"] for e in train} & {e["conv_id"] for e in quiz})

    def test_split_stable_under_growth(self):
        ex = mw.read_diary(self.make_diary())
        _, q1 = mw.split_quiz(ex)
        extra = [{"conv_id": "z%d" % i, "messages": ex[0]["messages"]} for i in range(30)]
        _, q2 = mw.split_quiz(ex + extra, min_turns=0)
        self.assertTrue({e["conv_id"] for e in q1} <= {e["conv_id"] for e in q2} or len(q1) >= 20)

    def test_practice_sft_added(self):
        diary = self.make_diary()
        p = Path(self.root, "p", "sft.jsonl")
        p.parent.mkdir()
        p.write_text(json.dumps({"messages": [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]}) + "\n")
        pairs = Path(self.root, "p", "pairs.jsonl")
        pairs.write_text(json.dumps({"prompt": [], "chosen": "x", "rejected": "y"}) + "\n")
        wd = Path(self.root, "w")
        base = mw.build_data(diary, [], wd, wd / "d")["train"]
        self.assertEqual(mw.build_data(diary, [str(p), str(pairs)], wd, wd / "d")["train"], base + 1)


class PureTest(unittest.TestCase):
    def test_plan_iters(self):
        self.assertEqual(mw.plan_iters(3600, 2.0), int((3600 - 540) / 2))
        self.assertEqual(mw.plan_iters(100, 2.0), 35)          # min reserve 30 s beats 15 %
        self.assertEqual(mw.plan_iters(20, 2.0), 0)
        self.assertEqual(mw.plan_iters(3600, 0), 0)

    def test_train_args(self):
        a = mw.lora_train_args("M", "D", "P", 50, resume=True, python="py")
        self.assertEqual(a[:5], ["py", "-m", "mlx_lm", "lora", "--model"])
        for flag in ("--train", "--grad-checkpoint"):
            self.assertIn(flag, a)
        self.assertEqual(a[a.index("--iters") + 1], "50")
        self.assertEqual(a[a.index("--resume-adapter-file") + 1], os.path.join("P", "adapters.safetensors"))
        self.assertEqual(a[a.index("--batch-size") + 1], "1")
        self.assertEqual(a[a.index("--num-layers") + 1], "16")
        self.assertEqual(a[a.index("--max-seq-length") + 1], "2048")
        b = mw.lora_train_args("M", "D", "P", 5, resume=False, grad_checkpoint=False, python="py")
        self.assertNotIn("--resume-adapter-file", b)
        self.assertNotIn("--grad-checkpoint", b)

    def test_test_args(self):
        a = mw.lora_test_args("M", "D", "P", python="py")
        self.assertEqual(a, ["py", "-m", "mlx_lm", "lora", "--model", "M", "--adapter-path", "P", "--data", "D", "--test"])

    def test_parse(self):
        text = "Iter 10: Train loss 2.1, It/sec 0.8, Tokens/sec 90\nIter 20: Train loss 1.9, It/sec 0.5\nTest loss 1.234, Test ppl 3.4\n"
        self.assertEqual(mw.parse_test_loss(text), 1.234)
        self.assertEqual(mw.parse_it_per_sec(text), 0.5)
        self.assertIsNone(mw.parse_test_loss("nothing"))


if __name__ == "__main__":
    unittest.main()
