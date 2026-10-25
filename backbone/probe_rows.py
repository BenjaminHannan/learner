"""Probe shards (generalize.probes output: OUT/<probe>/shard-NNNNN.{txt,jsonl}) -> QA rows in build_data's format.
  python3 backbone/probe_rows.py PROBE_DIR OUT_DIR    writes OUT_DIR/probe_<name>.jsonl for every probe folder
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_data import shard_rows, write_jsonl  # noqa: E402

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
for probe in sorted(p for p in src.iterdir() if p.is_dir()):
    rows = []
    for f in sorted(probe.glob("shard-*.txt")):
        rows += shard_rows(probe.name, int(f.stem.split("-")[1]), probe)
    write_jsonl(dst / f"probe_{probe.name}.jsonl", rows)
    print(f"[probe] {probe.name}: {len(rows)} rows")
