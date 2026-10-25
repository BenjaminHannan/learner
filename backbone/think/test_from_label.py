"""CPU test FL for from_label.py and summarize.py on label-only results:  python backbone/think/test_from_label.py   (test_think1.py calls test_fl)

The key mapping is checked against think1.py's own label_nums() and tags_for() (their source is pulled out with ast, so torch is not needed),
the truncation rule at every possible cut position of a long label (a value may be dropped, never changed), the parser on the two real labels,
`vast.py status` line parsing, and summarize.py on files rebuilt from labels: point estimates, intervals n/a, a real file beating a label file,
and unchanged output for normal results.
"""
import ast
import contextlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import from_label as FL
import summarize as SM
import test_summarize as TS

REAL = ["claude-think1-compassionate-davinci-s1|a_s1:v=65.8,d=81.3;b_s1:v=66.5,p1=60.1,d=82.5,dp1=74.8",
        "claude-think1-compassionate-davinci-s0|a_s0:v=67.0,vr=67.0,d=81.3;b_s0:v=68.1,p1=58.7,d=82.0,dp1=73.3"]


def think1_fns():
    """label_nums and tags_for from think1.py, compiled without importing torch."""
    src = (HERE / "think1.py").read_text()
    fns = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name in ("label_nums", "tags_for")]
    assert len(fns) == 2
    ns = {"HEAD": 5}
    exec(compile(ast.Module(fns, []), "think1_extract", "exec"), ns)
    return ns["label_nums"], ns["tags_for"]


def label_text(box, results):
    """What label_report.py writes for {name: label_nums} (percent, one decimal), not capped."""
    return box + "|" + ";".join(name + ":" + ",".join(f"{k}={v:.1f}" for k, v in nums.items()) for name, nums in results.items())


def test_mapping_inverts_label_nums():
    label_nums, tags_for = think1_fns()
    for k, arm in enumerate(SM.ARMS):
        ev = {"validation": {}, "dev": {}}
        for split in ev:
            for j, tag in enumerate(tags_for(arm, split)):
                ev[split][tag] = {"acc": (60 + k + j / 10) / 100}
        if arm in ("a", "b", "aplus", "bplus"):
            ev["validation"]["main"], ev["dev"]["main"] = {"acc": 0.667}, {"acc": 0.813}
            if arm == "b":
                ev["validation"]["pass1"], ev["dev"]["pass1"] = {"acc": 0.601}, {"acc": 0.748}
            if arm == "a":
                ev["validation"]["main_repeat"] = {"acc": 0.668}
        nums = label_nums(ev)
        assert nums, arm
        box, got, notes = FL.parse_label(label_text("box", {f"{arm}_s2": nums}))
        assert not notes and list(got) == [(arm, 2)], (arm, notes, got)
        res = FL.result_file(arm, 2, got[(arm, 2)])
        for split in ev:
            assert set(res["eval"][split]) == set(ev[split]), (arm, split, set(res["eval"][split]), set(ev[split]))
            for tag, e in ev[split].items():
                assert abs(res["eval"][split][tag]["acc"] - round(e["acc"] * 100, 1) / 100) < 1e-9, (arm, split, tag)
        head = SM.HEAD[arm]   # the headline tag of every arm exists in the rebuilt file
        assert any(SM.norm_tag(t) == SM.norm_tag(head) for t in res["eval"]["validation"]), (arm, head)
    assert tags_for("t", "validation").keys() >= {"L8", "swap8", "ref0"} and "main" not in tags_for("t", "validation")


