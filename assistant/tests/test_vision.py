import http.client
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import fake_upstream  # noqa: E402
import gateway  # noqa: E402
from test_gateway import free_port  # noqa: E402

B64 = "iVBORw0KGgo" + "A" * 3000          # stands in for a big PNG
DATA_URL = "data:image/png;base64," + B64


def img_msgs(url=DATA_URL, text="What is in this picture?"):
    return [{"role": "system", "content": "You are helpful."},
            {"role": "user", "content": [{"type": "text", "text": text},
                                         {"type": "image_url", "image_url": {"url": url}}]}]


class VisionBase(unittest.TestCase):
    vision_up = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.big = fake_upstream.start()
        self.big.gate.set()
        self.vis = fake_upstream.start_vision() if self.vision_up else None
        vurl = "http://127.0.0.1:%d" % (self.vis.server_port if self.vis else free_port())
        self.srv = gateway.make_server("http://127.0.0.1:%d" % self.big.server_port,
                                       "http://127.0.0.1:%d" % free_port(), 0, self.tmp.name,
                                       vision_url=vurl)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.port = self.srv.server_port
        self.diary = Path(self.tmp.name)

    def tearDown(self):
        for s in (self.srv, self.big, self.vis):
            if s:
                s.shutdown()
                s.server_close()
        self.tmp.cleanup()

    def post(self, body):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("POST", "/v1/chat/completions", json.dumps(body), {"Content-Type": "application/json"})
        r = c.getresponse()
        return r.status, r.read()

    def diary_text(self):
        for _ in range(100):  # the diary record is queued just after the reply is sent
            self.srv.gw.diary.flush()
            if list((self.diary / "raw").glob("*.jsonl")):
                break
            time.sleep(0.05)
        return "".join(f.read_text() for f in (self.diary / "raw").glob("*.jsonl"))


