export const meta = {
  name: 'custom-io-design',
  description: 'Opus design panel: 6 custom reader/reasoner/talker designs, 3 judges, synthesis into a test plan with marks',
  phases: [
    { title: 'Design', detail: '6 Opus designers, distinct angles' },
    { title: 'Judge', detail: '3 Opus judges, distinct lenses' },
    { title: 'Synthesize', detail: 'rank, pick 2-3, test plan with marks' },
  ],
}

const R = '/home/user/learner/custom_io/research'
const CONTEXT = `You are on the design panel for "Premonition", a small looped-reasoner model project (repo /home/user/learner, branch claude/custom-reader-talker-4x309r; do not modify the repo, do not commit, do not train, do not rent GPUs; never call mcp__hearthbot__ tools; return your answer as your final output).

THE PROBLEM. Today the model is a "sandwich": a frozen LFM2.5-1.2B LM reads the question, a ~9M looped latent core thinks, and the same frozen 1.2B writes the answer. Evidence shows the 1.2B does the reasoning (swapping in another question's core output left scores unchanged on new kinds; the core carries only a per-family "mode" signal; a talker that sees only the core collapses on unseen kinds; a 350M LM swap drops English to 66%).

WHAT BEN (the owner, a high-school senior) WANTS, in his words: "find out ways to have the model consume information in ways that would be better than the two massive LLMs that sandwich our reasoner... the LLM is doing most of the work in reasoning. We have to get around that." His answers: (1) "ideally, nothing pretrained. If the difference is really measurable though, go with [a small pretrained reader under ~100M]. I'd rather something completely different though than some transformer talker and reader if that would work. Something custom for this model." (2) size limit: he doesn't know (he counts any borrowed LM in the size). (3) success = "when the end to end model with the reasoner is able to beat similarly sized models measurably". His earlier design note: the talker should translate the reasoner's final state into words, not do its own reasoning. Long-term north star: beat Minecraft like a person; skills and critical thinking first; learn from few examples.

FACTS YOU MUST READ FIRST (files):
- ${R}/code-map.md (today's sandwich, module sizes, file:line)
- ${R}/results-digest.md (everything tried on readers/talkers/core, with numbers; do not re-propose what already failed without saying what is different)
- ${R}/data.md (the skills benchmark: 34 train families, 200k rows, dev splits in_dist/answer/frame/vocab/variant/family, answer types, multi-step families)
- ${R}/baselines.md (similar-size open LMs, bare 1.2B numbers)
- ${R}/papers.md (verified papers from 4 angles + syntheses) and ${R}/critic.md
- /home/user/learner/custom_io/CALIBRATION.md (NEW, shown, one seed each: plain causal char transformers trained FROM SCRATCH on the 200k rows reach in_dist 73.6% (3.2M) and 76.0% (10.8M) at 24k updates x batch 256 (14-22 min on a shared RTX 5090), vs 74.6% for the 1.2B sandwich; variant split only ~20%; held-out families 0-4%; weakest families chain_ops 2-8%, state_update 8-10%, var_chain 12-20%, table_lookup 22-28%, chain_story2 18-28%.)
- /home/user/learner/custom_io/README.md, custom_io/models/base.py, custom_io/models/plain_tf.py, custom_io/data.py (the test harness every design must plug into: char vocab of 108 ids incl. PAD/BOS/EOS/SEP/UNK and 8 answer-slot query ids Q0..Q7; batch = prompt_ids [B,T<=208], prompt_mask, ans_ids [B,9] (<=8 answer chars + EOS); model.loss(batch), model.generate(batch, lesion), LESIONS 'shuffle_state' / 'zero_state' / 'loops:K'; rows carry 'steps' (worked steps text) usable as extra supervision).

MORE SHOWN FACTS: the sandwich's core carries nothing row-specific on the skills set: replacing its output with another same-family row's gives 74.4% vs 74.6% intact (data.md section 6). Sandwich on the four chain families: 22.5%; bare 1.2B direct 5%, bare 1.2B writing worked steps first 71%. A bigger dev build with 200 rows per family-cell exists (same train hash): use it for confirmation (5 chain families x 200 rows). The dev family split has answers up to 12 chars (harness answer cap is 8 chars + EOS; can be raised).

TEST BUDGET. About $3 of rented RTX 5090 time in total for all screening and confirmation, so each run must finish 24k updates at batch 256 in <= ~25 min while sharing the GPU with 2-3 other runs (the 10.8M plain transformer did 18 updates/s shared 2-way). Confirmation of a winner needs 6 paired seeds. Same-size comparison arms available: plain_tf at matched parameters, plain_tf looped (n_loops) at matched compute, and fine-tuned small open LMs (see baselines.md).`

