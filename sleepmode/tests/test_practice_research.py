import json
import tempfile
import unittest

from sleepmode.practice import research
from sleepmode.practice.model import FakeModel, strip_think

DDG = """<html><body>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fsheets&rut=1">Sheets</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DabcdefghijK&rut=2">Video</a>
<a href="https://duckduckgo.com/about">about</a>
<a href="https://other.org/x">x</a></body></html>"""
PAGE = "<html><head><title>t</title><script>evil()</script></head><body><nav>menu</nav><p>" + \
       "Use SUMIFS to total by group. " * 30 + "</p><style>p{}</style></body></html>"
GOOD = json.dumps([{"title": "SUMIFS", "how": "sum by criterion", "example": "=SUMIFS()"}])


class Net:
    def __init__(self):
        self.urls = []

    def fetch(self, url):
        self.urls.append(url)
        return DDG if "duckduckgo" in url else PAGE


class ResearchTests(unittest.TestCase):
    def test_seeds(self):
        cards = research.SEEDS["spreadsheet"]
        self.assertGreaterEqual(len(cards), 14)
        for c in cards:
            self.assertTrue(c["title"] and c["how"] and c["example"] is not None and c["source"] == "builtin")
        self.assertEqual(len({c["title"] for c in cards}), len(cards))

    def test_html_helpers(self):
        t = research.html_to_text(PAGE)
        self.assertIn("SUMIFS", t)
        self.assertNotIn("evil", t)
        self.assertNotIn("menu", t)
        self.assertLessEqual(len(research.html_to_text("<p>" + "x " * 50000 + "</p>")), research.MAX_PAGE_CHARS)
        links = research.result_links(DDG)
        self.assertEqual(links, ["https://example.com/sheets", "https://www.youtube.com/watch?v=abcdefghijK",
                                 "https://other.org/x"])
        self.assertEqual(research.youtube_ids(links + ["https://youtu.be/ZZZZZZZZZZZ"]), ["abcdefghijK", "ZZZZZZZZZZZ"])

    def test_parse_cards_tolerant(self):
        self.assertEqual(len(research.parse_cards("```json\n" + GOOD + "\n```")), 1)
        self.assertEqual(len(research.parse_cards("Sure! here:\n" + GOOD + "\nhope it helps")), 1)
        self.assertEqual(len(research.parse_cards(json.dumps({"cards": json.loads(GOOD)}))), 1)
        self.assertEqual(research.parse_cards("no json at all"), [])
        self.assertEqual(research.parse_cards('[{"title": "", "how": "x"}, 5, "s"]'), [])
        c = research.parse_cards(json.dumps([{"title": "t" * 500, "how": "h" * 5000}]), "src")[0]
        self.assertLessEqual(len(c["title"]), 80)
        self.assertEqual(c["source"], "src")

    def test_get_tricks_web_and_cache(self):
        net, prompts = Net(), []
        model = FakeModel(lambda m: prompts.append(m[0]["content"]) or "<think>hmm</think>" + GOOD)
        tr = lambda vid: "transcript about SUMIFS " * 20
        with tempfile.TemporaryDirectory() as home:
            a = research.get_tricks("spreadsheet", home, model=model, fetch=net.fetch, transcript=tr, today="2026-10-25")
            n_calls, n_fetch = len(model.calls), len(net.urls)
            self.assertGreater(n_calls, 0)
            self.assertEqual(len(a), len(research.SEEDS["spreadsheet"]) + n_calls)
            self.assertTrue(any(c["source"].startswith("https://www.youtube.com/watch?v=") for c in a))
            self.assertTrue(any("untrusted" in p for p in prompts))
            b = research.get_tricks("spreadsheet", home, model=model, fetch=net.fetch, transcript=tr, today="2026-10-25")
            self.assertEqual((len(model.calls), len(net.urls)), (n_calls, n_fetch))  # cached for the day
            self.assertEqual(len(b), len(a))
            research.get_tricks("spreadsheet", home, model=model, fetch=net.fetch, transcript=tr, today="2026-10-26")
            self.assertGreater(len(net.urls), n_fetch)  # next day refreshes

    def test_failures_fall_back_to_seeds(self):
        def boom(url):
            raise OSError("offline")
        with tempfile.TemporaryDirectory() as home:
            cards = research.get_tricks("spreadsheet", home, model=FakeModel(lambda m: GOOD), fetch=boom)
            self.assertEqual(len(cards), len(research.SEEDS["spreadsheet"]))
            seeds_only = research.get_tricks("spreadsheet", home, web=False)
            self.assertEqual(len(seeds_only), len(cards))
            self.assertEqual(research.get_tricks("unknown-kind", home, web=False), [])

    def test_fetched_text_truncated_in_prompt(self):
        huge = "<p>" + "word " * 100000 + "</p>"
        seen = []
        model = FakeModel(lambda m: seen.append(m[0]["content"]) or "[]")
        research.web_cards("spreadsheet", model, fetch=lambda u: DDG if "duckduckgo" in u else huge,
                           transcript=lambda v: "")
        self.assertTrue(seen)
        self.assertTrue(all(len(p) < research.MAX_PAGE_CHARS + 1000 for p in seen))

    def test_strip_think(self):
        self.assertEqual(strip_think("<think>a\nb</think>\nhello"), "hello")
        self.assertEqual(strip_think("reasoning</think>answer"), "answer")
        self.assertEqual(strip_think("answer<think>unfinished"), "answer")


if __name__ == "__main__":
    unittest.main()
