"""CPU test of the fork-point finder and the prefix -> forced turn -> message reconstruction, with the real K2 tokenizer (tokenizer/config files only).
Usage: python3 skillsleep/tests/test_forks.py K2_TOKENIZER_DIR     (no GPU, no network, no tau2)"""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent))
import forks
from render import END, apply, load_tok, render_traj, to_chat

tok = load_tok(sys.argv[1]); env = json.load(open(HERE / "fixture_env_retail.json")); msgs = json.load(open(HERE / "fixture_traj.json"))["messages"]
chat, gen = to_chat(env["system"], msgs); text = apply(tok, chat, env["tools"])
enc = tok(text, add_special_tokens=False, return_offsets_mapping=True); ids = enc["input_ids"]; starts = [a for a, _ in enc["offset_mapping"]]
assert ids == render_traj(tok, env, msgs)[0]
ts = forks.turn_spans(text, msgs, gen)
gen_idx = [i for i, m in enumerate(msgs) if m["role"] == "assistant" and m.get("usage")]
assert [t[0] for t in ts] == gen_idx, (ts, gen_idx)  # the greeting is not a generated turn
types = forks.arg_types(env["tools"]); im_end = tok.convert_tokens_to_ids(END)
n_pts = {"turn": 0, "tool": 0, "arg": 0}

for mi, a, b in ts:
    pts = forks.decision_points(text, starts, a, b); j0 = pts[0][0]
    assert pts[0][1] == "turn" and starts[j0] == a, "turn start token must begin exactly at the turn"
    end_tok = next(j for j in range(j0, len(ids)) if starts[j] >= b)  # first token after the turn (the im_end is the last token of the turn)
    m = msgs[mi]
    for j, kind in pts:
        n_pts[kind] += 1
        piece = tok.decode([ids[j]], skip_special_tokens=False)
        if kind == "turn":
            assert piece == "<ifm|tool_calls>" or (m.get("content") or "").startswith(piece.strip()), (piece, m)
        elif kind == "tool":
            assert piece.strip() and piece.strip() in " ".join(t["name"] for t in m["tool_calls"]), (piece, m["tool_calls"])
        else:
            vals = [v if isinstance(v, str) else json.dumps(v) for t in m["tool_calls"] for v in t["arguments"].values()]
            assert any(v.startswith(piece.strip()) for v in vals), (piece, vals)
        # round trip: forcing the SAME token and decoding the rest must give back exactly this assistant turn
        turn_text = tok.decode(ids[j0:end_tok], skip_special_tokens=False)
        got = forks.parse_turn(turn_text, types)
        want_calls = [(t["name"], t["arguments"]) for t in m.get("tool_calls") or []]
        assert got == ((m.get("content") or "").strip(), want_calls), (got, m)
        # the same, through finish_turn with a fake server that "continues" the original tokens
        c = {"j": j, "ts": j0, "ru": ids[j]}
        forks.post = lambda path, body, _j=j, _e=end_tok: {"choices": [{"finish_reason": "stop", "text": "", "token_ids": ids[_j + 1:_e - 1]}]}
        fm = forks.finish_turn(tok, ids, c, types, "t", im_end)
        assert fm["content"] == ((m.get("content") or "").strip() or None) and [(t["name"], t["arguments"]) for t in fm["tool_calls"] or []] == want_calls, (fm, m)
        assert fm["usage"] and fm["role"] == "assistant"
print("round trip OK; decision points per kind:", n_pts)
assert all(n_pts.values())

