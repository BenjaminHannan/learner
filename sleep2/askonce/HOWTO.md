# Ask once, then remember: how to run it

All paths are relative to the repo root. Frozen inputs: `sleep2/askonce/data/` (sha256 files next to them). Deviations: `sleep2/askonce/DEVIATIONS.md`.

## 0. Tests and CPU smoke (no GPU, no API)
    python -m pytest tests/test_askonce.py -q
    python -m sleep2.askonce.smoke_e2e --out /tmp/askonce_smoke        # tiny random Llama; job1 -> tagger -> build_night_data -> job2 x2 seeds -> grade -> report

## 1. (Container, already done once) generate and freeze the text with Message Batches
    export LEARNER_ANTHROPIC_API_KEY=...        # never printed
    python -m sleep2.askonce.persona            # Sonnet: persona.json
    python -m sleep2.askonce.requests_gen       # Sonnet: requests.jsonl (days 1-7), asserts the leakage rule
    python -m sleep2.askonce.phrasings          # Haiku: answers, corrections, chosen questions, fact paraphrases, general prompts
Spend is appended to `data/spend.json` (batch price = 50% of list).

## 2. Job 1 (Kaggle, 1 GPU used): day logs + arm P
    python -m sleep2.askonce.kaggle.build_job --job 1 --out /tmp/kern1
    kaggle kernels push -p /tmp/kern1 --accelerator NvidiaTeslaT4
    kaggle kernels status thegreatergood/askonce-job1 ; kaggle kernels output thegreatergood/askonce-job1 -p /tmp/job1_out
Check output FILES (`out/job1/diary/day5.jsonl`, `results/P_1.json`, `status.json -> expected_files`), not return codes.

## 3. Container steps between the jobs
    python -m sleep2.askonce.tagger /tmp/job1_out/job1/diary /tmp/tags.jsonl [--haiku]     # rule pass (+ Haiku Batches pass)
    python -m sleep2.askonce.report_tagger /tmp/tags.jsonl /tmp/job1_out/job1/oracle /tmp/tagger_report.json   # precision/recall vs the oracle
    python -m sleep2.askonce.build_night_data --diary /tmp/job1_out/job1/diary --tags /tmp/tags.jsonl --out /tmp/nightdata   # needs HF access for the K2 tokenizer
    cmp /tmp/nightdata/eval_inputs.jsonl /tmp/job1_out/job1/nightdata_job1/eval_inputs.jsonl     # must be identical (P and trained arms see the same prompts)
`build_night_data` asserts the token-pass ledger (arms equal within 5%) and prints events per night.
STEP 0 gate (real gateway logs, 7+ days): run `tagger` on them and hand-check 100 turns before any adoption decision; not part of this harness.

## 4. Timing pilot, then job 2
    python -m sleep2.askonce.kaggle.build_job --job 2 --pilot --nightdata /tmp/nightdata --out /tmp/kern2p   # night 1 of A+ seed 1 only
    (push; read job2/pilot_seed1.json -> projection.night_seconds, suggested_night_scale)
If a night takes more than 9 minutes: rebuild the night files with `ASKONCE_NIGHT_SCALE=<suggested> ... build_night_data` (shrinks every arm equally) and
pass `--night-scale <suggested>`; `--scale` shrinks the eval sets, `--opt-steps` the optimizer steps per night (use the same value everywhere).
    python -m sleep2.askonce.kaggle.build_job --job 2 --nightdata /tmp/nightdata --out /tmp/kern2
    kaggle kernels push -p /tmp/kern2 --accelerator NvidiaTeslaT4      # T4 x2 in the kernel settings: lane0 = seed 1 (GPU0), lane1 = seed 2 (GPU1)

## 5. Grade and report (container)
    mkdir -p /tmp/res/results && cp /tmp/job1_out/job1/results/P_1.json /tmp/job2_out/job2/results/*.json /tmp/res/results/
    python -m sleep2.askonce.grade /tmp/res/results /tmp/nightdata/eval_inputs.jsonl /tmp/res        # Haiku ASK->slot map, Sonnet regrade of 60, kappa
    python -m sleep2.askonce.report /tmp/res/results /tmp/res/graded /tmp/res/REPORT.md