class TestVision(VisionBase):
    def test_image_becomes_caption(self):
        code, _ = self.post({"model": "qwen36-fast", "messages": img_msgs()})
        self.assertEqual(code, 200)
        up = self.big.requests[-1]
        user = up["messages"][1]["content"]
        self.assertIn("What is in this picture?", user)
        self.assertIn("[Image 1: A red square. Text: HELLO", user)
        self.assertNotIn("image_url", json.dumps(up))
        self.assertNotIn(B64, json.dumps(up))
        self.assertEqual(up["messages"][0], {"role": "system", "content": "You are helpful."})
        v = self.vis.requests[-1]  # request shape sent to the vision server
        self.assertEqual(v["model"], "fake-vlm")  # asked its /health for the loaded model
        self.assertEqual(v["max_tokens"], 400)
        self.assertEqual(v["temperature"], 0)
        self.assertEqual(v["messages"][0]["content"][0]["image_url"]["url"], DATA_URL)
        self.assertIn("Transcribe all visible text", v["messages"][0]["content"][1]["text"])

    def test_cache_hit_skips_second_call_and_survives_restart(self):
        self.post({"model": "qwen36-fast", "messages": img_msgs()})
        self.post({"model": "qwen36-fast", "messages": img_msgs(text="and now?")})
        self.assertEqual(len(self.vis.requests), 1)
        self.assertIn("[Image 1:", json.dumps(self.big.requests[-1]))
        # a new gateway on the same diary dir reads the on-disk cache
        gw2 = gateway.Gateway("http://x", "", self.tmp.name, vision_url="http://127.0.0.1:%d" % free_port())
        _, recs = gw2.replace_images({"messages": img_msgs()})
        self.assertTrue(recs[0]["caption"])
        self.assertEqual(len(self.vis.requests), 1)

    def test_two_images_numbered(self):
        msgs = img_msgs()
        msgs[1]["content"].append({"type": "input_image", "image_url": "data:image/png;base64,QUJD"})
        self.post({"model": "qwen36-fast", "messages": msgs})
        user = self.big.requests[-1]["messages"][1]["content"]
        self.assertIn("[Image 1:", user)
        self.assertIn("[Image 2:", user)
        self.assertEqual(len(self.vis.requests), 2)

    def test_offline_fallback_and_request_still_served(self):
        self.vis.shutdown()
        self.vis.server_close()
        code, _ = self.post({"model": "qwen36-fast", "messages": img_msgs()})
        self.assertEqual(code, 200)
        self.assertIn("[Image 1: could not be read, the image reader is offline]",
                      self.big.requests[-1]["messages"][1]["content"])
        self.vis = None  # already closed

    def test_failure_is_pinned_for_the_process_and_not_on_disk(self):
        self.vis.fail = True
        self.post({"model": "qwen36-fast", "messages": img_msgs()})
        self.assertIn("image reader is offline", self.big.requests[-1]["messages"][1]["content"])
        self.vis.fail = False
        self.srv.gw._vdown_until = 0
        self.post({"model": "qwen36-fast", "messages": img_msgs()})  # same image: still the fallback
        self.assertIn("image reader is offline", self.big.requests[-1]["messages"][1]["content"])
        self.assertEqual(len(self.vis.requests), 1)
        self.assertFalse(self.srv.gw._vdisk)
        gw2 = gateway.Gateway("http://x", "", self.tmp.name,   # a new process may caption it
                              vision_url="http://127.0.0.1:%d" % self.vis.server_port)
        _, recs = gw2.replace_images({"messages": img_msgs()})
        self.assertIn("A red square", recs[0]["caption"])

    def test_unreadable_ref_has_its_own_text(self):
        msgs = [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": ""}}]}]
        body, recs = self.srv.gw.replace_images({"messages": msgs})
        self.assertEqual(body["messages"][0]["content"], "[Image 1: could not be read]")
        self.assertEqual(len(self.vis.requests), 0)

    def test_cache_key_includes_model_and_prompt(self):
        gw = self.srv.gw
        k1 = gw._vkey("h")
        gw.vision_model = "other-model"
        self.assertNotEqual(gw._vkey("h"), k1)
        gw.vision_model = ""
        old = gateway.VISION_PROMPT_SHA
        gateway.VISION_PROMPT_SHA = "x"
        try:
            self.assertNotEqual(gw._vkey("h"), k1)
        finally:
            gateway.VISION_PROMPT_SHA = old

    def test_same_image_in_flight_is_captioned_once_and_lock_is_free(self):
        self.vis.delay = 0.6
        gw = self.srv.gw
        res = []
        ts = [threading.Thread(target=lambda: res.append(gw.replace_images({"messages": img_msgs()})))
              for _ in range(3)]
        for t in ts:
            t.start()
        time.sleep(0.2)
        self.assertTrue(gw._vlock.acquire(timeout=0.2))  # not held over the vision call
        gw._vlock.release()
        for t in ts:
            t.join(10)
        self.assertEqual(len(self.vis.requests), 1)
        self.assertEqual(len({json.dumps(r[0]) for r in res}), 1)
        self.assertIn("A red square", res[0][0]["messages"][1]["content"])

    def test_total_caption_time_capped_per_request(self):
        self.vis.delay = 0.3
        old = gateway.VISION_BUDGET_S
        gateway.VISION_BUDGET_S = 0.2
        try:
            msgs = img_msgs()
            for k in range(2):
                msgs[1]["content"].append({"type": "image_url", "image_url": {"url": DATA_URL + str(k)}})
            body, recs = self.srv.gw.replace_images({"messages": msgs})
        finally:
            gateway.VISION_BUDGET_S = old
        self.assertEqual(len(self.vis.requests), 1)  # first one ran; the rest got the fallback
        self.assertEqual([bool(r["caption"]) for r in recs], [True, False, False])
        self.assertIn("[Image 3: could not be read, the image reader is offline]",
                      body["messages"][1]["content"])

    def test_base64_not_in_diary_but_caption_and_hash_are(self):
        self.post({"model": "qwen36-fast", "messages": img_msgs()})
        raw = self.diary_text()
        self.assertNotIn(B64, raw)
        rec = json.loads(raw.splitlines()[0])
        self.assertEqual(rec["images"][0]["n"], 1)
        self.assertEqual(len(rec["images"][0]["sha256"]), 64)
        self.assertIn("A red square", rec["images"][0]["caption"])
        self.assertIn("[Image 1: A red square", rec["messages"][1]["content"])
        for f in (self.diary / "raw").rglob("*"):
            if f.is_file():
                self.assertNotIn(B64, f.read_text(errors="replace"))

    def test_auto_judge_sees_caption_not_base64(self):
        self.post({"model": "qwen36-auto", "messages": img_msgs()})
        j = self.big.judge_calls[-1]["messages"][1]["content"]
        self.assertIn("[Image 1:", j)
        self.assertNotIn(B64, j)

    def test_http_url_and_other_shapes(self):
        gw = self.srv.gw
        for part in ({"type": "image_url", "image_url": "http://example.test/a.png"},
                     {"type": "input_image", "image_url": "http://example.test/b.png"},
                     {"type": "image", "image": "http://example.test/c.png"},
                     {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "QUJD"}}):
            body, recs = gw.replace_images({"messages": [{"role": "user", "content": [part]}]})
            self.assertEqual(len(recs), 1, part)
            self.assertTrue(recs[0]["caption"], part)
            self.assertTrue(body["messages"][0]["content"].startswith("[Image 1:"))
        self.assertEqual(self.vis.requests[0]["messages"][0]["content"][0]["image_url"]["url"],
                         "http://example.test/a.png")

    def test_no_images_untouched_and_assistant_untouched(self):
        body = {"messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]},
                             {"role": "assistant", "content": "ok"}]}
        out, recs = self.srv.gw.replace_images(body)
        self.assertIs(out, body)
        self.assertEqual(recs, [])

    def test_health_reports_vision(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port)
        c.request("GET", "/health")
        d = json.loads(c.getresponse().read())
        self.assertEqual(d["status"], "ok")
        self.assertTrue(d["vision"]["up"])

    def test_dedupe_applies_to_image_messages(self):
        obi = "<openbot-developer-instructions>RULES</openbot-developer-instructions>\n"
        msgs = [{"role": "user", "content": obi + "one"},
                {"role": "assistant", "content": "a"},
                {"role": "user", "content": [{"type": "text", "text": obi + "two"},
                                             {"type": "image_url", "image_url": {"url": DATA_URL}}]}]
        self.post({"model": "qwen36-fast", "messages": msgs})
        last = self.big.requests[-1]["messages"][2]["content"]
        self.assertNotIn("RULES", last)
        self.assertIn("[Image 1:", last)