const ANGLES = [
  { key: 'latent-reread', brief: 'A looped latent reasoner that RE-READS a shallow encoding of the input every loop (Perceiver / Perceiver IO style latent bottleneck: a small set of latent slots cross-attends to per-character or per-word features each round, then self-attends/updates; weights shared across rounds). The reader is deliberately shallow (embeddings + at most local convolution, no global mixing), so cross-token reasoning can only happen in the loop. The talker reads ONLY the final latents (e.g. answer-slot queries -> characters, plus a copy pointer into the input).' },
  { key: 'recursive-refine', brief: 'A tiny recursive model in the style of HRM / TRM: a latent state and an answer draft are refined jointly over many recursions with deep supervision, so the "talker" is just a readout of an answer that the reasoner itself iteratively improves. Work out how to adapt grid-style TRM to text in, short text out (prompt up to 208 chars, answer up to 8 chars).' },
  { key: 'workspace-typed', brief: 'A structured workspace: the reader is a fixed, non-learned segmentation into words and numbers, each word encoded by a small char-CNN (handles unseen names/made-up words by spelling) and each number by a value-aware digit encoding; the reasoner loops over this set of word slots (binding, tracking, comparing); the talker is a set of TYPED answer heads that see only the reasoner state: pointer to a prompt word (copy), number written digit by digit, label class (yes/no/A/B/true/false), or a short char decoder for new words, with a learned type gate.' },
  { key: 'program-executor', brief: 'A neuro-symbolic design: the reasoner emits a short program (operations over workspace slots: add, sub, mul, div, compare, lookup, copy, count, ...) that an exact deterministic executor runs; arithmetic is therefore never done by a neural net. Training uses the rows\' "steps" field (worked solutions with a op b = c lines) as program supervision where it parses, and answer-only supervision elsewhere. Say clearly which families this covers and how non-arithmetic families are handled, and keep the "reasoner does the reasoning" property (the executor only calculates).' },
  { key: 'streaming-ponder', brief: 'No attention anywhere in the reader or talker: the reasoner core itself reads the prompt as a stream (character or word chunks) through a recurrent / state-space update (e.g. a gated RNN, minGRU, xLSTM/Mamba-like cell, or the looped core applied per chunk), then "ponders" for K extra steps with no input (adaptive computation / halting), and a small recurrent talker writes the answer from the final state only, with no access to the prompt. Compare against attention designs honestly: binding and lookup over ~200 chars are the known weakness of recurrent readers.' },
  { key: 'wildcard', brief: 'Your choice: the design you believe has the BEST chance of making a small from-scratch reasoner beat same-size plain transformers on the weak multi-step families and on the variant split, while keeping the talker a translator of the final state. Candidates to consider (pick or combine, or invent): step-supervised loops (each loop round is trained to hold the next intermediate result from the "steps" field, internalising chain-of-thought into the loop), equilibrium / fixed-point reasoners, neural cellular automata over the char grid, two-timescale loops, or a hybrid where a small PRETRAINED reader (<100M, Ben\'s fallback option c) is A/B-tested against a from-scratch one with everything else fixed.' },
]

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    name: { type: 'string' },
    one_line: { type: 'string' },
    reader: { type: 'string', description: 'exact mechanism, shapes, what it can and cannot compute' },
    reasoner: { type: 'string', description: 'exact mechanism, loops, state shape, weight sharing, halting' },
    talker: { type: 'string', description: 'exact mechanism; confirm it sees only the reasoner final state, or say what else it sees and why' },
    why_reasoner_must_reason: { type: 'string', description: 'the bottleneck argument, and what could still leak around it' },
    params: { type: 'string', description: 'parameter counts at a ~3M and a ~10M setting (breakdown by part) and FLOPs per example relative to plain_tf of the same params' },
    pretrained_parts: { type: 'string' },
    training: { type: 'string', description: 'losses (incl. any deep supervision or steps supervision), optimiser, updates, batch, lr; anything needed beyond the harness' },
    predictions: { type: 'string', description: 'numeric predictions vs plain_tf at matched params (24k updates): in_dist, variant, multi-step in_dist, worst families, held-out families; with honest uncertainty; label shown/suggested/untested' },
    evidence: { type: 'string', description: 'papers (arXiv ids from papers.md) and repo results that support or contradict this design' },
    lesions: { type: 'string', description: 'lesions that prove the reasoner carries the answer, with expected collapse sizes' },
    decisive_test: { type: 'string', description: 'the single cheapest test that would decide it, with pass marks and the result that proves it wrong' },
    implementation: { type: 'string', description: 'class and file names in custom_io/models, key pseudo-code, est. lines of code, gotchas (e.g. leaks of the prompt into the talker)' },
    risks: { type: 'string' },
    english_and_minecraft_path: { type: 'string', description: '2-4 sentences: how it extends to human-written English later and to an agent that plays Minecraft' },
  },
  required: ['name', 'one_line', 'reader', 'reasoner', 'talker', 'why_reasoner_must_reason', 'params', 'pretrained_parts', 'training', 'predictions', 'evidence', 'lesions', 'decisive_test', 'implementation', 'risks', 'english_and_minecraft_path'],
}

