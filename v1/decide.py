"""D5, mechanically: after both arms finished, pick the arm and decide whether the seal may be opened. Reads DEV numbers only.
  python -m v1.decide --floor OUT_FLOOR --full OUT_FULL --out DECISION_DIR
Rule (V1_PARAMS / consult d4): the arm with the higher dev main-task (D) accuracy, ties to FULL; the seal opens only if that arm meets
W1 and W2 on dev. Writes DECISION.json, and DEV_PASS.json (the only thing v1.sealed_read accepts) when the seal may open."""
import argparse, json
from pathlib import Path


def decide(floor: dict, full: dict) -> dict:
    fa, ua = floor["d_dev"]["accuracy"], full["d_dev"]["accuracy"]
    chosen = "full" if ua >= fa else "floor"
    c = full if chosen == "full" else floor
    w1, w2 = bool(c.get("W1_dev_pass")), bool(c.get("W2_dev_pass"))
    return {"floor_dev_accuracy": fa, "full_dev_accuracy": ua, "chosen": chosen, "W1_dev_pass": w1, "W2_dev_pass": w2,
            "open_seal": w1 and w2, "chosen_final": c, "floor_vs_full_dev_points": 100 * (ua - fa)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--floor", required=True)
    ap.add_argument("--full", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    f = json.loads((Path(a.floor) / "final_dev.json").read_text())
    u = json.loads((Path(a.full) / "final_dev.json").read_text())
    d = decide(f, u)
    d["arm_dirs"] = {"floor": a.floor, "full": a.full}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "DECISION.json").write_text(json.dumps(d, indent=1, default=float))
    if d["open_seal"]:
        (out / "DEV_PASS.json").write_text(json.dumps({"chosen": d["chosen"], "arm_dir": d["arm_dirs"][d["chosen"]]}))
    print(json.dumps({k: v for k, v in d.items() if k != "chosen_final"}, indent=1))


if __name__ == "__main__":
    main()
