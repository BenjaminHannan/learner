import json, subprocess, sys, tempfile, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import overlap13 as O


def run(*args):
    return subprocess.run([sys.executable, str(HERE / "overlap13.py"), *args], capture_output=True, text=True)


class T(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        panel = {"examples": [{"source_text": "Maya handed the red cup to Tom after the long walk home from the market on Tuesday evening.",
                               "questions": [{"question": "Who got the cup?", "canonical_answer": "SECRETANSWERZZ"}]}]}
        (self.d / "panel.json").write_text(json.dumps(panel))
        (self.d / "spec.json").write_text(json.dumps({"panels": [{"name": "t", "path": "panel.json", "format": "json_examples",
                                                                    "text_fields": ["source_text", "questions[].question"]}]}))
        self.idx = str(self.d / "i.npz")
        r = run("index", "--spec", str(self.d / "spec.json"), "--out", self.idx); self.assertEqual(r.returncode, 0, r.stderr)
        self.r = r

    def scan(self, docs):
        inp = self.d / "in.jsonl"; inp.write_text("".join(json.dumps(x) + "\n" for x in docs))
        r = run("scan", "--index", self.idx, "--input", str(inp), "--out", str(self.d / "o.jsonl"), "--report", str(self.d / "r.json"))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.load(open(self.d / "r.json"))

    def test_planted_copy_caught_paraphrase_kept(self):
        rep = self.scan([
            {"id": "copy", "text": "intro words here. Maya handed the RED cup to Tom, after the long walk home from the market on Tuesday evening! more"},
            {"id": "para", "text": "On Tuesday evening Tom received a red cup from Maya once the long trip back from the market was over."},
            {"id": "plain", "text": "The cat sat on the mat and looked at the garden for a very long time that day."}])
        self.assertEqual(rep["dropped_ids"], ["copy"]); self.assertEqual(rep["kept"], 2)

    def test_short_panel_text_ignored_and_no_answer_in_outputs(self):
        self.assertNotIn("SECRETANSWERZZ", (self.d / "r.json").read_text() if (self.d / "r.json").exists() else "")
        rep = self.scan([{"id": "q", "text": "Who got the cup?"}])
        self.assertEqual(rep["dropped"], 0)  # 4 words < MIN_SHORT
        self.assertNotIn("SECRETANSWERZZ", json.dumps(rep)); self.assertNotIn("maya", json.dumps(rep).lower())
        self.assertNotIn(b"SECRETANSWERZZ", (self.d / "i.npz").read_bytes())

    def test_protected_panel_refused(self):
        (self.d / "blind_panel.json").write_text(json.dumps({"examples": []}))
        (self.d / "s2.json").write_text(json.dumps({"panels": [{"name": "x", "path": "blind_panel.json", "format": "json_examples", "text_fields": ["q"]}]}))
        r = run("index", "--spec", str(self.d / "s2.json"), "--out", str(self.d / "x.npz"))
        self.assertNotEqual(r.returncode, 0); self.assertIn("REFUSED", r.stderr)

    def test_medium_panel_text_whole_match(self):
        (self.d / "p2.json").write_text(json.dumps({"examples": [{"s": "the quick brown fox jumps over one lazy dog"}]}))
        (self.d / "s3.json").write_text(json.dumps({"panels": [{"name": "m", "path": "p2.json", "format": "json_examples", "text_fields": ["s"]}]}))
        run("index", "--spec", str(self.d / "s3.json"), "--out", str(self.d / "m.npz"))
        self.idx = str(self.d / "m.npz")
        rep = self.scan([{"id": "a", "text": "Yesterday: the quick brown fox jumps over one lazy dog. ok"}, {"id": "b", "text": "the quick brown fox jumps over a lazy dog"}])
        self.assertEqual(rep["dropped_ids"], ["a"])


if __name__ == "__main__":
    unittest.main()