def test_real_labels():
    for text, a, b in ((REAL[0], 1, 1), (REAL[1], 0, 0)):
        box, got, notes = FL.parse_label(text)
        assert box.endswith(f"-s{a}") and not notes and sorted(got) == [("a", a), ("b", b)]
    _, g0, _ = FL.parse_label(REAL[1])
    assert g0[("a", 0)] == {"v": 67.0, "vr": 67.0, "d": 81.3} and g0[("b", 0)] == {"v": 68.1, "p1": 58.7, "d": 82.0, "dp1": 73.3}
    r = FL.result_file("b", 0, g0[("b", 0)], "box")
    assert r["source"] == "label" and r["eval"]["validation"] == {"main": {"acc": 0.681, "n": None}, "pass1": {"acc": 0.587, "n": None}}
    assert r["eval"]["dev"] == {"main": {"acc": 0.82, "n": None}, "pass1": {"acc": 0.733, "n": None}} and not any("hits" in e for d in r["eval"].values() for e in d.values())
    assert FL.split_key("dL8") == ("dev", "L8") and FL.split_key("L8") == ("validation", "L8") and FL.split_key("d") == ("dev", "main")
    assert FL.split_key("dvr") == ("dev", "main_repeat") and FL.split_key("rep1_8") == ("validation", "rep1_8")
    # empty summary = an aborted run; odd entries are skipped with a note, not fatal
    _, g, notes = FL.parse_label("x|a_s0:;zzz_s1:v=1.0;b_s0:v=nan?,d=2.0")
    assert g[("a", 0)] == {} and FL.result_file("a", 0, {})["aborted"] and ("b", 0) in g and g[("b", 0)] == {"d": 2.0} and len(notes) == 2, (g, notes)
    _, g, notes = FL.parse_label("no bar here")
    assert g == {} and notes


def test_truncation():
    results = {"a_s0": {"v": 67.0, "vr": 66.8, "d": 81.3}, "b_s0": {"v": 68.1, "p1": 58.7, "d": 82.0, "dp1": 73.3},
               "t_s0": {f"L{L}": 60.0 + L for L in (0, 1, 2, 4, 8, 12)} | {"swap8": 65.4, "dL8": 71.2}}
    full = label_text("box-s0", results)
    # (key, tag, index of the separator that ends the pair; None for the very last pair)
    pairs, pos = [], len("box-s0|")
    for name, nums in results.items():
        key = (name.split("_s")[0], int(name.split("_s")[1]))
        pos += len(name) + 1
        for j, (k, v) in enumerate(nums.items()):
            pos += len(f"{k}={v:.1f}")
            pairs.append((key, k, v, pos if pos < len(full) else None))
            pos += 1                        # the "," or ";"
    assert full[pairs[0][3]] == "," and full[pairs[2][3]] == ";"
    # parsed as if the label were capped at every possible length: exactly the pairs whose separator made it into the text survive
    # (so a value cut in the middle, like "v=6", is never read), nothing else is lost
    for c in range(1, len(full) + 1):
        text = full[:c]
        _, got, notes = FL.parse_label(text, cap=c)
        want = {}
        for key, k, v, sep in pairs:
            if sep is not None and sep < c:
                want.setdefault(key, {})[k] = v
        assert got == want, (c, text, got, want)
        if "|" in text:
            assert any("cap" in n for n in notes), (c, notes)
    # below the cap nothing is dropped, even for a text that looks cut
    _, got, notes = FL.parse_label("b|a_s0:v=67.0,d=8", cap=1000)
    assert got == {("a", 0): {"v": 67.0, "d": 8.0}} and not notes
    # concrete cut cases
    _, g, notes = FL.parse_label("b|a_s0:v=67.0,d=8", cap=len("b|a_s0:v=67.0,d=8"))
    assert g == {("a", 0): {"v": 67.0}} and "dropped the cut-off a_s0 pair 'd=8'" in notes[0], (g, notes)
    _, g, notes = FL.parse_label("b|a_s0:v=67.0,d=81.3;b_s0:v=6", cap=29)
    assert g == {("a", 0): {"v": 67.0, "d": 81.3}}, g          # b_s0's only pair was cut: the entry goes
    _, g, notes = FL.parse_label("b|a_s0:v=67.0;b_", cap=len("b|a_s0:v=67.0;b_"))
    assert g == {("a", 0): {"v": 67.0}}                        # cut inside an entry name
    # a label made by the real label_report formatting at the real cap
    many = {f"{arm}_s{s}": {"v": 66.0 + s, "d": 80.0, "dp1": 70.0} for arm in ("a", "b", "aplus", "bplus", "t1", "tw") for s in range(6)}
    many["t_s0"] = {f"L{L}": 60.0 + L / 10 for L in (0, 1, 2, 4, 8, 12, 16, 24)} | {"swap8": 1.0, "mean8": 2.0, "rep1_8": 3.0, "gatesoff8": 4.0, "ref0": 5.0}
    capped = label_text("claude-think1-x-s0", many)[:FL.CAP]
    assert len(capped) == FL.CAP
    _, got, notes = FL.parse_label(capped)
    assert got and len(notes) == 1 and "cap" in notes[0]
    assert all(n["v"] == 66.0 + k[1] for k, n in got.items() if "v" in n)


