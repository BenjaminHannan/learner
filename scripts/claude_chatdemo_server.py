#!/usr/bin/env python3
"""chat-demo harness: talk to Premonition exp 260 base (138m + openers).

Demo harness only: no scoring, no PASSMARKS, no seal, no ledger lines.
It must not change the model's behaviour: one daemon, one turn at a time,
exactly the mailbox path scripts/claude_openers260_run.py uses
(inbox/mNNNN.txt -> process_file -> outbox/mNNNN.txt).

Stdlib only. Bound to 127.0.0.1, port 8765 (8766 if taken).
Endpoints: GET / | POST /turn | GET /notebook | POST /flag | POST /reset
(+ GET /ready for the page's loading state).
"""
import datetime
import json
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

HOME = Path.home()
CHAT = HOME / "premonition-chat"
STATE = CHAT / "state"
OLD = CHAT / "old"
FLAGS_DIR = CHAT / "flags"
FLAGS_FILE = FLAGS_DIR / "flags.jsonl"
FLAGS_REPO = CHAT / "flags-repo"
TRANSCRIPT = CHAT / "transcript.jsonl"
PORT_FILE = CHAT / "port.txt"
COUNTER_FILE = STATE / "chatdemo_counter.txt"
PAGE = HERE / "claude_chatdemo_page.html"

AGENT = "scripts/claude_loop260_agent.py"
CONFIG = "artifacts/claude-openers260-20260922/loop260-config.json"

HOST = "127.0.0.1"
PORTS = (8765, 8766)
MAX_TEXT = 2000


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _load_turns():
    turns = []
    try:
        for line in TRANSCRIPT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                turns.append(json.loads(line))
    except FileNotFoundError:
        pass
    except OSError:
        pass
    return turns


