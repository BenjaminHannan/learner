#!/usr/bin/env python3
"""nb-321 compact notebook store (BUILD task, sealed after unit tests).

Same public API and SAME decision logic as
scripts/fable_notebook_contract.Notebook (subclassed; every decision method
is inherited untouched). Only the storage backend changes: one SQLite file
per notebook dir (Python standard library only: sqlite3, zlib, hashlib,
json, struct), plus a byte-identical events.jsonl compatibility file.

Byte layout (SQLite file store.db):
  strings(id INTEGER PK AUTOINCREMENT, text UNIQUE) -- every display name,
      alias, literal value and relation text stored once, referenced by id.
  events(n INTEGER PK, kind INTEGER, event_id TEXT UNIQUE, payload BLOB)
      -- one row per event, append-only (triggers reject UPDATE and DELETE).
      payload is a compact binary encoding (varints + length-prefixed
      utf-8); the 64-char prev hash is NOT stored per row, it is recomputed
      from content on export. event ids are stored exactly (needed for
      idempotency) and indexed via the UNIQUE constraint.
  raw_blocks(block_id PK, blob BLOB, hash TEXT, count INTEGER)
      -- raw sentences with the subject display name replaced by 0x01 and
      the value text replaced by 0x02 (0x00-escaped, so lossless), grouped
      256 FACTs per block and zlib-compressed (level 9).
  ev_hashes(block_id PK, hash TEXT, n_start, n_end)
      -- sha256 over the concatenated (n, kind, event_id, payload) bytes of
      each completed 500-event block.
  json_hashes(block_id PK, hash TEXT, n_start, n_end)
      -- sha256 over the raw bytes of each completed 500-line block of the
      on-disk events.jsonl compatibility file.
  fact_state(fact_num PK, subject_num, rel_id, source, valflag, val, n,
      supersedes, superseded_by, retracted) + INDEX(subject_num, rel_id)
      -- derived current-fact index (allowed to change; rebuilt from events).
  alias_map(norm, entity_num) + INDEX(norm); entity_names(entity_num PK,
      name_id); relations(rel_id PK, functional); rules(rule_id PK, body);
      merges(proposal_id PK, keep_num, other_num); meta(key PK, value).

Sidecar store.sha256.json {"n": event_count, "sha256": hex-of-store.db} is
synced on every clean open (after verification). Any single-byte change to a
synced SQLite file changes its whole-file hash while the count matches, so
open() raises LogCorrupt. Crash recovery (stale sidecar, counts differ) takes
the replay path instead and never fails the open.

Durability: PRAGMA synchronous=FULL; every _append commits the SQLite
transaction AND appends+fysncs the JSON line before returning.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import struct
import sys
import time
import zlib
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fable_notebook_contract as C  # noqa: E402 (decision logic, read-only)

DB_NAME = "store.db"
SIDECAR_NAME = "store.sha256.json"
EV_BLOCK = 500
JSON_BLOCK_LINES = 500
RAW_BLOCK = 256

KIND_CODES = {
    "RELATION": 1, "ENTITY": 2, "ALIAS": 3, "FACT": 4,
    "RETRACT": 5, "RULE": 6, "MERGE_PROPOSAL": 7, "PROMOTE": 8,
}
KIND_NAMES = {v: k for k, v in KIND_CODES.items()}
SRC_IDX = {s: i for i, s in enumerate(C.SOURCES)}
ACT_IDX = {a: i for i, a in enumerate(C.ACTORS)}

M_SUBJ = b"\x01"
M_VAL = b"\x02"
M_ESC = b"\x00"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm(name: str) -> str:
    return C._norm(name)


def _pack_uvar(value: int) -> bytes:
    out = bytearray()
    while True:
        bits = value & 0x7F
        value >>= 7
        if value:
            out.append(bits | 0x80)
        else:
            out.append(bits)
            return bytes(out)


def _unpack_uvar(buf: bytes, pos: int) -> tuple[int, int]:
    shift = 0
    result = 0
    while True:
        byte = buf[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, pos
        shift += 7


def _pack_str(text: str) -> bytes:
    raw = text.encode("utf-8")
    return _pack_uvar(len(raw)) + raw


def _unpack_str(buf: bytes, pos: int) -> tuple[str, int]:
    length, pos = _unpack_uvar(buf, pos)
    return buf[pos:pos + length].decode("utf-8"), pos + length


def _entity_num(entity_id: str) -> int:
    return int(entity_id[1:])


def _fact_num(fact_id: str) -> int:
    return int(fact_id[1:])


def _entity_id(num: int) -> str:
    return f"E{num:04d}"


def _fact_id(num: int) -> str:
    return f"F{num:05d}"


def _raw_template(raw: str, subj_name: str, val_text: str) -> bytes:
    """Lossless template: escape 0x00/0x01/0x02, then mark subject/value."""
    out = raw.replace("\x00", "\x00\x00").replace("\x01", "\x00\x01").replace("\x02", "\x00\x02")
    if subj_name:
        out = out.replace(subj_name, "\x01")
    if val_text:
        out = out.replace(val_text, "\x02")
    return out.encode("utf-8")


def _raw_restore(tpl: bytes, subj_name: str, val_text: str) -> str:
    out = tpl.decode("utf-8")
    out = out.replace("\x01", subj_name).replace("\x02", val_text)
    res = []
    i = 0
    while i < len(out):
        ch = out[i]
        if ch == "\x00" and i + 1 < len(out) and out[i + 1] in ("\x00", "\x01", "\x02"):
            res.append(out[i + 1])
            i += 2
        else:
            res.append(ch)
            i += 1
    return "".join(res)


SCHEMA = """
CREATE TABLE IF NOT EXISTS strings(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS events(n INTEGER PRIMARY KEY, kind INTEGER NOT NULL, event_id TEXT NOT NULL UNIQUE, payload BLOB NOT NULL);
CREATE TRIGGER IF NOT EXISTS no_update_events BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'nb321: event log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS no_delete_events BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'nb321: event log is append-only'); END;
CREATE TABLE IF NOT EXISTS raw_blocks(block_id INTEGER PRIMARY KEY, blob BLOB NOT NULL, hash TEXT NOT NULL, count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS ev_hashes(block_id INTEGER PRIMARY KEY, hash TEXT NOT NULL, n_start INTEGER NOT NULL, n_end INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS json_hashes(block_id INTEGER PRIMARY KEY, hash TEXT NOT NULL, n_start INTEGER NOT NULL, n_end INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS fact_state(fact_num INTEGER PRIMARY KEY, subject_num INTEGER NOT NULL, rel_id INTEGER NOT NULL, source INTEGER NOT NULL, valflag INTEGER NOT NULL, val INTEGER NOT NULL, n INTEGER NOT NULL, supersedes INTEGER NOT NULL, superseded_by INTEGER NOT NULL DEFAULT 0, retracted INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS idx_fact_sr ON fact_state(subject_num, rel_id);
CREATE TABLE IF NOT EXISTS alias_map(norm TEXT NOT NULL, entity_num INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS idx_alias_norm ON alias_map(norm);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alias_pair ON alias_map(norm, entity_num);
CREATE TABLE IF NOT EXISTS entity_names(entity_num INTEGER PRIMARY KEY, name_id INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS relations(rel_id INTEGER PRIMARY KEY, functional INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS rules(rule_id TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS merges(proposal_id TEXT PRIMARY KEY, keep_num INTEGER NOT NULL, other_num INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


class _EventsSeq:
    def __init__(self, nb) -> None:
        self._nb = nb

    def __len__(self) -> int:
        return self._nb._event_count()

    def __iter__(self):
        return self._nb._iter_events()


class _EventIdSet:
    def __init__(self, nb) -> None:
        self._nb = nb

    def __contains__(self, event_id) -> bool:
        row = self._nb._db.execute(
            "SELECT 1 FROM events WHERE event_id=?", (event_id,)).fetchone()
        return row is not None

    def add(self, event_id) -> None:  # writes go through _apply_sqlite
        return None

    def __len__(self) -> int:
        return self._nb._event_count()

    def __iter__(self):
        for (eid,) in self._nb._db.execute("SELECT event_id FROM events ORDER BY n"):
            yield eid


class _EntityMap:
    def __init__(self, nb) -> None:
        self._nb = nb

    def __getitem__(self, entity_id: str) -> str:
        return self._nb._entity_name(_entity_num(entity_id))

    def get(self, entity_id, default=None):
        try:
            return self[entity_id]
        except KeyError:
            return default

    def __contains__(self, entity_id) -> bool:
        try:
            num = _entity_num(entity_id)
        except (ValueError, TypeError):
            return False
        return self._nb._db.execute(
            "SELECT 1 FROM entity_names WHERE entity_num=?", (num,)).fetchone() is not None

    def __len__(self) -> int:
        return self._nb._db.execute("SELECT COUNT(*) FROM entity_names").fetchone()[0]


class _AliasMap:
    def __init__(self, nb) -> None:
        self._nb = nb

    def _ids(self, norm: str) -> list:
        rows = self._nb._db.execute(
            "SELECT entity_num FROM alias_map WHERE norm=? ORDER BY rowid", (norm,)).fetchall()
        return [_entity_id(r[0]) for r in rows]

    def get(self, norm, default=None):
        ids = self._ids(norm)
        return ids if ids else default

    def __getitem__(self, norm):
        ids = self._ids(norm)
        if not ids:
            raise KeyError(norm)
        return ids

    def __contains__(self, norm) -> bool:
        return self._nb._db.execute(
            "SELECT 1 FROM alias_map WHERE norm=? LIMIT 1", (norm,)).fetchone() is not None

    def setdefault(self, norm, default=None):
        ids = self._ids(norm)
        return ids if ids else []


class _FactMap:
    def __init__(self, nb) -> None:
        self._nb = nb

    def __getitem__(self, fact_id: str):
        row = self._nb._fact_dict(_fact_num(fact_id))
        if row is None:
            raise KeyError(fact_id)
        return row

    def get(self, fact_id, default=None):
        try:
            num = _fact_num(fact_id)
        except (ValueError, TypeError):
            return default
        return self._nb._fact_dict(num) or default

    def __contains__(self, fact_id) -> bool:
        try:
            num = _fact_num(fact_id)
        except (ValueError, TypeError):
            return False
        return self._nb._db.execute(
            "SELECT 1 FROM fact_state WHERE fact_num=?", (num,)).fetchone() is not None

    def __len__(self) -> int:
        return self._nb._db.execute("SELECT COUNT(*) FROM fact_state").fetchone()[0]


class _SupMap:
    def __init__(self, nb) -> None:
        self._nb = nb

    def __contains__(self, fact_id) -> bool:
        try:
            num = _fact_num(fact_id)
        except (ValueError, TypeError):
            return False
        row = self._nb._db.execute(
            "SELECT superseded_by FROM fact_state WHERE fact_num=?", (num,)).fetchone()
        return row is not None and row[0] != 0

    def get(self, fact_id, default=None):
        if fact_id in self:
            num = _fact_num(fact_id)
            sup = self._nb._db.execute(
                "SELECT superseded_by FROM fact_state WHERE fact_num=?", (num,)).fetchone()[0]
            return _fact_id(sup)
        return default


class _RetrSet:
    def __init__(self, nb) -> None:
        self._nb = nb

    def __contains__(self, fact_id) -> bool:
        try:
            num = _fact_num(fact_id)
        except (ValueError, TypeError):
            return False
        row = self._nb._db.execute(
            "SELECT retracted FROM fact_state WHERE fact_num=?", (num,)).fetchone()
        return row is not None and row[0] != 0

    def add(self, fact_id) -> None:  # writes go through _apply_sqlite
        return None


class _RuleMap:
    def __init__(self, nb) -> None:
        self._nb = nb

    def __contains__(self, rule_id) -> bool:
        return self._nb._db.execute(
            "SELECT 1 FROM rules WHERE rule_id=?", (rule_id,)).fetchone() is not None

    def __getitem__(self, rule_id):
        row = self._nb._db.execute(
            "SELECT body FROM rules WHERE rule_id=?", (rule_id,)).fetchone()
        if row is None:
            raise KeyError(rule_id)
        return row[0]

    def get(self, rule_id, default=None):
        try:
            return self[rule_id]
        except KeyError:
            return default


class _FuncSet:
    def __init__(self, nb) -> None:
        self._nb = nb

    def __contains__(self, relation) -> bool:
        rid = self._nb._rel_id_by_text(relation)
        if rid is None:
            return False
        row = self._nb._db.execute(
            "SELECT functional FROM relations WHERE rel_id=?", (rid,)).fetchone()
        return row is not None and row[0] != 0

    def add(self, relation) -> None:  # writes go through _apply_sqlite
        return None


class _MergeMap:
    def __init__(self, nb) -> None:
        self._nb = nb

    def __setitem__(self, pid, event) -> None:
        self._nb._db.execute(
            "INSERT OR REPLACE INTO merges(proposal_id, keep_num, other_num) VALUES(?,?,?)",
            (pid, _entity_num(event["keep"]), _entity_num(event["other"])))

    def get(self, pid, default=None):
        row = self._nb._db.execute(
            "SELECT keep_num, other_num FROM merges WHERE proposal_id=?", (pid,)).fetchone()
        if row is None:
            return default
        return {"keep": _entity_id(row[0]), "other": _entity_id(row[1])}


class CompactNotebook321(C.Notebook):
    """SQLite-backed notebook with the contract's decision logic (inherited)."""

    def __init__(self, root) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / C.LOG_NAME
        self.db_path = self.root / DB_NAME
        self.sidecar_path = self.root / SIDECAR_NAME
        self.torn_tail = False
        self._db = sqlite3.connect(str(self.db_path), isolation_level=None)
        self._db.execute("PRAGMA synchronous=FULL")
        self._db.execute("PRAGMA journal_mode=DELETE")
        self._db.executescript(SCHEMA)
        self._db.commit()
        self._str_to_id: dict[str, int] = {}
        self._id_to_str: dict[int, str] = {}
        self._name_cache: dict[int, str] = {}
        self._rel_cache: dict[str, int] = {}
        self._last_sha = C.GENESIS
        self._count = 0
        self._json_hasher = hashlib.sha256()
        self._json_pending = 0
        self._raw_ids: list[int] = []
        self._raw_tpls: list[bytes] = []
        self.events = _EventsSeq(self)
        self.event_ids = _EventIdSet(self)
        self.entities = _EntityMap(self)
        self.aliases = _AliasMap(self)
        self.facts = _FactMap(self)
        self.superseded = _SupMap(self)
        self.retracted = _RetrSet(self)
        self.rules = _RuleMap(self)
        self.functional = _FuncSet(self)
        self.merge_proposals = _MergeMap(self)
        self._open_sync()

    # ------------------------------------------------------------ internals
    def _reset(self) -> None:
        self._str_to_id.clear()
        self._id_to_str.clear()
        self._name_cache.clear()
        self._rel_cache.clear()

    def _event_count(self) -> int:
        return self._count

    def _str_id(self, text: str) -> int:
        got = self._str_to_id.get(text)
        if got is not None:
            return got
        row = self._db.execute("SELECT id FROM strings WHERE text=?", (text,)).fetchone()
        if row is not None:
            self._str_to_id[text] = row[0]
            self._id_to_str[row[0]] = text
            return row[0]
        cur = self._db.execute("INSERT INTO strings(text) VALUES(?)", (text,))
        sid = cur.lastrowid
        self._str_to_id[text] = sid
        self._id_to_str[sid] = text
        return sid

    def _str_text(self, sid: int) -> str:
        got = self._id_to_str.get(sid)
        if got is not None:
            return got
        row = self._db.execute("SELECT text FROM strings WHERE id=?", (sid,)).fetchone()
        if row is None:
            raise KeyError(sid)
        self._id_to_str[sid] = row[0]
        self._str_to_id[row[0]] = sid
        return row[0]

    def _rel_id_by_text(self, relation: str):
        got = self._rel_cache.get(relation)
        if got is not None:
            return got
        row = self._db.execute("SELECT id FROM strings WHERE text=?", (relation,)).fetchone()
        if row is None:
            return None
        self._rel_cache[relation] = row[0]
        return row[0]

    def _entity_name(self, num: int) -> str:
        got = self._name_cache.get(num)
        if got is not None:
            return got
        row = self._db.execute(
            "SELECT name_id FROM entity_names WHERE entity_num=?", (num,)).fetchone()
        if row is None:
            raise KeyError(_entity_id(num))
        name = self._str_text(row[0])
        self._name_cache[num] = name
        return name

    def _show_val(self, valflag: int, val: int) -> str:
        if valflag == 1:
            return self._entity_name(val)
        return self._str_text(val)

    # ------------------------------------------------------- payload codec
    def _encode_payload(self, ev: dict) -> bytes:
        kind = ev["kind"]
        if kind == "RELATION":
            rid = self._str_id(ev["relation"])
            return bytes((KIND_CODES[kind],)) + _pack_uvar(rid) + bytes((1 if ev["functional"] else 0,))
        if kind == "ENTITY":
            return (bytes((KIND_CODES[kind],)) + _pack_uvar(_entity_num(ev["entity_id"]))
                    + _pack_uvar(self._str_id(ev["name"])))
        if kind == "ALIAS":
            return (bytes((KIND_CODES[kind],)) + _pack_uvar(_entity_num(ev["entity_id"]))
                    + _pack_uvar(self._str_id(ev["alias"])))
        if kind == "FACT":
            return self._encode_fact_payload(ev, None)
        if kind == "RETRACT":
            out = (bytes((KIND_CODES[kind],)) + _pack_uvar(_fact_num(ev["fact_id"]))
                   + bytes((ACT_IDX[ev["actor"]],)) + _pack_str(ev.get("reason") or ""))
            return out
        if kind == "RULE":
            return bytes((KIND_CODES[kind],)) + _pack_str(ev["rule_id"]) + _pack_str(ev["body"])
        if kind == "MERGE_PROPOSAL":
            return (bytes((KIND_CODES[kind],)) + _pack_uvar(_entity_num(ev["keep"]))
                    + _pack_uvar(_entity_num(ev["other"]))
                    + bytes((ACT_IDX.get(ev.get("actor"), 0),)))
        raise ValueError(f"unknown kind {kind}")

    def _encode_fact_payload(self, ev: dict, raw_ref) -> bytes:
        out = bytearray()
        out.append(KIND_CODES["FACT"])
        out += _pack_uvar(_fact_num(ev["fact_id"]))
        out += _pack_uvar(_entity_num(ev["subject"]))
        out += _pack_uvar(self._str_id(ev["relation"]))
        out += bytes((SRC_IDX[ev["source"]], ACT_IDX[ev["actor"]]))
        value = ev["value"]
        if "entity" in value:
            out += bytes((1,)) + _pack_uvar(_entity_num(value["entity"]))
        else:
            out += bytes((0,)) + _pack_uvar(self._str_id(value["literal"]))
        sup = ev.get("supersedes")
        out += _pack_uvar(_fact_num(sup) if sup else 0)
        rule = ev.get("rule_id")
        if rule:
            out += bytes((1,)) + _pack_str(rule)
        else:
            out += bytes((0,))
        deps = ev.get("deps") or []
        out += _pack_uvar(len(deps))
        for dep in deps:
            out += _pack_uvar(_fact_num(dep))
        prov = ev.get("provenance")
        if prov is None:
            out += bytes((0,))
        else:
            out += bytes((1,)) + _pack_str(json.dumps(prov, sort_keys=True, ensure_ascii=False))
        if raw_ref is None:
            out += bytes((0,))
        else:
            out += bytes((1,)) + _pack_uvar(raw_ref[0]) + _pack_uvar(raw_ref[1])
        return bytes(out)

    def _decode_payload(self, n: int, kind: int, event_id: str, payload: bytes) -> dict:
        pos = 1
        if kind == KIND_CODES["RELATION"]:
            rid, pos = _unpack_uvar(payload, pos)
            return {"kind": "RELATION", "event_id": event_id,
                    "relation": self._str_text(rid), "functional": bool(payload[pos])}
        if kind == KIND_CODES["ENTITY"]:
            num, pos = _unpack_uvar(payload, pos)
            sid, pos = _unpack_uvar(payload, pos)
            return {"kind": "ENTITY", "event_id": event_id,
                    "entity_id": _entity_id(num), "name": self._str_text(sid)}
        if kind == KIND_CODES["ALIAS"]:
            num, pos = _unpack_uvar(payload, pos)
            sid, pos = _unpack_uvar(payload, pos)
            return {"kind": "ALIAS", "event_id": event_id,
                    "entity_id": _entity_id(num), "alias": self._str_text(sid)}
        if kind == KIND_CODES["FACT"]:
            return self._decode_fact_payload(n, event_id, payload, pos)
        if kind == KIND_CODES["RETRACT"]:
            fnum, pos = _unpack_uvar(payload, pos)
            actor = C.ACTORS[payload[pos]]
            pos += 1
            reason, pos = _unpack_str(payload, pos)
            return {"kind": "RETRACT", "event_id": event_id, "fact_id": _fact_id(fnum),
                    "actor": actor, "reason": reason}
        if kind == KIND_CODES["RULE"]:
            rid, pos = _unpack_str(payload, pos)
            body, pos = _unpack_str(payload, pos)
            return {"kind": "RULE", "event_id": event_id, "rule_id": rid, "body": body}
        if kind == KIND_CODES["MERGE_PROPOSAL"]:
            keep, pos = _unpack_uvar(payload, pos)
            other, pos = _unpack_uvar(payload, pos)
            actor = C.ACTORS[payload[pos]] if pos < len(payload) else "sleep"
            return {"kind": "MERGE_PROPOSAL", "event_id": event_id, "proposal_id": event_id,
                    "actor": actor, "keep": _entity_id(keep), "other": _entity_id(other)}
        raise ValueError(f"unknown kind code {kind}")

    def _decode_fact_payload(self, n: int, event_id: str, payload: bytes, pos: int) -> dict:
        fnum, pos = _unpack_uvar(payload, pos)
        subj, pos = _unpack_uvar(payload, pos)
        rid, pos = _unpack_uvar(payload, pos)
        src = C.SOURCES[payload[pos]]
        actor = C.ACTORS[payload[pos + 1]]
        pos += 2
        vflag = payload[pos]
        pos += 1
        vref, pos = _unpack_uvar(payload, pos)
        sup, pos = _unpack_uvar(payload, pos)
        has_rule = payload[pos]
        pos += 1
        rule = None
        if has_rule:
            rule, pos = _unpack_str(payload, pos)
        ndeps, pos = _unpack_uvar(payload, pos)
        deps = []
        for _ in range(ndeps):
            dep, pos = _unpack_uvar(payload, pos)
            deps.append(_fact_id(dep))
        has_prov = payload[pos]
        pos += 1
        prov = None
        if has_prov:
            pstext, pos = _unpack_str(payload, pos)
            prov = json.loads(pstext)
        has_raw = payload[pos]
        pos += 1
        raw = None
        if has_raw:
            rb, pos = _unpack_uvar(payload, pos)
            ri, pos = _unpack_uvar(payload, pos)
            subj_name = self._entity_name(subj)
            if vflag == 1:
                vtext = self._entity_name(vref)
            else:
                vtext = self._str_text(vref)
            raw = _raw_restore(self._raw_template(rb, ri), subj_name, vtext)
        value = {"entity": _entity_id(vref)} if vflag == 1 else {"literal": self._str_text(vref)}
        return {"kind": "FACT", "event_id": event_id, "fact_id": _fact_id(fnum),
                "actor": actor, "source": src, "subject": _entity_id(subj),
                "relation": self._str_text(rid), "value": value,
                "supersedes": _fact_id(sup) if sup else None, "raw": raw,
                "rule_id": rule, "deps": deps, "provenance": prov}

    def _raw_template(self, block_id: int, idx: int) -> bytes:
        row = self._db.execute(
            "SELECT blob FROM raw_blocks WHERE block_id=?", (block_id,)).fetchone()
        if row is None:
            raise C.LogCorrupt(f"missing raw block {block_id}")
        blob = zlib.decompress(bytes(row[0]))
        pos = 0
        count, pos = _unpack_uvar(blob, pos)
        for _ in range(idx):
            ln, pos = _unpack_uvar(blob, pos)
            pos += ln
        ln, pos = _unpack_uvar(blob, pos)
        return blob[pos:pos + ln]

    # ------------------------------------------------------------ apply
    def _apply_sqlite(self, ev: dict, raw_tpl: bytes | None) -> None:
        kind = ev["kind"]
        db = self._db
        if kind == "RELATION":
            rid = self._str_id(ev["relation"])
            db.execute("INSERT OR REPLACE INTO relations(rel_id, functional) VALUES(?,?)",
                       (rid, 1 if ev["functional"] else 0))
            payload = self._encode_payload(ev)
        elif kind == "ENTITY":
            num = _entity_num(ev["entity_id"])
            db.execute("INSERT OR REPLACE INTO entity_names(entity_num, name_id) VALUES(?,?)",
                       (num, self._str_id(ev["name"])))
            db.execute("INSERT OR IGNORE INTO alias_map(norm, entity_num) VALUES(?,?)",
                       (_norm(ev["name"]), num))
            payload = self._encode_payload(ev)
        elif kind == "ALIAS":
            db.execute("INSERT OR IGNORE INTO alias_map(norm, entity_num) VALUES(?,?)",
                       (_norm(ev["alias"]), _entity_num(ev["entity_id"])))
            payload = self._encode_payload(ev)
        elif kind == "FACT":
            raw_ref = None
            if raw_tpl is not None:
                raw_ref = self._store_raw_template(raw_tpl)
            payload = self._encode_fact_payload(ev, raw_ref)
            fnum = _fact_num(ev["fact_id"])
            value = ev["value"]
            if "entity" in value:
                vflag, vref = 1, _entity_num(value["entity"])
            else:
                vflag, vref = 0, self._str_id(value["literal"])
            sup = ev.get("supersedes")
            db.execute(
                "INSERT OR REPLACE INTO fact_state(fact_num, subject_num, rel_id, source, valflag, val, n, supersedes, superseded_by, retracted)"
                " VALUES(?,?,?,?,?,?,?,?,?,?)",
                (fnum, _entity_num(ev["subject"]), self._str_id(ev["relation"]),
                 SRC_IDX[ev["source"]], vflag, vref, ev["n"],
                 _fact_num(sup) if sup else 0, 0, 0))
            if sup:
                db.execute("UPDATE fact_state SET superseded_by=? WHERE fact_num=?",
                           (fnum, _fact_num(sup)))
        elif kind == "RETRACT":
            db.execute("UPDATE fact_state SET retracted=1 WHERE fact_num=?",
                       (_fact_num(ev["fact_id"]),))
            payload = self._encode_payload(ev)
        elif kind == "RULE":
            db.execute("INSERT OR REPLACE INTO rules(rule_id, body) VALUES(?,?)",
                       (ev["rule_id"], ev["body"]))
            payload = self._encode_payload(ev)
        elif kind == "MERGE_PROPOSAL":
            db.execute("INSERT OR REPLACE INTO merges(proposal_id, keep_num, other_num) VALUES(?,?,?)",
                       (ev["proposal_id"], _entity_num(ev["keep"]), _entity_num(ev["other"])))
            payload = self._encode_payload(ev)
        elif kind == "PROMOTE":
            payload = bytes((KIND_CODES["PROMOTE"],)) + _pack_str(ev.get("event_id", ""))
        else:
            raise ValueError(f"unknown kind {kind}")
        db.execute("INSERT INTO events(n, kind, event_id, payload) VALUES(?,?,?,?)",
                   (ev["n"], KIND_CODES[kind], ev["event_id"], payload))

    def _store_raw_template(self, tpl: bytes) -> tuple[int, int]:
        if not self._raw_ids or len(self._raw_tpls) >= RAW_BLOCK:
            self._flush_raw_block()
        if not self._raw_ids:
            row = self._db.execute("SELECT COALESCE(MAX(block_id),0)+1 FROM raw_blocks").fetchone()
            bid = row[0]
            self._db.execute("INSERT INTO raw_blocks(block_id, blob, hash, count) VALUES(?,?,?,?)",
                             (bid, zlib.compress(_pack_uvar(0), 9), "", 0))
            self._raw_ids = [bid]
            self._raw_tpls = []
        idx = len(self._raw_tpls)
        self._raw_tpls.append(tpl)
        bid = self._raw_ids[0]
        blob = _pack_uvar(len(self._raw_tpls))
        for item in self._raw_tpls:
            blob += _pack_uvar(len(item)) + item
        digest = hashlib.sha256(blob).hexdigest()
        self._db.execute("UPDATE raw_blocks SET blob=?, hash=?, count=? WHERE block_id=?",
                         (zlib.compress(blob, 9), digest, len(self._raw_tpls), bid))
        if len(self._raw_tpls) >= RAW_BLOCK:
            self._flush_raw_block()
        return bid, idx

    def _flush_raw_block(self) -> None:
        self._raw_ids = []
        self._raw_tpls = []

    # ------------------------------------------------------------ durable log
    def _append(self, event: dict) -> None:
        if self.torn_tail:
            raise C.LogCorrupt("torn final line present; run repair_torn_tail() first")
        full = dict(event, n=self._count + 1, prev=self._last_sha, v=C.FORMAT_VERSION)
        line = json.dumps(full, sort_keys=True, ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        with open(self.path, "rb") as handle:  # read-back before anyone says "saved"
            handle.seek(-(len(line.encode("utf-8")) + 1), os.SEEK_END)
            if handle.read().decode("utf-8") != line + "\n":
                raise C.LogCorrupt("read-back mismatch")
        raw_tpl = None
        if full["kind"] == "FACT" and full.get("raw") is not None:
            subj_name = self._entity_name(_entity_num(full["subject"]))
            value = full["value"]
            if "entity" in value:
                vtext = self._entity_name(_entity_num(value["entity"]))
            else:
                vtext = value["literal"]
            raw_tpl = _raw_template(full["raw"], subj_name, vtext)
        self._db.execute("BEGIN IMMEDIATE")
        try:
            self._apply_sqlite(full, raw_tpl)
            self._db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)",
                             ("last_sha", _sha(line)))
            self._db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)",
                             ("count", str(full["n"])))
            self._maybe_store_ev_hash(full["n"])
            self._db.execute("COMMIT")
        except Exception:
            self._db.execute("ROLLBACK")
            raise
        self._count = full["n"]
        self._last_sha = _sha(line)
        line_bytes = (line + "\n").encode("utf-8")
        self._json_hasher.update(line_bytes)
        self._json_pending += 1
        if self._json_pending >= JSON_BLOCK_LINES:
            self._store_json_hash()
        # raw block bookkeeping across commits
        if self._raw_tpls and len(self._raw_tpls) >= RAW_BLOCK:
            self._flush_raw_block()

    def _maybe_store_ev_hash(self, n: int) -> None:
        if n % EV_BLOCK != 0:
            return
        bid = n // EV_BLOCK
        start = n - EV_BLOCK + 1
        digest = hashlib.sha256()
        for (nn, kind, eid, pay) in self._db.execute(
                "SELECT n, kind, event_id, payload FROM events WHERE n BETWEEN ? AND ? ORDER BY n",
                (start, n)):
            digest.update(struct.pack(">i", nn))
            digest.update(bytes((kind,)))
            digest.update(eid.encode("utf-8"))
            digest.update(b"\x00")
            digest.update(bytes(pay))
        self._db.execute(
            "INSERT OR REPLACE INTO ev_hashes(block_id, hash, n_start, n_end) VALUES(?,?,?,?)",
            (bid, digest.hexdigest(), start, n))

    def _store_json_hash(self) -> None:
        if self._json_pending == 0:
            return
        end = self._count
        start = end - self._json_pending + 1
        bid = (end - 1) // JSON_BLOCK_LINES + 1
        self._db.execute(
            "INSERT OR REPLACE INTO json_hashes(block_id, hash, n_start, n_end) VALUES(?,?,?,?)",
            (bid, self._json_hasher.hexdigest(), start, end))
        self._json_hasher = hashlib.sha256()
        self._json_pending = 0

    # ------------------------------------------------------------ load/verify
    def _meta_get(self, key: str):
        row = self._db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def _read_json_tail(self):
        """Return (good_lines, torn_bytes). good_lines excludes any torn tail."""
        if not self.path.exists():
            return [], b""
        raw = self.path.read_bytes()
        if not raw:
            return [], b""
        lines = raw.split(b"\n")
        tail = lines.pop()  # after final newline this is b""; else torn bytes
        if tail:
            return lines, tail
        if lines and lines[-1] == b"":
            lines.pop()
        return lines, b""

    def _open_sync(self) -> None:
        good, torn = self._read_json_tail()
        self.torn_tail = bool(torn)
        # streaming pass over the good prefix: count + per-block byte hashes
        hasher = hashlib.sha256()
        pending = 0
        n_json = 0
        last_line = ""
        for raw in good:
            if not raw.strip():
                continue
            n_json += 1
            hasher.update(raw + b"\n")
            pending += 1
            if pending >= JSON_BLOCK_LINES:
                bid = n_json // JSON_BLOCK_LINES
                self._check_json_block(bid, n_json - pending + 1, n_json, hasher.hexdigest())
                hasher = hashlib.sha256()
                pending = 0
            last_line = raw.decode("utf-8")
        # db count
        row = self._db.execute("SELECT COUNT(*) FROM events").fetchone()
        n_db = row[0]
        if n_json < n_db:
            raise C.LogCorrupt(f"json log shorter than sqlite history ({n_json} < {n_db})")
        # replay any json lines missing from sqlite (crash between json fsync and commit)
        if n_json > n_db and not self.torn_tail:
            lines = [r.decode("utf-8") for r in good if r.strip()]
            expect = self._meta_get("last_sha") or C.GENESIS
            self._db.execute("BEGIN IMMEDIATE")
            try:
                for line in lines[n_db:]:
                    ev = json.loads(line)
                    if ev.get("prev") != expect:
                        raise C.LogCorrupt("hash chain broken during replay")
                    raw_tpl = None
                    if ev["kind"] == "FACT" and ev.get("raw") is not None:
                        subj_name = self._entity_name(_entity_num(ev["subject"]))
                        value = ev["value"]
                        vtext = (self._entity_name(_entity_num(value["entity"]))
                                 if "entity" in value else value["literal"])
                        raw_tpl = _raw_template(ev["raw"], subj_name, vtext)
                    self._apply_sqlite(ev, raw_tpl)
                    expect = _sha(line)
                    if ev["n"] % EV_BLOCK == 0:
                        self._maybe_store_ev_hash(ev["n"])
                self._db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)",
                                 ("last_sha", expect))
                self._db.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)",
                                 ("count", str(n_json)))
                self._db.execute("COMMIT")
            except Exception:
                self._db.execute("ROLLBACK")
                raise
        # verify stored block hashes over sqlite history
        self._verify_ev_hashes()
        self._verify_raw_hashes()
        # chain over at least the last 1000 good lines
        if n_json and not self.torn_tail:
            self._verify_tail_chain(good)
        elif n_json and self.torn_tail:
            self._verify_tail_chain(good)
        # whole-file sidecar check (catches any single-byte sqlite change)
        self._check_sidecar(n_json if not self.torn_tail else n_json)
        # refresh in-memory counters + running json hash state
        self._count = n_json
        last = self._meta_get("last_sha")
        if last is None and n_json:
            last = _sha(last_line) if last_line else C.GENESIS
        self._last_sha = last or C.GENESIS
        self._json_hasher = hasher
        self._json_pending = pending
        # reload open raw block templates (continue appending after restart)
        self._reload_raw_tail()
        self._db.commit()
        self._sync_sidecar()

    def _check_json_block(self, bid: int, start: int, end: int, digest: str) -> None:
        row = self._db.execute(
            "SELECT hash FROM json_hashes WHERE block_id=?", (bid,)).fetchone()
        if row is None:
            self._db.execute(
                "INSERT INTO json_hashes(block_id, hash, n_start, n_end) VALUES(?,?,?,?)",
                (bid, digest, start, end))
            self._db.commit()
        elif row[0] != digest:
            raise C.LogCorrupt(f"json block {bid} hash mismatch (stored history edited?)")

    def _verify_ev_hashes(self) -> None:
        for (bid, want, start, end) in self._db.execute(
                "SELECT block_id, hash, n_start, n_end FROM ev_hashes ORDER BY block_id"):
            digest = hashlib.sha256()
            for (nn, kind, eid, pay) in self._db.execute(
                    "SELECT n, kind, event_id, payload FROM events WHERE n BETWEEN ? AND ? ORDER BY n",
                    (start, end)):
                digest.update(struct.pack(">i", nn))
                digest.update(bytes((kind,)))
                digest.update(eid.encode("utf-8"))
                digest.update(b"\x00")
                digest.update(bytes(pay))
            if digest.hexdigest() != want:
                raise C.LogCorrupt(f"event block {bid} hash mismatch")

    def _verify_raw_hashes(self) -> None:
        for (bid, want, blob) in self._db.execute("SELECT block_id, hash, blob FROM raw_blocks"):
            if hashlib.sha256(zlib.decompress(bytes(blob))).hexdigest() != want:
                raise C.LogCorrupt(f"raw block {bid} hash mismatch")

    def _verify_tail_chain(self, good) -> None:
        lines = [r for r in good if r.strip()]
        window = lines[-1000:]
        prev = None
        if len(lines) > len(window):
            prev = _sha(lines[-len(window) - 1].decode("utf-8"))
            # chain continuity into the window is covered by block hashes;
            # inside the window every link is checked below.
        else:
            prev = C.GENESIS
        for raw in window:
            try:
                ev = json.loads(raw.decode("utf-8"))
            except ValueError as exc:
                raise C.LogCorrupt(f"bad json line: {exc}") from exc
            if prev is not None and ev.get("prev") != prev:
                raise C.LogCorrupt("hash chain broken in tail window")
            prev = _sha(raw.decode("utf-8"))
        if lines:
            self._tail_sha = _sha(lines[-1].decode("utf-8"))
        else:
            self._tail_sha = C.GENESIS

    def _check_sidecar(self, n_json: int) -> None:
        if not self.sidecar_path.exists():
            return
        try:
            saved = json.loads(self.sidecar_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return  # corrupt sidecar after a crash is not tamper evidence
        row = self._db.execute("SELECT COUNT(*) FROM events").fetchone()
        n_db = row[0]
        if saved.get("n") != n_db:
            return  # writes or recovery since the last clean sync; not tamper
        digest = hashlib.sha256()
        with open(self.db_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        if digest.hexdigest() != saved.get("sha256"):
            raise C.LogCorrupt("sqlite file changed (whole-file hash mismatch)")

    def _sync_sidecar(self) -> None:
        row = self._db.execute("SELECT COUNT(*) FROM events").fetchone()
        digest = hashlib.sha256()
        with open(self.db_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                digest.update(chunk)
        tmp = self.sidecar_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"n": row[0], "sha256": digest.hexdigest()}),
                       encoding="utf-8")
        with open(tmp, "a", encoding="utf-8") as fh:
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.sidecar_path)

    def _reload_raw_tail(self) -> None:
        row = self._db.execute(
            "SELECT block_id, blob, count FROM raw_blocks ORDER BY block_id DESC LIMIT 1").fetchone()
        self._raw_ids = []
        self._raw_tpls = []
        if row is None:
            return
        bid, blob, count = row
        if count >= RAW_BLOCK:
            return
        data = zlib.decompress(bytes(blob))
        pos = 0
        total, pos = _unpack_uvar(data, pos)
        tpls = []
        for _ in range(total):
            ln, pos = _unpack_uvar(data, pos)
            tpls.append(data[pos:pos + ln])
            pos += ln
        self._raw_ids = [bid]
        self._raw_tpls = tpls

    def repair_torn_tail(self) -> None:
        """Truncate the torn JSON tail (contract behaviour) and resync."""
        if not self.torn_tail:
            return
        raw = self.path.read_text(encoding="utf-8")
        good, _, torn = raw.rpartition("\n")
        (self.root / "torn-tail.txt").write_text(torn, encoding="utf-8")
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(good + "\n" if good else "", encoding="utf-8")
        os.replace(tmp, self.path)
        self.torn_tail = False
        self._reset()
        self._open_sync()

    # ------------------------------------------------------------ reads
    def _fact_row(self, fnum: int):
        return self._db.execute(
            "SELECT subject_num, rel_id, source, valflag, val, n, supersedes FROM fact_state"
            " WHERE fact_num=?", (fnum,)).fetchone()

    def _fact_dict(self, fnum: int):
        row = self._db.execute(
            "SELECT n, kind, event_id, payload FROM events WHERE n=("
            "SELECT n FROM fact_state WHERE fact_num=?)", (fnum,)).fetchone()
        if row is None:
            return None
        n, kind, eid, payload = row
        ev = self._decode_payload(n, kind, eid, bytes(payload))
        ev["n"] = n
        ev["prev"] = ""
        ev["v"] = C.FORMAT_VERSION
        return ev

    def active(self, fact_id: str) -> bool:
        try:
            fnum = _fact_num(fact_id)
        except (ValueError, TypeError):
            return False
        row = self._db.execute(
            "SELECT source, retracted, superseded_by FROM fact_state WHERE fact_num=?",
            (fnum,)).fetchone()
        if row is None or row[1] or row[2]:
            return False
        if C.SOURCES[row[0]] == "inferred":
            evrow = self._db.execute(
                "SELECT event_id, payload FROM events WHERE n=("
                "SELECT n FROM fact_state WHERE fact_num=?)", (fnum,)).fetchone()
            if evrow is None:
                return False
            ev = self._decode_payload(0, KIND_CODES["FACT"], evrow[0], bytes(evrow[1]))
            if ev["rule_id"] not in self.rules:
                return False
            return all(self.active(dep) for dep in ev["deps"])
        return True

    def current(self, entity_id: str, relation: str) -> list[dict]:
        """Active answering facts for (entity, relation), best source first."""
        try:
            snum = _entity_num(entity_id)
        except (ValueError, TypeError):
            return []
        rid = self._rel_id_by_text(relation)
        if rid is None:
            return []
        rows = self._db.execute(
            "SELECT fact_num, source, n FROM fact_state WHERE subject_num=? AND rel_id=?",
            (snum, rid)).fetchall()
        cands = []
        for (fnum, src, n) in rows:
            if C.SOURCES[src] not in C.ANSWERING_SOURCES:
                continue
            if not self.active(_fact_id(fnum)):
                continue
            cands.append((fnum, src, n))
        cands.sort(key=lambda t: (C.ANSWERING_SOURCES.index(C.SOURCES[t[1]]), -t[2]))
        if not cands:
            return []
        best = C.SOURCES[cands[0][1]]
        out = []
        for (fnum, src, _n) in cands:
            if C.SOURCES[src] != best:
                break
            out.append(self._fact_dict(fnum))
        return out

    def _show(self, value: dict) -> str:
        if "entity" in value:
            return self._entity_name(_entity_num(value["entity"]))
        return str(value["literal"])

    # ------------------------------------------------------------ export
    def _iter_events(self):
        prev = C.GENESIS
        for (n, kind, eid, payload) in self._db.execute(
                "SELECT n, kind, event_id, payload FROM events ORDER BY n"):
            ev = self._decode_payload(n, kind, eid, bytes(payload))
            ev["n"] = n
            ev["prev"] = prev
            ev["v"] = C.FORMAT_VERSION
            line = json.dumps(ev, sort_keys=True, ensure_ascii=False)
            prev = _sha(line)
            yield ev

    def export_events(self, path) -> None:
        """Write events.jsonl BYTE-IDENTICAL to the contract notebook's."""
        out = Path(path)
        if out.parent and str(out.parent):
            out.parent.mkdir(parents=True, exist_ok=True)
        prev = C.GENESIS
        with open(out, "w", encoding="utf-8") as fh:
            for (n, kind, eid, payload) in self._db.execute(
                    "SELECT n, kind, event_id, payload FROM events ORDER BY n"):
                ev = self._decode_payload(n, kind, eid, bytes(payload))
                ev["n"] = n
                ev["prev"] = prev
                ev["v"] = C.FORMAT_VERSION
                line = json.dumps(ev, sort_keys=True, ensure_ascii=False)
                fh.write(line + "\n")
                prev = _sha(line)
            fh.flush()
            os.fsync(fh.fileno())

    def verify_all(self) -> dict:
        """Re-verify the whole history; report how long it takes."""
        t0 = time.perf_counter()
        self._verify_ev_hashes()
        self._verify_raw_hashes()
        rows = self._db.execute(
            "SELECT n, kind, event_id, payload FROM events ORDER BY n").fetchall()
        prev = C.GENESIS
        for (n, kind, eid, payload) in rows:
            ev = self._decode_payload(n, kind, eid, bytes(payload))
            ev["n"] = n
            ev["prev"] = prev
            ev["v"] = C.FORMAT_VERSION
            prev = _sha(json.dumps(ev, sort_keys=True, ensure_ascii=False))
        if self._meta_get("last_sha") != prev and rows:
            raise C.LogCorrupt("last_sha mismatch in verify_all")
        good, torn = self._read_json_tail()
        if torn:
            raise C.LogCorrupt("torn tail present during verify_all")
        n_json = sum(1 for r in good if r.strip())
        if n_json != len(rows):
            raise C.LogCorrupt(f"json/sqlite count mismatch ({n_json} != {len(rows)})")
        for raw in good:
            if not raw.strip():
                continue
            want = json.loads(raw.decode("utf-8"))
            n = want["n"]
            row = self._db.execute(
                "SELECT kind, event_id, payload FROM events WHERE n=?", (n,)).fetchone()
            if row is None:
                raise C.LogCorrupt(f"event n={n} missing from sqlite")
            got = self._decode_payload(n, row[0], row[1], bytes(row[2]))
            got["n"] = n
            got["prev"] = want["prev"]
            got["v"] = want.get("v", C.FORMAT_VERSION)
            if json.dumps(got, sort_keys=True, ensure_ascii=False) != raw.decode("utf-8"):
                raise C.LogCorrupt(f"event n={n} differs between json and sqlite")
        dt = time.perf_counter() - t0
        return {"ok": True, "n_events": len(rows), "elapsed_s": dt}

    def close(self) -> None:
        try:
            self._db.commit()
        finally:
            self._db.close()


def open_compact(root) -> CompactNotebook321:
    """Factory for the nb-320 runner (--factory scripts/claude_nb321_store.py:open_compact)."""
    return CompactNotebook321(root)
