"""Unit tests for the money stop, with a fake client (no network, no key). Run: python -m pytest -q

mutation_check.py removes each guard line in turn and requires these tests to fail."""

from types import SimpleNamespace as NS

import pytest

import money
from guarded import GuardedClient
from money import Guard, MoneyStop, usage_cost, worst_case

P = money.load_pricing()
OPUS, SONNET, HAIKU = "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"


class Resp:
    def __init__(self, usage):
        self.usage = NS(model_dump=lambda: usage)


class FakeClient:
    def __init__(self, usage=None, error=None):
        self.usage = usage or {"input_tokens": 1000, "output_tokens": 500}
        self.error = error
        self.calls = 0
        self.batch_calls = 0
        self.messages = NS(create=self._create, batches=NS(create=self._batch, retrieve=self._ret, results=self._res))

    def _create(self, **kw):
        self.calls += 1
        if self.error:
            raise self.error
        return Resp(self.usage)

    def _batch(self, requests):
        self.batch_calls += 1
        return NS(id="b1")

    def _ret(self, i):
        return NS(processing_status="ended")

    def _res(self, i):
        msg = NS(usage=NS(model_dump=lambda: self.usage))
        return [NS(custom_id="a", result=NS(type="succeeded", message=msg)),
                NS(custom_id="b", result=NS(type="errored", message=None))]


class ApiError(Exception):
    def __init__(self, status):
        self.status_code = status


@pytest.fixture
def g(tmp_path):
    return Guard(ledger=tmp_path / "ledger.jsonl", pricing=P)


def fill(g, stage, usd):
    g._append({"t": 0, "stage": stage, "model": "x", "tag": "pre", "usd": usd})


def params(model=SONNET, max_tokens=1000, text="hi", tools=None):
    p = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": text}]}
    if tools:
        p["tools"] = tools
    return p


# --- pricing from the response's own usage ------------------------------------------------
def test_basic_prices():
    assert usage_cost(P, OPUS, {"input_tokens": 1_000_000, "output_tokens": 1_000_000}) == pytest.approx(24.0)
    assert usage_cost(P, SONNET, {"input_tokens": 1_000_000, "output_tokens": 1_000_000}) == pytest.approx(12.0)
    assert usage_cost(P, HAIKU, {"input_tokens": 50_000, "output_tokens": 0}) == pytest.approx(0.005)
    assert usage_cost(P, HAIKU, {"input_tokens": 200_000, "output_tokens": 0}) == pytest.approx(0.10)   # long-prompt rate


def test_cache_and_search_and_batch_prices():
    u = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 1_000_000}
    assert usage_cost(P, OPUS, u) == pytest.approx(0.20)
    w = {"cache_creation_input_tokens": 1_000_000,
         "cache_creation": {"ephemeral_5m_input_tokens": 1_000_000, "ephemeral_1h_input_tokens": 0}}
    assert usage_cost(P, OPUS, w) == pytest.approx(5.0)
    w1 = {"cache_creation_input_tokens": 1_000_000}       # no breakdown: priced at the dearer 1h rate
    assert usage_cost(P, OPUS, w1) == pytest.approx(8.0)
    s = {"server_tool_use": {"web_search_requests": 6}}
    assert usage_cost(P, SONNET, s) == pytest.approx(0.06)
    assert usage_cost(P, OPUS, {"input_tokens": 1_000_000, "output_tokens": 0}, batch=True) == pytest.approx(2.0)


def test_worst_case_is_at_least_actual():
    wc = worst_case(P, SONNET, 2000, 1000, max_searches=6)
    actual = usage_cost(P, SONNET, {"input_tokens": 2000, "output_tokens": 1000,
                                    "server_tool_use": {"web_search_requests": 6}})
    assert wc >= actual
    assert worst_case(P, OPUS, 1000, 1000, cache_write="1h") > worst_case(P, OPUS, 1000, 1000)


