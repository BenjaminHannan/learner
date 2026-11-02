"""Run in the tau2 venv: build a real-looking retail trajectory (golden actions of a train task run on the real environment, so the tool results are real)
and write tests/fixture_traj.json. Usage: make_fixture.py TASK_ID OUT_JSON"""
import json, sys
from tau2 import registry
from tau2.data_model.message import ToolCall
from tau2.runner.helpers import get_tasks

tid, outp = sys.argv[1:3]
task = [t for t in get_tasks("retail", task_split_name="train") if t.id == tid][0]
env = registry.get_env_constructor("retail")()
acts = task.evaluation_criteria.actions
print(task.user_scenario.instructions)
U = {"usage": {"completion_tokens": 20}}; msgs = [{"role": "assistant", "content": "Hi! How can I help you today?"}]
msgs.append({"role": "user", "content": "Hi, I'm " + acts[0].arguments.get("email", "a customer") + " and I want to return some items I received."})
i = 0; n = 0
while i < len(acts):
    batch = [acts[i]]
    while i + len(batch) < len(acts) and acts[i].name.startswith("get_order") and acts[i + len(batch)].name == acts[i].name:
        batch.append(acts[i + len(batch)])
    i += len(batch)
    if batch[0].name == "return_delivered_order_items":
        msgs += [{"role": "assistant", "content": "I can return those items to your original payment method. Do you confirm (yes/no)?", **U}, {"role": "user", "content": "Yes, please go ahead."}]
    calls = [{"id": f"call_{n + k}", "name": a.name, "arguments": a.arguments, "requestor": "assistant"} for k, a in enumerate(batch)]; n += len(batch)
    msgs.append({"role": "assistant", "content": None, "tool_calls": calls, **U})
    for c in calls:
        r = env.get_response(ToolCall(**c)); msgs.append({"role": "tool", "id": r.id, "content": r.content, "requestor": "assistant", "error": r.error})
msgs += [{"role": "assistant", "content": "Your return has been submitted. Anything else I can help with?", **U}, {"role": "user", "content": "No, thanks. ###STOP###"}]
json.dump({"task_id": tid, "messages": msgs}, open(outp, "w"), indent=1)
print(len(msgs), "messages")
