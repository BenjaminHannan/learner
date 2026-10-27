"""Tests for the read-only handoff diagnostic (scripts/premonition_handoff_diag.py).

Generator determinism, the exact tuple interpreter, pair-construction invariants, mask semantics on the
two-edge fixture, N == U, and label-perturbation invariance.  Eval only: no training, no parameter updates,
no GPU, and the old test split is never loaded.

    PY -B tests/test_premonition_handoff_diag.py
"""
from __future__ import annotations

import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_handoff_diag as H  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402

CKPT = ROOT / "artifacts" / "claude-relcut-long-20260919" / "ckpt"
NAME = "relcutlong-s0-12000"


def test_generator_determinism(spec) -> None:
    a = H.generate_set("dev", spec=spec)
    b = H.generate_set("dev", spec=spec)
    import torch
    assert a["rejections"] == b["rejections"], "rejection counts are not reproducible"
    assert len(a["chunks"]) == len(b["chunks"])
    for x, y in zip(a["chunks"], b["chunks"]):
        for side in ("a", "b"):
            assert torch.equal(x[side].tokens, y[side].tokens), "tokens are not reproducible"
            assert torch.equal(x[side].q_span, y[side].q_span)
        assert x["meta"] == y["meta"], "pair metadata is not reproducible"
    # different sets must not be the same worlds
    other = H.generate_set("onehop", spec=spec)
    assert not torch.equal(a["chunks"][0]["a"].tokens[:, :64], other["chunks"][0]["a"].tokens[:, :64])


def test_pair_invariants(spec, dataset) -> None:
    """Only the friend link differs, and the two target values differ."""
    import torch
    for chunk in dataset["chunks"]:
        a, b = chunk["a"], chunk["b"]
        assert torch.equal(a.lengths, b.lengths)
        differing = (a.tokens != b.tokens)
        assert differing.sum(1).tolist() == [1] * a.tokens.shape[0], "a pair differs in more than one token"
        view_a, view_b = H.FieldView(a, spec), H.FieldView(b, spec)
        for q, meta in enumerate(chunk["meta"]):
            visit = int(view_a.q_visit[q])
            position = int(differing[visit].nonzero()[0])
            line = int(a.line_of[visit, position])
            assert int(view_a.kind[visit, line]) == H.KIND_LINK, "the changed line is not a link card"
            assert int(view_a.subj[visit, line]) == meta["subject"], "the changed link is not the query's"
            assert int(view_a.obj_ent[visit, line]) == meta["dest_a"]
            assert int(view_b.obj_ent[visit, line]) == meta["dest_b"]
            assert meta["dest_a"] != meta["dest_b"]
            assert meta["value_a"] != meta["value_b"], "the two target values are equal"
            assert meta["answer_a"] != meta["answer_b"]


def test_interpreter_is_exact(spec, dataset) -> None:
    audit = H.dataset_audit(dataset, spec)
    assert audit["interpreter"]["accuracy"] == 1.0, audit["interpreter"]["failures"]
    assert audit["interpreter"]["pair_accuracy"] == 1.0
    for name, row in audit["shortcut_ceilings"].items():
        assert row["pair_expected_uniform"] < 0.80, f"{name} shortcut sits above the success threshold"


def test_one_hop_set_has_no_handoff(spec) -> None:
    """One-hop questions show no LINK token, so the second-source gate can never fire."""
    manifest = json.loads(H.manifest_path().read_text())
    data = H.load_set("onehop", manifest)
    for chunk in data["chunks"]:
        for side in ("a", "b"):
            view = H.FieldView(chunk[side], spec)
            assert not bool(view.q_has_link.any()), "a one-hop question contains the LINK token"


def test_fixture_mask_semantics() -> None:
    import torch
    out = H.fixture_checks()
    assert out["pass"], json.dumps(out, indent=1)
    f = H._Fixture()
    # NULL survives a mask that removes every real card
    none = H.subject_mask(f, torch.tensor([f.OTHER, f.OTHER]), f.LINES)
    scores = torch.tensor([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, -1.0]])
    masked = H.apply_mask(scores, none[:1])
    assert float(masked[0, -1]) == -1.0
    assert all(masked[0, i] == float("-inf") for i in range(f.LINES))
    # D is inactive on a non-link first fetch and on one-hop questions
    for first in (4, 5, f.LINES, -1):
        active, _ = H.handoff_source(f, torch.tensor([first, first]), f.LINES)
        assert not bool(active[0])
    active, source = H.handoff_source(f, torch.tensor([0, 0]), f.LINES)
    assert bool(active[0]) and not bool(active[1])
    assert int(source[0]) == f.B


def test_n_equals_u_and_label_invariance(spec, dataset) -> None:
    import torch
    model, _record = H.load_checkpoint(NAME, CKPT / f"{NAME}.pt",
                                       CKPT.parent / "runs" / f"{NAME}.json")
    before = __import__("premonition_first_card_probe").fingerprint(model)
    merged = H.score_set(model, dataset, H.CONDITIONS, spec)
    for key in ("correct", "first_card", "ask", "restricted", "handoff_attempted"):
        assert torch.equal(merged["N"][key], merged["U"][key]), f"N differs from U on {key}"
    perturbed = H.label_perturbation_check(model, dataset, spec)
    assert perturbed["pass"], perturbed
    after = __import__("premonition_first_card_probe").fingerprint(model)
    assert before == after, "weights changed during evaluation"
    # Q and QD must issue a bit-identical first request
    assert merged["Q"]["digests"][0::H.REQUESTS] == merged["QD"]["digests"][0::H.REQUESTS]
    assert torch.equal(merged["Q"]["first_card"], merged["QD"]["first_card"])


def main() -> int:
    L.bootstrap()
    import torch
    torch.set_num_threads(4)
    spec = L.spec()
    manifest = json.loads(H.manifest_path().read_text())
    dataset = H.load_set("dev", manifest)
    tests = [(test_generator_determinism, (spec,)), (test_pair_invariants, (spec, dataset)),
             (test_interpreter_is_exact, (spec, dataset)), (test_one_hop_set_has_no_handoff, (spec,)),
             (test_fixture_mask_semantics, ()),
             (test_n_equals_u_and_label_invariance, (spec, dataset))]
    failures = 0
    with torch.no_grad():
        for fn, args in tests:
            try:
                fn(*args)
                print(f"ok   {fn.__name__}")
            except AssertionError as error:
                failures += 1
                print(f"FAIL {fn.__name__}: {error}")
    print(f"{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