class TestNonTextParts(VisionBase):
    vision_up = False

    def test_prepare_replaces_non_text_parts(self):
        msgs = [{"role": "user", "content": [
            {"type": "text", "text": "hi"},
            {"type": "image_url", "image_url": {"url": DATA_URL}},
            {"type": "input_image", "image_url": DATA_URL},
            {"type": "file", "file": {"filename": "a.pdf", "file_data": "QUJD"}}]}]
        out = gateway.prepare({"messages": msgs}, False, 10)["messages"][0]["content"]
        self.assertTrue(all(p["type"] == "text" for p in out))
        self.assertEqual(out[0]["text"], "hi")
        self.assertIn("image omitted", out[1]["text"])
        self.assertIn("file omitted", out[3]["text"])
        self.assertNotIn(B64, json.dumps(out))

    def test_vision_off_request_reaches_big_model_as_text_only(self):
        gw = self.srv.gw
        gw.vision_url = ""
        msgs = img_msgs()
        msgs[1]["content"].append({"type": "file", "file": {"file_data": "QUJD"}})
        code, _ = self.post({"model": "qwen36-fast", "messages": msgs})
        self.assertEqual(code, 200)
        up = json.dumps(self.big.requests[-1])
        for bad in ("image_url", '"file"', B64):
            self.assertNotIn(bad, up)
        self.assertIn("[Image 1:", up)
        self.assertIn("file omitted", up)

    def test_input_and_output_text_parts_keep_their_text(self):
        msgs = [{"role": "user", "content": [{"type": "input_text", "text": "hello"}]},
                {"role": "assistant", "content": [{"type": "output_text", "text": "yo"}]}]
        out = gateway.prepare({"messages": msgs}, None, 10)["messages"]
        self.assertEqual(out[0]["content"], [{"type": "text", "text": "hello"}])
        self.assertEqual(out[1]["content"], [{"type": "text", "text": "yo"}])

    def test_diary_redacts_files_and_assistant_images(self):
        msgs = [{"role": "user", "content": [{"type": "text", "text": "see"},
                                             {"type": "file", "file": {"filename": "a.pdf", "file_data": B64}},
                                             {"type": "input_text", "text": "kept"}]},
                {"role": "assistant", "content": [{"type": "image_url", "image_url": {"url": DATA_URL}}]},
                {"role": "user", "content": "next"}]
        out = gateway.redact_non_text(msgs)
        raw = json.dumps(out)
        self.assertNotIn(B64, raw)
        self.assertIn("kept", raw)
        self.assertRegex(out[0]["content"][1]["text"], r"^\[file omitted: sha256 [0-9a-f]{64}, \d+ bytes\]$")
        self.assertRegex(out[1]["content"][0]["text"], r"^\[image omitted: sha256 [0-9a-f]{64}, %d bytes\]$" % len(DATA_URL))
        code, _ = self.post({"model": "qwen36-fast", "messages": [{"role": "system", "content": "s"}] + msgs})
        self.assertEqual(code, 200)
        self.assertNotIn(B64, self.diary_text())

    def test_image_in_assistant_message_stripped(self):
        out = gateway.prepare({"messages": [{"role": "assistant", "content": [
            {"type": "image_url", "image_url": {"url": DATA_URL}}]}]}, None, 10)
        self.assertNotIn("image_url", json.dumps(out))


class TestVisionDisabled(VisionBase):
    vision_up = False

    def test_down_does_not_fail_and_no_wait_after_first_failure(self):
        for _ in range(2):
            code, _ = self.post({"model": "qwen36-fast", "messages": img_msgs()})
            self.assertEqual(code, 200)
        self.assertGreater(self.srv.gw._vdown_until, 0)

    def test_empty_vision_url(self):
        gw = gateway.Gateway("http://x", "", self.tmp.name, vision_url="")
        body, recs = gw.replace_images({"messages": img_msgs()})
        self.assertIn("image reader is offline", body["messages"][1]["content"])
        self.assertIsNone(recs[0]["caption"])


if __name__ == "__main__":
    unittest.main()
