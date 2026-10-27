"""Tests for the eval-only gate-G suite (scripts/premonition_pair_suite.py).

Exact statistics (binomial cutoffs, Fisher, Wilson), generator determinism, per-cell construction invariants
(question kind, inventory preservation, visible-token diffs), the deterministic interpreter, the shortcut
ceilings, label separation and world-level state isolation.  Eval only: no training, no parameter updates,
no GPU, and the old test split is never loaded.

    PY -B tests/test_premonition_pair_suite.py
"""
from __future__ import annotations

from fractions import Fraction
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_handoff_diag as H  # noqa: E402
import premonition_ovn_ladder as L  # noqa: E402
import premonition_pair_suite as S  # noqa: E402

CKPT = ROOT / "artifacts" / "claude-relcut-long-20260919" / "ckpt"
NAME = "relcutlong-s0-12000"
SMALL = "c6_irrelevant_edit"          # the cheapest cell to regenerate in a test


def test_exact_cutoffs() -> None:
    """The frozen pass marks are the smallest counts rejecting the stated null at alpha = 0.05/6."""
    checked = S.verify_cutoffs()
    for name, row in checked.items():
        assert row["agrees"], f"{name}: frozen {row['frozen_cutoff']} != computed {row['computed_cutoff']}"
        assert row["tail_at_frozen_cutoff"] <= float(S.ALPHA), name
        assert row["tail_one_below"] > float(S.ALPHA), f"{name}: the cutoff is not the smallest one"
    assert checked["c1_own_one_hop"]["frozen_cutoff"] == 1969
    assert checked["c3_own_heldout_two_hop"]["frozen_cutoff"] == 1876
    assert checked["c4_changed_link"]["frozen_cutoff"] == 945
    # a tail we can verify by hand: P(X >= n) = p^n
    assert S.binom_tail_ge(4, 4, Fraction(1, 2)) == Fraction(1, 16)
    assert S.binom_tail_ge(4, 0, Fraction(1, 2)) == 1


def test_fisher_and_wilson() -> None:
    """Probability-ordering Fisher against hand-computable tables; Wilson against a known interval."""
    assert abs(S.fisher_exact_two_sided(3, 0, 0, 3) - 0.1) < 1e-12          # 2x2 with margins 3,3
    assert S.fisher_exact_two_sided(1, 1, 1, 1) == 1.0
    assert abs(S.fisher_exact_two_sided(10, 0, 0, 10) - 1.0825088224e-05) < 1e-12
    p = S.fisher_exact_two_sided(15, 0, 0, 15)
    assert 0.0 < p < 1e-7
    low, high = S.wilson(15, 15)
    assert 0.78 < low < 0.80 and high == 1.0
    assert S.wilson(0, 0) == [0.0, 1.0]
    # symmetry in the arguments that must not matter
    assert S.fisher_exact_two_sided(7, 3, 2, 8) == S.fisher_exact_two_sided(3, 7, 8, 2)


def test_generator_determinism(spec) -> None:
    import torch
    a = S.generate_set(SMALL, spec=spec)
    b = S.generate_set(SMALL, spec=spec)
    assert a["rejections"] == b["rejections"], "rejection counts are not reproducible"
    for x, y in zip(a["chunks"], b["chunks"]):
        for side in ("a", "b"):
            assert torch.equal(x[side].tokens, y[side].tokens), "tokens are not reproducible"
        assert x["meta"] == y["meta"], "metadata is not reproducible"
    other = S.generate_set("c5_changed_endpoint_value", spec=spec)
    assert not torch.equal(a["chunks"][0]["a"].tokens[:, :64], other["chunks"][0]["a"].tokens[:, :64]), \
        "two cells drew the same worlds"


def test_single_cells_ask_the_right_question(spec, sets) -> None:
    """One scored question per world, of exactly the declared hop count and relation class."""
    for name in ("c1_own_one_hop", "c2_own_practised_two_hop", "c3_own_heldout_two_hop"):
        data = sets[name]
        assert data["kind"] == "single"
        seen = 0
        for chunk in data["chunks"]:
            view = H.FieldView(chunk["a"], spec)
            assert chunk["a"].q_visit.shape[0] == len(chunk["meta"])
            assert len(set(chunk["a"].q_visit.tolist())) == len(chunk["meta"]), "two questions share a world"
            for q, meta in enumerate(chunk["meta"]):
                seen += 1
                two = bool(view.q_has_link[q])
                assert two == (meta["hops"] == 2), "the question's LINK token disagrees with its hop count"
                if two:
                    assert (meta["relation"] == spec.heldout_relation) == (name == "c3_own_heldout_two_hop")
                assert int(view.q_subject[q]) == meta["subject"]
                assert int(view.q_rel[q]) == meta["relation"]
        assert seen == data["n"]


