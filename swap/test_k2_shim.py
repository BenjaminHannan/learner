"""Pure-python tests for swap/k2_shim.parse (stubs transformers): python swap/test_k2_shim.py"""
import sys, types, unittest
from pathlib import Path

sys.modules.setdefault("transformers", types.SimpleNamespace(AutoTokenizer=None))
sys.path.insert(0, str(Path(__file__).parent))
from k2_shim import parse, parse2

TOOLS = [{"type": "function", "function": {"name": "f", "parameters": {"properties": {
    "n": {"type": "integer"}, "s": {"type": "string"}, "o": {"anyOf": [{"type": "string"}, {"type": "null"}]}}}}}]


def call(name, *args, close=True):
    return f"<ifm|tool_calls>\n<ifm|tool_call>{name}\n" + "".join(f"<ifm|arg_key>{k}</ifm|arg_key>\n<ifm|arg_type>{t}</ifm|arg_type>\n<ifm|arg_value>{v}</ifm|arg_value>\n" for k, t, v in args) + ("</ifm|tool_call>\n</ifm|tool_calls>" if close else "")


class T(unittest.TestCase):
    def test_normal_call(self):
        r, c, calls = parse("hi " + call("f", ("s", "string", "x")), TOOLS, False)
        self.assertEqual((r, c, calls), (None, "hi", [("f", {"s": "x"})]))

    def test_thinking_closed(self):
        r, c, calls = parse("plan\n</ifm|think>ok " + call("f", ("n", "integer", "5")), TOOLS, True)
        self.assertEqual((r, c, calls), ("plan", "ok", [("f", {"n": 5})]))

    def test_thinking_unclosed_no_leak(self):
        r, c, calls, tr = parse2("still thinking about it", TOOLS, True)
        self.assertEqual((r, c, calls, tr), ("still thinking about it", "", [], True))
        r, c, calls, tr = parse2("hmm\n" + call("f", ("n", "integer", "5")), TOOLS, True)
        self.assertEqual((r, c, calls, tr), ("hmm", "", [("f", {"n": 5})], True))

    def test_string_type_keeps_digits(self):
        self.assertEqual(parse(call("f", ("o", "string", "1001"), ("s", "string", "null")), TOOLS, False)[2], [("f", {"o": "1001", "s": "null"})])
        self.assertEqual(parse(call("f", ("o", "string|null", "1001")), TOOLS, False)[2], [("f", {"o": "1001"})])
        self.assertEqual(parse(call("f", ("o", "", "1001")), TOOLS, False)[2], [("f", {"o": "1001"})])  # schema anyOf-with-string, no usable arg_type

    def test_int_arg(self):
        self.assertEqual(parse(call("f", ("n", "integer", "42")), TOOLS, False)[2], [("f", {"n": 42})])
        self.assertEqual(parse(call("f", ("z", "any", "oops{")), TOOLS, False)[2], [("f", {"z": "oops{"})])

    def test_truncated_call_dropped(self):
        t = call("f", ("s", "string", "a")).replace("</ifm|tool_call>\n</ifm|tool_calls>", "") + "<ifm|arg_key>n</ifm|arg_key>\n<ifm|arg_type>integer</ifm|arg_type>\n<ifm|arg_value>4"
        r, c, calls, tr = parse2(t, TOOLS, False)
        self.assertEqual((calls, tr), ([], True))
        t = call("f", ("s", "string", "a")) .replace("</ifm|tool_call>\n</ifm|tool_calls>", "</ifm|tool_call>\n") + "<ifm|tool_call>f\n<ifm|arg_key>n</ifm|arg_key>\n<ifm|arg_type>integer</ifm|arg_type>\n<ifm|arg_value>4"
        r, c, calls, tr = parse2(t, TOOLS, False)
        self.assertEqual((calls, tr), ([("f", {"s": "a"})], True))  # complete call kept, cut-off one dropped

    def test_bare_text(self):
        self.assertEqual(parse2("  just text ", TOOLS, False), (None, "just text", [], False))


if __name__ == "__main__":
    unittest.main()
