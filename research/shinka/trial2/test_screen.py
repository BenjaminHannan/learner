"""Tests for screen.py with fake clients (no network)."""
import json

import pytest

import fake_screen_client
import screen
from guarded import GuardedClient
from money import Guard, MoneyStop


def card(i, core, mech="m"):
    return {"id": f"c{i:03d}", "core_operation": core, "mechanism": mech, "why_novel_names": "w",
            "nearest_known": "n", "prediction": "p", "fits_interface": "yes"}


def test_dedupe_drops_near_identical_cores_only():
    a = card(0, "pool states with a learned rotation of the keys across heads")
    b = card(1, "pool states with a learned rotation of the keys across heads again")
    c = card(2, "completely different mechanism using error correcting parity bits")
    kept, dropped = screen.dedupe([a, b, c])
    assert [k["id"] for k in kept] == ["c000", "c002"] and dropped == [{"id": "c001", "duplicate_of": "c000"}]


def test_build_families_never_drops_a_card():
    cards = [card(i, f"core {i}") for i in range(5)]
    obj = {"families": [{"name": "a", "members": ["c000", "c001", "c099"]}, {"name": "b", "members": ["c001", "c002"]}, "junk"]}
    fams = screen.build_families(obj, cards)
    members = [m for f in fams for m in f["members"]]
    assert sorted(members) == [c["id"] for c in cards]            # each card exactly once
    assert screen.build_families(None, cards) and len(screen.build_families(None, cards)) == 5


def test_representative_is_longest_mechanism():
    cards = [card(0, "x", "short"), card(1, "y", "a much longer mechanism text")]
    by = {c["id"]: c for c in cards}
    assert screen.representative({"members": ["c000", "c001"]}, by)["id"] == "c001"


@pytest.mark.parametrize("v,ok", [
    ({"implementable": True, "known_item": "none", "combination": False}, True),
    ({"implementable": True, "known_item": "NetVLAD", "combination": False}, False),
    ({"implementable": True, "known_item": "none", "combination": True}, False),
    ({"implementable": False, "known_item": "none", "combination": False}, False),
    ({"implementable": "true", "known_item": "none", "combination": False}, False),
    ({"implementable": True, "known_item": None, "combination": False}, False),
    ({"implementable": True, "combination": False}, False),
    (None, False)])
def test_passes(v, ok):
    assert screen.passes(v) is ok


def test_cluster_and_screen_calls_are_guarded_and_within_stop(tmp_path):
    g = Guard(ledger=tmp_path / "l.jsonl")
    cards = [card(i, f"core {i}") for i in range(40)]
    fc = fake_screen_client.FakeClient()
    gc = GuardedClient(fc, g)
    r = gc.create("2", "s2-cluster", **screen.cluster_params(cards))
    fams = screen.build_families(screen.last_json(screen.text_of(r), "families"), cards)
    assert len(fams) == 20
    assert g.spent("2") < g.stage_stop("2") == 3.6 and g.stage_cap("2") == 4.0


def test_screen_refused_when_stage2_stop_reached(tmp_path):
    g = Guard(ledger=tmp_path / "l.jsonl")
    with g._locked():
        g._write([{"t": 0, "stage": "2", "model": "x", "tag": "fill", "usd": 3.59}])
    fc = fake_screen_client.FakeClient()
    with pytest.raises(MoneyStop):
        GuardedClient(fc, g).create("2", "s2-cluster", **screen.cluster_params([card(0, "c")] * 3))
    assert fc.calls == 0


def test_screen_params_do_not_send_effort_to_haiku():
    p = screen.screen_params(card(0, "x"))
    assert p["model"] == "claude-haiku-5-5" and "output_config" not in p and p["max_tokens"] <= 21000
    assert screen.cluster_params([card(0, "x")])["max_tokens"] <= 21000