def test_pair_cells_are_inventory_preserving(spec, sets) -> None:
    """Exactly the intended visible tokens change, the question is identical, and values are only moved."""
    import torch
    for name in ("c4_changed_link", "c5_changed_endpoint_value", "c6_irrelevant_edit"):
        data = sets[name]
        cfg = S.CELLS[name]
        for chunk in data["chunks"]:
            a, b = chunk["a"], chunk["b"]
            assert torch.equal(a.lengths, b.lengths)
            assert torch.equal(a.q_span, b.q_span), "the question moved between the twins"
            differing = (a.tokens != b.tokens)
            assert differing.sum(1).tolist() == [cfg["token_diffs"]] * a.tokens.shape[0], \
                f"{name}: wrong number of changed visible tokens"
            view_a, view_b = H.FieldView(a, spec), H.FieldView(b, spec)
            for q, meta in enumerate(chunk["meta"]):
                visit = int(view_a.q_visit[q])
                assert int(view_a.q_subject[q]) == int(view_b.q_subject[q]) == meta["subject"]
                assert int(view_a.q_rel[q]) == int(view_b.q_rel[q]) == spec.heldout_relation
                # the whole world's value inventory is identical in the twins
                inv_a = sorted(view_a.value[visit][view_a.value[visit] >= 0].tolist())
                inv_b = sorted(view_b.value[visit][view_b.value[visit] >= 0].tolist())
                assert inv_a == inv_b, f"{name}: the value inventory changed"
                changed = differing[visit].nonzero().flatten().tolist()
                kinds = {int(a.line_of[visit, position]) for position in changed}
                if name == "c4_changed_link":
                    line = changed[0]
                    row = int(a.line_of[visit, line])
                    assert int(view_a.kind[visit, row]) == H.KIND_LINK, "the changed card is not a link"
                    assert int(view_a.subj[visit, row]) == meta["subject"]
                    assert int(view_a.obj_ent[visit, row]) == meta["dest_a"]
                    assert int(view_b.obj_ent[visit, row]) == meta["dest_b"]
                    assert meta["value_a"] != meta["value_b"]
                else:
                    assert len(kinds) == 2, f"{name}: the swap did not touch two different cards"
                    for row in kinds:
                        assert int(view_a.kind[visit, row]) == H.KIND_ATTR, "a changed card is not an attribute"
                        assert int(view_a.rel[visit, row]) == spec.heldout_relation
                        assert int(view_a.subj[visit, row]) != meta["subject"], "the asker's fact was edited"
                        if name == "c6_irrelevant_edit":
                            assert int(view_a.subj[visit, row]) != meta["dest_a"], \
                                "an irrelevant edit touched the friend's fact"
                    if name == "c5_changed_endpoint_value":
                        assert meta["value_a"] != meta["value_b"], "the endpoint value did not change"
                        assert meta["dest_a"] == meta["dest_b"], "the endpoint cell changed the link"
                    else:
                        assert meta["value_a"] == meta["value_b"], "the irrelevant edit changed the answer"
                        assert meta["answer_a"] == meta["answer_b"]


def test_interpreter_and_shortcut_ceilings(spec, sets) -> None:
    """Every generated example is answered by the deterministic interpreter; shortcuts cannot reach the gate."""
    manifest = S.load_manifest()
    for name, data in sets.items():
        audit = S.audit_set(data, spec)
        assert audit["interpreter"]["accuracy"] == 1.0, (name, audit["interpreter"]["failures"])
        assert audit["interpreter"]["unit_accuracy"] == 1.0, name
        assert audit == manifest["cells"][name]["audit"], f"{name}: the manifest audit does not reproduce"
        threshold = S.CELLS[name]["cutoff"] / S.CELLS[name]["n"]
        if name == "c1_own_one_hop":
            # a one-hop question IS a direct subject+relation lookup, so that "shortcut" is the task itself;
            # the two chaining-blind strategies must still fail.
            assert audit["shortcut_ceilings"]["direct_question_subject"]["unit_deterministic"] == 1.0
            blind = ("question_blind_modal", "relation_only")
        else:
            blind = tuple(audit["shortcut_ceilings"])
        for shortcut in blind:
            row = audit["shortcut_ceilings"][shortcut]
            assert row["unit_deterministic"] < threshold, \
                f"{name}: the {shortcut} shortcut reaches the pass mark"
            assert row["unit_expected_uniform"] < threshold, f"{name}: {shortcut} uniform draw reaches the mark"


