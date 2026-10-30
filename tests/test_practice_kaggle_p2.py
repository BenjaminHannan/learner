"""practice.kaggle.build_p2: the Practice-2 Kaggle kernel (one arm per T4, resumable over two sessions)."""
import json

from practice.kaggle import build_p2


def test_build_and_resume(tmp_path):
    r = build_p2.build(build_p2.build_parser().parse_args(["--out", str(tmp_path / "a"), "--skill", "zebra_puzzles"]))
    assert r["id"].endswith("/practice2-zebra") and r["payload_kb"] < 800 and not r["kernel_sources"]
    assert "--rg-arm P" in r["lanes"][0] and "--rg-arm C" in r["lanes"][1] and "--nf4" in r["lanes"][0] and "--oc-eager" in r["lanes"][1]
    nb = json.loads((tmp_path / "a" / "practice2-zebra.ipynb").read_text())
    src = nb["cells"][0]["source"]
    compile(src, "cell", "exec")
    assert "opencode-ai@1.19.4" in src and "proxy_logs" in src and "reasoning-gym==0.1.25" in src
    import base64, io, tarfile
    names = tarfile.open(fileobj=io.BytesIO(base64.b64decode(build_p2.payload() and base64.b64encode(build_p2.payload()))), mode="r:xz").getnames()
    assert "tests/k2_fake_upstream.py" in names and "practice/rg_run.py" in names and "practice/mac_run.py" not in names
    b = build_p2.build(build_p2.build_parser().parse_args(["--out", str(tmp_path / "b"), "--resume-from", "practice2-zebra"]))
    assert b["id"].endswith("/practice2-zebra-b") and b["kernel_sources"] == [r["id"]]
    assert '\\"resume\\": true' in json.loads((tmp_path / "b" / "practice2-zebra-b.ipynb").read_text())["cells"][0]["source"]
