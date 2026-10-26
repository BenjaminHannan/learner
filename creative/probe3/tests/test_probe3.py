"""No-network, no-GPU tests for Probe-3 (data filter, no-target assertion, answer-only masking, collation)."""
import json, os, random, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import build_data as bd  # noqa  (also puts probe1 on sys.path)
import probe_common as pc  # noqa

TASKS = pc.load_tasks()
try:
    TARGET = set(pc.target_ids(pc.DEFAULT_RESULTS))
except OSError:   # results mount absent: use the 48 first-seen ids so the tests still run
    TARGET = {t["id"] for t in TASKS[::9]}
NON = [t for t in TASKS if t["id"] not in TARGET]
BY = {t["id"]: t for t in TASKS}


def row(t, s, checks, ok=True):
    return dict(task=t["id"], sample=s, parse_ok=ok, checks=checks, source="haiku")


def fake_file(n=40):
    """Per task: sample 0 and 1 are the task's own checks (hold on the reference), then bad sets."""
    rows = []
    for t in NON[:n]:
        good = t["checks"]
        rows += [row(t, 0, good), row(t, 1, good), row(t, 2, good), row(t, 3, [{"type": "bogus"}] * 2)]
    return rows


def test_real_task_checks_are_kept_and_bad_sets_dropped():
    t = next(t for t in NON if 2 <= len(t["checks"]) <= 6)
    ref = bd.replay.replay_reference(t)
    assert bd.keep_reason(t, row(t, 0, t["checks"]), ref) is None
    assert bd.keep_reason(t, row(t, 0, None, ok=False)) == "parse"
    assert bd.keep_reason(t, row(t, 0, "x")) == "parse"
    assert bd.keep_reason(t, row(t, 0, t["checks"][:1] * 1 if len(t["checks"]) > 1 else [])) == "size"
    assert bd.keep_reason(t, row(t, 0, [t["checks"][0]] * 7)) == "size"
    assert bd.keep_reason(t, row(t, 0, [t["checks"][0], {"type": "email_sent"}])) == "invalid"
    assert bd.keep_reason(t, row(t, 0, [t["checks"][0], None])) == "invalid"
    # valid but false on the reference end state
    assert bd.keep_reason(t, row(t, 0, [{"type": "file_exists", "path": "/nope/never.txt"}, {"type": "file_exists", "path": "/nope/two.txt"}])) == "reference"
    # one failing check among good ones drops the whole set
    assert bd.keep_reason(t, row(t, 0, list(t["checks"][:5]) + [{"type": "file_exists", "path": "/nope/x"}]), ref) in ("reference", "size")


def test_build_caps_two_per_task_holds_out_by_task_and_is_deterministic():
    rows = fake_file()
    tr, va, st = bd.build(rows, TASKS, TARGET)
    ok = [t for t in NON[:40] if 2 <= len(t["checks"]) <= 6]
    assert st["kept"] == 3 * len(ok) and st["invalid"] == 40 and st["tasks_with_kept"] == len(ok)
    assert len(tr) + len(va) == 2 * len(ok)
    tt, vt = {r["task"] for r in tr}, {r["task"] for r in va}
    assert not tt & vt and len(vt) == max(1, round(0.1 * len(ok)))
    for part in (tr, va):
        c = {}
        for r in part:
            c[r["task"]] = c.get(r["task"], 0) + 1
        assert max(c.values()) <= 2
    assert set(tr[0]) == {"prompt", "target", "task"}
    r = tr[0]
    assert r["prompt"] == bd.wp.task_prompt(BY[r["task"]], with_state=True) and "Before the assistant starts" in r["prompt"]
    assert json.loads(r["target"])["checks"] and r["target"].startswith('{"checks":[{') and ": " not in r["target"][:20]
    assert bd.build(rows, TASKS, TARGET)[:2] == (tr, va)
    assert bd.build(rows, TASKS, TARGET, seed=1)[1] != va or len(ok) < 3


def test_target_text_is_compact_json():
    assert bd.target_text([{"type": "no_email_sent"}]) == '{"checks":[{"type":"no_email_sent"}]}'


def test_no_target_task_may_appear():
    t = next(t for t in TASKS if t["id"] in TARGET)
    with pytest.raises(AssertionError, match="target"):
        bd.build(fake_file(5) + [row(t, 0, t["checks"])], TASKS, TARGET)
    with pytest.raises(AssertionError, match="unknown"):
        bd.build([dict(task="zzz", sample=0, parse_ok=True, checks=[])], TASKS, TARGET)
    tr, va, _ = bd.build(fake_file(), TASKS, TARGET)
    assert not {r["task"] for r in tr + va} & TARGET