class ChatDemo:
    def __init__(self):
        self.lock = threading.Lock()
        self.ready = False
        self.daemon = None
        self.dcls = None
        self.base = None
        self.turns = _load_turns()
        self.push_status = "never pushed yet"

    def build(self):
        import fable_marks123_all as M
        _mod, dcls, _, _ = M.load_agent(AGENT)
        base = M.load_base_cfg(CONFIG)
        STATE.mkdir(parents=True, exist_ok=True)
        d = M.make_daemon(dcls, base, STATE)
        self.dcls = dcls
        self.base = base
        self.daemon = d
        self.ready = True

    def _next_n(self):
        try:
            n = int(COUNTER_FILE.read_text(encoding="utf-8").strip())
        except (FileNotFoundError, ValueError, OSError):
            n = 0
            for sub in ("inbox", "outbox", "done"):
                try:
                    for p in (STATE / sub).glob("m*.txt"):
                        try:
                            n = max(n, int(p.stem[1:]) + 1)
                        except ValueError:
                            pass
                except OSError:
                    pass
            n = max(n, len(self.turns))
        return n

    def do_turn(self, text):
        import fable_loop90_agent as L90
        t0 = time.perf_counter()
        with self.lock:
            if not self.ready:
                raise RuntimeError("daemon not ready yet")
            before = L90.notebook_triples(self.daemon.loop.nb)
            before_set = sorted(map(list, before))
            n = self._next_n()
            name = "m%04d.txt" % n
            ipath = STATE / "inbox" / name
            ipath.parent.mkdir(parents=True, exist_ok=True)
            ipath.write_text(text, encoding="utf-8")
            rec = self.daemon.process_file(ipath)
            opath = STATE / "outbox" / name
            reply = opath.read_text(encoding="utf-8").strip()
            after = L90.notebook_triples(self.daemon.loop.nb)
            after_set = sorted(map(list, after))
            bs = sorted([tuple(t) for t in before_set])
            as_ = sorted([tuple(t) for t in after_set])
            added = [list(t) for t in as_ if t not in bs]
            removed = [list(t) for t in bs if t not in as_]
            try:
                COUNTER_FILE.write_text(str(n + 1), encoding="utf-8")
            except OSError:
                pass
            sec = time.perf_counter() - t0
            why = {"ears_stage": rec.get("ears_stage", ""),
                   "ears_score": rec.get("ears_score", 0.0),
                   "records": rec.get("records", [])}
            idx = len(self.turns)
            row = {"time": _now(), "index": idx, "user": text,
                   "reply": reply, "added": added, "removed": removed,
                   "why": why, "seconds": round(sec, 3)}
            self.turns.append(row)
            try:
                TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
                with TRANSCRIPT.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")
            except OSError:
                pass
        return {"reply": reply, "added": added, "removed": removed,
                "notebook": after_set, "why": why, "seconds": round(sec, 3),
                "turn_index": idx}

    def notebook(self):
        import fable_loop90_agent as L90
        with self.lock:
            if not self.ready:
                return None
            return sorted(map(list, L90.notebook_triples(
                self.daemon.loop.nb)))

    def do_flag(self, turn_index, note):
        with self.lock:
            if not (0 <= turn_index < len(self.turns)):
                raise IndexError("unknown turn_index")
            t = self.turns[turn_index]
            ctx = self.turns[max(0, turn_index - 3):turn_index]
            line = {"time": _now(), "user": t["user"], "reply": t["reply"],
                    "added": t.get("added", []),
                    "removed": t.get("removed", []),
                    "why": t.get("why", {}), "note": note or "",
                    "context": [{"user": c["user"], "reply": c["reply"]}
                                for c in ctx]}
            try:
                FLAGS_DIR.mkdir(parents=True, exist_ok=True)
                with FLAGS_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(line) + "\n")
            except OSError as e:
                raise RuntimeError("could not save flag: %s" % e)
        th = threading.Thread(target=_push_flags, daemon=True)
        th.start()
        return {"ok": True, "push": "queued (%s)" % self.push_status}

    def do_reset(self):
        with self.lock:
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            dest = OLD / ("state-%s" % stamp)
            OLD.mkdir(parents=True, exist_ok=True)
            try:
                if STATE.exists():
                    shutil.move(str(STATE), str(dest))
            except OSError as e:
                raise RuntimeError("could not move state: %s" % e)
            STATE.mkdir(parents=True, exist_ok=True)
            try:
                if COUNTER_FILE.exists():
                    COUNTER_FILE.unlink()
            except OSError:
                pass
            import fable_marks123_all as M
            self.daemon = M.make_daemon(self.dcls, self.base, STATE)
            self.ready = True
            return {"ok": True, "moved_to": str(dest)}


def _origin_url():
    try:
        r = subprocess.run(["git", "-C", str(WORKTREE),
                            "remote", "get-url", "origin"],
                           capture_output=True, text=True, timeout=20)
        url = r.stdout.strip()
        if url:
            return url
    except Exception:
        pass
    return "git@github.com:BenjaminHannan/learner.git"


def _git(*args, cwd=None, timeout=60):
    return subprocess.run(["git"] + list(args), cwd=cwd,
                          capture_output=True, text=True, timeout=timeout)