def test_vast_status_lines():
    lab = REAL[1]
    out = f"41234567 {lab} A100 SXM4 running 0.612 3.5 h\n41234568 claude-bb|loop1:m=50.0 H100 running 1.0 0.2 h\n41234569 no-label-here None A100 stopped 0 0 h\n"
    assert FL.vast_labels(out) == [lab, "claude-bb|loop1:m=50.0"]
    capped = ("claude-think1-compassionate-davinci-s0 DONE|" + "a_s0:v=67.0,d=81.3;" * 60)[:1000]
    assert FL.vast_labels(f"7 {capped} A100 SXM4 running 0.5 1.0 h")[0] == capped and len(capped) == 1000


def test_merge_and_write():
    tmp = tempfile.TemporaryDirectory()
    out = Path(tmp.name) / "o"
    paths, notes = FL.write_all(REAL + ["other|a_s0:v=67.0"], out)
    assert sorted(p.name for p in paths) == ["result_a_s0.json", "result_a_s1.json", "result_b_s0.json", "result_b_s1.json"]
    assert any("a seed 0 is in two labels" in n for n in notes)
    d = json.loads((out / "result_a_s0.json").read_text())      # the entry with more keys won
    assert d["source"] == "label" and d["eval"]["validation"]["main_repeat"]["acc"] == 0.67 and d["box"].endswith("-s0")
    # CLI
    p = subprocess.run([sys.executable, str(HERE / "from_label.py"), "--out", str(Path(tmp.name) / "cli"), REAL[0]], capture_output=True, text=True)
    assert p.returncode == 0 and (Path(tmp.name) / "cli" / "result_b_s1.json").exists(), p.stderr
    p = subprocess.run([sys.executable, str(HERE / "from_label.py"), "--out", str(Path(tmp.name) / "cli2"), "garbage"], capture_output=True, text=True)
    assert p.returncode == 1
    tmp.cleanup()


def rounded_labels(lab, box):
    """The labels a finished run of the scenario in `lab` would give: label_nums values at 0.1 resolution."""
    label_nums, _ = think1_fns()
    by_box = {}
    for (arm, seed), r in sorted(lab.res.items()):
        ev = {sp: {t: {"acc": e["acc"]} for t, e in d.items()} for sp, d in r["eval"].items()}
        by_box.setdefault(seed, {})[f"{arm}_s{seed}"] = label_nums(ev)
    return [label_text(f"{box}-s{seed}", res) for seed, res in by_box.items()]