phase('Design')
const designs = (await parallel(ANGLES.map(a => () => agent(`${CONTEXT}

YOUR ANGLE: ${a.brief}

Produce ONE complete, concrete design from this angle that fits the harness and budget. Be specific enough that a coder could build it in a few hours (shapes, layer counts, losses). Be honest: if your angle is likely to lose to a same-size plain transformer, say so and say where it could still win. Prefer simple, testable designs over elaborate ones. Label each claim shown / suggested / untested.`, { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA }).then(d => d && ({ key: a.key, ...d }))))).filter(Boolean)
log(`${designs.length} designs: ${designs.map(d => d.name).join(' | ')}`)

const LENSES = [
  { key: 'evidence', text: 'EXPECTED GAIN AND EVIDENCE. How likely is each design to beat a same-size plain char transformer (matched params AND matched compute) trained on the same data for the same updates, especially on the variant split, the weak multi-step families and the held-out families? Be skeptical: weigh the papers and repo results, and note where a claimed advantage is really just "more compute" or "more supervision" that a baseline could also get.' },
  { key: 'ben-fit', text: 'FIT WITH BEN\'S GOALS. Nothing pretrained (or a measured case for a small one); something custom rather than a transformer reader/talker; the reasoner provably does the reasoning (lesions); the talker only translates the final state; beats similarly sized models; a believable path to human English and to a Minecraft-playing agent; skills and learning from few examples first.' },
  { key: 'testability', text: 'TESTABILITY, COST AND RISK. Can Sonnet coders build it on the harness in a few hours with low bug risk? Will 24k updates at batch 256 finish in <= 25 min on a shared RTX 5090? Are the lesions clean? What are the leak or bug risks (e.g. the talker peeking at the prompt, executor doing the reasoning, supervision unavailable for most families)? Is the decisive test decisive?' },
]
const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    scores: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, score: { type: 'number', description: '1-10' }, best_point: { type: 'string' }, critical_flaw: { type: 'string' }, fix: { type: 'string' } },
      required: ['name', 'score', 'best_point', 'critical_flaw'] } },
    top3: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string', description: '<= 300 words: cross-design observations, ideas worth grafting' },
  },
  required: ['scores', 'top3', 'notes'],
}
phase('Judge')
const designText = JSON.stringify(designs, null, 1)
const judgments = (await parallel(LENSES.map(l => () => agent(`${CONTEXT}

You are a judge. Score EVERY design below from 1 to 10 under this lens only:
${l.text}

Check claims against the files listed above where they matter (e.g. family answer types in data.md, past failures in results-digest.md). Designs:
${designText}`, { label: `judge:${l.key}`, phase: 'Judge', schema: JUDGE_SCHEMA }).then(j => j && ({ lens: l.key, ...j }))))).filter(Boolean)

phase('Synthesize')
const synthesis = await agent(`${CONTEXT}

You are the synthesis lead. Below are ${designs.length} designs and ${judgments.length} judge reports (lenses: evidence, Ben-fit, testability). Produce a markdown document (<= 2200 words) with:
1. A ranked table of all designs: name, one line, total and per-lens scores, whole-model size, verdict (test now / later / drop) with one reason.
2. The 2 or 3 designs to TEST NOW (diverse mechanisms, so the result teaches something either way), each as a final merged spec that grafts the judges' fixes: reader, reasoner, talker, sizes (one setting matched to the 3.2M plain_tf and, if cheap, one to the 10.8M), losses, updates/batch/lr, lesions. Keep each buildable in a few hours on the harness.
3. A TEST PLAN in two stages, built so one change is tested at a time:
   - Screen: 2 seeds per arm, 24k updates, batch 256, arms = each chosen design + plain_tf at matched params + plain_tf looped at matched compute; say which arms share which seeds.
   - Confirm: 6 paired seeds for any design that clears the screen, plus the similar-size open-LM baseline(s) fine-tuned on the same rows with the same updates (name exact HF ids from baselines.md, and a few-shot run without fine-tuning).
   - Marks FIXED IN ADVANCE: primary metric (pooled exact match over in_dist+answer+frame+vocab+variant, and separately the multi-step families and the variant split), the paired-difference statistic and 95% interval across seeds, PASS / FAIL thresholds, the lesion marks that prove the reasoner carries the answer (shuffle_state collapse, loops:0/1 collapse on multi-step), and the result that would prove each design wrong. Use realistic thresholds given one-seed spread is unknown (a noise job is measuring it; leave a placeholder the lead fills from it).
4. Cost estimate in GPU-minutes and dollars ($0.45/hr box) for screen and confirm.
5. What to do if all designs fail to beat plain_tf (the fallback), and where option (c), a small pretrained reader, would be tested.
6. A plain-language summary for Ben (a high-school senior), <= 150 words.

DESIGNS:
${designText}

JUDGMENTS:
${JSON.stringify(judgments, null, 1)}`, { label: 'synthesis', phase: 'Synthesize' })

return { designs, judgments, synthesis }
