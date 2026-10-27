"""Chain-order steps in the data (codi-plan Step 0 / P1): python -m pytest backbone/think/test_steps_data.py

Builds validation shard 0 with backbone/build_data.py (about 15 s) and checks that
  - the raw shard files (.txt and .jsonl) are byte-for-byte those of the v1 digests, i.e. the oracle's new ordered path changed nothing the generator writes;
  - every old field of every row is unchanged (sha256 over the old rows, taken from the build before the change), and `steps` / `steps_src` are the only new fields;
  - each row's steps are exactly its evidence lines (as a set), in the oracle's derivation order, and that order differs from file order for many rows;
  - rows without steps are the depth-0 "not told" rows.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(ROOT))
import build_data as BD  # noqa: E402

OLD_FIELDS_SHA = "d57d9f4c08c52c894b2e8046be0b1234ee9526be219bb0c21261a06cedfb1516"  # sha256 of validation shard 0's 2,167 rows as build_data wrote them before `steps`
STEPS_SHA = "98b65700ea749f9c0370c0bdf17c092432253b2b7acc808dc7399791291bee8f"        # sha256 of json.dumps([id, steps, steps_src]) over the same rows
OLD_KEYS = {"id", "split", "shard", "visit_id", "qtype", "base_qtype", "bank", "template", "style", "rule_family", "action", "depth", "long_range", "visible",
            "knowable", "context", "question", "answer"}


@pytest.fixture(scope="module")
def shard(tmp_path_factory):
    d = tmp_path_factory.mktemp("raw") / "validation"
    BD._init()
    BD.make_shard(("validation", 0, d))
    return d, BD.shard_rows("validation", 0, d)


def test_raw_shard_bytes_match_v1_digests(shard):
    d, _ = shard
    sums = BD.v1_sums()
    if not sums:
        pytest.skip("v1 digest list not readable (git history missing)")
    for ext in ("jsonl", "txt"):
        assert BD.sha(d / f"shard-00000.{ext}") == sums[f"validation/shard-00000.{ext}"], ext
    assert (d / "shard-00000.paths.ndjson").exists()


def test_old_fields_unchanged_and_new_fields_additive(shard):
    _, rows = shard
    assert len(rows) == 2167
    h = hashlib.sha256()
    for r in rows:
        assert set(r) == OLD_KEYS | {"steps", "steps_src"}
        h.update((json.dumps({k: v for k, v in r.items() if k in OLD_KEYS}, sort_keys=True) + "\n").encode())
    assert h.hexdigest() == OLD_FIELDS_SHA
    h = hashlib.sha256()
    for r in rows:
        h.update(json.dumps([r["id"], r["steps"], r["steps_src"]]).encode())
    assert h.hexdigest() == STEPS_SHA


def test_steps_are_the_evidence_in_chain_order(shard):
    d, rows = shard
    lines = (d / "shard-00000.txt").read_text(encoding="utf-8").split("\n")
    raw = {}
    for line in (d / "shard-00000.jsonl").read_text(encoding="utf-8").splitlines():
        q = json.loads(line)
        if q["kind"] == "question":
            raw[q["id"]] = q
    src = {}
    differs = 0
    for r in rows:
        src[r["steps_src"]] = src.get(r["steps_src"], 0) + 1
        q = raw[r["id"]]
        evidence = sorted({t for t in q["evidence_text_lines"] if t is not None})
        if r["steps_src"] == "none_told":
            assert r["steps"] == [] and (not r["knowable"] or r["depth"] == 0)
            continue
        assert r["steps_src"] in ("chain", "file_order"), r["steps_src"]
        assert sorted(r["steps"]) == sorted(lines[t] for t in evidence), r["id"]  # same lines, none missing, none extra
        assert all(s and not s.startswith("[question]") for s in r["steps"])
        file_order = [lines[t] for t in evidence]
        if r["steps_src"] == "chain" and r["steps"] != file_order:
            differs += 1
        if r["steps_src"] == "file_order":
            assert r["steps"] == file_order
    assert src.get("chain", 0) > 1500 and differs > 500, (src, differs)
    assert src["none_told"] == sum(not r["knowable"] or r["depth"] == 0 for r in rows)
    print(f"steps_src {src}; chain order differs from file order in {differs} rows")


def test_depth0_rows_have_no_steps_and_others_do(shard):
    _, rows = shard
    assert all((r["steps"] == []) == (r["steps_src"] == "none_told") for r in rows)
    assert all(r["answer"] == "not told" for r in rows if r["steps_src"] == "none_told" and not r["knowable"])
