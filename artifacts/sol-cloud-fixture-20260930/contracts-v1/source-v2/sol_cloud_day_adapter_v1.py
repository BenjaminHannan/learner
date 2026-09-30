"""Read-only admission of a pinned HUMAN TRAIN engineering fixture batch.

This adapter never imports a model, optimizes, reads mixed corpus files, or
claims that replayed corpus records are live user experience.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
from contextlib import closing

ROOT = Path(__file__).resolve().parents[1]
OWN = ROOT / "artifacts/sol-cloud-fixture-20260930"
SCHEMA = "sol.cloud.fixture-batch.v1"
ORIGIN = "verified-human-TRAIN-fixture"


class FixtureError(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def identity(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_pin(record):
    path = Path(record["path"]).resolve()
    lowered = path.as_posix().lower()
    forbidden = ("/uncle-questions/", "readpanel320", "dev100", "stop88",
                 "/human-documents/", "/pairs.json", "/train-v1.1.json",
                 "/blind/", "/sealed-panels/", "/sealedquestions/")
    if any(value in lowered for value in forbidden):
        raise FixtureError("forbidden source path")
    digest = record.get("sha256")
    if (not isinstance(digest, str) or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
            or not path.is_file() or sha(path) != digest):
        raise FixtureError("pinned bytes absent or changed: " + str(path))
    return path


def owned(path, *, allowed_root=None):
    path = Path(path).resolve()
    base = OWN.resolve() if allowed_root is None else Path(allowed_root).resolve()
    if path == base or not path.is_relative_to(base):
        raise FixtureError("new fixture-owned output path required")
    return path


def source_rows(source):
    """The independently owned safe loader checks packet exclusion/provenance.

    Only the standalone packet, its manifest and pinned Python loader are opened.
    No fallback to raw TRAIN, pairs.json, documents or reserved panels exists.
    """
    packet = verify_pin(source["packet"])
    manifest = verify_pin(source["manifest"])
    loader = verify_pin(source["loader"])
    if loader.suffix != ".py":
        raise FixtureError("pinned TRAIN-only Python loader required")
    spec = importlib.util.spec_from_file_location(
        "_cloud_fixture_trainonly_" + source["loader"]["sha256"][:16], loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = module.load_packet(str(packet), source["packet"]["sha256"],
                              manifest_path=str(manifest),
                              manifest_sha256=source["manifest"]["sha256"])
    if not isinstance(rows, list) or not rows:
        raise FixtureError("nonempty verified TRAIN-only packet required")
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or row.get("split") != "train"
                or not isinstance(row.get("id"), str) or row["id"] in seen
                or any(not isinstance(row.get(key), str) for key in
                       ("question", "context", "target_text", "source_sha256"))
                or not row["question"].strip() or not row["target_text"].strip()):
            raise FixtureError("invalid or repeated HUMAN TRAIN row")
        seen.add(row["id"])
    return rows


def _load_rows(path, expected_sha256, bundle_sha256=None, *, allowed_root=None,
               require_running=True):
    """Return verbatim admitted rows, retaining their original TRAIN identities.

    SQLite opens read-only, including under an enclosing writer lock. The store
    claim and exact source-row bytes are checked; author-written eligibility
    flags cannot substitute for the source loader or capture membership.
    """
    batch_path = owned(path, allowed_root=allowed_root)
    verify_pin({"path": str(batch_path), "sha256": expected_sha256})
    batch = read(batch_path)
    if (batch.get("schema") != SCHEMA or batch.get("split") != "TRAIN"
            or batch.get("actual_user_day") is not False
            or batch.get("model_authored_text_included") is not False
            or batch.get("origin") != ORIGIN):
        raise FixtureError("fixture qualification or schema differs")
    bundle = verify_pin(batch["bundle"])
    if bundle_sha256 is not None and batch["bundle"]["sha256"] != bundle_sha256:
        raise FixtureError("fixture targets another awake bundle")
    verify_pin(batch["capture_driver"])
    verify_pin(batch["adapter"])
    if batch["adapter"]["sha256"] != sha(__file__):
        raise FixtureError("fixture adapter source changed")
    directory = owned(batch["state_dir"], allowed_root=allowed_root)
    database = directory / "fixture.sqlite3"
    if not database.is_file():
        raise FixtureError("actual fixture capture store absent")
    originals = {row["id"]: row for row in source_rows(batch["source"])}
    result = []
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=5)) as db:
        state = db.execute("SELECT revision,source_identity,bundle_sha256 FROM state WHERE id=1").fetchone()
        if (state is None or state[1:] != (identity(batch["source"]), batch["bundle"]["sha256"])
                or (require_running and state[0] != batch["capture_revision"])):
            raise FixtureError("capture binding changed or activity resumed")
        claim = db.execute("SELECT batch_path,batch_sha256,revision,status FROM claims WHERE claim_id=?",
                           (batch["claim_id"],)).fetchone()
        if (claim is None or claim[:3] != (str(batch_path), expected_sha256, batch["capture_revision"])
                or claim[3] not in ("claimed", "running", "complete", "failed")):
            raise FixtureError("immutable batch has no matching durable claim")
        if require_running and claim[3] != "running":
            raise FixtureError("optimizer admission requires a running unconsumed fixture claim")
        events = batch.get("events")
        if not isinstance(events, list) or not events:
            raise FixtureError("empty eligible fixture batch")
        seen = set()
        for event in events:
            row_id = event["source_row_id"]
            if row_id in seen or row_id not in originals:
                raise FixtureError("unknown or repeated source identity")
            seen.add(row_id)
            row = originals[row_id]
            digest = identity(row)
            if event != {"source_row_id": row_id, "row_sha256": digest,
                         "day_record_id": "fixture-" + digest}:
                raise FixtureError("fixture event differs from original TRAIN record")
            captured = db.execute("SELECT source_row_id,row_sha256,row_json FROM captures WHERE day_record_id=?",
                                  (event["day_record_id"],)).fetchone()
            if captured != (row_id, digest, canonical(row)):
                raise FixtureError("source row absent or altered in capture journal")
            result.append(dict(row, source_row_id=row_id,
                               day_record_id=event["day_record_id"], origin=ORIGIN,
                               training_origin=ORIGIN, actual_user_day=False,
                               bundle_sha256=batch["bundle"]["sha256"],
                               source_packet_sha256=batch["source"]["packet"]["sha256"]))
    verify_pin({"path": str(bundle), "sha256": batch["bundle"]["sha256"]})
    return result


def load_rows(path, expected_sha256, bundle_sha256=None, *, allowed_root=None):
    """Optimizer admission only: a current running durable claim is mandatory."""
    return _load_rows(path, expected_sha256, bundle_sha256, allowed_root=allowed_root,
                      require_running=True)


def inspect_rows(path, expected_sha256, bundle_sha256=None, *, allowed_root=None):
    """Historical source/membership recount only; never optimizer admission."""
    return _load_rows(path, expected_sha256, bundle_sha256, allowed_root=allowed_root,
                      require_running=False)