def _push_flags():
    """Push ONLY the flags file to branch chat-flags. Never anything else."""
    try:
        FLAGS_REPO.mkdir(parents=True, exist_ok=True)
        if not (FLAGS_REPO / ".git").exists():
            _git("init", cwd=str(FLAGS_REPO))
        url = _origin_url()
        cur = _git("remote", "get-url", "origin",
                   cwd=str(FLAGS_REPO))
        if cur.returncode != 0 or cur.stdout.strip() != url:
            _git("remote", "remove", "origin", cwd=str(FLAGS_REPO))
            _git("remote", "add", "origin", url, cwd=str(FLAGS_REPO))
        _git("fetch", "origin", "chat-flags", cwd=str(FLAGS_REPO))
        has_remote = _git("rev-parse", "--verify",
                          "origin/chat-flags", cwd=str(FLAGS_REPO))
        if has_remote.returncode == 0:
            _git("checkout", "-B", "chat-flags", "origin/chat-flags",
                 cwd=str(FLAGS_REPO))
            _git("reset", "--hard", "origin/chat-flags",
                 cwd=str(FLAGS_REPO))
        else:
            _git("checkout", "-B", "chat-flags", cwd=str(FLAGS_REPO))
        shutil.copyfile(str(FLAGS_FILE), str(FLAGS_REPO / "flags.jsonl"))
        _git("add", "flags.jsonl", cwd=str(FLAGS_REPO))
        st = _git("status", "--porcelain", cwd=str(FLAGS_REPO))
        if not st.stdout.strip():
            APP.push_status = "up to date"
            return
        c = _git("commit", "-m", "chat flag", cwd=str(FLAGS_REPO))
        if c.returncode != 0:
            APP.push_status = "commit failed; push pending"
            return
        p = _git("push", "origin", "HEAD:chat-flags", cwd=str(FLAGS_REPO))
        if p.returncode == 0:
            APP.push_status = "pushed just now"
        else:
            APP.push_status = ("push failed; will retry on next flag "
                               "(flag saved, push pending)")
    except Exception as e:
        APP.push_status = "push error (%s); flag saved, push pending" % e


APP = ChatDemo()


class Handler(BaseHTTPRequestHandler):
    server_version = "ChatDemo/1.0"

    def _send(self, code, obj, ctype="application/json"):
        body = (obj if isinstance(obj, (bytes, bytearray))
                else json.dumps(obj).encode("utf-8"))
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0 or n > 65536:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return {}

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            try:
                html = PAGE.read_bytes()
            except OSError:
                self._send(500, {"error": "page file missing"})
                return
            self._send(200, html, "text/html; charset=utf-8")
        elif path == "/ready":
            self._send(200, {"ready": APP.ready})
        elif path == "/notebook":
            if not APP.ready:
                self._send(503, {"ready": False})
                return
            try:
                nb = APP.notebook()
            except Exception as e:
                self._send(500, {"error": "%s" % e})
                return
            self._send(200, {"ready": True, "notebook": nb,
                             "turns": len(APP.turns),
                             "push_status": APP.push_status})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/turn":
            if not APP.ready:
                self._send(503, {"error": "loading..."})
                return
            data = self._body()
            text = str(data.get("text", "")).strip()
            if not text:
                self._send(400, {"error": "empty text"})
                return
            text = text[:MAX_TEXT]
            try:
                self._send(200, APP.do_turn(text))
            except Exception as e:
                self._send(500, {"error": "%s" % e})
        elif path == "/flag":
            data = self._body()
            try:
                idx = int(data.get("turn_index"))
            except (TypeError, ValueError):
                self._send(400, {"error": "turn_index required"})
                return
            try:
                self._send(200, APP.do_flag(idx, str(data.get("note", ""))))
            except IndexError:
                self._send(400, {"error": "unknown turn_index"})
            except Exception as e:
                self._send(500, {"error": "%s" % e})
        elif path == "/reset":
            try:
                self._send(200, APP.do_reset())
            except Exception as e:
                self._send(500, {"error": "%s" % e})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))
        sys.stderr.flush()


def main():
    t0 = time.perf_counter()
    srv = None
    port = None
    for p in PORTS:
        try:
            srv = ThreadingHTTPServer((HOST, p), Handler)
            port = p
            break
        except OSError:
            continue
    if srv is None:
        print("no free port (8765/8766 taken)", flush=True)
        return 1
    srv.daemon_threads = True
    try:
        PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        PORT_FILE.write_text(str(port), encoding="utf-8")
    except OSError:
        pass
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    print("listening on %s:%d (page serves immediately)" % (HOST, port),
          flush=True)
    try:
        APP.build()
    except Exception as e:
        print("DAEMON BUILD FAILED: %r" % (e,), flush=True)
        print("serving / with ready=false", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return 1
    print("daemon ready in %.1fs" % (time.perf_counter() - t0), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
