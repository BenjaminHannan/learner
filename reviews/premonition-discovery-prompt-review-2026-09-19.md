# Review of the discovery reports and revised prompt

19 September 2026. Scope: prompt improvement grounded in the local repo. No model training, checkpoint execution, GPU work, or model-source edits were performed.

The historical synthesis is a useful research lens: find a difficult operation that the formulation makes unnecessarily hard. The companion prompt already improves substantially on the earlier “invent eight ideas, then kill anything familiar” prompt in this repo. It preserves competing explanations, distinguishes shared ingredients from identical mechanisms, protects held-out structure, and separates a successful intervention from its proposed explanation. Keep those parts.

The largest remaining gains come from updating the evidence, asking for a principle that predicts behavior across a task family, and making the next experiment settle a specific disagreement. More insistence on “game-changing” or a larger candidate quota would not address those issues.

The revised brief is [premonition-discovery-prompt-v2.md](premonition-discovery-prompt-v2.md), tailored to **GPT-6 Astra with Ultra reasoning**, as requested. This is a proposed improvement to the research process; it has not been experimentally shown to elicit better discoveries.

For Astra, I made the scientific criteria firm while leaving the research decomposition, search order, branch count, and useful breadth to the model. I removed the fixed candidate quota and specified what completion means so the session continues beyond an outline or first novelty objection. This follows the general advice to avoid overprescribed recipes and define completion in [official Astra prompting guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra). It is not evidence that Ultra guarantees original discoveries. Select Astra and Ultra in the session settings; including their names in prompt text does not change the active configuration.

## Corrections that change the research question

### The shortcut rerun is complete

The supplied prompt says the 12,000-step relation-shortcut rerun is pending. The saved [report](../artifacts/claude-relcut-long-20260919/REPORT.md) and five `runs/*.json` records contain the results. All-seed held-out counts, in seed order, are:

| Arm | Correct /171, seeds 0–4 | Mean accuracy | Prior joint gate |
|---|---|---|---|
| Long baseline | 6, 13, 88, 18, 12 | 16.0% | 1/5 |
| Long shortcut | 171, 32, 35, 170, 132 | 63.2% | 2/5 |

The shortcut's three runs that learned retrieval show substantial held-out performance. However, its advance rule required at least four of five runs to meet all three thresholds; it failed that rule. Seed 4 missed the oracle reading mark by one question, and seeds 1–2 remained stuck. These are exploratory validation results, not a fresh confirmation of broad generalization.

Consequently, the short-run first-request regression should not be presented as an established permanent conflict between retrieval stages. Investigate reproducible learning as well as generalization, and compare future ideas against this stronger existing method. Do not discard the unsuccessful seeds or infer a reliable difference in stuck rates from two failures versus one.

### The instrument is much smaller than the project target

The original description can be read as a 2M-parameter experiment at width 32. The ladder instead has 79,748 parameters by the repo's static formula, or 80,293 with the 545-parameter shortcut. The larger approximately 2M configuration uses width 128. I calculated these from `parameter_breakdown` with the ladder's vocabulary and four-loop configuration; I did not instantiate or measure a checkpoint.

The actual experiment also uses `D-card-bypass`, not the unmodified default reasoner. These distinctions matter for learning dynamics, efficiency claims, and transfer to the intended model. [Configuration](../premonition/config.py), [ladder](../premonition/toy_ladder.py), [retrieval harness](../scripts/premonition_ovn_retrieval.py).

### Some diagnostic conclusions need narrower wording

The [stuck-run report](../artifacts/claude-relcut-long-20260919/STUCK_PROBE.md) offers useful evidence, but “kappa is not the cause” exceeds its intervention. Rescaling fixed similarities tests inference-time ranking/loss. It does not test how temperature changed gradients or representation learning earlier. With age biases absent, multiplying all scores by a positive constant cannot change their ordering in the first place. [Probe implementation](../scripts/premonition_stuck_probe.py).

A linear decoder near chance on card keys also does not establish total information absence. The [person probe](../scripts/premonition_person_probe.py) trains a specific linear readout on even validation visits and evaluates odd visits. Treat it as evidence about accessible linear information, with causal use still unresolved.

Oracle-card accuracy is weaker evidence of reasoning than the headline suggests: only one supplied gold card contains an attribute value. Extraction can solve that diagnostic without choosing among competing attribute values. The separate distractor experiment addresses a different question. Preserve that separation.

### Inspect the source actually imported

