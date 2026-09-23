#!/usr/bin/env python3
"""lis-311 chat server: COPY of scripts/claude_chatdemo_server.py loading
build_agent311 (292 + real lis-300 listener) on port 8767.

Own state dir ~/premonition-chat/lis311-state, own transcript
~/premonition-chat/lis311-transcript.jsonl, own port file
~/premonition-chat/lis311-port.txt, own log
~/premonition-chat/lis311-server.log. Ben's existing notebook/daemon on
8765/8766 is never touched: this server binds ONLY 8767 and its /reset
moves only lis311-state. Flag notes append locally (no push anywhere).

Endpoints: GET / | POST /turn | GET /notebook | POST /flag | POST /reset
(+ GET /ready). New file only; claude_chatdemo_server.py is not edited.
"""
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

_DEPS = Path(tempfile.gettempdir()) / "lis311deps"


def ensure_deps() -> None:
    if str(_DEPS / "scripts") in sys.path:
        return
    (_DEPS / "scripts").mkdir(parents=True, exist_ok=True)
    (_DEPS / "design" / "v3" / "60-listener").mkdir(parents=True,
                                                    exist_ok=True)
    jobs = {"scripts/claude_lis300_common.py":
            _DEPS / "scripts" / "claude_lis300_common.py",
            "scripts/claude_lis300_read.py":
            _DEPS / "scripts" / "claude_lis300_read.py",
            "scripts/claude_lis300_compiler.py":
            _DEPS / "scripts" / "claude_lis300_compiler.py",
            "design/v3/60-listener/relation-names.txt":
            _DEPS / "design" / "v3" / "60-listener" / "relation-names.txt"}
    for src, dst in jobs.items():
        if not dst.exists():
            r = subprocess.run(["git", "-C", str(WORKTREE), "show",
                                "origin/main:" + src],
                               capture_output=True, timeout=60)
            if r.returncode != 0:
                raise RuntimeError("cannot extract " + src)
            dst.write_bytes(r.stdout)
    sys.path.insert(0, str(_DEPS / "scripts"))


HOME = Path.home()
CHAT = HOME / "premonition-chat"
STATE = CHAT / "lis311-state"
FLAGS_FILE = CHAT / "lis311-flags.jsonl"
TRANSCRIPT = CHAT / "lis311-transcript.jsonl"
PORT_FILE = CHAT / "lis311-port.txt"
COUNTER_FILE = STATE / "lis311_counter.txt"
PAGE = HERE / "claude_chatdemo_page.html"

HOST = "127.0.0.1"
PORT = 8767
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


class Chat311:
    def __init__(self):
        self.lock = threading.Lock()
        self.ready = False
        self.daemon = None
        self.turns = _load_turns()

    def build(self):
        import copy as _copy

        ensure_deps()
        import claude_lis311_agent as A311

        cfg = _copy.deepcopy(A311.DEFAULT_CONFIG311)
        cfg["state_dir"] = str(STATE)
        STATE.mkdir(parents=True, exist_ok=True)
        self.daemon = A311.Loop311Daemon(str(STATE), cfg=cfg,
                                         idle_seconds=30.0)
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
            line = {"time": _now(), "user": t["user"], "reply": t["reply"],
                    "added": t.get("added", []),
                    "removed": t.get("removed", []),
                    "note": note or ""}
            try:
                FLAGS_FILE.parent.mkdir(parents=True, exist_ok=True)
                with FLAGS_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(line) + "\n")
            except OSError as e:
                raise RuntimeError("could not save flag: %s" % e)
        return {"ok": True, "push": "local only (never pushed)"}

    def do_reset(self):
        with self.lock:
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            dest = CHAT / "old" / ("lis311-state-%s" % stamp)
            (CHAT / "old").mkdir(parents=True, exist_ok=True)
            try:
                if STATE.exists():
                    shutil.move(str(STATE), str(dest))
            except OSError as e:
                raise RuntimeError("could not move state: %s" % e)
            import copy as _copy

            import claude_lis311_agent as A311

            cfg = _copy.deepcopy(A311.DEFAULT_CONFIG311)
            cfg["state_dir"] = str(STATE)
            STATE.mkdir(parents=True, exist_ok=True)
            try:
                if COUNTER_FILE.exists():
                    COUNTER_FILE.unlink()
            except OSError:
                pass
            self.daemon = A311.Loop311Daemon(str(STATE), cfg=cfg,
                                             idle_seconds=30.0)
            self.ready = True
            return {"ok": True, "moved_to": str(dest)}


APP = Chat311()


class Handler(BaseHTTPRequestHandler):
    server_version = "Chat311/1.0"

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
            except Exception as e:  # noqa: BLE001
                self._send(500, {"error": "%s" % e})
                return
            self._send(200, {"ready": True, "notebook": nb,
                             "turns": len(APP.turns)})
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
            except Exception as e:  # noqa: BLE001
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
            except Exception as e:  # noqa: BLE001
                self._send(500, {"error": "%s" % e})
        elif path == "/reset":
            try:
                self._send(200, APP.do_reset())
            except Exception as e:  # noqa: BLE001
                self._send(500, {"error": "%s" % e})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))
        sys.stderr.flush()


def main():
    t0 = time.perf_counter()
    try:
        srv = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as e:
        print("port %d taken: %s" % (PORT, e), flush=True)
        return 1
    srv.daemon_threads = True
    try:
        PORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        PORT_FILE.write_text(str(PORT), encoding="utf-8")
    except OSError:
        pass
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    print("listening on %s:%d (page serves immediately)" % (HOST, PORT),
          flush=True)
    try:
        APP.build()
    except Exception as e:  # noqa: BLE001
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
