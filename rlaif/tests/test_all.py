import json, os, torch, pytest
from sandbox import World
from checks import run_checks, validate_check

TASK = {"id": "x1", "scenario": "multi_step", "user": "Read /home/user/notes/plan.txt and email the date to bob@x.com with subject Plan.",
        "state": {"today": "2026-10-24", "files": {"/home/user/notes/plan.txt": "Launch on 2026-11-03.\nBring snacks."},
                  "emails": [{"id": "e1", "from": "bob@x.com", "to": "me@example.com", "subject": "Hi", "body": "Ping me about the plan", "date": "2026-10-20"}],
                  "calendar": [{"title": "Standup", "date": "2026-10-25", "start": "09:00", "end": "09:15", "attendees": []}]},
        "checks": [{"type": "email_sent", "to": "bob@x.com", "subject_contains": "plan", "body_contains": "2026-11-03"}, {"type": "reply_contains", "any_of": ["sent"]}],
        "reference": [{"name": "read_file", "arguments": {"path": "/home/user/notes/plan.txt"}},
                      {"name": "send_email", "arguments": {"to": ["bob@x.com"], "subject": "Plan", "body": "Launch on 2026-11-03"}}],
        "reference_reply": "Email sent to Bob.", "rubric": "Reads the file, emails the date to Bob."}


def test_sandbox_tools():
    w = World.from_json(TASK["state"])
    assert "Launch" in w.call("read_file", {"path": "~/notes/plan.txt"})
    assert w.call("read_file", {"path": "/nope"}).startswith("error")
    assert w.call("read_file", {}).startswith("error: missing")
    assert w.call("bogus", {}).startswith("error")
    assert json.loads(w.call("list_dir", {"path": "/home/user"})) == ["notes/"]
    assert json.loads(w.call("search_files", {"query": "snacks"}))[0].endswith("plan.txt:2: Bring snacks.")
    assert len(json.loads(w.call("email_search", {"query": "from:bob plan"}))) == 1
    assert len(json.loads(w.call("calendar_list_events", {"start_date": "2026-10-24", "end_date": "2026-10-26"}))) == 1
    assert "ok" in w.call("calendar_create_event", {"title": "Lunch", "start": "2026-10-27T12:00", "end": "2026-10-27T13:00"})
    assert w.call("calendar_create_event", {"title": "x", "start": "tomorrow", "end": "later"}).startswith("error")
    w.call("notes_append", {"title": "T", "text": "a"}); w.call("notes_append", {"title": "T", "text": "b"})
    assert w.notes["T"] == "a\nb"
    w2 = World.from_json(w.to_json())
    assert w2.files == w.files and w2.events == w.events and TASK["state"]["files"]["/home/user/notes/plan.txt"].startswith("Launch")


def test_checks_and_reference():
    w = World.from_json(TASK["state"])
    assert run_checks(TASK, w, "") == [False, False]
    for c in TASK["reference"]:
        w.call(c["name"], c["arguments"])
    assert run_checks(TASK, w, TASK["reference_reply"]) == [True, True]
    assert run_checks({"checks": [{"type": "no_email_sent"}, {"type": "no_event_created"}]}, World.from_json(TASK["state"]), "") == [True, True]
    assert not validate_check({"type": "email_sent"}) and not validate_check({"type": "zzz"}) and validate_check({"type": "reply_contains", "any_of": ["a"]})


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    from transformers import AutoTokenizer, Qwen3Config, Qwen3ForCausalLM
    d = str(tmp_path_factory.mktemp("tiny"))
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B")
    torch.manual_seed(0)
    cfg = Qwen3Config(vocab_size=len(tok) + 256, hidden_size=64, intermediate_size=128, num_hidden_layers=2, num_attention_heads=4,
                      num_key_value_heads=2, head_dim=16, tie_word_embeddings=True, eos_token_id=tok.convert_tokens_to_ids("<|im_end|>"))
    m = Qwen3ForCausalLM(cfg)
    m.save_pretrained(d); tok.save_pretrained(d)
    return d, tok, m.float().eval()


def test_template_pieces(tiny):
    from rollout import prompt_ids, tool_piece, GEN_PROMPT
    _, tok, _ = tiny
    ids = prompt_ids(tok, TASK)
    assert tok.decode(ids).endswith(GEN_PROMPT)
    assert "PRIVILEGED" in tok.decode(prompt_ids(tok, TASK, "PRIVILEGED HINTS x"))
    # tool results block matches the chat template's rendering of a tool turn
    msgs = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "", "tool_calls": [{"type": "function", "function": {"name": "f", "arguments": {}}}]},
            {"role": "tool", "content": "R1"}, {"role": "tool", "content": "R2"}]
    full = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    assert "<|im_end|>\n" + tool_piece(["R1", "R2"]) in full


def test_logprobs_match_sampling(tiny):
    from rollout import rollout, recompute_logps
    _, tok, m = tiny
    t2 = dict(TASK, user="Short one.")
    eps = rollout(m, tok, [(TASK, None), (t2, None), (TASK, "PRIVILEGED HINTS (only you can see these): hi")], max_new=10, max_total=40, record_logps=True)
    for e in eps:
        got = torch.tensor(recompute_logps(m, e)); ref = torch.tensor(e.logps)
        assert got.shape == ref.shape and len(ref) > 0
        assert torch.allclose(got, ref, atol=2e-3), (got - ref).abs().max()


