"""Tests for ideate.py with the fake client (no network)."""
import json
import sys
import tempfile
from pathlib import Path

import pytest

import fake_client
import ideate
from guarded import GuardedClient
from money import Guard, MoneyStop


def test_parse_keeps_only_wellformed_cards():
    good = {f: "x" for f in ideate.FIELDS}
    bad = {f: "x" for f in ideate.FIELDS[:-1]}
    text = "preamble {not json} " + json.dumps({"cards": [good, bad, "str", {**good, "mechanism": ""}]})
    assert ideate.parse_cards(text) == [good]
    assert ideate.parse_cards("no json at all") == []


def test_g1_counts_only_fits_interface_yes():
    cards = [{**{f: "x" for f in ideate.FIELDS}, "fits_interface": v} for v in ["yes"] * 60 + ["no"] * 5]
    assert ideate.g1(cards)["G1_pass"] and ideate.g1(cards[:59] + cards[60:])["G1_pass"] is False


def test_whole_pipeline_on_fake_client_stays_under_stop(tmp_path):
    g = Guard(ledger=tmp_path / "l.jsonl")
    gc = GuardedClient(fake_client.FakeClient(), g)
    jobs = [(mk, l, None) for l in ideate.LENSES for mk in ("opus", "sonnet")]
    cards, info = ideate.run_batch(gc, "t", jobs, 0.0)
    assert len(cards) == 120 and info["returned"] == 24
    assert g.spent("1") < g.stage_stop("1")
    assert len(ideate.pick_far_lenses(cards)) == 6


def test_batch_refused_whole_when_worst_case_does_not_fit(tmp_path):
    g = Guard(ledger=tmp_path / "l.jsonl")
    with g._locked():
        g._write([{"t": 0, "stage": "1", "model": "x", "tag": "fill", "usd": 15.0}])
    fc = fake_client.FakeClient()
    with pytest.raises(MoneyStop):
        ideate.run_batch(GuardedClient(fc, g), "t", [("opus", "l", None)] * 24, 0.0)
    assert fc.reqs == {}                       # nothing was sent
