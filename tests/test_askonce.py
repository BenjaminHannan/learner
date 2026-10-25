"""Unit tests for the Ask-once harness (CPU only; no network, no API). Frozen-data tests skip until sleep2/askonce/data is generated."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sleep2.askonce import compute_ledger as CL  # noqa: E402
from sleep2.askonce import grade, tools_mock as TM  # noqa: E402
from sleep2.askonce.config import DATA, jl_read, norm  # noqa: E402
from sleep2.askonce.slot_memory import SlotMemory  # noqa: E402
from sleep2.askonce.world import render  # noqa: E402
from sleep2.common import paired  # noqa: E402

HAVE_DATA = all((DATA / f).exists() for f in ("persona.json", "requests.jsonl", "phrasings.json"))
needs_data = pytest.mark.skipif(not HAVE_DATA, reason="frozen data not generated")


# ---------------------------------------------------------------- tools_mock checker
def test_checker_normalises_and_compares():
    gold = {"tool": "send_email", "args": {"to": "Ann.H@Example.com"}}
    assert TM.check_action({"tool": "send_email", "args": {"to": " ann.h@example.com "}}, gold) == (True, [])
    assert TM.check_action({"tool": "send_email", "args": {"to": "bob@example.com"}}, gold) == (False, ["to"])
    assert TM.check_action({"tool": "draft_email", "args": {"to": "ann.h@example.com"}}, gold) == (False, ["tool"])
    g2 = {"tool": "create_event", "args": {"attendees": ["b@x.com", "a@x.com"], "duration_min": 30}}
    assert TM.check_action({"tool": "create_event", "args": {"attendees": ["A@x.com", "b@x.com"], "duration_min": "30 minutes"}}, g2)[0]
    assert TM.check_action({"tool": "create_event", "args": {"attendees": "a@x.com", "duration_min": 30}}, g2) == (False, ["attendees"])
    assert TM.check_action({"tool": "create_event", "args": {"attendees": ["a@x.com", "b@x.com"]}}, g2) == (False, ["duration_min"])
    assert TM.check_action({"tool": "open_file", "args": {"path": "/Ａ/b.docx"}}, {"tool": "open_file", "args": {"path": "/A/b.docx"}})[0]  # NFKC


def test_parse_reply():
    assert TM.parse_reply('ACT {"tool": "open_file", "args": {"path": "/a.txt"}}') == ("ACT", {"tool": "open_file", "args": {"path": "/a.txt"}})
    assert TM.parse_reply("ASK Which Sam do you mean?") == ("ASK", "Which Sam do you mean?")
    assert TM.parse_reply('Sure. ACT {"tool": "send_email", "args": {"to": "a@b.c"}} thanks')[0] == "ACT"
    assert TM.parse_reply("gibberish")[0] == "OTHER"
    assert TM.parse_reply("")[0] == "OTHER"


def test_mock_world_executes():
    w = TM.MockWorld()
    assert w.execute({"tool": "send_email", "args": {"to": "a@b.c"}})["ok"]
    assert not w.execute({"tool": "send_email", "args": {}})["ok"]
    assert w.sent == [{"tool": "send_email", "args": {"to": "a@b.c"}}]


# ---------------------------------------------------------------- render == K2 no-think template (verified against the real tokenizer + jinja)
def test_render_matches_k2_template():
    msgs = [{"role": "system", "content": "SYS"}, {"role": "user", "content": "hi"}]
    assert render(msgs, True, "<|ifm|begin_of_text|>") == ("<|ifm|begin_of_text|><|ifm|im_start|>system\nSYS<|ifm|im_end|><|ifm|im_start|>user\nhi<|ifm|im_end|>"
                                                           "<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>")
    m2 = msgs + [{"role": "assistant", "content": "ASK x?"}]
    assert render(m2, False, "<|ifm|begin_of_text|>").endswith("<|ifm|im_start|>assistant\n<ifm|think>\n</ifm|think>ASK x?<|ifm|im_end|>")


# ---------------------------------------------------------------- slot memory
def test_slot_memory_bm25_topk_and_budget():
    m = SlotMemory()
    m.add(1, "qa", "Sam", 'Sam: asked "which Sam"; Ben answered: sam.r@example.com the classmate')
    m.add(1, "qa", "the essay", 'the essay: asked "which"; Ben answered: /docs/essay_final.docx')
    m.add(2, "corr", "mom", "mom: Ben corrected me: no, ann.h@example.com")
    m.add(2, "corr", "boss", "boss: Ben corrected me: " + "x " * 400)
    hits = m.retrieve("email Sam the agenda")
    assert "sam.r@example.com" in hits[0]
    assert len(m.retrieve("boss mom essay Sam", k=3)) <= 3
    assert sum(len(h) for h in m.retrieve("boss mom essay Sam")) <= 150 * 4 + 40
    assert m.retrieve("zzzz qqqq") == []
    assert m.hit_with_values(["sam.r@example.com"], before_day=2) and not m.hit_with_values(["sam.r@example.com"], before_day=1)


# ---------------------------------------------------------------- statistics
def test_mcnemar_exact_and_pooling():
    assert paired.mcnemar(0, 0) == 1.0
    assert paired.mcnemar(0, 8) == pytest.approx(2 * 0.5 ** 8)
    assert paired.mcnemar(5, 5) == 1.0
    a, b = [0] * 20 + [1] * 5, [1] * 12 + [0] * 8 + [1] * 5
    r = paired.mcnemar_items(a, b)
    assert (r["a_only"], r["b_only"], r["b_minus_a"]) == (0, 12, 48.0) and r["p"] == pytest.approx(2 * 0.5 ** 12, abs=1e-4)
    pooled = paired.pooled_and_per_seed({1: [0, 0, 1, 0], 2: [0, 1, 0, 0]}, {1: [1, 1, 1, 0], 2: [1, 1, 0, 1]})
    assert pooled["n"] == 8 and pooled["sign_ok_all_seeds"]
    worse = paired.pooled_and_per_seed({1: [1, 1], 2: [0, 0]}, {1: [0, 0], 2: [1, 1]})
    assert not worse["sign_ok_all_seeds"]
    ci = paired.cluster_bootstrap_ci([0] * 10, [1] * 10, list("aabbccddee"), n_boot=200)
    assert ci["lo"] == ci["hi"] == 100.0


# ---------------------------------------------------------------- compute ledger
def _length(prompt, target):
    return len(prompt.split()) + len(target.split())


def test_ledger_units_and_equality():
    sft = {"kind": "sft", "prompt": "a b c", "target": "d e"}
    pair = {"kind": "pair", "prompt": "a b c", "chosen": "d e", "rejected": "f g h"}
    assert CL.item_units(sft, _length) == {"train": 15, "ref": 0}
    assert CL.item_units(pair, _length) == {"train": 3 * 11, "ref": 11}
    per = {a: CL.night_ledger([sft] * 10, sl, 4, 20, _length, 3) for a, sl in (("A+", [sft] * 7), ("B", [pair] * 2), ("B-sft", [sft] * 7))}
    assert CL.assert_equal(per, 0.05) < 0.05
    bad = dict(per)
    bad["A+"] = CL.night_ledger([sft] * 10, [sft] * 60, 4, 20, _length, 3)
    with pytest.raises(AssertionError, match="differ by"):
        CL.assert_equal(bad, 0.05)
    bad2 = {a: dict(l) for a, l in per.items()}
    bad2["B"]["calls"] = 4
    with pytest.raises(AssertionError, match="call counts"):
        CL.assert_equal(bad2, 0.05)


# ---------------------------------------------------------------- slot-id mapping + right-move definition
@needs_data
def test_slot_id_mapping_and_right_move():
    from sleep2.askonce.world import Persona
    P = Persona.load()
    s = P.slot(P.by_split["new"][0])
    cand = [c for c in s["candidates"]][:2]
    q = f"Which {s['ref']} do you mean: {cand[0]['value']} or {cand[1]['value']}?" if s["kind"] in ("contact", "meeting", "file") else f"How long is {s['ref']}?"
    assert grade.rule_map(q, P) == s["slot_id"]
    assert grade.rule_map("What time works for you?", P) == "none"
    item = {"slots": [s["slot_id"]]}
    ask = {"move": "ASK", "act_ok": False}
    act = {"move": "ACT", "act_ok": True}
    assert grade.right_move("H_new", ask, item, s["slot_id"]) and not grade.right_move("H_new", ask, item, "contact_99")
    assert not grade.right_move("H_new", act, item, None)           # guessing right is not the right move on a new ambiguity
    assert grade.right_move("H_know", act, item, None) and not grade.right_move("H_know", ask, item, s["slot_id"])
    assert grade.right_move("R_full", act, item, None) and not grade.right_move("R_full", ask, item, s["slot_id"])
    assert grade.right_move("silent", act, item, None) and grade.right_move("silent", ask, item, s["slot_id"])
    assert grade.cohen_kappa(list("aabb"), list("aabb")) == 1.0 and grade.cohen_kappa(list("aabb"), list("abab")) == 0.0


# ---------------------------------------------------------------- frozen data checks
@needs_data
def test_persona_schema_and_hash():
    from sleep2.askonce.config import sha256_file
    from sleep2.askonce.world import Persona, validate_persona
    P = Persona.load()
    assert validate_persona(P.d) == []
    assert len(P.slots) == 60 and len(P.facts) == 40
    assert {k: len(v) for k, v in P.by_split.items()} == {"new": 20, "silent": 5, "train": 35}
    assert (DATA / "persona.sha256").read_text().split()[0] == sha256_file(DATA / "persona.json")
    assert (DATA / "requests.sha256").read_text().split()[0] == sha256_file(DATA / "requests.jsonl")
    assert (DATA / "phrasings.sha256").read_text().split()[0] == sha256_file(DATA / "phrasings.json")


@needs_data
def test_requests_composition_gold_and_leakage_rule():
    import collections
    from sleep2.askonce.requests_gen import check_text, leak_check
    from sleep2.askonce.world import Persona
    P = Persona.load()
    rows = jl_read(DATA / "requests.jsonl")
    c = collections.Counter(r["split"] for r in rows)
    assert c == {"train": 200, "H_know": 80, "H_new": 80, "H_full": 40, "R_new": 30, "R_know": 70, "R_full": 100, "silent": 20}
    assert collections.Counter(r["day"] for r in rows if r["split"] == "train") == {d: 40 for d in range(1, 6)}
    assert leak_check(rows, P) == []                                  # new-ambiguity slots never appear in days 1-5 text
    new = set(P.by_split["new"])
    assert not any(set(r["slots"]) & new for r in rows if r["day"] <= 5)
    assert all(set(r["slots"]) <= new for r in rows if r["split"] in ("H_new", "R_new"))
    assert all(set(r["slots"]) <= set(P.by_split["train"]) for r in rows if r["split"] in ("H_know", "R_know"))
    assert all(set(r["slots"]) <= set(P.by_split["silent"]) for r in rows if r["split"] == "silent")
    tr = [r for r in rows if r["split"] == "train"]
    assert 0.4 <= sum(r["underspecified"] for r in tr) / len(tr) <= 0.6    # about 50% underspecified
    for r in rows:
        assert check_text(r, r["text"], P) == "", (r["req_id"], r["text"])
        assert bool(r["slots"]) == r["underspecified"]
        assert all(k in TM.KEY_ARGS[r["gold"]["tool"]] for k in r["gold"]["args"])
    assert len({norm(r["text"]) for r in rows}) == len(rows)


@needs_data
def test_phrasings_contain_values():
    from sleep2.askonce.phrasings import check_slot
    from sleep2.askonce.world import Persona
    P = Persona.load()
    phr = json.load(open(DATA / "phrasings.json"))
    assert set(phr["slots"]) == set(P.by_split["train"]) | set(P.by_split["silent"])
    for sid, v in phr["slots"].items():
        assert check_slot(dict(v), P.slot(sid)) == [], sid
    assert len(phr["general"]) == 200


# ---------------------------------------------------------------- sim + tagger + oracle on the scripted policy
@needs_data
def test_day_sim_tagger_oracle_consistency(tmp_path):
    from sleep2.askonce.config import jload
    from sleep2.askonce.oracle_labels import oracle_labels
    from sleep2.askonce.report_tagger import prf
    from sleep2.askonce.simulate_days import run_days
    from sleep2.askonce.smoke import scripted_gen
    from sleep2.askonce.tagger import tag_all
    from sleep2.askonce.world import Persona, load_requests
    P, phr = Persona.load(), jload(DATA / "phrasings.json")
    reqs = load_requests(split="train")
    run_days(scripted_gen(P, reqs), P, phr, "<|ifm|begin_of_text|>", out_dir=tmp_path, requests=reqs, log=lambda *a: None)
    orc = oracle_labels(tmp_path / "oracle")
    assert sum(o["type"] == "regret" for o in orc) > 5 and sum(o["type"] == "annoyance" for o in orc) > 5
    tags = tag_all(tmp_path / "diary")
    r = prf(tags, orc)
    assert r["regret"]["precision"] >= 0.9 and r["regret"]["recall"] >= 0.6, r
    assert r["annoyance"]["precision"] >= 0.9 and r["annoyance"]["recall"] >= 0.6, r
    # the tagger never reads oracle data: tags only carry diary-visible fields
    assert set(tags[0]) == {"day", "req_id", "type", "slot_ref", "evidence", "source"}
    # silent slots are never corrected
    rows = [x for d in range(1, 6) for x in jl_read(tmp_path / "diary" / f"day{d}.jsonl")]
    silent_refs = {P.slot(s)["ref"] for s in P.by_split["silent"]}
    corr_reqs = {x["req_id"] for x in rows if x["meta"].get("kind") == "correction"}
    for x in rows:
        if x["meta"].get("kind") == "request" and x["req_id"] in corr_reqs:
            assert not (set(x["meta"]["lookup_refs"]) & silent_refs)


@needs_data
def test_user_sim_is_deterministic_and_value_bearing():
    from sleep2.askonce.config import jload
    from sleep2.askonce.user_sim import UserSim
    from sleep2.askonce.phrasings import value_in
    from sleep2.askonce.world import Persona, load_requests
    P, phr = Persona.load(), jload(DATA / "phrasings.json")
    sim = UserSim(P, phr)
    for r in [x for x in load_requests(split="train") if x["underspecified"]][:30]:
        sid = r["slots"][0]
        a1, s1, an1 = sim.answer_ask(r, "Which one do you mean?", set())
        assert (a1, s1, an1) == sim.answer_ask(r, "Which one do you mean?", set()) and s1 == sid and not an1 and value_in(a1, P.slot(sid))
        assert sim.answer_ask(r, "Which one?", {sid})[2]               # annoyed when the slot is already known
        c = sim.correction(r, sid)
        assert (c is None) == (P.slot(sid)["split"] == "silent")
    full = next(x for x in load_requests(split="train") if not x["underspecified"])
    assert sim.answer_ask(full, "Which address?", set())[2]


# ---------------------------------------------------------------- torch: tiny-model generation + training + DPO + ledger agreement
@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    torch = pytest.importorskip("torch")
    pytest.importorskip("peft")
    from sleep2.askonce.model_io import get_tokenizer, load_model
    from sleep2.askonce.smoke import make_tiny_model
    d = tmp_path_factory.mktemp("tiny")
    name = make_tiny_model(d / "t", ["Which Sam do you mean?", "ACT {\"tool\": \"open_file\", \"args\": {\"path\": \"/a/b.txt\"}}", "sam.r@example.com", "Write one fact"])
    return name, get_tokenizer(name), load_model(name, torch.float32, "cpu")


def test_generate_batching_matches_single(tiny):
    from sleep2.askonce.model_io import generate
    name, tok, model = tiny
    ps = [render([{"role": "user", "content": t}], True, tok.bos_token) for t in ("Which Sam?", "open file /a/b.txt please now", "hi")]
    together = generate(model, tok, ps, 6, 0.0, 0, bs=3)
    single = [generate(model, tok, [p], 6, 0.0, 0, bs=1)[0] for p in ps]
    assert together == single and all(isinstance(x, str) for x in together)


def test_lora_night_dpo_sft_anchor_and_units(tiny):
    import torch
    from sleep2.askonce.model_io import load_model
    from sleep2.askonce.train_core import LoRATrainer
    name, tok, _ = tiny
    model = load_model(name, torch.float32, "cpu")
    tr = LoRATrainer(model, tok, seed=3, device="cpu", use_scaler=False)
    pr = render([{"role": "user", "content": "Open the essay"}], True, tok.bos_token)
    E = "<|ifm|im_end|>"
    sft = {"kind": "sft", "prompt": pr, "target": 'ACT {"tool": "open_file", "args": {"path": "/a/b.txt"}}' + E}
    pair = {"kind": "pair", "prompt": pr, "chosen": "ASK Which essay do you mean?" + E, "rejected": 'ACT {"tool": "open_file", "args": {"path": "/z.txt"}}' + E}
    anchors = [render([{"role": "user", "content": "Why is the sky blue?"}], True, tok.bos_token)]
    # KL anchor is ~0 at init (adapter B = 0)
    a = tr.encode(anchors[0], "")
    a["mask"] = [0] + [1] * (len(a["ids"]) - 1)
    assert tr.anchor_kl(a).item() < 1e-6
    kw = dict(anchors=anchors, n_opt=8, log=lambda *x: None)
    s1 = tr.run_night([sft] * 8, lr=1e-3, night=1, **kw)
    s2 = tr.run_night([sft] * 8, lr=1e-3, night=2, **kw)
    assert s2["sft_loss"] < s1["sft_loss"]                          # the adapter is carried from night to night and keeps learning
    first = tr.run_night([sft] * 6 + [pair] * 6, lr=1e-3, night=3, anchors=anchors, n_opt=6, log=lambda *x: None)
    assert first["dpo_loss"] < 0.6931 and first["dpo_margin"] > 0 and first["dpo_acc"] > 0.5       # DPO moves toward the chosen side
    assert first["anchor_kl"] >= 0 and first["opt_steps"] == 6
    # token-pass accounting agrees with the ledger computed from the same lengths
    planned = CL.night_ledger([sft] * 6, [pair] * 6, 6, len(a["ids"]), lambda p, t: tr.length(p, t), 0)
    assert abs(first["units_total"] - planned["total"]) / planned["total"] < 0.02
    base = tr.release()
    assert not any("lora" in n for n, _ in base.named_parameters())


def test_build_night_data_equal_compute_on_synthetic_logs(tmp_path, tiny):
    pytest.importorskip("torch")
    if not HAVE_DATA:
        pytest.skip("frozen data not generated")
    from sleep2.askonce import build_night_data
    from sleep2.askonce.config import jload
    from sleep2.askonce.simulate_days import run_days
    from sleep2.askonce.smoke import scripted_gen
    from sleep2.askonce.tagger import tag_all
    from sleep2.askonce.world import Persona, load_requests
    name, tok, _ = tiny
    P, phr = Persona.load(), jload(DATA / "phrasings.json")
    reqs = load_requests(split="train")
    run_days(scripted_gen(P, reqs), P, phr, tok.bos_token, days=[1, 2, 3], out_dir=tmp_path / "logs", requests=reqs, log=lambda *a: None)
    tags = tag_all(tmp_path / "logs" / "diary")
    plan = build_night_data.build(tmp_path / "logs" / "diary", tags, tok, tmp_path / "nd", persona=P, phr=phr, requests=load_requests(), nights=3, log=lambda *a: None)
    for n, p in plan.items():
        assert p["spread"] <= 0.05
        tot = {a: l["total"] for a, l in p["per_arm"].items()}
        assert max(tot.values()) / min(tot.values()) < 1.11
        sl = p["per_arm"]["B"]["slice"] / p["per_arm"]["B"]["total"]
        assert sl <= 0.151 + 1e-9                                       # B's slice never exceeds 15% of the night
    # shared part identical in all arms; only the slice differs
    shared = lambda arm, n: [json.dumps(x, sort_keys=True) for x in jl_read(tmp_path / "nd" / "nights" / arm / f"night{n}.jsonl") if x.get("src") in ("fact", "corr_action")]  # noqa: E731
    for n in plan:
        assert shared("A+", n) == shared("B", n) == shared("B-sft", n)
    kinds = {a: {x["kind"] for x in jl_read(tmp_path / "nd" / "nights" / a / "night2.jsonl")} for a in ("A+", "B", "B-sft")}
    assert kinds["B"] == {"sft", "pair"} and kinds["A+"] == {"sft"} and kinds["B-sft"] == {"sft"}
    ev = jl_read(tmp_path / "nd" / "eval_inputs.jsonl")
    assert len(ev) == 620 - 200 and all("[Memory]" in e["prompt"] for e in ev)


# ---------------------------------------------------------------- Kaggle packaging
@needs_data
def test_build_job_payload_and_metadata(tmp_path):
    from sleep2.askonce.kaggle import build_job
    r1 = build_job.build(1, tmp_path / "k1")
    meta = json.loads((tmp_path / "k1" / "kernel-metadata.json").read_text())
    assert meta["id"] == "thegreatergood/askonce-job1" and meta["enable_gpu"] == "true" and meta["enable_internet"] == "true" and meta["is_private"] == "true"
    nb = json.loads((tmp_path / "k1" / "askonce-job1.ipynb").read_text())
    assert len(nb["cells"]) == 1 and "pip uninstall -y -q torchao" in nb["cells"][0]["source"] and "KILLED_DEADLINE" in nb["cells"][0]["source"]
    assert r1["payload_kb"] < 800
    compile(nb["cells"][0]["source"], "cell", "exec")
