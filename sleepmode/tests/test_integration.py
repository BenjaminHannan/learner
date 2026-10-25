"""Scheduler + the real practice package through an OpenAI-compatible HTTP endpoint (a local fake server)."""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from sleepmode.scheduler import Scheduler, default_practice_fn
from sleepmode.workers import FakeWorker

from .helpers import TmpCase

REPLY = "```python\nimport csv\nopen('output.csv', 'w').write('a,b\\n1,2\\n')\n```"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        body = json.dumps({"choices": [{"message": {"role": "assistant", "content": REPLY}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class IntegrationTests(TmpCase):
    def test_sleep_then_practice_round(self):
        srv = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        raw = os.path.join(self.cfg.diary_dir, "raw")
        os.makedirs(raw)
        with open(os.path.join(raw, "2026-10-25.jsonl"), "w") as f:
            for q in ["make a pivot table of this spreadsheet", "sum column B by region in my excel sheet",
                      "vlookup the prices from the csv", "write a formula for monthly totals"]:
                f.write(json.dumps({"ts": "2026-10-25T10:00:00+00:00", "messages": [{"role": "user", "content": q}],
                                    "response": {"content": "ok"}}) + "\n")
        self.cfg.practice_model_url = "http://127.0.0.1:%d" % srv.server_port
        self.cfg.research_web = False
        self.cfg.practice_tasks = 3
        self.cfg.hour_s = 1.0
        sch = Scheduler(self.cfg, FakeWorker(lambda h: 50.0, hour_s=1.0), default_practice_fn(self.cfg, None))
        t = threading.Thread(target=sch.run)
        t.start()
        end = time.time() + 30
        while time.time() < end and not sch.state.events("practice_round"):
            time.sleep(0.05)
        open(os.path.join(self.cfg.home, "WAKE"), "w").close()
        t.join(30)
        self.assertFalse(t.is_alive())
        ev = sch.state.events("practice_round")
        self.assertTrue(ev, sch.state.events())
        r = ev[0]["result"]
        self.assertEqual(r["kind"], "spreadsheet")
        self.assertEqual(r["n"], 3)
        self.assertEqual(r["pass_any"], 0)
        self.assertTrue(os.path.exists(r["rounds_path"]))
