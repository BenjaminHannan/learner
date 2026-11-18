"""Tests for the MLX port of Probe-3 (creative/probe3/mlx). Pure-python parts always run (no torch, no mlx needed): constants and label masking against train_lora.py's own code,
the probe record format, schedule/ordering parity, verdict rule. The mlx parts (gradient checks, tiny-model train/gen smoke, resume) need `pip install mlx mlx-lm` (Linux: `mlx[cpu]`) and
the HF hub for the tokenizer + config files; they skip otherwise."""
import ast, json, math, os, random, subprocess, sys
import pytest
HERE = os.path.dirname(os.path.abspath(__file__))
P3 = os.path.dirname(HERE)
MLXD = os.path.join(P3, "mlx")
sys.path.insert(0, MLXD)
import mlx_common as C  # noqa  (puts probe1 on sys.path)
import probe_common as pc  # noqa
import write_probes as wp  # noqa
import analyze as an  # noqa
import summarize as sm  # noqa

TASKS = pc.load_tasks()
LORA_SRC = open(os.path.join(P3, "train_lora.py")).read()
CUDA = ast.parse(LORA_SRC)


def cuda_consts():
    out = {}
    for n in CUDA.body:
        if isinstance(n, ast.Assign):
            v = ast.literal_eval(n.value) if not isinstance(n.value, ast.Call) else None
            tgt = n.targets[0]
            if isinstance(tgt, ast.Tuple) and v is not None:
                out.update(dict(zip((t.id for t in tgt.elts), v)))
            elif isinstance(tgt, ast.Name) and v is not None:
                out[tgt.id] = v
    return out


def cuda_encode():
    """train_lora.encode, lifted out of the CUDA file by ast (that file imports torch; this function does not use it)."""
    fn = next(n for n in CUDA.body if isinstance(n, ast.FunctionDef) and n.name == "encode")
    ns = {}
    exec(compile(ast.Module([fn], []), "train_lora.encode", "exec"), ns)
    return ns["encode"]


class FakeTok:
    """Chat-template stand-in that renders like k2_nothink (bos, user turn, generation prompt) and tokenises by characters."""
    pad_token_id = 0

    def apply_chat_template(self, msgs, chat_template=None, add_generation_prompt=False, tokenize=False):
        s = "<B>" + "".join(f"<u>{m['content']}<e>" if m["role"] == "user" else f"<a>{m['content']}<e>" for m in msgs)
        return s + ("<a>" if add_generation_prompt else "")

    def __call__(self, text, add_special_tokens=False):
        return dict(input_ids=[ord(c) + 10 for c in text])


def test_recipe_constants_equal_train_lora():
    k = cuda_consts()
    for name in ("R", "ALPHA", "DROPOUT", "LR", "WARMUP", "EPOCHS", "BATCH", "SEED", "MODEL", "TARGETS"):
        assert getattr(C, name) == k[name], name
    assert C.TEMPLATE == os.path.join(os.path.dirname(P3), "guess1", "k2_nothink.jinja") and os.path.exists(C.TEMPLATE)
    assert (C.R, C.ALPHA, C.DROPOUT, C.LR, C.WARMUP, C.EPOCHS, C.BATCH, C.SEED) == (16, 32, 0.05, 1e-4, 0.03, 2, 16, 0)
    assert sorted(p.split(".")[1] for p in C.LORA_KEYS) == sorted(C.TARGETS) and len(C.LORA_KEYS) == 7
    assert C.TINY["hidden_size"] == 64   # the CUDA smoke's --tiny config
    src = LORA_SRC[LORA_SRC.index("def load_model"):LORA_SRC.index("def merge_and_save")]
    for kk, vv in C.TINY.items():
        assert f"{kk}={vv}".replace(" ", "") in src.replace(" ", ""), kk


def test_encode_matches_train_lora_on_fake_and_edge_cases():
    enc = cuda_encode()
    tok = FakeTok()
    for prompt, target in (("hello", '{"checks":[]}'), ("multi\nline <u> prompt", '{"checks":[{"type":"no_email_sent"}]}'), ("é ü 漢字", "x")):
        assert C.encode(tok, "", prompt, target) == enc(tok, "", prompt, target)
        assert C.encode(tok, "", prompt, target, max_len=5) == enc(tok, "", prompt, target, max_len=5) is None
    ids, lab = C.encode(tok, "", "hello", '{"checks":[]}')
    n = len(tok.apply_chat_template([dict(role="user", content="hello")], add_generation_prompt=True))
    assert all(x == -100 for x in lab[:n]) and lab[n:] == ids[n:] and bytes(x - 10 for x in lab[n:]).decode() == '{"checks":[]}<e>'
    assert C.prompt_ids(tok, "", "hello") == ids[:n]


