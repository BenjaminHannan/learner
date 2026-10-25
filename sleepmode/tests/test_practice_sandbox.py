import os
import socket
import tempfile
import threading
import time
import unittest

from sleepmode.practice import sandbox


class ProfileTests(unittest.TestCase):
    def test_profile_string(self):
        p = sandbox.build_profile("/private/tmp/sbx", "/Users/ben", ["/opt/py", "/Users/ben/venv"])
        self.assertTrue(p.startswith("(version 1)"))
        self.assertIn("(deny network*)", p)
        self.assertIn('(allow file-write* (subpath "/private/tmp/sbx") (subpath "/dev"))', p)
        self.assertIn('(deny file-read* (subpath "/Users/ben"))', p)
        self.assertIn('(subpath "/opt/py")', p)
        self.assertIn('(subpath "/Users/ben/venv")', p)
        # deny rules come before the allow rules that carve exceptions (later rules win)
        self.assertLess(p.index("(deny file-write*)"), p.index("(allow file-write*"))
        self.assertLess(p.index("(deny file-read*"), p.index("(allow file-read*"))

    def test_profile_escapes_quotes(self):
        self.assertIn('\\"', sandbox.build_profile('/tmp/a"b', "/h", []))


class RunTests(unittest.TestCase):
    def test_ok_and_files_out(self):
        code = "import csv\nprint(open('in.csv').read().strip())\nopen('output.csv','w').write('a,b\\n1,2\\n')\n"
        r = sandbox.run_python(code, {"in.csv": "x\n"})
        self.assertTrue(r.ok, r.stderr)
        self.assertEqual(r.stdout.strip(), "x")
        self.assertEqual(r.files_out, {"output.csv": "a,b\n1,2\n"})  # input and attempt.py not returned
        self.assertIn(r.isolation, ("sandbox-exec", "unshare", "rlimits-only"))
        self.assertFalse(os.path.exists(r.dir))

    def test_error_reported(self):
        r = sandbox.run_python("raise ValueError('boom')")
        self.assertFalse(r.ok)
        self.assertIn("boom", r.stderr)

    def test_timeout_kills(self):
        t0 = time.time()
        r = sandbox.run_python("while True:\n    pass\n", timeout_s=1)
        self.assertTrue(r.timed_out)
        self.assertFalse(r.ok)
        self.assertLess(time.time() - t0, 15)

    def test_env_is_minimal(self):
        os.environ["HTTP_PROXY"] = "http://example.invalid:1"
        try:
            r = sandbox.run_python("import os\nprint(os.getcwd()==os.environ['HOME'], 'HTTP_PROXY' in os.environ, sorted(os.environ)[:0])")
        finally:
            del os.environ["HTTP_PROXY"]
        self.assertTrue(r.stdout.startswith("True False"), r.stdout + r.stderr)

    def test_outside_write(self):
        with tempfile.TemporaryDirectory() as home:
            victim = os.path.join(home, "precious.txt")
            with open(victim, "w") as f:
                f.write("keep")
            code = ("import os\n"
                    "p=%r\n"
                    "for fn in (lambda: open(p,'w').write('gone'), lambda: os.remove(p)):\n"
                    "    try: fn()\n"
                    "    except Exception as e: print('blocked', type(e).__name__)\n" % victim)
            r = sandbox.run_python(code)
            self.assertIn(r.isolation, ("sandbox-exec", "unshare", "rlimits-only"))
            if r.isolation == "sandbox-exec":
                self.assertTrue(os.path.exists(victim))
                self.assertEqual(open(victim).read(), "keep")
            # unshare / rlimits-only give no file-write protection; only the field is asserted

    def test_network_blocked_when_isolated(self):
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(5)
        port = srv.getsockname()[1]
        srv.settimeout(5)
        threading.Thread(target=lambda: [srv.accept()[0].close() for _ in range(1)], daemon=True).start()
        code = ("import socket\ntry:\n    socket.create_connection(('127.0.0.1', %d), timeout=2)\n"
                "    print('connected')\nexcept OSError:\n    print('blocked')\n" % port)
        try:
            r = sandbox.run_python(code)
        finally:
            srv.close()
        self.assertTrue(r.ok, r.stderr)
        if r.isolation != "rlimits-only":
            self.assertEqual(r.stdout.strip(), "blocked")

    def test_forced_rlimits_only_still_runs(self):
        r = sandbox.run_python("print(1)", isolation="rlimits-only")
        self.assertTrue(r.ok)
        self.assertEqual(r.isolation, "rlimits-only")


if __name__ == "__main__":
    unittest.main()
