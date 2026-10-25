import unittest

from sleepmode.practice import agent
from sleepmode.practice.model import FakeModel, ModelError, tool_call_msg
from sleepmode.tools import ToolBox

MSGS = [{"role": "system", "content": "sys"}, {"role": "user", "content": "go"}]


def box():
    return ToolBox("", web=False, sandbox_files={"d.txt": "42"})


class AgentTests(unittest.TestCase):
    def test_native_tool_calls(self):
        def fn(messages):
            if messages[-1]["role"] == "tool":
                return "answer is " + messages[-1]["content"].split("stdout:\n")[1].split()[0]
            return tool_call_msg("python", {"code": "print(open('d.txt').read())"})
        m = FakeModel(fn)
        text, tr = agent.run_agent(m, MSGS, box())
        self.assertEqual(text, "answer is 42")
        self.assertEqual(agent.tool_counts(tr), {"python": 1})
        last = m.calls[-1]
        self.assertEqual([x["role"] for x in last], ["system", "user", "assistant", "tool"])
        self.assertEqual(last[3]["tool_call_id"], "call_1")
        self.assertEqual(MSGS[0]["content"], "sys")  # input not mutated
        self.assertIn("TOOL:", last[0]["content"])

    def test_text_fallback(self):
        def fn(messages):
            if messages[-1]["content"].startswith("RESULT python:"):
                return "done: " + messages[-1]["content"]
            return 'I will check.\nTOOL: python {"code": "print(6*7)"}'
        text, tr = agent.run_agent(FakeModel(fn), MSGS, box())
        self.assertIn("done: RESULT python:", text)
        self.assertIn("42", text)
        self.assertEqual(tr[1]["mode"], "text")

    def test_text_call_parsing(self):
        self.assertEqual(agent.parse_text_call('x\nTOOL: diary_search {"query": "a"}\n'), ("diary_search", {"query": "a"}))
        self.assertEqual(agent.parse_text_call("TOOL: diary_search"), ("diary_search", {}))
        self.assertIsNone(agent.parse_text_call("no tool here"))

    def test_step_cap_forces_answer(self):
        def fn(messages):
            if "No more tool calls" in messages[-1].get("content", ""):
                return "forced answer"
            return tool_call_msg("python", {"code": "print(1)"})
        text, tr = agent.run_agent(FakeModel(fn), MSGS, box(), max_steps=3)
        self.assertEqual(text, "forced answer")
        self.assertEqual(agent.tool_counts(tr)["python"], 3)
        self.assertTrue(tr[-1]["forced"])

    def test_budget_zero_and_unknown_tool(self):
        text, _ = agent.run_agent(FakeModel(lambda m: "final" if "No more" in m[-1]["content"] else "x"), MSGS, box(), budget_s=0)
        self.assertEqual(text, "final")
        seq = iter([tool_call_msg("web_search", {"query": "x"}), "ok"])
        text, tr = agent.run_agent(FakeModel(lambda m: next(seq)), MSGS, box())
        self.assertEqual(text, "ok")
        self.assertIn("ERROR", tr[1]["result"])  # web disabled

    def test_model_without_tools_support(self):
        class Plain:
            def __init__(self):
                self.n = 0

            def chat(self, messages, max_tokens=0, temperature=0):
                self.n += 1
                return "TOOL: python {\"code\": \"print(5)\"}" if self.n == 1 else "fine"
        text, tr = agent.run_agent(Plain(), MSGS, box())
        self.assertEqual(text, "fine")
        self.assertEqual(agent.tool_counts(tr), {"python": 1})

    def test_server_rejects_tools_then_falls_back(self):
        class Picky(FakeModel):
            def chat_tools(self, *a, **k):
                raise ModelError("400")
        text, _ = agent.run_agent(Picky(lambda m: "plain"), MSGS, box())
        self.assertEqual(text, "plain")


if __name__ == "__main__":
    unittest.main()