def test_encode_rejects_template_without_generation_prefix():
    class Bad(FakeTok):
        def apply_chat_template(self, msgs, **kw):
            return "x" if kw.get("add_generation_prompt") else "y"
    with pytest.raises(AssertionError):
        C.encode(Bad(), "", "p", "t")


def real_tok():
    try:
        return C.hf_tokenizer()
    except Exception as e:  # noqa  (offline)
        pytest.skip(f"K2 tokenizer unavailable: {e}")


def test_real_k2_tokenizer_masking_parity_and_stop_ids():
    tok, tpl, enc = real_tok(), open(C.TEMPLATE).read(), cuda_encode()
    t = next(t for t in TASKS if 2 <= len(t["checks"]) <= 6)
    for prompt in ("Say hi", wp.task_prompt(t, with_state=True)):
        target = json.dumps({"checks": t["checks"]}, separators=(",", ":"), ensure_ascii=False)
        mine, theirs = C.encode(tok, tpl, prompt, target), enc(tok, tpl, prompt, target)
        assert mine == theirs
        ids, lab = mine
        end = tok.convert_tokens_to_ids(C.END_OF_TURN)
        ans = [x for x in lab if x != -100]
        assert end == 250019 and ans[-1] == end and ids[0] == tok.bos_token_id and ids.count(tok.bos_token_id) == 1
        assert tok.decode(ans[:-1]) == target and tok.decode(ids[:len(ids) - len(ans)]).endswith("</ifm|think>")
        assert C.prompt_ids(tok, tpl, prompt) == ids[:len(ids) - len(ans)]   # generation sees exactly the training prompt
    assert C.stop_ids(tok, 1) == [1, 250019] and C.stop_ids(tok, [1, 250019]) == [1, 250019]


try:
    import mlx.core as mx
    import mlx.nn as nn
    import mlx_lm  # noqa
    from mlx.utils import tree_flatten, tree_map
    import train_mlx as T
    import gen_mlx as G
    HAVE_MLX = True
except ImportError:
    HAVE_MLX = False
needs_mlx = pytest.mark.skipif(not HAVE_MLX, reason="mlx / mlx-lm not installed (Linux: pip install 'mlx[cpu]' mlx-lm)")