# a real fork: replace one argument-value token's continuation (runner-up digit) -> different arguments, same structure
mi, a, b = [t for t in ts if msgs[t[0]].get("tool_calls") and any(c["name"] == "return_delivered_order_items" for c in msgs[t[0]]["tool_calls"])][0]
pts = forks.decision_points(text, starts, a, b); j0 = pts[0][0]
j, _ = [p for p in pts if p[1] == "arg"][1]  # first token of the second argument value (order id / item ids)
end_tok = next(k for k in range(j0, len(ids)) if starts[k] >= b)
alt = tok("#W9999999", add_special_tokens=False)["input_ids"][0]
forks.post = lambda path, body: {"choices": [{"finish_reason": "stop", "text": "", "token_ids": ids[j + 1:end_tok - 1]}]}
fm = forks.finish_turn(tok, ids, {"j": j, "ts": j0, "ru": alt}, types, "x", im_end)
print("forced:", repr(tok.decode([ids[j]])), "->", repr(tok.decode([alt])), "| args:", fm["tool_calls"][0]["arguments"], "| was:", msgs[mi]["tool_calls"][0]["arguments"])
assert fm["tool_calls"][0]["arguments"] != msgs[mi]["tool_calls"][0]["arguments"]
# a vLLM without return_token_ids answers with text only: same turn
forks.post = lambda path, body: {"choices": [{"finish_reason": "stop", "text": tok.decode(ids[j + 1:end_tok - 1], skip_special_tokens=False)}]}
fm2 = forks.finish_turn(tok, ids, {"j": j, "ts": j0, "ru": alt}, types, "x", im_end)
assert fm2["tool_calls"][0]["arguments"] == fm["tool_calls"][0]["arguments"], (fm2, fm)
# a cut-off turn is dropped, a forced turn that ends the turn at once is dropped
forks.post = lambda path, body: {"choices": [{"finish_reason": "length", "text": "", "token_ids": []}]}
assert forks.finish_turn(tok, ids, {"j": j, "ts": j0, "ru": alt}, types, "x", im_end) is None
assert forks.parse_turn("<ifm|tool_calls>\n<ifm|tool_call>get_order_details\n<ifm|arg_key>order_id</ifm|arg_key>\n<ifm|arg_value>#W1", types) is None
assert forks.parse_turn("", types) is None
# non-string arguments keep their JSON type
t = forks.parse_turn('<ifm|tool_calls>\n<ifm|tool_call>return_delivered_order_items\n<ifm|arg_key>item_ids</ifm|arg_key>\n<ifm|arg_value>["1", "2"]</ifm|arg_value>\n</ifm|tool_call>\n</ifm|tool_calls>', types)
assert t[1][0][1]["item_ids"] == ["1", "2"], t

# candidates: fake prompt_logprobs where every sampled token is the top-1 with p=0.95 and a runner-up with p=0.02 (except some that fail the marks)
plp = [None] + [{str(ids[j]): {"logprob": math.log(0.95)}, str(ids[j] + 1): {"logprob": math.log(0.02)}, "249999": {"logprob": math.log(0.001)}} for j in range(1, len(ids))]
tps = [(mi, bisect_i, forks.decision_points(text, starts, a, b)) for mi, a, b in ts for bisect_i in [forks.decision_points(text, starts, a, b)[0][0]]]
cs = forks.candidates(ids, tps, plp)
assert len(cs) == sum(n_pts.values())
assert all(c["ru"] == ids[c["j"]] + 1 and abs(c["p1"] - 0.95) < 1e-6 for c in cs)
plp2 = list(plp); j = cs[0]["j"]
plp2[j] = {str(ids[j]): {"logprob": math.log(0.8)}, "249998": {"logprob": math.log(0.1)}}  # p1 < 0.9
assert j not in [c["j"] for c in forks.candidates(ids, tps, plp2)]
plp2[j] = {str(ids[j]): {"logprob": math.log(0.95)}, "249998": {"logprob": math.log(0.001)}}  # p2 < 0.005
assert j not in [c["j"] for c in forks.candidates(ids, tps, plp2)]
plp2[j] = {"249998": {"logprob": math.log(0.95)}, str(ids[j]): {"logprob": math.log(0.02)}}  # the sampled token was not the top-1
assert j not in [c["j"] for c in forks.candidates(ids, tps, plp2)]
# pick: at most 6, spread over distinct turns first, sorted by position
pk = forks.pick(cs)
assert len(pk) == 6 and len({c["mi"] for c in pk}) == min(6, len({c["mi"] for c in cs})) and [c["j"] for c in pk] == sorted(c["j"] for c in pk)
print("picked turns:", [c["mi"] for c in pk], "kinds:", [c["kind"] for c in pk])
many = [{"mi": i, "j": i, "p2": 0.01 * (i + 1)} for i in range(20)]
assert [c["mi"] for c in forks.pick(many)] == [1, 5, 8, 11, 15, 18]
assert len(forks.pick(many[:3] + [{"mi": 0, "j": 99, "p2": 0.5}] * 2)) == 5  # fewer turns than 6: second picks per turn fill up
print("FORK TESTS OK")
