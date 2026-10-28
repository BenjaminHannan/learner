import json
import os
import sqlite3
import unittest

from sleepmode import tools
from sleepmode.tools import ToolBox

try:
    from .helpers import TmpCase
except ImportError:
    from helpers import TmpCase

DDG = ('<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa&rut=x">Pivot <b>tips</b></a>'
       '<a class="result__snippet" href="x">How to make a pivot table</a>')


def rec(conv, user, reply):
    return {"ts": "2026-10-01T10:00:00Z", "conv_id": conv,
            "messages": [{"role": "system", "content": {"$blob": "h"}}, {"role": "user", "content": user}],
            "response": {"content": reply, "tool_calls": []}}


class SsrfTests(unittest.TestCase):
    def test_guard(self):
        for u in ("file:///etc/passwd", "ftp://example.com/x", "http://localhost/x", "http://127.0.0.1:8080/",
                  "http://10.0.0.5/", "http://192.168.1.1/", "http://169.254.169.254/latest", "http://[::1]/",
                  "http://[::ffff:127.0.0.1]/", "http://foo.local/", "javascript:alert(1)", ""):
            self.assertIsNotNone(tools.check_url(u), u)
        self.assertIsNone(tools.check_url("https://8.8.8.8/x"))

    def test_fetch_refuses_without_fetching(self):
        hits = []
        tb = ToolBox("", fetch=lambda u: hits.append(u) or "<p>x</p>")
        self.assertTrue(tb.call("fetch_page", {"url": "http://127.0.0.1/"}).startswith("ERROR"))
        self.assertTrue(tb.call("fetch_page", {"url": "file:///etc/passwd"}).startswith("ERROR"))
        self.assertEqual(hits, [])


class WebTests(unittest.TestCase):
    def test_search_and_fetch(self):
        seen = []
        tb = ToolBox("", fetch=lambda u: seen.append(u) or (DDG if "duckduckgo" in u else "<html><body><p>Hello pivot</p><script>x</script></body></html>"))
        out = tb.call("web_search", {"query": "pivot tips"})
        self.assertIn("https://example.com/a", out)
        self.assertIn("Pivot tips", out)
        self.assertIn("How to make a pivot table", out)
        self.assertIn("UNTRUSTED", out)
        page = tb.call("fetch_page", {"url": "https://8.8.8.8/p"})
        self.assertIn("Hello pivot", page)
        self.assertNotIn("script", page.replace("UNTRUSTED", ""))
        self.assertIn("UNTRUSTED", page)

    def test_custom_searcher_and_errors(self):
        tb = ToolBox("", searcher=lambda q: [{"title": "T", "url": "https://x.org", "snippet": "S"}])
        self.assertIn("https://x.org", tb.call("web_search", {"query": "q"}))

        def boom(u):
            raise OSError("down")
        tb = ToolBox("", fetch=boom)
        self.assertTrue(tb.call("web_search", {"query": "q"}).startswith("ERROR"))

    def test_web_disabled(self):
        tb = ToolBox("", web=False)
        names = [s["function"]["name"] for s in tb.schemas()]
        self.assertNotIn("web_search", names)
        self.assertIn("python", names)
        self.assertTrue(tb.call("web_search", {"query": "x"}).startswith("ERROR"))

    def test_schemas_and_clip(self):
        tb = ToolBox("", fetch=lambda u: "<p>" + "word " * 5000 + "</p>")
        for s in tb.schemas():
            self.assertEqual(s["type"], "function")
            self.assertIn("parameters", s["function"])
        self.assertLessEqual(len(tb.call("fetch_page", {"url": "https://8.8.8.8/"})), 4100)
        self.assertTrue(tb.call("nope", {}).startswith("ERROR"))
        self.assertTrue(tb.call("python", {}).startswith("ERROR"))
        self.assertEqual(tb.call("python", "not json")[:5], "ERROR")


class PythonTests(unittest.TestCase):
    def test_sees_task_files(self):
        tb = ToolBox("", sandbox_files={"in.csv": "a,b\n1,2\n"})
        out = tb.call("python", {"code": "print(open('in.csv').read().strip());open('o.txt','w').write('z')"})
        self.assertIn("exit: 0", out)
        self.assertIn("a,b", out)
        self.assertIn("o.txt", out)
        tb.sandbox_files = {}
        self.assertIn("exit: 1", tb.call("python", {"code": "open('in.csv')"}))


