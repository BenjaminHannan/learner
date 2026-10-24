"""Item generation: rules are the creative generator's; the answer is f(c); the village side keeps splits apart; D's rows are read without changing D."""
import random
from pathlib import Path

import pytest
import torch

from creative import rules_real as R
from bridgelab.real import data as D
from bridgelab.real import dmsg
from custom_io.models import progparse as pp


def test_make_prompt_answer_is_f_of_c_and_pins_the_rule():
    D.warm_references(("add", "mult", "last_digit", "square"))
    rng = random.Random(0)
    for c in (0, 1, 2, 3, 4, 7, 12):
        for kinds in (("add", "mult"), ("last_digit", "square")):
            it = D.make_prompt(c, rng, kinds, uid="u")
            f = R.fn(it["kind"], tuple(it["params"]))
            assert it["row"]["answer"] == str(f(c)) and it["typed"]["answer"] == it["row"]["answer"]
            assert it["row"]["prompt"].count("@") == 1 and "@" not in it["typed"]["prompt"]
            assert it["typed"]["prompt"] == it["row"]["prompt"].replace("@", str(c))
            assert it["nums"][-1] == c
            xs, ys = it["nums"][0:6:2], it["nums"][1:6:2]
            assert all(f(x) == y for x, y in zip(xs, ys))
            # no other rule that fits the examples predicts a different value at c
            assert {R.fn(k, p)(c) for k, p in R.ALL_RULES if all(R.fn(k, p)(x) == y for x, y in zip(xs, ys))} == {f(c)}
            D.register(it)
            assert pp.row_targets(it["row"])["prog"]
            D.release(it)


def test_eval_prompts_are_deterministic_and_do_not_depend_on_order():
    D.warm_references(("add", "mult"))
    a = D.make_prompt(3, D.item_rng(0, "dev", "dev-1:q2"), ("add", "mult"))
    b = D.make_prompt(3, D.item_rng(0, "dev", "dev-1:q2"), ("add", "mult"))
    c = D.make_prompt(3, D.item_rng(1, "dev", "dev-1:q2"), ("add", "mult"))
    assert a["row"]["prompt"] == b["row"]["prompt"] and a["row"]["prompt"] != c["row"]["prompt"]


def test_c_stats_prior_and_entropy():
    tr = torch.tensor([0, 0, 0, 1, 2, 3])
    s = D.c_stats(torch.tensor([0, 0, 1, 2]), tr)
    assert s["mode"] == 0 and s["prior_acc"] == 0.5 and s["min"] == 0 and s["max"] == 2
    assert abs(s["entropy_bits"] - 1.5) < 1e-9


def test_word_to_int():
    assert D.word_to_int("four") == 4 and D.word_to_int("not told") == -1 and D.word_to_int("twenty") == 20 and D.word_to_int("") == -1


def test_sealed_split_is_refused():
    with pytest.raises(ValueError):
        D.open_village("/nonexistent", "x", splits=("train", "test"))
    with pytest.raises(ValueError):
        D.village_items(None, Path("."), "test")


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    root = D.make_smoke_root(tmp_path_factory.mktemp("village") / "root", train_visits=40, dev_visits=20, val_visits=20, per_shard=20)
    tok, splits = D.open_village(root, Path(__file__).resolve().parents[3] / "data/tokenizer/premonition-tok-v2.json")
    return tok, splits


def test_splits_are_disjoint_and_items_are_count_questions(tiny):
    tok, splits = tiny
    ids = {s: set(it.qid) for s, it in splits.items()}
    assert not (ids["train"] & ids["dev"]) and not (ids["train"] & ids["validation"]) and not (ids["dev"] & ids["validation"])
    for it in splits.values():
        assert len(it) > 0 and set(it.bank) <= set(D.COUNT_BANKS)
        assert int(it.c.min()) >= 0 and int(it.c.max()) <= D.CMAX


