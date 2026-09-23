#!/usr/bin/env python3
"""Exp 280b re-run adapter (director ruling 2026-09-23 08:28 UTC).

One mechanical rename only: the blind panel names its turn-text column
`user`, the sealed runner requires `user_text`. Every row is copied
identically except the key `user` renamed to `user_text` at the same
position (same order, same values, no other key touched).

Checks (asserts, recorded in rerun/ADAPT.txt):
  - row count is exactly 50
  - every source row carries `user` (str) and no `user_text`
  - every adapted row carries `user_text` with text equal to source `user`
  - every other key and value equal between source and adapted row
Never prints item text; only counts and sha256 values.
"""

import hashlib
import json
import os
import sys

SRC = "artifacts/claude-capabilpanel280b-20260923/panel.jsonl"
DST = "artifacts/claude-capab280b-20260923/rerun/panel-adapted.jsonl"
REPORT = "artifacts/claude-capab280b-20260923/rerun/ADAPT.txt"
EXPECTED_ROWS = 50


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    checks = []
    src_lines = open(SRC, encoding="utf-8").read().strip().split("\n")
    src_lines = [x for x in src_lines if x.strip()]
    rows = [json.loads(x) for x in src_lines]

    n = len(rows)
    checks.append(f"row_count={n} expected={EXPECTED_ROWS} ok={n == EXPECTED_ROWS}")
    assert n == EXPECTED_ROWS, f"row count {n} != {EXPECTED_ROWS}"

    out_rows = []
    for i, r in enumerate(rows):
        assert isinstance(r, dict), f"row {i} not an object"
        assert "user" in r, f"row {i} missing key user"
        assert "user_text" not in r, f"row {i} already has key user_text"
        assert isinstance(r["user"], str), f"row {i} user not a string"
        new = {}
        for k, v in r.items():
            new["user_text" if k == "user" else k] = v
        assert list(new.keys()) == [
            "user_text" if k == "user" else k for k in r.keys()
        ], f"row {i} key order changed"
        assert new["user_text"] == r["user"], f"row {i} text mismatch"
        for k, v in r.items():
            if k == "user":
                continue
            assert k in new and new[k] == v, f"row {i} key {k} changed"
        assert set(new.keys()) == set(r.keys()) - {"user"} | {"user_text"}
        out_rows.append(new)
    checks.append(f"all_{n}_rows:_user_key_present,_other_keys_and_values_equal=True")
    checks.append(f"all_{n}_rows:_user_text_equal_to_user_text=True")

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    src_sha = sha256_file(SRC)
    dst_sha = sha256_file(DST)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("exp280b panel adapter report (rename user -> user_text only)\n")
        f.write(f"src={SRC}\n")
        f.write(f"src_sha256={src_sha}\n")
        f.write(f"dst={DST}\n")
        f.write(f"dst_sha256={dst_sha}\n")
        for c in checks:
            f.write(f"assert:{c}\n")
    print(f"rows={n}")
    print(f"src_sha256={src_sha}")
    print(f"dst_sha256={dst_sha}")
    print("asserts_passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