def test_lr_schedule_and_epoch_orders_match_cuda_recipe():
    total = 58
    warm = math.ceil(C.WARMUP * total)
    assert warm == 2
    f = lambda s: C.lr_at(s, warm, total) / C.LR  # noqa
    assert f(0) == 0 and f(1) == pytest.approx(0.5) and f(warm) == pytest.approx(1.0) and f(total) == pytest.approx(0, abs=1e-12)
    assert f(warm + (total - warm) // 2) == pytest.approx(0.5, abs=0.02)
    assert all(f(s) >= f(s + 1) for s in range(warm, total))
    # same shuffles as train_lora.main: one Random(SEED), fresh list(range(n)) shuffled each epoch
    rng, ref = random.Random(0), []
    for _ in range(2):
        o = list(range(449))
        rng.shuffle(o)
        ref.append(o)
    assert C.epoch_orders(449, 2) == ref


def test_record_format_is_write_probes_record():
    chunk = [(TASKS[0], 0), (TASKS[0], 3)]

    class Tk:
        def decode(self, ids, skip_special_tokens=False):
            assert skip_special_tokens
            return {0: '{"checks":[{"type":"no_email_sent"}]}', 1: "not json"}[ids[0]]
    rows, logs = C.make_rows(chunk, [[1, 2, 3], [1, 2]], [[0, 9], [1]], Tk(), 768)
    assert rows[0] == wp.record("k2", TASKS[0]["id"], 0, '{"checks":[{"type":"no_email_sent"}]}')
    assert set(rows[0]) == {"key", "task", "sample", "source", "parse_ok", "checks", "raw"} and rows[0]["source"] == "k2"
    assert rows[0]["key"] == f"{TASKS[0]['id']}|0" and rows[0]["checks"] == [{"type": "no_email_sent"}] and rows[0]["parse_ok"] is True
    assert rows[1]["parse_ok"] is False and rows[1]["checks"] is None and rows[1]["sample"] == 3
    assert logs[0]["prompt_tokens"] == 3 and logs[0]["new_tokens"] == 2 and logs[0]["hit_max"] is False
    # analyze.py reads them unchanged
    p = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"probes_fmt_{os.getpid()}.jsonl")
    with open(p, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    try:
        assert an.load_probes(p) == {TASKS[0]["id"]: [[{"type": "no_email_sent"}], None]}
    finally:
        os.remove(p)
    assert C.OUT_NAMES == dict(tuned="probes_k2.jsonl", base="probes_k2base_mlx.jsonl")
    assert wp.N_SAMPLES == 4 and (wp.TEMPERATURE, wp.TOP_P) == (0.7, 0.95)
    assert "Before the assistant starts" in wp.task_prompt(TASKS[0], with_state=True)   # the with-state prompt gen_mlx sends


def mk_report(p, a=0.8, self_=100 * 66 / 192, v=None):
    pr = dict(SELF=dict(all=self_), **{"PROBE-S": dict(all=p)})
    r = dict(metrics=dict(pick_rate=pr, auroc={"PROBE-S": a}), diagnostics=dict(k2={}), p1_needs=self_ + 5, wrong_at=37.5)
    r.update(an.verdict(r["metrics"], 37.5) if v is None else dict(verdict=v, checks={}))
    return r


def test_addendum1_rule_mlx_base_reaching_p1_voids_a_pass():
    tuned = mk_report(100 * 80 / 192)
    assert tuned["verdict"] == "PASS"
    assert sm.combine(tuned, mk_report(30.0))[0] == "PASS"
    assert sm.combine(tuned, mk_report(100 * 76 / 192))[0] == "INCONCLUSIVE"          # 39.58% >= 39.375
    assert sm.combine(tuned, mk_report(100 * 75 / 192))[0] == "PASS"                  # 39.06% < 39.375
    assert sm.combine(mk_report(36.0), mk_report(40.0))[0] == "INCONCLUSIVE"
    assert sm.combine(mk_report(37.0), mk_report(30.0))[0] == "PROVED WRONG"
    assert "provisional" in sm.combine(tuned, None)[1]


ARCH = C.arch_module()[0] if HAVE_MLX else None
CFG = dict(model_type="k2_horizon", hidden_size=64, num_hidden_layers=2, intermediate_size=128, num_attention_heads=4, num_key_value_heads=2, head_dim=16, vocab_size=60,
           rms_norm_eps=1e-6, max_position_embeddings=4096, mlp_only_layers=[0, 1], layernorm_num_groups=2, rope_head_dim=16, rope_parameters=dict(rope_theta=1e7, rope_type="default"),
           num_experts=0, norm_topk_prob=True, query_key_norm=False, tie_word_embeddings=False)


def lora_net(dropout=0.05, checkpoint=False, seed=0):
    from mlx_lm.tuner.utils import linear_to_lora_layers
    mx.random.seed(seed)
    net = ARCH.Model(ARCH.ModelArgs.from_dict(CFG))
    mx.eval(net.parameters())
    net.freeze()
    linear_to_lora_layers(net, 2, dict(rank=4, scale=2.0, dropout=dropout, keys=C.LORA_KEYS))
    assert T.use_keyed_dropout(net) == 14 and T.use_keyed_dropout(net) == 0   # 7 projections x 2 layers
    net.update(tree_map(lambda p: mx.random.normal(p.shape) * 0.05, net.trainable_parameters()))   # lora_b = 0 at init would hide lora_a's gradient
    if checkpoint:
        from mlx_lm.tuner.trainer import grad_checkpoint
        grad_checkpoint(net.layers[0])
    net.train()
    return net


IDS = [1, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]
LAB = [-100] * 5 + IDS[5:]


@needs_mlx
def test_logits_only_at_answer_positions_equal_full_cross_entropy():
    net = lora_net(dropout=0.0)
    net.eval()
    s, n = T.answer_loss(net, IDS, LAB)
    assert n == 6
    full = net(mx.array([IDS]))[0, :-1]
    ref = nn.losses.cross_entropy(full, mx.array([max(x, 0) for x in LAB[1:]]), reduction="none")
    keep = mx.array([x != -100 for x in LAB[1:]])
    assert float(s) == pytest.approx(float((ref * keep).sum()), rel=1e-4)
    assert {tuple(k.split(".")[-1:]) for k, _ in tree_flatten(net.trainable_parameters())} == {("lora_a",), ("lora_b",)}


@needs_mlx
def test_only_lora_params_get_gradients_and_untrained_lora_is_identity():
    net = lora_net(dropout=0.0)
    l, g = nn.value_and_grad(net, lambda m: T.answer_loss(m, IDS, LAB)[0])(net)
    mx.eval(l, g)
    names = [k for k, _ in tree_flatten(g)]
    assert names and all(".lora_" in k for k in names) and len(names) == 28
    mx.random.seed(0)
    base = ARCH.Model(ARCH.ModelArgs.from_dict(CFG))
    mx.eval(base.parameters())
    net0 = lora_net(dropout=0.0)
    net0.update(tree_map(lambda p: p * 0, net0.trainable_parameters()))   # lora_b = 0 -> adds nothing
    assert float(T.answer_loss(net0, IDS, LAB)[0]) == pytest.approx(float(T.answer_loss(base, IDS, LAB)[0]), rel=1e-5)


@needs_mlx
def test_keyed_dropout_makes_gradient_checkpointing_exact():
    """With nn.Dropout, mx.checkpoint's recompute draws a new mask and the gradient is wrong; KeyedDropout must give identical grads with and without checkpointing."""
    res = []
    for ck in (False, True):
        net = lora_net(dropout=0.5, checkpoint=ck)
        T.DROPOUT_SEED[0] = 77
        l, g = nn.value_and_grad(net, lambda m: T.answer_loss(m, IDS, LAB)[0])(net)
        mx.eval(l, g)
        res.append((float(l), dict(tree_flatten(g))))
    assert res[0][0] == res[1][0]
    assert max(float(mx.abs(res[0][1][k] - res[1][1][k]).max()) for k in res[0][1]) < 1e-5
    T.DROPOUT_SEED[0] = 78
    net = lora_net(dropout=0.5)
    assert float(T.answer_loss(net, IDS, LAB)[0]) != res[0][0]            # the mask follows the seed
    net.eval()
    a = float(T.answer_loss(net, IDS, LAB)[0])
    T.DROPOUT_SEED[0] = 5
    assert float(T.answer_loss(net, IDS, LAB)[0]) == a                    # no dropout in eval


# ---- end-to-end smoke on a random-init tiny K2 (tokenizer + config.json from the hub)
def hub_ok():
    try:
        real_tok()
        from huggingface_hub import hf_hub_download
        hf_hub_download(C.MODEL, "config.json")
        return True
    except BaseException as e:  # noqa
        pytest.skip(f"HF hub unavailable: {e}")


def py(script, *args):
    return subprocess.run([sys.executable, os.path.join(MLXD, script), *args], capture_output=True, text=True, timeout=1500, env=dict(os.environ, TOKENIZERS_PARALLELISM="false"))


@pytest.fixture(scope="module")
def smoke_data(tmp_path_factory):
    hub_ok()
    d = tmp_path_factory.mktemp("data")
    ts = [t for t in TASKS if 2 <= len(t["checks"]) <= 6][:6]
    rows = [dict(prompt=wp.task_prompt(t, with_state=True), target=json.dumps({"checks": t["checks"]}, separators=(",", ":")), task=t["id"]) for t in ts]
    for nm, rs in (("train", rows[:4]), ("val", rows[4:])):
        (d / f"{nm}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rs))
    return str(d)


@pytest.fixture(scope="module")
def tiny_adapter(smoke_data, tmp_path_factory):
    out = tmp_path_factory.mktemp("train")
    r = py("train_mlx.py", "--data", smoke_data, "--out", str(out), "--tiny", "--batch", "2", "--max-steps", "2", "--save-every", "1")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return out


@needs_mlx
def test_train_smoke_two_steps(tiny_adapter):
    ad = tiny_adapter / "adapter"
    assert (ad / "adapters.safetensors").exists()
    cfg = json.load(open(ad / "adapter_config.json"))
    assert cfg["lora_parameters"] == dict(rank=16, scale=2.0, dropout=0.05, keys=C.LORA_KEYS) and cfg["fine_tune_type"] == "lora"
    log = [json.loads(l) for l in open(tiny_adapter / "train_log.jsonl")]
    vals, steps = [r for r in log if r["event"] == "val"], [r for r in log if r["event"] == "step"]
    assert [v["epoch"] for v in vals] == [0, 1] and len(steps) == 2 and all(math.isfinite(v["val_loss"]) for v in vals)
    assert steps[0]["lr"] == 0.0 and steps[1]["lr"] > 0 and all(s["s_per_step"] > 0 and "peak_gb" in s and s["grad_norm"] > 0 for s in steps)
    w = mx.load(str(ad / "adapters.safetensors"))
    assert w and all(".lora_" in k for k in w) and all(v.dtype == mx.float32 for v in w.values())
    assert any(float(mx.abs(v).max()) > 0 for k, v in w.items() if k.endswith("lora_b"))   # B moved off zero


@needs_mlx
def test_train_rerun_with_final_adapter_is_a_noop(tiny_adapter, smoke_data):
    r = py("train_mlx.py", "--data", smoke_data, "--out", str(tiny_adapter), "--tiny")
    assert r.returncode == 0 and "already exists" in r.stdout


@needs_mlx
def test_gen_smoke_one_sample_resume_and_arms(tiny_adapter, tmp_path):
    res = os.path.join(P3, "inputs", "guess1_run")
    if not os.path.exists(os.path.join(res, "target.json")):
        pytest.skip("committed inputs missing")
    base = ["--results", res, "--tiny", "--limit-tasks", "1", "--samples", "1", "--max-tokens", "8", "--out-dir", str(tmp_path)]
    r = py("gen_mlx.py", "--arm", "tuned", "--adapter", str(tiny_adapter / "adapter"), *base)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    rows = [json.loads(l) for l in open(tmp_path / "probes_k2.jsonl")]
    assert len(rows) == 1 and set(rows[0]) == {"key", "task", "sample", "source", "parse_ok", "checks", "raw"} and rows[0]["source"] == "k2"
    assert rows[0]["task"] == json.load(open(os.path.join(res, "target.json")))["T"][0]
    r = py("gen_mlx.py", "--arm", "tuned", "--adapter", str(tiny_adapter / "adapter"), *base)   # resumes: nothing left
    assert r.returncode == 0 and "0 to write" in r.stdout and len(open(tmp_path / "probes_k2.jsonl").readlines()) == 1
    r = py("gen_mlx.py", "--arm", "base", "--sequential", *base)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert (tmp_path / "probes_k2base_mlx.jsonl").exists() and "sequential" in r.stdout
    assert py("gen_mlx.py", "--arm", "tuned", *base).returncode != 0 and py("gen_mlx.py", "--arm", "base", "--adapter", "x", *base).returncode != 0


@needs_mlx
def test_train_resume_equals_uninterrupted_run(smoke_data, tmp_path):
    """Kill-and-resume safety: a run stopped after 3 steps and continued from its checkpoint ends with the same adapter as an uninterrupted 4-step run
    (data order, LR schedule, optimizer state and dropout masks all depend on the step only)."""
    common = ["--data", smoke_data, "--tiny", "--batch", "2", "--save-every", "1", "--limit-val", "1"]
    a, b = tmp_path / "A", tmp_path / "B"
    assert py("train_mlx.py", *common, "--out", str(a)).returncode == 0
    r = py("train_mlx.py", *common, "--out", str(b), "--max-steps", "3")
    assert r.returncode == 0 and (b / "ckpt" / "state.json").exists()
    os.rename(b / "adapter", b / "adapter_partial")
    r = py("train_mlx.py", *common, "--out", str(b))
    assert r.returncode == 0 and "resuming from step 2" in r.stdout, r.stdout[-1500:]
    wa, wb = mx.load(str(a / "adapter" / "adapters.safetensors")), mx.load(str(b / "adapter" / "adapters.safetensors"))
    assert wa.keys() == wb.keys() and max(float(mx.abs(wa[k] - wb[k]).max()) for k in wa) < 1e-6
    vals = [json.loads(l) for l in open(b / "train_log.jsonl") if '"val"' in l]
    assert [v["epoch"] for v in vals] == [0, 1, 2]   # epoch-1 validation not repeated after the resume
