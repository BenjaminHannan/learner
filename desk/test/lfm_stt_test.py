import json, os, sys, threading, unittest, urllib.request, urllib.error
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "stt"))
import lfm_stt


class Fake:
    def __init__(self): self.calls = []; self.warmed = False; self.fail = False
    def warm(self): self.warmed = True
    def transcribe(self, s):
        if self.fail: raise RuntimeError("boom")
        self.calls.append(s); return "hello world"


def post(port, path, body):
    r = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=body, method="POST")
    try:
        with urllib.request.urlopen(r) as x: return x.status, json.loads(x.read())
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read())


class T(unittest.TestCase):
    def setUp(self):
        self.m = Fake()
        self.srv = lfm_stt.make_server(self.m)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
    def tearDown(self): self.srv.shutdown(); self.srv.server_close()

    def test_transcribe(self):
        c, j = post(self.port, "/transcribe", b"\x00\x10" * 16000)
        self.assertEqual((c, j), (200, {"text": "hello world"}))
        self.assertEqual(len(self.m.calls[0]), 16000)
        self.assertAlmostEqual(float(self.m.calls[0][0]), 4096 / 32768.0)
    def test_too_short_is_empty_and_not_run(self):
        self.assertEqual(post(self.port, "/transcribe", b"\x00\x00" * 100), (200, {"text": ""}))
        self.assertEqual(self.m.calls, [])
    def test_too_long(self):
        self.assertEqual(post(self.port, "/transcribe", b"\x00" * (lfm_stt.MAX_BYTES + 2))[0], 413)
    def test_error_reported_server_survives(self):
        self.m.fail = True
        c, j = post(self.port, "/transcribe", b"\x00\x01" * 3200)
        self.assertEqual(c, 500); self.assertIn("boom", j["error"])
        self.m.fail = False
        self.assertEqual(post(self.port, "/transcribe", b"\x00\x01" * 3200)[0], 200)
    def test_warm_health_404(self):
        self.assertEqual(post(self.port, "/warm", b"")[0], 200); self.assertTrue(self.m.warmed)
        with urllib.request.urlopen("http://127.0.0.1:%d/health" % self.port) as x: self.assertTrue(json.loads(x.read())["ok"])
        self.assertEqual(post(self.port, "/nope", b"")[0], 404)


if __name__ == "__main__":
    unittest.main()
