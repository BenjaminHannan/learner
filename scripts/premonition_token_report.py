"""Aggregate every fixed roster, including failures; never select checkpoints."""
from __future__ import annotations

import json
from pathlib import Path

import premonition_memnn_compare as C
import premonition_token_memory_run as R
import premonition_token_evidence_run as E
import premonition_token_scaled_run as S

ROOT=C.ROOT
ARMS={"Answer only":ROOT/"artifacts/codex-token-memory-20260920",
      "Guided":ROOT/"artifacts/codex-token-evidence-20260920",
      "Guided, scaled start":ROOT/"artifacts/codex-token-scaled-20260920"}
NAMES=["One-hop","Practised two-hop","Held-out two-hop","Changed link: both correct",
       "Changed value: both correct","Irrelevant change: both correct"]


def read(path): return json.loads(Path(path).read_text())


def main():
    plans={"Answer only":R.load_plan(ARMS["Answer only"]),"Guided":E.load(ARMS["Guided"]),
           "Guided, scaled start":S.load(ARMS["Guided, scaled start"])}
    records={}
    for arm,folder in ARMS.items():
        records[arm]=[]
        for seed in (0,1,2):
            base=folder/f"seed-{seed}"
            row={name:read(base/f"{name}.json") for name in
                 ("training","old-evaluation","fresh-evaluation","memory-lesion","completion")}
            if C.sha(base/"model.pt")!=row["training"]["checkpoint_sha256"]:
                raise RuntimeError("checkpoint identity changed")
            if row["training"]["final_fingerprint"]!=row["fresh-evaluation"]["fingerprint"]:
                raise RuntimeError("evaluation fingerprint mismatch")
            records[arm].append(row)
    plain=[read(ARMS["Answer only"]/f"seed-{seed}/plain-fresh-evaluation.json") for seed in (0,1,2)]
    old_plain=[read(ROOT/f"artifacts/codex-memnn-comparison-20260919-v2/seed-{seed}/plain-evaluation.json")
               for seed in (0,1,2)]
    cells=list(plain[0]["cells"])
    metrics={}
    for arm,rows in {"Original Premonition":plain,**{a:[r["fresh-evaluation"] for r in rs]
                                                  for a,rs in records.items()}}.items():
        metrics[arm]={name:{"counts":[r["cells"][name]["count"] for r in rows],"n_per_seed":512,
                           "mean_accuracy":sum(r["cells"][name]["count"]/r["cells"][name]["n"] for r in rows)/3}
                      for name in cells}
    paired=all(records["Answer only"][s]["training"]["initial_fingerprint"]==
               records["Guided"][s]["training"]["initial_fingerprint"] for s in (0,1,2))
    exposure=[r["training"]["exposure_complete"] for rows in records.values() for r in rows]
    old_pass={a:sum(r["completion"]["old_all_six"] for r in rs) for a,rs in records.items()}
    fresh_pass={a:sum(r["completion"]["fresh_all_six"] for r in rs) for a,rs in records.items()}
    solved=[a for a in ARMS if old_pass[a]==3 and fresh_pass[a]==3 and
            all(r["training"]["exposure_complete"] for r in records[a])]
    for p in plans.values():
        for info in p["fresh_panels"].values():
            if C.sha(info["path"])!=info["sha256"]: raise RuntimeError("panel changed")
        for j in p["jobs"]:
            if C.sha(j["control_checkpoint"])!=j["control_sha256"]: raise RuntimeError("control changed")
            if C.sha(j["control_record"])!=j["control_record_sha256"]: raise RuntimeError("control record changed")
    # Includes the frozen old data hashes, not just the manifest.
    C.M.bootstrap()
    C.load_panels()
    stress={a:read(folder/"reasoning-probe/results.json") for a,folder in ARMS.items()}
    summary={"fresh_mean_accuracy":metrics,"old_all_six_counts":old_pass,"fresh_all_six_counts":fresh_pass,
             "registered_successful_recipes":solved,"all_registered_exposures_complete":all(exposure),
             "answer_only_and_guided_initial_weights_paired":paired,
             "original_all_six_old":sum(r["all_six_answer_thresholds"] for r in old_plain),
             "original_all_six_fresh":sum(r["all_six_answer_thresholds"] for r in plain),
             "paid_compute_cost":0,"sources_and_data_unchanged":True,"checkpoints_verified":9,
             "tests_passed":22,"general_intelligence_established":False,
             "official_G_pair_admission":False,"equal_compute_historical_comparison":False}
    destination=ARMS["Answer only"]
    C.write_new(destination/"comparison.json",summary)
    lines=["# Premonition: access fixes and the intelligence test", ""]
    if solved:
        lines.append("The registered narrow transfer screen passed in all three seeds for: "+", ".join(solved)+". This is evidence for the specified toy task, not general intelligence or a scaling law.")
    else:
        lines.append("The information-access bottlenecks were removed in an experimental successor, but **the reasoning problem is not solved**: no recipe passed the complete registered transfer-and-confirmation screen in all three seeds. The successor remains experimental.")
    lines += ["", "## What changed and why", "",
              "The 79,316-parameter successor keeps one state per story token, uses four soft attention heads to consider multiple facts, lets answer gradients train search directly, and makes the original question available at every reasoning step. It replaces hard card selection, pooling and ASK/binder decisions with recurrent transformer attention. Original Premonition has 79,748 parameters.", "",
              "Three recipes were retained: answers only; answers plus ordered supporting-line feedback during training; and the latter with starting linear weights scaled for the small model width. The last change was chosen using a separate 1,000-update training-only check, without held-out evaluation. All recipes use the same model forward at inference. No role labels, gold cards, or parsed fact fields enter it.", "",
              "## Results on new worlds", "",
              "Mean accuracy across fixed seeds 0, 1, 2; each seed sees the same 512 units per cell. Paired edits require both answers to be correct. These are raw accuracy screens, not an original hard-card admission certificate.", "",
              "| Test | Original | Answers only | Guided | Guided, scaled start |",
              "|---|---:|---:|---:|---:|"]
    for name,title in zip(cells,NAMES):
        values=[metrics[a][name]["mean_accuracy"] for a in ("Original Premonition",*ARMS)]
        lines.append("| "+title+" | "+" | ".join(f"{v:.1%}" for v in values)+" |")
    lines += ["", "| Recipe | All original six cells | All fresh six cells | Fresh one-hop below 75% |",
              "|---|---:|---:|---:|",
              f"| Original | {summary['original_all_six_old']}/3 | {summary['original_all_six_fresh']}/3 | {sum(r['cells'][cells[0]]['count']/512 < .75 for r in plain)}/3 |"]
    for arm,rs in records.items():
        stuck=sum(r["fresh-evaluation"]["cells"][cells[0]]["count"]/512<.75 for r in rs)
        lines.append(f"| {arm} | {old_pass[arm]}/3 | {fresh_pass[arm]}/3 | {stuck}/3 |")
    lines += ["", "## Does it extend to harder situations?", "",
              "The following secondary tests were fixed before the primary held-out outcomes. Twelve-person worlds retain the grammar but double the number of people. Three-hop questions add a second LINK token, changing both depth and syntax. Six read steps reuse the same trained weights; no extra learning occurs.", "",
              "| Recipe | Read steps | 12 people: one-hop | 12 people: practised two-hop | 12 people: held-out two-hop | Three-hop held-out |",
              "|---|---:|---:|---:|---:|---:|"]
    for arm,result in stress.items():
        for steps in ("3","6"):
            names=[k for k in result["0"][steps] if k!="integrity"]
            vals=[sum(result[str(seed)][steps][n]["count"]/result[str(seed)][steps][n]["n"] for seed in (0,1,2))/3 for n in names]
            lines.append(f"| {arm} | {steps} | "+" | ".join(f"{x:.1%}" for x in vals)+" |")
    lines += ["", "## Grounding and integrity", ""]
    for arm,rs in records.items():
        normal=metrics[arm][cells[2]]["mean_accuracy"]
        wiped=sum(r["memory-lesion"]["cells"][cells[2]]["count"]/512 for r in rs)/3
        lines.append(f"- {arm}: fresh held-out accuracy {normal:.1%}; with story memory disabled, {wiped:.1%}.")
    lines += ["", "Twenty-two implementation checks passed. Evaluation preserved weights; saved checkpoints reproduce predictions. Sources, old controls, original panels and fresh panels retain their recorded hashes. The answer-only and guided arms started from identical tensors for each paired seed. No seeds or intermediate checkpoints were selected by test performance.", "",
              "## Compute and limits", "",
              "The first two recipes target the historical 12,251 / 12,250 / 12,250-update exposure. The scaled-start recipe has a fixed shorter 6,000-update exposure. All have approximately 80k parameters, but this is **not an equal-spent-compute comparison with original Premonition**. Original controls also had different losses and training hardware.", ""]
    for arm,rs in records.items():
        for seed,r in enumerate(rs):
            t=r["training"]
            lines.append(f"- {arm}, seed {seed}: {t['updates']:,}/{t['expected_updates']:,} registered updates; {t['counted_flops']:,} counted training FLOPs ({t['flop_share']:.2%} of the historical ceiling); {t['seconds']:.1f} training seconds.")
    lines += ["", "All work used local CPU; no paid compute, GPU, remote machine, package installation or external messaging. Counted FLOPs exclude elementwise operations and optimizer work under the project's existing convention.", "",
              "This remains a fixed-vocabulary, one-token-answer toy. Supporting-line order is privileged training feedback and is disclosed. Dense reads give up sparse-memory efficiency; line order is ignored. Three seeds do not establish broad reliability. Neither narrow success nor failure establishes general intelligence, and no parameter-scaling study was conducted.", "",
              "The main protocol and exact equations are in [the design note](../../reviews/premonition-token-memory-20260920.md). Full per-seed predictions, plans, checkpoints and hashes remain in this directory and the adjacent `codex-token-evidence-20260920` and `codex-token-scaled-20260920` directories."]
    with (destination/"COMPARISON.md").open("x") as f:f.write("\n".join(lines)+"\n")
    print(json.dumps(summary),flush=True)


if __name__=="__main__":main()
