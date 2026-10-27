"""Conservative, cross-process reservations and size-enforcing artifact writes.

This is an application guard, not an OS quota. Uncontrolled external tools are
not supported. A reservation alone is NOT permission to launch an unbounded
writer: use atomic_write/download, or an equivalently enforced aggregate bound.
"""
from contextlib import contextmanager
import errno
import io
import json
import math
import os
from pathlib import Path
import shutil
import socket
import stat
import time
import uuid
import urllib.request


class BudgetError(RuntimeError):
    pass


def _host_identity():
    """Return the local host label used to scope PID ownership checks."""
    return socket.gethostname()


def _pid_liveness(pid):
    """Return ``alive``, ``dead``, or ``unknown`` without signaling the process.

    A successful ``kill(pid, 0)`` only proves that some process currently owns
    the PID.  That conservative interpretation is intentional: PID reuse must
    never make us reclaim a reservation while a demonstrably live PID exists.
    Permission and platform errors are treated as unknown/fail-closed.
    """
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return "unknown"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return "dead"
    except PermissionError:
        return "unknown"
    except OSError as error:
        if error.errno == errno.ESRCH:
            return "dead"
        return "unknown"
    return "alive"


def _process_start_identity(pid):
    """Best-effort PID start identity using Linux procfs, else ``None``.

    Python's standard library has no portable process-start-time API.  The
    identity is therefore diagnostic/conservative only: a mismatch proves PID
    reuse where procfs is available, but even then a live PID is never reaped.
    """
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
        _, separator, tail = text.rpartition(") ")
        fields = tail.split()
        if not separator or len(fields) <= 19:
            return None
        return f"procfs-start-ticks:{fields[19]}"
    except (OSError, ValueError):
        return None


class BoundedFile:
    """Reject the offending write BEFORE it reaches the filesystem."""
    def __init__(self, raw, limit):
        if not isinstance(limit, int) or limit < 0:
            raise ValueError("A nonnegative integer byte bound is mandatory")
        self.raw, self.limit, self.high_water = raw, limit, 0

    def write(self, data):
        end = self.raw.tell() + len(data)
        if end > self.limit:
            raise BudgetError(f"Write would exceed {self.limit} bytes")
        written = self.raw.write(data)
        self.high_water = max(self.high_water, self.raw.tell())
        return written

    def seek(self, offset, whence=0):
        position = (offset if whence == 0 else self.raw.tell() + offset
                    if whence == 1 else self.high_water + offset)
        if not 0 <= position <= self.limit:
            raise BudgetError("Seek outside reserved extent")
        return self.raw.seek(position)

    def tell(self):
        return self.raw.tell()

    def flush(self):
        return self.raw.flush()

    def fileno(self):
        return self.raw.fileno()


def _inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


