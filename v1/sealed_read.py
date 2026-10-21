"""THE sealed read (D6). Allowed once, only for the arm named in DEV_PASS.json written by v1.decide (W1 and W2 met on dev).
  python -m v1.sealed_read --decision DECISION_DIR --root DATA_ROOT --b2 B2_CKPT --skills SKILLS_DIR
Refuses without DEV_PASS.json, refuses a second time (SEALED_READ.json), writes the result before printing. The village `test`
cache is built here and nowhere else; the creative test.jsonl is scored here and nowhere else."""
import argparse, json, sys, time
from pathlib import Path

import torch


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--decision", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--b2", required=True)
    ap.add_argument("--skills", required=True)
    ap.add_argument("--tokenizer", default=str(Path(__file__).resolve().parent.parent / "data/tokenizer/premonition-tok-v2.json"))
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    a = ap.parse_args(argv)
    dec = Path(a.decision)
    if not (dec / "DEV_PASS.json").exists():
        sys.exit("REFUSED: DEV_PASS.json missing; the chosen arm did not meet W1 and W2 on dev, so the seal stays shut.")
    if (dec / "SEALED_READ.json").exists() or (dec / "SEALED_READ.started").exists():
        sys.exit("REFUSED: the sealed split was already opened once (SEALED_READ.json or .started exists); never re-read, even after a crash.")
    (dec / "SEALED_READ.started").write_text(time.strftime("%Y-%m-%d %H:%M:%S"))      # a crash after this still counts as opened
    import os
    os.environ["V1_SEALED_READ"] = "1"
    pas = json.loads((dec / "DEV_PASS.json").read_text())
    arm_dir = Path(pas["arm_dir"])
    from premonition import data as pdata, preprocess
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    from premonition.train import mini_config_from, validation_hook
    from memorylab.storage import Budget
    from learnlab.tokenizer import Tokenizer
    from v1 import baselines, creative_sleep, dtrain, run as vrun
    from v1.joint import Bridge
    root = Path(a.root)
    tok = Tokenizer.load(Path(a.tokenizer))
    budget = Budget(root.parent, hard=100_000_000_000, steady=80_000_000_000)
    det = pdata.name_detector(budget, root.name)
    test = pdata.load_or_build(budget, root.name, "test", tok, det, split="test", regime=preprocess.LABEL_FREE, log=lambda s: None)
    train = pdata.load_or_build(budget, root.name, "train", tok, det, regime=preprocess.LABEL_FREE, log=lambda s: None)
    saved = torch.load(arm_dir / "D-final.pt", map_location=a.device, weights_only=False)
    d = PremonitionMini(mini_config_from(saved["config"])).to(a.device)
    d.load_state_dict(saved["model"])
    b2, _, _ = vrun.load_creative(a.b2, a.device)
    bridge = Bridge(d.config.d_model, b2.d).to(a.device).attach(d, b2)
    bridge.load_state_dict(saved["bridge"])
    bridge.frozen_ctx = True
    batches, stops = vrun.make_eval_batches(test, len(test), tok)
    r = validation_hook(batches, tokenizer=tok, stop=stops)(d)
    base = baselines.baselines(train, test)
    dev_base = json.loads((arm_dir / "final_dev.json").read_text())["baseline_dev"]["best"]
    w1_thr = dev_base + 0.10
    cres = creative_sleep.dev_report(str(arm_dir / "creative" / "W2.pt"), a.device, attach=bridge.attach_creative, split="test")
    out = {"arm": pas["chosen"], "village_test_accuracy": r["accuracy"], "village_test_questions": r["questions"],
           "dev_baseline_best": dev_base, "W1_threshold": w1_thr, "W1": r["accuracy"] >= w1_thr,
           "creative_test_first_try": cres["first_try"], "creative_by_kind": cres["by_kind"], "W2": cres["first_try"] >= 0.20,
           "test_set_baseline_for_reference": base}
    out["working"] = out["W1"] and out["W2"]
    (dec / "SEALED_READ.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