def test_manifest_is_frozen_and_model_free(sets) -> None:
    """Hashes, seeds and cutoffs are recorded, and the data files still match them."""
    manifest = S.load_manifest()
    assert manifest["written_before_any_model_was_loaded"] is True
    assert set(manifest["cells"]) == set(S.CELLS)
    for name, cfg in S.CELLS.items():
        info = manifest["cells"][name]
        assert info["seed"] == cfg["seed"] and info["n"] == cfg["n"] and info["cutoff"] == cfg["cutoff"]
        assert H.sha256_file(L.ROOT / info["file"]) == info["sha256"], f"{name}: the data file changed"
        assert manifest["cutoff_verification"][name]["agrees"]
    assert manifest["condition"] == "U" and manifest["loops"] == 4
    assert manifest["generator_sources"]["frozen/premonition/toy_ladder.py"] == H.sha256_file(
        L.ARCHIVE / "frozen" / "premonition" / "toy_ladder.py")


def test_labels_never_reach_the_model(spec, sets) -> None:
    """_strip_labels removes every evaluator label, and perturbing them changes nothing the model sees."""
    import torch
    from learnlab.core import IGNORE_INDEX
    data = sets[SMALL]
    blind = H._strip_labels(data["chunks"][0]["a"])
    assert bool((blind.answer == IGNORE_INDEX).all()) and bool((blind.gold_lines < 0).all())
    assert blind.slices is None and all(q.startswith("blind-") for q in blind.question_ids)
    assert bool((blind.depth == 0).all())
    model, _blob = __import__("premonition_first_card_probe").load_from(NAME, CKPT)
    checked = H.label_perturbation_check(model, {"chunks": [data["chunks"][0]]}, spec)
    assert checked["pass"], checked


def test_condition_u_parity_and_world_isolation(spec, sets) -> None:
    """U reproduces own_fixed(..., loops=4) exactly, and a world scores the same alone as in its chunk."""
    import premonition_first_card_probe as P
    model, _blob = P.load_from(NAME, CKPT)
    before = P.fingerprint(model)
    parity = S.own_fixed_parity(model, sets["c1_own_one_hop"], spec)
    assert parity["pass"], parity
    isolation = S.world_isolation(model, sets["c3_own_heldout_two_hop"], spec, sample=6)
    assert isolation["pass"], isolation
    assert P.fingerprint(model) == before, "weights changed during evaluation"


def test_scoring_and_gate_arithmetic(spec, sets) -> None:
    """A cell result is well formed, the invariant cell needs identical answers, and G is the conjunction."""
    import premonition_first_card_probe as P
    model, _blob = P.load_from(NAME, CKPT)
    small = {"name": SMALL, "cell": 6, "kind": "pair", "n": len(sets[SMALL]["chunks"][0]["meta"]),
             "invariant": True, "chunks": sets[SMALL]["chunks"][:1]}
    result = S.score_cell(model, small, spec)
    assert 0 <= result["count"] <= result["both_correct"] <= small["n"]
    assert result["count"] <= result["identical_answers"]
    assert result["both_correct"] <= min(result["single_correct"]["a"], result["single_correct"]["b"])
    held = {"name": "c3", "cell": 3, "kind": "single", "n": len(sets["c3_own_heldout_two_hop"]["chunks"][0]["meta"]),
            "invariant": False, "chunks": sets["c3_own_heldout_two_hop"]["chunks"][:1]}
    diag = S.score_cell(model, held, spec, diagnostics=True)["diagnostics"]
    assert diag["questions"] == held["n"]
    assert diag["requests_made"] == sum(diag["requests_made_per_step"]) <= S.REQUESTS * held["n"]
    for key in ("request1", "request2"):
        block = diag["by_request"][key]
        assert sum(block["classes"].values()) == held["n"]
        assert block["right_both"] <= min(block["right_person"], block["right_relation"])
    assert 0 <= diag["both_gold_cards_fetched"] <= held["n"]


def main() -> int:
    L.bootstrap()
    import torch
    torch.set_num_threads(4)
    spec = L.spec()
    manifest = S.load_manifest()
    sets = {name: S.load_set(name, manifest) for name in S.CELLS}
    tests = [(test_exact_cutoffs, ()), (test_fisher_and_wilson, ()),
             (test_generator_determinism, (spec,)),
             (test_single_cells_ask_the_right_question, (spec, sets)),
             (test_pair_cells_are_inventory_preserving, (spec, sets)),
             (test_interpreter_and_shortcut_ceilings, (spec, sets)),
             (test_manifest_is_frozen_and_model_free, (sets,)),
             (test_labels_never_reach_the_model, (spec, sets)),
             (test_condition_u_parity_and_world_isolation, (spec, sets)),
             (test_scoring_and_gate_arithmetic, (spec, sets))]
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