class DiaryTests(TmpCase):
    def raw(self):
        d = os.path.join(self.root, "diary", "raw")
        os.makedirs(d)
        with open(os.path.join(d, "2026-10-01.jsonl"), "w") as f:
            f.write(json.dumps(rec("c1", "my dentist is Dr. Okafor on Elm Street", "Noted.")) + "\n")
            f.write(json.dumps(rec("c2", "write a poem about rain", "Rain falls softly.")) + "\n")
            f.write("garbage\n")
        return os.path.join(self.root, "diary")

    def test_jsonl_scan(self):
        tb = ToolBox(self.raw(), web=False)
        out = tb.call("diary_search", {"query": "dentist Okafor"})
        self.assertIn("2026-10-01", out)
        self.assertIn("Okafor", out)
        self.assertNotIn("poem", out)
        self.assertIn("no matches", tb.call("diary_search", {"query": "zebra"}))
        self.assertIn("Rain falls", tb.call("diary_read", {"date": "2026-10-01", "conv_id": "c2"}))
        self.assertNotIn("Okafor", tb.call("diary_read", {"date": "2026-10-01", "conv_id": "c2"}))
        self.assertIn("nothing", tb.call("diary_read", {"date": "1999-01-01"}))
        # cfg.diary_dir style (points at raw/) works too
        self.assertIn("Okafor", ToolBox(os.path.join(self.raw_dir(), "raw")).call("diary_search", {"query": "dentist"}))

    def raw_dir(self):
        return os.path.join(self.root, "diary")

    def test_sqlite_fts(self):
        d = os.path.join(self.root, "diary")
        os.makedirs(d)
        con = sqlite3.connect(os.path.join(d, "diary.sqlite"))
        con.execute("create virtual table turns using fts5(date, conv_id, user, assistant)")
        con.execute("insert into turns values ('2026-09-30','c9','my sister is named Priya','ok')")
        con.execute("insert into turns values ('2026-09-29','c8','weather today','sunny')")
        con.commit()
        con.close()
        tb = ToolBox(d)
        out = tb.call("diary_search", {"query": "sister Priya", "limit": 3})
        self.assertIn("2026-09-30", out)
        self.assertIn("Priya", out)
        self.assertNotIn("weather", out)
        # read-only: file unchanged and no journal left behind
        self.assertEqual(sorted(os.listdir(d)), ["diary.sqlite"])
        # punctuation in the query must not break FTS syntax
        self.assertNotIn("ERROR", tb.call("diary_search", {"query": 'Priya? "sister" AND ('}))

    def test_sqlite_plain_table_and_bad_schema(self):
        d = os.path.join(self.root, "diary")
        os.makedirs(d)
        con = sqlite3.connect(os.path.join(d, "diary.sqlite"))
        con.execute("create table turns (date text, text text)")
        con.execute("insert into turns values ('2026-09-30','I like oat milk')")
        con.commit()
        con.close()
        self.assertIn("oat milk", ToolBox(d).call("diary_search", {"query": "oat"}))
        # unrelated schema: falls back to raw scan (none) without crashing
        os.remove(os.path.join(d, "diary.sqlite"))
        con = sqlite3.connect(os.path.join(d, "diary.sqlite"))
        con.execute("create table other (x)")
        con.commit()
        con.close()
        self.assertIn("no matches", ToolBox(d).call("diary_search", {"query": "oat"}))
        with open(os.path.join(d, "diary.sqlite"), "wb") as f:
            f.write(b"not a database")
        self.assertIn("no matches", ToolBox(d).call("diary_search", {"query": "oat"}))


if __name__ == "__main__":
    unittest.main()


class RedirectGuardTests(unittest.TestCase):
    def test_redirect_to_private_refused(self):
        import urllib.error
        import urllib.request
        from sleepmode.tools import _CheckedRedirect
        h = _CheckedRedirect()
        req = urllib.request.Request("https://example.com/")
        with self.assertRaises(urllib.error.URLError):
            h.redirect_request(req, None, 302, "Found", {}, "http://127.0.0.1:8090/v1/models")
        ok = h.redirect_request(req, None, 302, "Found", {}, "https://example.org/x")
        self.assertEqual(ok.full_url, "https://example.org/x")