class Budget:
    HARD = 100_000_000_000
    STEADY = 80_000_000_000
    CONTROL_ALLOWANCE = 1_048_576

    def __init__(self, root, shared=(), hard=HARD, steady=STEADY, free_floor=1_000_000_000):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise BudgetError("Project root must already exist")
        self.shared = list(dict.fromkeys(str(Path(p).resolve()) for p in shared))
        if any(not Path(p).exists() for p in self.shared):
            raise BudgetError("A declared shared resource is missing")
        self.hard, self.steady, self.free_floor = int(hard), int(steady), int(free_floor)
        if not 0 < self.steady <= self.hard:
            raise ValueError("Invalid limits")
        # Control files have a fixed <=1 MiB allowance, including replacement.
        initial = self.scan()
        if initial["accounted_bytes"] + self.CONTROL_ALLOWANCE > self.hard:
            raise BudgetError("Initial audit exceeds hard budget")
        if shutil.disk_usage(self.root).free < self.free_floor + self.CONTROL_ALLOWANCE:
            raise BudgetError("Insufficient real free space for guard bootstrap")
        self.control = self.root / ".budget"
        self.control.mkdir(exist_ok=True)
        self.ledger_path = self.control / "ledger.json"
        self.lock_path = self.control / "lock"

    def scan(self):
        seen, totals, unregistered = set(), [], []
        all_roots = [self.root] + [Path(p) for p in self.shared]
        for root in all_roots:
            logical = allocated = accounted = files = 0
            stack = [root]
            while stack:
                path = stack.pop()
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue  # Concurrent staging cleanup; reservations still count.
                identity = (info.st_dev, info.st_ino)
                if identity in seen:
                    continue
                seen.add(identity)
                blocks = getattr(info, "st_blocks", math.ceil(info.st_size / 512)) * 512
                logical += info.st_size
                allocated += blocks
                accounted += max(info.st_size, blocks)
                files += 1
                if stat.S_ISLNK(info.st_mode):
                    resolved = path.resolve()
                    if not any(_inside(resolved, r) for r in all_roots):
                        unregistered.append({"link": str(path), "target": str(resolved)})
                    # Follow registered links to count each physical inode once.
                    elif resolved.exists():
                        stack.append(resolved)
                elif stat.S_ISDIR(info.st_mode):
                    stack.extend(path.iterdir())
            totals.append({"path": str(root), "shared_read_only": root != self.root,
                           "logical_bytes": logical, "allocated_bytes": allocated,
                           "accounted_bytes": accounted, "unique_inodes": files})
        return {"roots": totals,
                "logical_bytes": sum(t["logical_bytes"] for t in totals),
                "allocated_bytes": sum(t["allocated_bytes"] for t in totals),
                "accounted_bytes": sum(t["accounted_bytes"] for t in totals),
                "unregistered_symlinks": unregistered}

    @contextmanager
    def _locked(self):
        with open(self.lock_path, "a+b") as handle:
            if os.name == "nt":
                import msvcrt
                if handle.tell() == 0:
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_ledger(self):
        if not self.ledger_path.exists():
            return {"active": {}, "reservation_peak_bytes": 0,
                    "sampled_peak_bytes": 0, "reaped_reservations": []}
        if self.ledger_path.stat().st_size > 65536:
            raise BudgetError("Oversized ledger; fail closed")
        try:
            ledger = json.loads(self.ledger_path.read_text())
        except (ValueError, OSError) as error:
            raise BudgetError("Invalid ledger; do not clear reservations blindly") from error
        if not isinstance(ledger, dict) or not isinstance(ledger.get("active"), dict):
            raise BudgetError("Malformed ledger; fail closed")
        for key in ("reservation_peak_bytes", "sampled_peak_bytes"):
            value = ledger.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BudgetError("Malformed ledger counters; fail closed")
        # Old ledgers had no reaping history.  Keep their active entries
        # untouched and merely add an empty compatible audit field in memory.
        ledger.setdefault("reaped_reservations", [])
        if not isinstance(ledger["reaped_reservations"], list):
            raise BudgetError("Malformed reap history; fail closed")
        return ledger

    def _write_ledger(self, ledger):
        data = json.dumps(ledger, indent=2, allow_nan=False).encode()
        if len(data) > 65536:
            raise BudgetError("Too many reservations")
        stage = self.control / f"ledger-{uuid.uuid4().hex}.tmp"
        try:
            with open(stage, "xb") as raw:
                BoundedFile(raw, 65536).write(data)
                raw.flush()
                os.fsync(raw.fileno())
            os.replace(stage, self.ledger_path)  # Only our own control metadata.
        finally:
            if stage.exists():
                stage.unlink()

    @staticmethod
    def _valid_reap_candidate(ticket, entry):
        """Only current-format, fully formed reservations may be reaped."""
        if not isinstance(ticket, str) or not ticket or not isinstance(entry, dict):
            return False
        cap = entry.get("cap")
        pid = entry.get("pid")
        created_ns = entry.get("created_ns")
        start_identity = entry.get("process_start_identity")
        return (
            entry.get("owner_version") == 1
            and isinstance(entry.get("name"), str)
            and bool(entry["name"])
            and isinstance(cap, int) and not isinstance(cap, bool) and cap > 0
            and isinstance(entry.get("host"), str) and bool(entry["host"])
            and isinstance(pid, int) and not isinstance(pid, bool) and pid > 0
            and isinstance(created_ns, int) and not isinstance(created_ns, bool) and created_ns > 0
            and (start_identity is None or isinstance(start_identity, str))
        )

    def _reap_stale_reservations(self, ledger):
        """Reap only same-host reservations whose PID is certainly absent.

        This must be called while holding ``self._locked()``.  Foreign-host,
        legacy, malformed, permission-uncertain, and live owners all remain
        charged.  If PID reuse is observable via procfs, it is recorded in the
        audit event only indirectly by preserving the reservation; a live
        reused PID is deliberately not reclaimed.
        """
        local_host = _host_identity()
        reaped = []
        for ticket, entry in list(ledger["active"].items()):
            if not self._valid_reap_candidate(ticket, entry):
                continue
            if entry["host"] != local_host:
                continue
            liveness = _pid_liveness(entry["pid"])
            if liveness != "dead":
                # Best-effort identity check documents/detects PID reuse where
                # possible, but cannot authorize reaping a currently live PID.
                if liveness == "alive" and entry.get("process_start_identity"):
                    _process_start_identity(entry["pid"])
                continue
            removed = ledger["active"].pop(ticket)
            event = {
                "ticket": ticket,
                "name": removed["name"],
                "cap": removed["cap"],
                "host": removed["host"],
                "pid": removed["pid"],
                "created_ns": removed["created_ns"],
                "reaped_ns": time.time_ns(),
                "reason": "same-host owner PID authoritatively absent",
            }
            reaped.append(event)
        if reaped:
            history = ledger["reaped_reservations"] + reaped
            ledger["reaped_reservations"] = history[-64:]
        return reaped

    @staticmethod
    def _active_reserved_bytes(ledger):
        total = 0
        for entry in ledger["active"].values():
            if not isinstance(entry, dict):
                raise BudgetError("Malformed active reservation; fail closed")
            cap = entry.get("cap")
            if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
                raise BudgetError("Malformed active reservation; fail closed")
            total += cap
        return total

    def _admit(self, ledger, cap, transient):
        scan = self.scan()
        if scan["unregistered_symlinks"]:
            raise BudgetError("Register external symlink targets before writing")
        current = scan["accounted_bytes"]
        active = self._active_reserved_bytes(ledger)
        pressure = current + active + cap + self.CONTROL_ALLOWANCE
        ceiling = self.hard if transient else self.steady
        if pressure > ceiling:
            raise BudgetError(f"Peak reservation {pressure} exceeds {ceiling}")
        if shutil.disk_usage(self.root).free < active + cap + self.CONTROL_ALLOWANCE + self.free_floor:
            raise BudgetError("Actual disk free space cannot cover concurrent reservations")
        ledger["reservation_peak_bytes"] = max(ledger["reservation_peak_bytes"], pressure)
        ledger["sampled_peak_bytes"] = max(ledger["sampled_peak_bytes"], current)

    @contextmanager
    def reserve(self, name, cap, transient=False):
        if not isinstance(cap, int) or cap <= 0:
            raise BudgetError("Unknown/nonpositive-size reservations are refused")
        ticket = uuid.uuid4().hex
        with self._locked():
            ledger = self._read_ledger()
            if self._reap_stale_reservations(ledger):
                # Persist recovery even if admission of the new reservation
                # subsequently fails for an unrelated budget reason.
                self._write_ledger(ledger)
            self._admit(ledger, cap, transient)
            pid = os.getpid()
            ledger["active"][ticket] = {"name": name, "cap": cap,
                                        "owner_version": 1,
                                        "host": _host_identity(),
                                        "pid": pid,
                                        "process_start_identity": _process_start_identity(pid),
                                        "created_ns": time.time_ns()}
            self._write_ledger(ledger)
        try:
            yield ticket
        finally:
            with self._locked():
                ledger = self._read_ledger()
                ledger["active"].pop(ticket, None)
                ledger["sampled_peak_bytes"] = max(ledger["sampled_peak_bytes"],
                                                   self.scan()["accounted_bytes"])
                self._write_ledger(ledger)

    def ensure_runtime_directories(self):
        with self.reserve("bounded runtime directory bootstrap", 262144):
            for suffix in ["tmp", "cache", "cache/torch", "cache/inductor", "cache/triton",
                           "cache/cuda", "cache/huggingface", "cache/pip", "cache/uv"]:
                (self.root / ".runtime" / suffix).mkdir(parents=True, exist_ok=True)

    def atomic_write(self, relative, max_bytes, writer):
        if not isinstance(max_bytes, int) or max_bytes <= 0:
            raise BudgetError("A positive byte limit is required before serialization")
        target = self.root / relative
        if not _inside(target.resolve(), self.root) or _inside(target.resolve(), self.control):
            raise BudgetError("Artifact target escapes project or targets guard metadata")
        if target.exists() or target.is_symlink():
            raise BudgetError(f"Refusing to overwrite existing artifact: {target}")
        with self.reserve(f"write {relative}", max_bytes + 65536):
            target.parent.mkdir(parents=True, exist_ok=True)
            stage = target.parent / f".staging-{uuid.uuid4().hex}"
            try:
                with open(stage, "xb") as raw:
                    writer(BoundedFile(raw, max_bytes))
                    raw.flush()
                    os.fsync(raw.fileno())
                # link is no-clobber, unlike a check-then-replace race.
                os.link(stage, target)
            finally:
                if stage.exists():
                    stage.unlink()  # Only this operation's newly created staging file.
        return target

    def save_json(self, relative, value, max_bytes=1_000_000):
        def write(handle):
            encoder = json.JSONEncoder(indent=2, allow_nan=False)
            for chunk in encoder.iterencode(value):
                handle.write(chunk.encode("utf-8"))
        return self.atomic_write(relative, max_bytes, write)

    def download(self, url, relative, max_bytes=None):
        if not isinstance(max_bytes, int) or max_bytes <= 0:
            raise BudgetError("Downloads without an enforced byte limit are refused")
        if not url.startswith("https://"):
            raise BudgetError("Only HTTPS downloads are supported")
        def write(handle):
            with urllib.request.urlopen(url, timeout=20) as response:
                length = response.headers.get("Content-Length")
                if length is not None and int(length) > max_bytes:
                    raise BudgetError("Declared download exceeds reservation")
                while True:
                    chunk = response.read(min(65536, max_bytes + 1))
                    if not chunk:
                        break
                    handle.write(chunk)
        return self.atomic_write(relative, max_bytes, write)

    def audit(self):
        with self._locked():
            ledger = self._read_ledger()
            if self._reap_stale_reservations(ledger):
                self._write_ledger(ledger)
            report = self.scan()
        report.update(hard_limit_bytes=self.hard, steady_target_bytes=self.steady,
                      free_disk_bytes=shutil.disk_usage(self.root).free,
                      free_disk_floor_bytes=self.free_floor,
                      active_reservations=ledger["active"],
                      reaped_reservations=ledger["reaped_reservations"],
                      reservation_peak_bytes=ledger["reservation_peak_bytes"],
                      sampled_peak_bytes=max(ledger["sampled_peak_bytes"], report["accounted_bytes"]),
                      accounting="Sum max(logical,allocated) per unique device/inode; shared roots included; APFS clones conservatively counted separately.")
        return report
