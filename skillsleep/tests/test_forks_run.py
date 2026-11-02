"""CPU test of forks_run.py in the tau2 venv: forked history -> real environment tool results -> tau2 Orchestrator -> tau2's evaluator on the ORIGINAL task.
The three LLM calls (agent, user simulator, NL judge) are replaced by scripts; the environment, the orchestrator and the DB check are tau2's own.
Usage: PYTHONPATH=skillsleep python skillsleep/tests/test_forks_run.py OUT_DIR"""
import copy, gzip, json, sys, time
from pathlib import Path

import tau2.agent.llm_agent as la
import tau2.evaluator.evaluator_nl_assertions as nl
import tau2.user.user_simulator as us
from tau2.data_model.message import AssistantMessage, UserMessage

import forks, forks_run

HERE = Path(__file__).parent; out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
msgs = json.load(open(HERE / "fixture_traj.json"))["messages"]
calls_seen = []
la.generate = lambda **kw: (calls_seen.append(kw["messages"][-1].role), AssistantMessage.text("Your return has been submitted. Anything else?", usage={"completion_tokens": 9}))[1]
us.generate = lambda **kw: UserMessage(role="user", content="No thanks. ###STOP###")
nl.generate = lambda **kw: AssistantMessage.text(json.dumps({"results": [{"expectedOutcome": "x", "reasoning": "r", "metExpectation": True}]}))

ret = [i for i, m in enumerate(msgs) if m.get("tool_calls") and m["tool_calls"][0]["name"] == "return_delivered_order_items"][0]
orig = msgs[ret]; calls = [(t["name"], t["arguments"]) for t in orig["tool_calls"]]
wrong = copy.deepcopy(calls); wrong[0][1]["payment_method_id"] = "gift_card_0000000"  # not the user's payment method: the tool errors, nothing changes
fk = [{"fork_id": "same", "task_id": "13", "mi": ret, "history": msgs[:ret], "msg": forks.forked_message(None, calls, 10, "a")},
      {"fork_id": "wrongpay", "task_id": "13", "mi": ret, "history": msgs[:ret], "msg": forks.forked_message(None, wrong, 10, "b")},
      {"fork_id": "textonly", "task_id": "13", "mi": ret, "history": msgs[:ret], "msg": forks.forked_message("Which items do you want to return?", [], 10, "c")},
      {"fork_id": "early", "task_id": "13", "mi": 2, "history": msgs[:2], "msg": forks.forked_message("May I have your name and zip code?", [], 10, "d")}]
with gzip.open(out / "forks.json.gz", "wt") as f:
    json.dump(fk, f)
(out / "res.jsonl").unlink(missing_ok=True)
forks_run.main("retail", "train", str(out / "forks.json.gz"), str(out / "res.jsonl"), 2, time.time() + 600, '{"api_base": "http://localhost:1/v1", "api_key": "none"}')
res = {json.loads(l)["fork_id"]: json.loads(l)["sim"] for l in open(out / "res.jsonl")}
for k, s in res.items():
    print(k, "reward", s["reward_info"]["reward"], "db", s["reward_info"]["db_check"], s["termination_reason"], [m["role"] + (":" + m["tool_calls"][0]["name"] if m.get("tool_calls") else "") for m in s["messages"]][-5:])
assert set(res) == {"same", "wrongpay", "textonly", "early"}
assert res["same"]["reward_info"]["reward"] == 1.0, "same turn as the parent must pass (a double-applied gold action would break this)"
assert res["wrongpay"]["reward_info"]["reward"] == 0.0 and res["textonly"]["reward_info"]["reward"] == 0.0
assert all(s["termination_reason"].endswith("user_stop") for s in res.values())
assert [m["role"] for m in res["same"]["messages"][ret:ret + 2]] == ["assistant", "tool"], "tool results come from the environment"
assert res["wrongpay"]["messages"][ret + 1]["error"] is True
assert len(res["same"]["messages"]) > ret + 2 and res["same"]["messages"][ret]["usage"]
import common
assert common.real(res["same"]) and common.ok(res["same"])
print("FORK RUN TEST OK")
