"""Run one bench132_4hop item once on an agent (v3 driver, as suitediff does). Args: agent.py config workdir item_id"""
import sys, json, copy, shutil
from pathlib import Path
sys.path.insert(0, 'scripts')
import fable_suitediff as SD
import fable_fix172b_benchv3 as V3
agent, cfgp, work, iid = sys.argv[1:5]
mod, dcls, _, _ = SD.load_agent(agent)
cfg = copy.deepcopy(SD.load_base_cfg(cfgp)); cfg["sleep_threshold"] = 100000
items = [json.loads(l) for l in Path("data/open/bench132/fable_edit132_4hop.jsonl").read_text().splitlines() if l.strip()]
it = [x for x in items if x["id"] == iid][0]
w = Path(work); shutil.rmtree(w, ignore_errors=True); w.mkdir(parents=True)
r = V3.run_item_v3(it, w, cfg, SD.mailbox_daemon_cls(dcls), "v3")
print(json.dumps({k: r.get(k) for k in ("id", "verdict", "ears_stage", "reply")}, ensure_ascii=False))