def test_summarize_label_only():
    tmp = tempfile.TemporaryDirectory()
    R = Path(tmp.name)
    # (1) the two real labels: stage 1 only, so a point-estimate report and INCOMPLETE
    FL.write_all(REAL, R / "real")
    o = SM.summarize(R / "real", R / "nowhere")
    assert o["verdict"] == "INCOMPLETE" and o["label_sourced"] == ["a s0", "a s1", "b s0", "b s1"]
    arms = {(r["arm"], r["seed"]): r for r in o["arms"]}
    assert abs(arms[("b", 0)]["validation"] - 68.1) < 1e-6 and abs(arms[("a", 1)]["dev"] - 81.3) < 1e-6 and arms[("b", 1)]["validation_n"] is None
    assert abs(o["floors"]["a"] - 66.4) < 1e-6 and abs(o["floors"]["b"] - 67.3) < 1e-6
    assert o["noise"]["a_s0_repeat"] is not None and abs(o["noise"]["diff"]) < 1e-6
    assert abs(o["lesions"]["b_pass1"] - 59.4) < 1e-6
    assert all(m["ci"] is None for m in o["marks"] if "ci" in m) and all(v is None for v in o["intervals"].values())
    txt = SM.report(o)
    assert "FROM LABELS: a s0, a s1, b s0, b s1" in txt and "0.1-point rounding" in txt and "95% n/a" in txt and "VERDICT: INCOMPLETE" in txt
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        assert SM.main([str(R / "real"), "--data", str(R / "nowhere"), "--json"]) == 0
    assert json.loads(buf.getvalue())["label_sourced"] == ["a s0", "a s1", "b s0", "b s1"]

    # (2) a full PASS scenario through labels: same statuses, point estimates within the rounding, intervals n/a
    lab = TS.scenario(R / "full")
    out, data = lab.write()
    ref = SM.summarize(out, data)
    assert ref["verdict"] == "PASS" and "label_sourced" not in ref and "FROM LABELS" not in SM.report(ref) and "n/a" not in SM.report(ref)
    FL.write_all(rounded_labels(lab, "bx"), R / "lab")
    o = SM.summarize(R / "lab", data)
    assert o["verdict"] == "PASS", (o["verdict"], o["why"])
    assert {m["id"]: m["status"] for m in o["marks"]} == {m["id"]: m["status"] for m in ref["marks"]}
    for key in ("G", "R1a", "R4a"):
        a, b = TS.marks(o)[key]["value"], TS.marks(ref)[key]["value"]
        assert abs(a - b) < 0.2, (key, a, b)
    assert abs(o["curve"]["t"]["8"]["mean"] - ref["curve"]["t"]["8"]["mean"]) < 0.1
    assert o["secondary"]["M1"]["status"] == SM.ND and o["secondary"]["slices"] == {}
    assert o["lesions"]["gates_off_rows_differing_from_a"] is None
    txt = SM.report(o)
    assert "n/a" in txt and "S(8) - best floor" in txt and "VERDICT: PASS" in txt

    # (3) a real result file for the same arm and seed wins over the label file, in either order; intervals come back for it
    d_out = R / "mixed"
    FL.write_all(rounded_labels(lab, "bx"), d_out / "lab")
    res_dir = d_out / "real"
    for (arm, seed), r in lab.res.items():
        (res_dir / f"{arm}_s{seed}").mkdir(parents=True, exist_ok=True)
        (res_dir / f"{arm}_s{seed}" / f"result_{arm}_s{seed}.json").write_text(json.dumps(r))
    o = SM.summarize(d_out, data)
    assert "label_sourced" not in o and any("using the real result file" in n for n in o["notes"]) and o["marks"][0]["ci"] is not None
    assert abs(o["curve"]["t"]["8"]["mean"] - ref["curve"]["t"]["8"]["mean"]) < 1e-9
    # (4) one label-only arm among real ones: marked, and no interval is made from a partial set of rows
    (res_dir / "t_s2" / "result_t_s2.json").unlink()
    o = SM.summarize(d_out, data)
    assert o["label_sourced"] == ["t s2"] and all(v is None for v in o["intervals"].values()), o.get("label_sourced")
    assert abs(o["curve"]["t"]["8"]["mean"] - ref["curve"]["t"]["8"]["mean"]) < 0.1 and o["verdict"] == "PASS"
    tmp.cleanup()


def test_fl():
    test_mapping_inverts_label_nums()
    test_real_labels()
    test_truncation()
    test_vast_status_lines()
    test_merge_and_write()
    test_summarize_label_only()
    print("FL ok: label keys invert think1.label_nums for every arm, truncation at every cut, vast status lines, label-only summarize "
          "(point estimates, intervals n/a), real files beat labels, normal output unchanged")


if __name__ == "__main__":
    test_fl()