def test_caps_match_plan():
    assert P["whole_trial"]["hard_stop_usd"] == 45.0 and P["whole_trial"]["warn_usd"] == 40.0
    assert P["stages"]["0"]["cap_usd"] == 0.5
    assert P["whole_trial"]["hard_stop_usd"] < P["whole_trial"]["ben_ceiling_usd"]


# --- the stage cap -------------------------------------------------------------------------
def test_call_refused_when_worst_case_passes_stage_cap(g):
    fill(g, "0", 0.49)
    c = FakeClient()
    gc = GuardedClient(c, g)
    with pytest.raises(MoneyStop, match="stage cap"):
        gc.create("0", "t", **params(max_tokens=4000))
    assert c.calls == 0                                   # refused BEFORE sending


def test_call_inside_cap_is_sent_and_charged_from_usage(g):
    c = FakeClient({"input_tokens": 1000, "output_tokens": 500})
    GuardedClient(c, g).create("0", "t", **params())
    assert c.calls == 1
    assert g.spent("0") == pytest.approx((1000 * 2 + 500 * 10) / 1e6)


def test_ledger_shared_across_instances(g):
    GuardedClient(FakeClient(), g).create("0", "t", **params())
    assert Guard(ledger=g.ledger, pricing=P).spent() == pytest.approx(g.spent()) and g.spent() > 0


def test_no_borrowing_between_stages(g):
    fill(g, "1", 7.999)
    c = FakeClient()
    with pytest.raises(MoneyStop, match="stage cap"):
        GuardedClient(c, g).create("1", "t", **params(OPUS, max_tokens=8000))
    assert c.calls == 0
    GuardedClient(c, g).create("2", "t", **params())     # stage 2 has its own money
    assert c.calls == 1


def test_unknown_stage_refused(g):
    with pytest.raises(MoneyStop):
        GuardedClient(FakeClient(), g).create("9", "t", **params())


# --- the whole-trial hard stop, separate from stage caps -------------------------------------
def test_hard_stop_refuses_even_when_stage_has_room(g):
    for st, usd in (("0", 0.5), ("1", 8.0), ("2", 4.0), ("3", 16.0), ("4", 6.0), ("5", 8.0), ("6", 2.0)):
        fill(g, st, usd)                                    # 44.5 in total; stage 6 still has $1.00 of its own
    c = FakeClient()
    assert g.stage_left("6") == pytest.approx(1.0) and g.trial_left() == pytest.approx(0.5)
    with pytest.raises(MoneyStop, match="hard stop"):
        GuardedClient(c, g).create("6", "t", **params(OPUS, max_tokens=35000))   # worst ~ $0.70: fits stage, not trial
    assert c.calls == 0


def test_warn_flag(g):
    assert not g.warn()
    fill(g, "3", 15)
    fill(g, "1", 8)
    fill(g, "5", 8)
    fill(g, "4", 6)
    fill(g, "2", 3)
    assert g.warn()


def test_charge_that_overshoots_raises_and_blocks_further_calls(g):
    c = FakeClient({"input_tokens": 3_000_000, "output_tokens": 0})   # costs $6 on Sonnet, stage 0 cap 0.5
    with pytest.raises(MoneyStop, match="over its cap"):
        GuardedClient(c, g).create("0", "t", **params())
    with pytest.raises(MoneyStop):
        GuardedClient(FakeClient(), g).create("0", "t", **params())


def test_charge_that_crosses_only_the_trial_stop_raises(g):
    for st, usd in (("0", 0.5), ("1", 8.0), ("2", 4.0), ("3", 16.0), ("4", 6.0), ("5", 8.0), ("6", 2.0)):
        fill(g, st, usd)                                    # 44.5; stage 6 stays far under its cap
    with pytest.raises(MoneyStop, match="hard stop"):
        g.charge("6", OPUS, {"input_tokens": 0, "output_tokens": 30_000}, "t")   # $0.60 -> 45.1