The [ladder bootstrap](../scripts/premonition_ovn_ladder.py) verifies and imports an archived source snapshot. I checked that the live config, model, toy ladder, and answer-path files currently match their archived counterparts; that agreement is not guaranteed after future edits. A research handoff should record the imported source, configuration, evaluation policy, and artifacts rather than rely on filenames alone.

A [separate key-pooling scorer](../scripts/premonition_key_pool.py) already exists and adds 33 parameters at this width. It is a known candidate/control, not a new invention. No completed result for that variant was found in the local artifact inventory inspected for this review. That does not establish the status of work running elsewhere.

## What the revision adds

1. **A refreshed, portable evidence snapshot.** Repo sessions verify raw outputs and actual imports. Web sessions receive accurate counts and limitations without pretending to access files. The old reports remain intact.
2. **A prediction across a controlled task family.** A discovery candidate must say how its advantage changes with a relevant burden and include a boundary where it should fail. This helps distinguish a transferable principle from fitting one generator's shortcut.
3. **Less steering of initial inventors.** Give them neutral facts and different computational questions, withholding the lead's favored mechanism, famous examples, and exhaustive prior-art list until the audit. This is a plausible anti-anchoring choice, not an established LLM discovery result. Merge computational duplicates rather than fill an eight-item quota.
4. **Room for coupled ideas and ordinary explanations.** The prompt prioritizes architecture but allows a schedule or objective fix to defeat an architectural story. Two necessary components can be one coherent proposal if a factorial experiment can separate their contributions.
5. **A distinction between capability and reliability.** Use all seeds and count the cost of failed starts. Five seeds are a useful first comparison, not universal proof of reliability: even zero failures in five independent runs gives an exact one-sided 95% upper failure-probability bound of about 45.1%, from `1 - 0.05**(1/5)`.
6. **A concrete build handoff and decision tree.** Specify interfaces, information access, the strongest baseline, a mechanism falsifier, and what each possible result triggers. A gain with the wrong explanation remains useful but changes the research claim.

The proposal does not require a universal theorem, guaranteed tenfold result, or proof of worldwide novelty before experimentation. It does require an explicit argument for why a large gain could arise and an experiment that can reject that argument.

## How to apply it

In a fresh session with this repo open, select **GPT-6 Astra → Ultra**, then use:

> Read `reviews/premonition-discovery-prompt-v2.md` and carry out its research brief. Refresh its evidence from the local artifacts before selecting a mechanism. Produce one buildable hypothesis and its decisive experiment under `reviews/`. Follow the brief's research-only scope; implementation and training are a subsequent task.

For a session without repo access, paste the entire revised brief. Its evidence is explicitly dated; refresh it before reuse if additional experiments finish. The historical review is optional context for the lead, not required reading for every initial inventor.

Keep diagnosis and invention connected without letting the current plateau define the project's whole ambition. The most useful immediate question is: **what general learning burden does this plateau expose, and what other task would reveal the same burden?** The answer might support a new principle, a known repair, or rejection of the architectural explanation. Each can inform the next experiment.

## How to tell whether this prompt is actually better

Do not grade it by the model's confidence, number of citations, or how novel the proposal sounds. Compare the original and revised prompts using the same refreshed evidence, tools, and research budget; otherwise improved factual context is confounded with improved instructions. Remove prompt labels when assessing the resulting briefs. A small rubric should check:

- Accurate evidence and model configuration, including failed runs and structural hints.
- A specified computation and learning signal that an engineer can implement.
- An exact, verified difference from the closest prior method, or honest identification as an established method.
- A discriminating prediction plus an experiment capable of falsifying it.
- A competent baseline, protected data, and affordable complete cost.
- A credible transfer test connecting the local result to the broader ambition.

Several independent sessions would be needed to assess consistency. These checks assess research-output quality; only subsequent experiments can establish an architectural advance. This evaluation approach follows the general recommendation to assess prompts through recorded outputs and focused checks in [official OpenAI documentation](https://developers.openai.com/blog/eval-skills); its application to discovery here is my proposal.

## Verification performed

Read both supplied reports. Inspected the relevant local reports, source, raw run JSON, probe implementation, and artifact inventory. Recomputed the five-seed tables and joint gates from saved outputs, calculated parameter counts from the static formula, and compared four live source files with their frozen copies. No new scientific experiments were run. The historical review's author/year attributions were considered as supplied context; this review does not claim to have independently re-audited its 48 sources.
