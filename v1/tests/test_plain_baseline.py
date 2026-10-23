"""CPU smoke tests for v1/plain_baseline.py on a tiny generated village (a few dozen visits per split; generated once per session).
Run: python3 -m pytest v1/tests/test_plain_baseline.py -q"""
import json
import shutil
import sys
from pathlib import Path

import pytest
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from learnlab.tokenizer import Tokenizer  # noqa: E402
from v1 import plain_baseline as pb  # noqa: E402

TOK = ROOT / "data/tokenizer/premonition-tok-v2.json"
TINY = "32,2,2"            # d_model, layers, heads for speed; --allow-off-band is always passed with it
PER = 20                   # visits per tiny shard


@pytest.fixture(scope="session")
def village(tmp_path_factory):
    from learnlab.village import shards as S
    base = tmp_path_factory.mktemp("village")
    build = base / "_build"
    S.write_shards("train", 3 * PER, build, 1, seed=0, visits_per_shard=PER, verbose=False)
    S.write_shards("validation", 2 * PER, build, 1, seed=0, visits_per_shard=PER, verbose=False)
    root = base / "v1village"
    for name, src, pick in (("train", "train", [0, 1]), ("dev", "train", [2]), ("validation", "validation", [0, 1])):
        (root / name).mkdir(parents=True)
        for k in pick:
            for p in (build / src).glob(f"shard-{k:05d}.*"):
                shutil.copy(p, root / name / p.name)
        shutil.copy(build / src / "manifest.json", root / name / "manifest.json")
    return root


def test_param_band_and_refusal():
    m = pb.build_model(pb.VOCAB)
    n = m.num_parameters()
    assert abs(n - pb.TARGET_PARAMS) <= 0.10 * pb.TARGET_PARAMS
    with pytest.raises(pb.BandError):
        pb.build_model(pb.VOCAB, (256, 4, 4))            # contender A's own 4M shape: far outside the band
    with pytest.raises(pb.BandError):
        pb.build_model(pb.VOCAB, (64, 2, 2))
    pb.build_model(pb.VOCAB, (64, 2, 2), enforce_band=False)


def test_sealed_split_refused(village):
    for name in ("test", "test-long"):
        with pytest.raises(pb.SealedSplitError):
            pb.open_split(village, name)
        with pytest.raises(pb.SealedSplitError):
            pb.split_questions(village, name)
    (village / "test").mkdir(exist_ok=True)           # even a present test dir is never listed or read
    assert all((village / "test") not in p.parents for pair in pb.open_split(village, "train") for p in pair)
    shutil.rmtree(village / "test")


def test_examples_are_label_free(village):
    tok = Tokenizer.load(TOK)
    qs = pb.split_questions(village, "dev")
    assert qs
    from premonition.lookup import LineIds
    lines = LineIds(tok, regime=pb.REGIME)
    fb = tok.token_to_id("[feedback]")
    ans = tok.token_to_id("[answer]")
    for q in qs[:50]:
        e = pb.make_example(q, lines, tok)
        assert fb not in e.ids                                  # no feedback label anywhere
        first_ans = e.ids.index(ans)
        assert len(e.ids) <= 768 and len(e.ids) == len(e.mask)
        # every [answer] except the last is followed by a masked, answer-free newline; the last is followed by the target
        pos = [i for i, t in enumerate(e.ids) if t == ans]
        assert all(not e.mask[i + 1] for i in pos[:-1])
        assert all(e.mask[i] for i in range(pos[-1] + 1, len(e.ids)))
        assert first_ans >= 0


def run_main(village, out, steps, *extra):
    return pb.main(["--root", str(village), "--out", str(out), "--steps", str(steps), "--workers", "2", "--device", "cpu",
                    "--shape", TINY, "--allow-off-band", "--max-tokens", "4000", "--group-shards", "1", "--ckpt-every", "3",
                    "--eval-every", "100000", "--final-limit", "20", *extra])


def test_three_steps_run_and_final_json(village, tmp_path):
    assert run_main(village, tmp_path / "a", 3) == 0
    fin = json.loads((tmp_path / "a" / "final_dev.json").read_text())
    assert fin["dev"]["questions"] == 20 and fin["validation"]["questions"] == 20
    assert 0.0 <= fin["dev"]["accuracy"] <= 1.0 and fin["dev"]["by_qtype"]
    log = (tmp_path / "a" / "train_log.jsonl")
    assert (tmp_path / "a" / "wake-ckpt" / "step-3.pt").exists()


def test_resume_equals_uninterrupted(village, tmp_path):
    run_main(village, tmp_path / "full", 6)
    run_main(village, tmp_path / "cut", 6, "--stop-after", "3")        # killed after 3 steps (checkpoint at step 3)
    assert not (tmp_path / "cut" / "final_dev.json").exists()
    run_main(village, tmp_path / "cut", 6)                              # resumes from step 3
    a = torch.load(tmp_path / "full" / "plain-final.pt")
    b = torch.load(tmp_path / "cut" / "plain-final.pt")
    assert a.keys() == b.keys()
    for k in a:
        assert torch.equal(a[k], b[k]), k
    fa = json.loads((tmp_path / "full" / "final_dev.json").read_text())
    fb = json.loads((tmp_path / "cut" / "final_dev.json").read_text())
    assert fa["dev"] == fb["dev"] and fa["validation"] == fb["validation"]


def test_question_set_equals_d(village):
    """The scored question ids are exactly the ids of D's caches (premonition.data via v1.dtrain.open_data)."""
    from v1 import dtrain
    data = dtrain.open_data(village, TOK, workers=1, log=lambda s: None)
    for name, cache in (("dev", data.dev), ("validation", data.validation)):
        mine = [q.id for q in pb.split_questions(village, name)]
        assert mine == list(cache.question_ids), name
