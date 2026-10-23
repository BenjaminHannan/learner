# wordprob-v1: verified arithmetic word-problem corpus generator

Answers never come from an LLM. The Claude API writes only TEMPLATES (text with `{a}`-style numeric slots, slot ranges,
an answer expression, and ordered one-operation steps). Code then draws slot values, evaluates with an
`ast`-whitelisted interpreter (no `eval`; only `+ - * //` on ints, slot names, `s1..s3`), and builds the scratchpad.

Scratchpad format: `37 + 46 = 83. 83 - 9 = 74. Answer: 74` (`/` in a step means exact integer division).

## Files
- `core.py` validation, safe evaluator, instantiation, `Acceptor` (schema + valid-rate + compose + leak + near-dup).
- `gen_templates.py` concurrent, spend-capped ($25 hard stop, price assumed $3/M in, $15/M out) template generation. Needs env `LEARNER_ANTHROPIC_API_KEY` (never logged).
- `build_corpus.py` replays candidates through the Acceptor, splits by template, instantiates ~100 per template, writes the corpus and `MANIFEST.json` (sha256 of each file, counts, spend, rejections), verifying the copy to the output mount.
- `test_wordprob.py` run `python -m pytest scripts/wordprob`.

## Template acceptance rules
every slot in the text and in a step; no digits outside slots; slot ranges lo>=2, hi<=5000; 1-4 steps, each a single binary op; each
intermediate used later; >=90% of 50 draws valid (nonneg, integer, <=100000, answer>=1); answer expression == last step on 20 draws;
no 8-gram overlap (digits, slots and capitalised names masked) with the 1965 old-corpus questions
(`artifacts/sol-cloud-capability-plan-20260930/corpus1965-v1/QUESTION-COUNT-PACKET-v1.jsonl`); word-3-gram Jaccard <= 0.7 against earlier accepted templates; >=30 distinct instances available.

## Splits
By template: sha256(salt|template_id) % 100: <80 train, <90 dev, else heldout_template. Structural holdout: all 4-step templates of 2 randomly
chosen topics (seeded) go only to `heldout_structure`. Instances of a template stay in one split.

## Run
    python scripts/wordprob/gen_templates.py --out WORK --calls 200 --workers 8
    python scripts/wordprob/build_corpus.py --work WORK --out /mnt/project-files/data/wordprob-v1/
- `audit_llm.py` spot audit: model solves N random corpus questions at temperature 0, reports agreement (audit only; never a source of answers).