def test_dmsg_extract_shapes_and_d_is_unchanged_by_the_capture(tiny):
    tok, splits = tiny
    items = splits["dev"].take(range(min(6, len(splits["dev"]))))
    m = dmsg.load_d("random", "cpu", tok.vocab_size)
    out = dmsg.extract(m, items, tok, "cpu", max_tokens=20000)
    n = len(items)
    assert out["regs"].shape == (n, m.config.registers, m.config.d_model) and out["reg0"].shape == (n, m.config.d_model)
    assert torch.equal(out["reg0"], out["regs"][:, 0]) and out["regs"].abs().sum() > 0
    # same answers as D alone (the wrapper only reads), and identity of the method afterwards
    from learnlab import step1
    stops = sorted(step1.stop_ids(tok)[0])
    before = type(m)._greedy
    for order, batch in dmsg.item_batches(items, None, 20000):
        a = m.answer(batch, stop=stops).tokens
        with dmsg.capture_final_rows(m):
            b = m.answer(batch, stop=stops).tokens
        assert torch.equal(a, b)
    assert "_greedy" not in m.__dict__ and type(m)._greedy is before
    assert not any(p.requires_grad for p in m.parameters())


def test_item_batches_hold_exactly_the_chosen_questions(tiny):
    tok, splits = tiny
    items = splits["train"]
    seen = {}
    for order, batch in dmsg.item_batches(items, None, 20000):
        assert len(order) == batch.q_visit.shape[0]
        for k, i in enumerate(order):
            assert batch.question_ids[k] == items.qid[i]
            seen[i] = True
    assert len(seen) == len(items)


def test_msg_source_registers_is_unchanged_and_decoder_is_a_single_row(tiny):
    tok, splits = tiny
    items = splits["dev"].take(range(min(6, len(splits["dev"]))))
    m = dmsg.load_d("random", "cpu", tok.vocab_size)
    base = dmsg.extract(m, items, tok, "cpu", max_tokens=20000)                              # default = registers
    reg = dmsg.extract(m, items, tok, "cpu", max_tokens=20000, msg_source="registers")
    dec = dmsg.extract(m, items, tok, "cpu", max_tokens=20000, msg_source="decoder")
    for k in ("regs", "reg0", "d_int", "loops"):
        assert torch.equal(base[k], reg[k]), k
    assert base["d_text"] == reg["d_text"] == dec["d_text"]
    assert torch.equal(base["d_int"], dec["d_int"])                                          # capturing the decoder state does not change D's answers
    assert dec["regs"].shape == (len(items), 1, m.config.d_model) and torch.equal(dec["reg0"], dec["regs"][:, 0])
    assert dec["regs"].abs().sum() > 0 and not torch.equal(dec["reg0"], base["reg0"])
    assert "_greedy" not in m.__dict__


def test_msg_source_cache_key_is_separate(tmp_path, monkeypatch):
    import argparse
    from bridgelab.real import train as T
    monkeypatch.setattr(T, "HERE", tmp_path)
    calls = []
    monkeypatch.setattr(T.dmsg, "extract", lambda *a, **k: calls.append(k.get("msg_source")) or {"x": torch.zeros(1)})
    ns = lambda s: argparse.Namespace(village_root="r", fresh_messages=False, d_max_tokens=1, **({} if s is None else dict(msg_source=s)))
    for s in (None, "registers", "decoder", "decoder"):
        T.get_messages(None, [0], None, "cpu", "tag", "dev", ns(s))
    assert calls == ["registers", "decoder"]                                                 # None and 'registers' share one cache file; decoder has its own; 2nd decoder hit the cache


def test_message_cache_key_depends_on_items(tmp_path, monkeypatch):
    """Different subsamples of the same size (another --seed) must not share a message cache (seeds 1-2 of run3 did; voided)."""
    import argparse
    from bridgelab.real import train as T
    monkeypatch.setattr(T, "HERE", tmp_path)
    calls = []
    monkeypatch.setattr(T.dmsg, "extract", lambda *a, **k: calls.append(1) or {"x": torch.zeros(1)})
    ns = argparse.Namespace(village_root="r", fresh_messages=False, d_max_tokens=1, msg_source="decoder")
    for qids in (["q1", "q2"], ["q3", "q4"], ["q1", "q2"]):
        T.get_messages(None, _Sized(qids), None, "cpu", "tag", "dev", ns)
    assert len(calls) == 2


class _Sized(list):
    @property
    def qid(self):
        return list(self)