def test_views_align_and_kl(tiny):
    from rollout import rollout, prompt_ids, seq_terms
    _, tok, m = tiny
    (e,) = rollout(m, tok, [(TASK, None)], max_new=8, max_total=40)
    ids, pos = e.view(e.ids[:e.prompt_len])
    assert ids == e.ids and [e.ids[p] for p in pos] == e.ids[e.prompt_len:]
    c = prompt_ids(tok, TASK, "PRIVILEGED HINTS (only you can see these): something")
    oids, opos = e.view(c)
    assert oids[len(c):] == e.ids[e.prompt_len:] and len(opos) == len(pos)
    _, kl0 = seq_terms(m, ids, pos, e.view(e.ids[:e.prompt_len]))
    _, kl1 = seq_terms(m, ids, pos, (oids, opos))
    assert kl0.abs().max() < 1e-5 and kl1 is not None and (kl1 >= -1e-6).all()


@pytest.mark.parametrize("algo", ["grpo", "jolt_plus"])
def test_smoke_train(tiny, tmp_path, algo):
    import train
    d, _, _ = tiny
    tp = tmp_path / "t.jsonl"
    tp.write_text("\n".join(json.dumps(dict(TASK, id=f"x{i}")) for i in range(3)))
    out = str(tmp_path / "out")
    train.main(["--algo", algo, "--model", d, "--train", str(tp), "--heldout", str(tp), "--outdir", out, "--steps", "1", "--tasks-per-step", "2",
                "--group", "2", "--max-new", "8", "--max-total", "40", "--fake-grader", "--lr", "1e-3"])
    row = json.loads(open(out + "/log.jsonl").readline())
    assert row["step"] == 1 and (row["grader_calls"] == (8 if algo == "jolt_plus" else 4))
    assert os.path.exists(out + "/adapter_final/adapter_config.json")
    if algo == "jolt_plus":
        assert row["loss_kl_student"] >= 0 and row["loss_kl_teacher"] >= 0
    train.main(["--eval-only", "--model", d, "--adapter", out + "/adapter_final", "--heldout", str(tp), "--outdir", out, "--fake-grader", "--eval-grade", "--n-eval", "2", "--max-total", "40"])
    assert os.path.exists(out + "/eval_adapter_final.json")


def test_scripted_tool_loop(tiny):
    """A scripted 'model' emits a tool call then a final reply; checks sandbox execution, masks and the final state."""
    from rollout import rollout
    _, tok, m = tiny
    eos = tok.convert_tokens_to_ids("<|im_end|>")
    scripts = [
        '<tool_call>\n{"name": "send_email", "arguments": {"to": ["bob@x.com"], "subject": "Plan", "body": "Launch on 2026-11-03"}}\n</tool_call>',
        "Email sent to Bob."]

    class Fake:
        training = False
        def __init__(s): s.turn = 0
        def parameters(s): return iter([next(m.parameters())])
        def eval(s): pass
        def train(s): pass
        def generate(s, input_ids, **kw):
            g = tok(scripts[s.turn], add_special_tokens=False)["input_ids"] + [eos]
            s.turn += 1
            return type("O", (), {"sequences": torch.cat([input_ids, torch.tensor([g])], 1)})
    (e,) = rollout(Fake(), tok, [(TASK, None)])
    assert e.done and e.turns == 2 and e.final == "Email sent to Bob."
    assert e.checks() == [True, True]
    assert sum(e.mask) == len(tok(scripts[0], add_special_tokens=False)["input_ids"]) + len(tok(scripts[1], add_special_tokens=False)["input_ids"]) + 2
    assert "<tool_response>" in tok.decode(e.ids) and [t["role"] for t in e.transcript] == ["user", "assistant", "tool", "assistant"]


def test_baseline_adv():
    from baseline import baseline_adv
    r, sc = [1.0, 0.0, 0.5, 0.5], ["a", "a", "b", "b"]
    A, _ = baseline_adv(r, sc, 2, "group", {}, 0.1)
    assert A == [0.5, -0.5, 0.0, 0.0]
    A, _ = baseline_adv(r, sc, 1, "none", {}, 0.1)
    assert A == r
    V0 = {"a": 0.5, "b": 0.2}
    A, V = baseline_adv(r, sc, 1, "value", V0, 0.1)
    assert A == pytest.approx([0.5, -0.5, 0.3, 0.3])  # old V
    assert V["a"] == pytest.approx(0.5 + 0.1 * 0.5 + 0.1 * (0 - 0.55)) and V["b"] == pytest.approx(0.2 + 0.03 + 0.1 * (0.5 - 0.23))
    assert V0 == {"a": 0.5, "b": 0.2}


def test_baseline_self_and_parse():
    from baseline import baseline_adv, parse_pct, pearson
    A, V = baseline_adv([1.0, 0.0, 0.5], ["a", "a", "b"], 1, "self", {}, 0.1, pred=[0.7, 0.2, 0.5])
    assert A == pytest.approx([0.3, -0.2, 0.0]) and V == {}
    assert parse_pct("70") == 0.7 and parse_pct("I think 85%") == 0.85 and parse_pct("150") == 1.0 and parse_pct("none") is None
    assert pearson([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0) and pearson([1, 1], [0, 1]) is None
