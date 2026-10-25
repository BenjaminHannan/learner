"""Run an untrusted Python attempt in a throwaway directory with limits."""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field

MAX_OUT = 20000
MAX_FILE = 2_000_000
_ISO: list = []  # probe cache


@dataclass
class RunResult:
    ok: bool
    stdout: str
    stderr: str
    files_out: dict = field(default_factory=dict)  # name -> text
    dir: str = ""
    returncode: int | None = None
    timed_out: bool = False
    isolation: str = "rlimits-only"


def _q(path: str) -> str:
    return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_profile(sandbox_dir: str, home: str, prefixes) -> str:
    """macOS sandbox-exec profile (later rules win in SBPL). Only file-read-data is denied under HOME, so
    metadata lookups (stat/realpath of parent dirs) still work. All paths are realpath'd."""
    sandbox_dir, home = os.path.realpath(sandbox_dir), os.path.realpath(home)
    prefixes = [os.path.realpath(p) for p in prefixes if p]
    lines = ["(version 1)", "(allow default)", "(deny network*)",
             "(deny file-write*)",
             "(allow file-write* (subpath %s) (subpath \"/dev\"))" % _q(sandbox_dir),
             "(deny file-read-data (subpath %s))" % _q(home)]
    allowed = [sandbox_dir] + prefixes
    subs = " ".join("(subpath %s)" % _q(p) for p in allowed)
    lines.append("(allow file-read* %s)" % subs)
    lines.append("(allow file-read-data %s)" % subs)  # macOS 27: file-read* does not undo the file-read-data deny
    return "\n".join(lines) + "\n"


def _probe(cmd) -> bool:
    try:
        return subprocess.run(cmd, capture_output=True, timeout=10).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def detect_isolation() -> str:
    if not _ISO:
        mode = "rlimits-only"
        if sys.platform == "darwin" and shutil.which("sandbox-exec") and \
                _probe(["sandbox-exec", "-p", "(version 1)(allow default)", "/usr/bin/true"]):
            mode = "sandbox-exec"
        elif sys.platform.startswith("linux") and shutil.which("unshare") and \
                _probe(["unshare", "-rn", "true"]):
            mode = "unshare"
        _ISO.append(mode)
    return _ISO[0]


def _limiter():
    try:
        import resource
    except ImportError:
        return None

    def apply():
        for name, val in (("RLIMIT_CPU", 30), ("RLIMIT_FSIZE", 20 * 1024 * 1024),
                          ("RLIMIT_NPROC", 128), ("RLIMIT_CORE", 0)):
            lim = getattr(resource, name, None)
            if lim is None:
                continue
            try:
                resource.setrlimit(lim, (val, val))
            except (ValueError, OSError):
                pass
    return apply


def _clip(b: bytes, n: int = MAX_OUT) -> str:
    return b[:n].decode("utf-8", "replace")


def run_python(code: str, files: dict | None = None, timeout_s: float = 30,
               isolation: str | None = None) -> RunResult:
    iso = isolation or detect_isolation()
    d = os.path.realpath(tempfile.mkdtemp(prefix="sleepmode-sbx-"))
    try:
        inputs = {}
        for name, text in (files or {}).items():
            name = os.path.basename(name)
            inputs[name] = text
            with open(os.path.join(d, name), "w", encoding="utf-8", newline="") as f:
                f.write(text)
        with open(os.path.join(d, "attempt.py"), "w", encoding="utf-8") as f:
            f.write(code)
        cmd = [sys.executable, "-I", "attempt.py"]
        if iso == "sandbox-exec":
            home = os.path.realpath(os.path.expanduser("~"))
            prefixes = {os.path.realpath(p) for p in (sys.prefix, sys.base_prefix)}
            cmd = ["sandbox-exec", "-p", build_profile(d, home, sorted(prefixes))] + cmd
        elif iso == "unshare":
            cmd = ["unshare", "-rn"] + cmd
        env = {"PATH": "/usr/bin:/bin", "HOME": d, "TMPDIR": d, "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"}
        res = RunResult(False, "", "", dir=d, isolation=iso)
        kw = {"preexec_fn": _limiter()} if os.name == "posix" else {}
        try:
            p = subprocess.Popen(cmd, cwd=d, env=env, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 start_new_session=True, **kw)
        except OSError as e:
            res.stderr = "could not start: %s" % e
            return res
        try:
            out, err = p.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            res.timed_out = True
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                p.kill()
            out, err = p.communicate()
        res.stdout, res.stderr, res.returncode = _clip(out), _clip(err), p.returncode
        if res.timed_out:
            res.stderr += "\n[timed out after %ss]" % timeout_s
        res.ok = p.returncode == 0 and not res.timed_out
        for root, _, names in os.walk(d):
            for n in names:
                rel = os.path.relpath(os.path.join(root, n), d)
                if rel == "attempt.py":
                    continue
                try:
                    with open(os.path.join(root, n), "rb") as f:
                        text = f.read(MAX_FILE).decode("utf-8", "replace")
                except OSError:
                    continue
                if inputs.get(rel) != text:
                    res.files_out[rel] = text
        return res
    finally:
        shutil.rmtree(d, ignore_errors=True)