# --- batches -------------------------------------------------------------------------------
def test_batch_refused_when_summed_worst_case_exceeds_stage_left(g):
    reqs = [{"custom_id": str(i), "params": params(OPUS, max_tokens=4000)} for i in range(60)]   # ~$0.08 each
    c = FakeClient()
    with pytest.raises(MoneyStop, match="batch"):
        GuardedClient(c, g).batch_submit("2", "t", reqs)    # stage 2 cap is $4
    assert c.batch_calls == 0


def test_batch_each_request_fine_but_sum_is_not(g):
    one = GuardedClient(FakeClient(), g).worst(params(OPUS, max_tokens=4000))
    n = int(4.0 / one) + 5
    gc = GuardedClient(FakeClient(), g)
    gc.guard.authorize("2", one)                            # a single request would be allowed
    with pytest.raises(MoneyStop):
        gc.batch_submit("2", "t", [{"custom_id": str(i), "params": params(OPUS, max_tokens=4000)} for i in range(n)])


def test_batch_accepted_holds_money_then_charges_at_batch_rate(g):
    reqs = [{"custom_id": "a", "params": params(max_tokens=500)}, {"custom_id": "b", "params": params(max_tokens=500)}]
    c = FakeClient({"input_tokens": 1000, "output_tokens": 500})
    gc = GuardedClient(c, g)
    gc.batch_submit("2", "t", reqs)
    assert c.batch_calls == 1 and g.spent("2") > 0          # held
    held = g.spent("2")
    gc.batch_collect("2", "t", "b1", {"a": SONNET, "b": SONNET}, poll_s=0)
    assert g.spent("2") == pytest.approx(0.5 * (1000 * 2 + 500 * 10) / 1e6)   # only 'a' succeeded
    assert g.spent("2") < held


def test_batch_hold_blocks_other_spend(g):
    reqs = [{"custom_id": str(i), "params": params(OPUS, max_tokens=4000)} for i in range(30)]
    c = FakeClient()
    gc = GuardedClient(c, g)
    gc.batch_submit("2", "t", reqs)
    with pytest.raises(MoneyStop):
        gc.create("2", "t", **params(OPUS, max_tokens=100000))


# --- failures --------------------------------------------------------------------------------
def test_rejected_request_is_not_charged_but_unknown_failure_is(g):
    gc = GuardedClient(FakeClient(error=ApiError(400)), g)
    with pytest.raises(ApiError):
        gc.create("0", "t", **params())
    assert g.spent() == 0
    gc = GuardedClient(FakeClient(error=ApiError(529)), g)
    with pytest.raises(ApiError):
        gc.create("0", "t", **params())
    assert g.spent() > 0


def test_search_calls_count_searches_in_worst_case(g):
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 6}]
    gc = GuardedClient(FakeClient(), g)
    assert gc.worst(params(tools=tools)) > gc.worst(params()) + 0.059


# --- the prosecutor wrapper (draft) -----------------------------------------------------------
def test_prosecute_goes_through_the_guard_and_parses(g):
    import prosecute
    text = 'blah {"closest": "PMA", "citations": ["u"], "case": "c", "same_core_operation": true, "confidence": 4}'
    resp = NS(content=[NS(type="server_tool_use"), NS(type="text", text=text)], stop_reason="end_turn",
              usage=NS(model_dump=lambda: {"input_tokens": 3000, "output_tokens": 400,
                                           "server_tool_use": {"web_search_requests": 1}}))
    c = FakeClient()
    c.messages.create = lambda **kw: resp
    out = prosecute.prosecute(GuardedClient(c, g), "0", {"core_operation": "x"}, "known", "t")
    assert out["case"]["closest"] == "PMA" and out["searches"] == 1
    assert g.spent("0") == pytest.approx((3000 * 2 + 400 * 10) / 1e6 + 0.01)


def test_parse_case_garbage_is_none():
    import prosecute
    assert prosecute.parse_case("no json here") is None
    assert prosecute.parse_case('{"a": 1} trailing {') == {"a": 1}
