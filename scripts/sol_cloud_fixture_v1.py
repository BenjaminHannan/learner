#!/usr/bin/env python3
"""Pinned human TRAIN fixture capture, idle claim and watcher-only dispatch.

Optimization/validation/explicit candidate rollback belong to the separate night
driver. Replayed HUMAN TRAIN records always remain actual_user_day=false.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from contextlib import contextmanager

from sol_cloud_day_adapter_v1 import (
    ROOT, OWN, SCHEMA, ORIGIN, FixtureError, canonical, identity, inspect_rows, load_rows,
    owned, read, sha, source_rows, verify_pin,
)

SPEC_SCHEMA = "sol.cloud.fixture-spec.v1"


def rollback_path(path):
    """Read sibling night evidence; fixture output writes still use owned()."""
    path = Path(path).resolve()
    permitted = (OWN.resolve(), (ROOT / "artifacts/sol-cloud-night-20260930").resolve())
    if path.name != "rollback.json" or not any(path.is_relative_to(base) and path != base for base in permitted):
        raise FixtureError("exact fixture/night-owned rollback.json receipt required")
    return path


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def pin(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": sha(path)}


def save_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(canonical(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


class FixtureStore:
    def __init__(self, directory, *, allowed_root=None):
        self.directory = owned(directory, allowed_root=allowed_root)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / "fixture.sqlite3"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), activity REAL NOT NULL, revision INTEGER NOT NULL, source_identity TEXT NOT NULL, bundle_sha256 TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS captures (day_record_id TEXT PRIMARY KEY, source_row_id TEXT NOT NULL UNIQUE, row_sha256 TEXT NOT NULL, row_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS claims (claim_id TEXT PRIMARY KEY, batch_path TEXT NOT NULL UNIQUE, batch_sha256 TEXT NOT NULL, revision INTEGER NOT NULL UNIQUE, status TEXT NOT NULL)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=5)
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    def capture(self, source, bundle, row_ids):
        verify_pin(bundle)
        rows = {row["id"]: row for row in source_rows(source)}
        if (not isinstance(row_ids, list) or not 1 <= len(row_ids) <= 64
                or len(set(row_ids)) != len(row_ids) or any(row_id not in rows for row_id in row_ids)):
            raise FixtureError("preselected unique permitted TRAIN identities required")
        events = []
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = db.execute("SELECT revision,source_identity,bundle_sha256 FROM state WHERE id=1").fetchone()
            if state is not None or db.execute("SELECT count(*) FROM captures").fetchone()[0]:
                raise FixtureError("capture store already used; no duplicate fixture cycle")
            for row_id in row_ids:
                row = rows[row_id]
                digest = identity(row)
                record = "fixture-" + digest
                db.execute("INSERT INTO captures VALUES(?,?,?,?)", (record, row_id, digest, canonical(row)))
                events.append({"source_row_id": row_id, "row_sha256": digest, "day_record_id": record})
            db.execute("INSERT INTO state VALUES(1,?,1,?,?)", (time.time(), identity(source), bundle["sha256"]))
        return {"captured_rows": len(events), "events": events, "capture_revision": 1,
                "actual_user_day": False, "origin": ORIGIN}

    def activity(self):
        """Trusted activity handler invalidates an idle claim; no user text parsed."""
        with self.connect() as db:
            if db.execute("UPDATE state SET activity=?,revision=revision+1 WHERE id=1", (time.time(),)).rowcount != 1:
                raise FixtureError("no initialized fixture capture")

    def unchanged(self, revision):
        with self.connect() as db:
            row = db.execute("SELECT revision FROM state WHERE id=1").fetchone()
        return row is not None and row[0] == revision

    def snapshot(self, spec, *, allowed_root=None):
        if type(spec["idle_seconds"]) is not int or not 1 <= spec["idle_seconds"] <= 3600:
            raise FixtureError("bounded real idle interval required")
        batch_path = owned(spec["batch_path"], allowed_root=allowed_root)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = db.execute("SELECT activity,revision,source_identity,bundle_sha256 FROM state WHERE id=1").fetchone()
            if state is None:
                return {"ready": False, "reason": "no captured eligible fixture"}
            activity, revision, source_identity, bundle_digest = state
            if source_identity != identity(spec["source"]) or bundle_digest != spec["bundle"]["sha256"]:
                raise FixtureError("snapshot source/bundle binding differs")
            if time.time() - activity < spec["idle_seconds"]:
                return {"ready": False, "reason": "activity has not been idle long enough"}
            if db.execute("SELECT 1 FROM claims WHERE claim_id=? OR revision=?",
                          (spec["claim_id"], revision)).fetchone():
                raise FixtureError("fixture claim already consumed; no duplicate optimizer cycle")
            if db.execute("SELECT 1 FROM claims WHERE status='running'").fetchone():
                raise FixtureError("another fixture dispatch is running")
            events = [{"source_row_id": row_id, "row_sha256": digest, "day_record_id": record}
                      for record, row_id, digest in db.execute("SELECT day_record_id,source_row_id,row_sha256 FROM captures ORDER BY rowid")]
            if not events or [event["source_row_id"] for event in events] != spec["fixture_row_ids"]:
                raise FixtureError("captured identities differ from sealed fixture selection")
            batch = {"schema": SCHEMA, "split": "TRAIN", "actual_user_day": False,
                     "model_authored_text_included": False, "origin": ORIGIN,
                     "source": spec["source"], "bundle": spec["bundle"],
                     "capture_driver": pin(__file__), "adapter": pin(Path(__file__).with_name("sol_cloud_day_adapter_v1.py")),
                     "state_dir": str(self.directory), "capture_revision": revision,
                     "claim_id": spec["claim_id"], "activity_unix": activity, "events": events}
            save_new(batch_path, batch)
            batch_pin = pin(batch_path)
            db.execute("INSERT INTO claims VALUES(?,?,?,?,?)", (spec["claim_id"], str(batch_path), batch_pin["sha256"], revision, "claimed"))
        return {"ready": True, "batch": batch_pin, "capture_revision": revision,
                "claim_id": spec["claim_id"], "rows": len(events), "actual_user_day": False}

    def begin_dispatch(self, claim, idle_seconds):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            state = db.execute("SELECT activity,revision FROM state WHERE id=1").fetchone()
            if (state is None or state[1] != claim["capture_revision"]
                    or time.time() - state[0] < idle_seconds):
                raise FixtureError("activity resumed after snapshot; no optimizer dispatch")
            if db.execute("SELECT 1 FROM claims WHERE status='running'").fetchone():
                raise FixtureError("concurrent fixture optimizer dispatch forbidden")
            if db.execute("UPDATE claims SET status='running' WHERE claim_id=? AND batch_sha256=? AND revision=? AND status='claimed'",
                          (claim["claim_id"], claim["batch"]["sha256"], claim["capture_revision"])).rowcount != 1:
                raise FixtureError("claim unavailable or already dispatched")

    def finish_dispatch(self, claim_id, status):
        with self.connect() as db:
            if db.execute("UPDATE claims SET status=? WHERE claim_id=? AND status='running'", (status, claim_id)).rowcount != 1:
                raise FixtureError("dispatch state changed unexpectedly")


def checked_spec(path, expected_sha256):
    verify_pin({"path": str(path), "sha256": expected_sha256})
    spec = read(path)
    if (spec.get("schema") != SPEC_SCHEMA or spec.get("actual_user_day") is not False
            or spec.get("activation_allowed") is not False):
        raise FixtureError("fixture-only inactive engineering spec required")
    for key, cap in (("idle_seconds", 3600), ("wait_seconds", 3600), ("pipeline_seconds", 1800)):
        if type(spec.get(key)) is not int or not 1 <= spec[key] <= cap:
            raise FixtureError("bounded watcher wait/pipeline budget required")
    if spec["wait_seconds"] + spec["pipeline_seconds"] > 4200:
        raise FixtureError("watcher outer timeout needs headroom")
    for key in ("state_dir", "batch_path", "claim_receipt", "completion_receipt", "failure_receipt", "dispatch_log"):
        owned(spec[key])
    rollback_path(spec["rollback_receipt"])
    if not isinstance(spec.get("claim_id"), str) or not spec["claim_id"]:
        raise FixtureError("new claim identity required")
    verify_dependencies(spec)
    command = spec["pipeline"]["argv"]
    entrypoint = verify_pin(spec["pipeline"]["entrypoint"])
    if (not isinstance(command, list) or not all(isinstance(arg, str) for arg in command)
            or len(command) < 2 or command[0] != "{python}"
            or Path(command[1]).resolve() != entrypoint or entrypoint.suffix != ".py"
            or any(arg in ("-c", "-m") for arg in command[1:])):
        raise FixtureError("one explicit pinned Python entrypoint required; shell forbidden")
    for flag, placeholder in (("--day-rows", "{day_batch}"), ("--day-sha256", "{day_batch_sha256}")):
        if (command.count(flag) != 1 or command.index(flag) + 1 >= len(command)
                or command[command.index(flag) + 1] != placeholder):
            raise FixtureError("night phase must consume the immutable fixture batch")
    return spec


def verify_dependencies(spec):
    verify_pin(spec["bundle"])
    verify_pin(spec["pipeline"]["entrypoint"])
    for item in spec["dependency_pins"]:
        verify_pin(item)
    for key in ("packet", "manifest", "loader"):
        verify_pin(spec["source"][key])


def watcher_required():
    if not os.environ.get("JOB") or Path(os.environ.get("TREE", "")).resolve() != ROOT.resolve():
        raise FixtureError("existing repository watcher JOB and exact TREE required; no direct training")


def validate_disposition(path, previous_bundle):
    result = read(path)
    if (result.get("schema") != "sol.cloud.candidate-disposition.v1"
            or result.get("actual_user_day") is not False or result.get("activated") is not False
            or result.get("disposition") != "rollback"
            or result.get("operation") != "reject-candidate-retain-prior"
            or result.get("previous_bundle_sha256") != previous_bundle["sha256"]
            or result.get("pointer_before") != result.get("pointer_after")
            or result.get("prior_pointer_unchanged") is not True
            or result.get("previous_bundle_unchanged") is not True
            or result.get("mechanics_complete") is not True):
        raise FixtureError("complete explicit rollback preserving prior pointer required")
    verify_pin(previous_bundle)
    verify_pin(result["candidate_manifest"])
    verify_pin(result["validation"])
    return result


def dispatch(spec, claim):
    watcher_required()
    verify_dependencies(spec)
    inspect_rows(claim["batch"]["path"], claim["batch"]["sha256"], spec["bundle"]["sha256"])
    store = FixtureStore(spec["state_dir"])
    store.begin_dispatch(claim, spec["idle_seconds"])
    substitutions = {"{python}": sys.executable, "{day_batch}": claim["batch"]["path"],
                     "{day_batch_sha256}": claim["batch"]["sha256"]}
    command = [substitutions.get(arg, arg) for arg in spec["pipeline"]["argv"]]
    process = None
    started = time.monotonic()
    started_utc = utc()
    try:
        rows = load_rows(claim["batch"]["path"], claim["batch"]["sha256"], spec["bundle"]["sha256"])
        with owned(spec["dispatch_log"]).open("x", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=ROOT,
                                       env=dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1",
                                                HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1"),
                                       stdout=log, stderr=subprocess.STDOUT)
            while process.poll() is None:
                if time.monotonic() - started > spec["pipeline_seconds"] or not store.unchanged(claim["capture_revision"]):
                    process.terminate()
                    try:
                        process.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    raise FixtureError("activity/budget interruption; preserve candidate and prior pointer")
                time.sleep(0.25)
            if process.returncode:
                raise FixtureError("night validation/rollback phase failed: rc=" + str(process.returncode))
        if not store.unchanged(claim["capture_revision"]):
            raise FixtureError("activity resumed before completion; prior pointer retained")
        verify_dependencies(spec)
        disposition = validate_disposition(rollback_path(spec["rollback_receipt"]), spec["bundle"])
        result = {"schema": "sol.cloud.fixture-completion.v1", "actual_user_day": False,
                  "activated": False, "claim": claim, "eligible_rows": len(rows),
                  "started_utc": started_utc, "completed_utc": utc(),
                  "wall_seconds": time.monotonic() - started, "watcher_job": os.environ["JOB"],
                  "rollback_receipt": pin(spec["rollback_receipt"]),
                  "candidate_manifest": disposition["candidate_manifest"],
                  "scope": "fixture engineering cycle; semantic improvement and live user learning unshown"}
        save_new(owned(spec["completion_receipt"]), result)
        store.finish_dispatch(claim["claim_id"], "complete")
        return result
    except BaseException as exc:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        store.finish_dispatch(claim["claim_id"], "failed")
        save_new(owned(spec["failure_receipt"]), {"schema": "sol.cloud.fixture-failure.v1",
                 "actual_user_day": False, "activated": False, "claim": claim,
                 "started_utc": started_utc, "failed_utc": utc(), "error": str(exc),
                 "candidate_disposition": "preserve incomplete evidence; retain prior pointer",
                 "optimizer_updates": "inspect pinned night ledger; never infer from command return code"})
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("action", choices=("capture", "poll", "run", "cycle", "activity"))
    args = parser.parse_args()
    spec = checked_spec(args.spec, args.spec_sha256)
    if args.action in ("run", "cycle"):
        watcher_required()
    store = FixtureStore(spec["state_dir"])
    if args.action == "activity":
        store.activity()
        print(json.dumps({"activity_recorded": True, "actual_user_day": False}))
        return
    if args.action in ("capture", "cycle"):
        captured = store.capture(spec["source"], spec["bundle"], spec["fixture_row_ids"])
        print(json.dumps(captured), flush=True)
        if args.action == "capture":
            return
    if args.action in ("poll", "cycle"):
        started = time.monotonic()
        while True:
            verify_dependencies(spec)
            result = store.snapshot(spec)
            if result["ready"]:
                save_new(owned(spec["claim_receipt"]), result)
                break
            if args.action == "poll" or time.monotonic() - started >= spec["wait_seconds"]:
                print(json.dumps(result), flush=True)
                return
            time.sleep(min(0.25, max(0, spec["wait_seconds"] - (time.monotonic() - started))))
        if args.action == "poll":
            print(json.dumps(result), flush=True)
            return
    claim = read(spec["claim_receipt"])
    print(json.dumps(dispatch(spec, claim)), flush=True)


if __name__ == "__main__":
    try:
        main()
    except FixtureError as exc:
        raise SystemExit("FIXTURE UNAVAILABLE: " + str(exc))