# ---- training script (torch needed; skipped without it)
torch = pytest.importorskip("torch")
import train_lora as tl  # noqa


class FakeTok:
    """Chat-template stand-in: renders like k2_nothink (bos, user turn, generation prompt) and tokenises by characters (ids = ord + 10)."""
    pad_token_id = 0

    def apply_chat_template(self, msgs, chat_template=None, add_generation_prompt=False, tokenize=False):
        s = "<B>" + "".join(f"<u>{m['content']}<e>" if m["role"] == "user" else f"<a>{m['content']}<e>" for m in msgs)
        return s + ("<a>" if add_generation_prompt else "")

    def __call__(self, text, add_special_tokens=False):
        return dict(input_ids=[ord(c) + 10 for c in text])


def test_labels_cover_only_the_answer():
    tok, prompt, target = FakeTok(), "hello", '{"checks":[]}'
    ids, lab = tl.encode(tok, "", prompt, target)
    p = tok.apply_chat_template([dict(role="user", content=prompt)], add_generation_prompt=True)
    n = len(p)
    assert ids[:n] == tok(p)["input_ids"] and all(x == -100 for x in lab[:n])
    assert lab[n:] == ids[n:] and bytes(x - 10 for x in lab[n:]).decode() == target + "<e>"   # answer + end-of-turn token
    assert tl.encode(tok, "", prompt, target, max_len=5) is None


def test_encode_rejects_template_without_generation_prefix():
    class Bad(FakeTok):
        def apply_chat_template(self, msgs, **kw):
            return "x" if kw.get("add_generation_prompt") else "y"
    with pytest.raises(AssertionError):
        tl.encode(Bad(), "", "p", "t")


def test_collate_pads_right_and_masks():
    a, b = ([5, 6, 7], [-100, 6, 7]), ([8, 9], [-100, 9])
    ids, att, lab = tl.collate([a, b], pad_id=0)
    assert ids.tolist() == [[5, 6, 7], [8, 9, 0]] and att.tolist() == [[1, 1, 1], [1, 1, 0]] and lab.tolist() == [[-100, 6, 7], [-100, 9, -100]]


def test_answer_loss_matches_full_cross_entropy_and_only_uses_answer_rows():
    torch.manual_seed(0)
    V, H = 11, 6

    class Base(torch.nn.Module):
        def __init__(s):
            super().__init__()
            s.emb, s.lm_head = torch.nn.Embedding(V, H), torch.nn.Linear(H, V, bias=False)
            s.model = lambda input_ids, attention_mask, use_cache: type("O", (), {"last_hidden_state": s.emb(input_ids)})()
    m = Base()
    items = [([1, 2, 3, 4], [-100, -100, 3, 4]), ([5, 6, 7], [-100, 6, 7])]
    ids, att, lab = tl.collate(items, 0)
    s, n = tl.answer_loss(m, ids, att, lab)
    assert n == 4
    full = m.lm_head(m.emb(ids))[:, :-1].reshape(-1, V)
    ref = torch.nn.functional.cross_entropy(full, lab[:, 1:].reshape(-1), ignore_index=-100, reduction="sum")
    assert float(s) == pytest.approx(float(ref), rel=1e-5)


def test_real_k2_tokenizer_and_template():
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(tl.MODEL)
    except Exception as e:  # noqa  (offline)
        pytest.skip(f"K2 tokenizer unavailable: {e}")
    tpl = open(tl.TEMPLATE).read()
    ids, lab = tl.encode(tok, tpl, "Say hi", '{"checks":[]}')
    end = tok.convert_tokens_to_ids("<|ifm|im_end|>")
    ans = [x for x in lab if x != -100]
    assert ids[0] == tok.bos_token_id and ids.count(tok.bos_token_id) == 1 and ans[-1] == end
    assert tok.decode(ans[:-1]) == '{"checks":[]}' and tok.decode(ids[:len(ids) - len(ans)]).endswith("</ifm|think>")


def test_probe3_wrong_mark_is_absolute_and_default_unchanged():
    import analyze as an
    mk = lambda p, a=.8: dict(pick_rate={"SELF": {"all": 100 * 66 / 192}, "PROBE-S": {"all": p}}, auroc={"PROBE-S": a})  # noqa  SELF 34.375
    assert an.verdict(mk(37.5), 37.5)["verdict"] == "PROVED WRONG" and an.verdict(mk(37.5))["verdict"] == "INCONCLUSIVE"
    assert an.verdict(mk(100 * 73 / 192), 37.5)["verdict"] == "INCONCLUSIVE" and an.verdict(mk(100 * 76 / 192), 37.5)["verdict"] == "PASS"
    assert an.verdict(mk(100 * 76 / 192, .7), 37.5)["verdict"] == "INCONCLUSIVE"
