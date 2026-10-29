import json
from types import SimpleNamespace
import unittest

from sleepmlx.mac_gateway import CREATIVE_TAG, clean_messages, install, scratch


def gateway_module():
    calls = []

    class Gateway:
        big_url = "http://127.0.0.1:18080"

        def small_up(self): return False
        def route(self, model): return "old", "old", False, 1
        def note_prefix(self, body): calls.append(("prefix", body))

    class Handler:
        headers = {}

        def record(self, body, *args, **kwargs): calls.append(("record", body))

    def prepare(body, thinking, default_max):
        calls.append(("prepare", thinking))
        return dict(body, model="default_model", max_tokens=body.get("max_tokens", default_max))

    def diary(body, *args, **kwargs): return body

    return SimpleNamespace(Gateway=Gateway, Handler=Handler, prepare=prepare,
                           build_diary=diary, BIG_MAX=8192, MODEL_IDS=["qwen36"]), calls


class MacGatewayTests(unittest.TestCase):
    def test_fast_and_main_use_same_lfm_weights_with_native_thinking_control(self):
        module, calls = gateway_module(); install(module)
        gw = module.Gateway()
        for alias, thinking in (("lfm3", True), ("lfm3-fast", False), ("lfm3-auto", False)):
            name, url, enabled, maximum = gw.route(alias)
            self.assertEqual((name, url, enabled), ("big", gw.big_url, thinking))
            body = module.prepare({"messages": [], "temperature": .9}, enabled, maximum)
            self.assertEqual(body["model"], "lfm3")
            self.assertEqual(body["chat_template_kwargs"]["enable_thinking"], thinking)
            self.assertEqual(body["temperature"], .9)
            self.assertNotIn("presence_penalty", body)
        self.assertTrue(all(value is None for key, value in calls if key == "prepare"))

    def test_scratch_is_never_diary_or_saved_prefix_and_metadata_not_serialized(self):
        module, calls = gateway_module(); install(module)
        body = {"messages": [{"role": "user", "content": "brainstorm"}], "test": True,
                "purpose": "creative-proposals"}
        module.Handler().record(body)
        prepared = module.prepare(body, False, 128)
        module.Gateway().note_prefix(prepared)
        self.assertFalse(any(key in ("prefix", "record") for key, _ in calls))
        upstream = json.loads(json.dumps(prepared))
        self.assertNotIn("test", upstream); self.assertNotIn("purpose", upstream)
        self.assertNotIn("scratch_request", upstream)

    def test_ordinary_chat_keeps_real_request_but_excludes_generated_candidate(self):
        module, calls = gateway_module(); install(module)
        real = {"role": "user", "content": "brainstorm a story"}
        candidate = {"role": "user", "content": CREATIVE_TAG + '\n{"approaches":["idea"]}'}
        body = {"messages": [real, candidate]}
        result = module.build_diary(body)
        self.assertEqual(result["messages"], [real])
        self.assertEqual(body["messages"], [real, candidate])
        module.Handler().record(body)
        module.Gateway().note_prefix(module.prepare(body, False, 128))
        self.assertTrue(any(key == "record" for key, _ in calls))
        self.assertFalse(any(key == "prefix" for key, _ in calls))

    def test_header_only_test_and_warm_requests_are_excluded(self):
        self.assertTrue(scratch({}, {"X-Test": "1"}))
        self.assertTrue(scratch({}, {"X-Premonition-Warm": "1"}))
        self.assertFalse(scratch({"test": "false"}))
        self.assertEqual(clean_messages([{"role": "assistant", "content": CREATIVE_TAG}]),
                         [{"role": "assistant", "content": CREATIVE_TAG}])

    def test_install_is_idempotent_and_normal_prefix_survives(self):
        module, calls = gateway_module(); install(module)
        first = module.prepare; install(module)
        self.assertIs(module.prepare, first)
        module.Gateway().note_prefix(module.prepare({"messages": []}, False, 1))
        self.assertEqual(sum(key == "prefix" for key, _ in calls), 1)


if __name__ == "__main__": unittest.main()
