export const meta = {
  name: 'think-block-panel',
  description: 'Six independent thinking-block designs, three lens judges, adversarial attacks on the top three, synthesis and a completeness check',
  phases: [
    { title: 'Design', detail: 'six designers, one angle each' },
    { title: 'Judge', detail: 'three judges score every design on four axes' },
    { title: 'Attack', detail: 'two attackers per top-three design' },
    { title: 'Synthesize', detail: 'final design spec with grafts and pass marks' },
    { title: 'Critic', detail: 'what is missing or unverified' },
  ],
}

const S = '/tmp/claude-0/-home-user-learner/08e723bd-e536-5532-87e4-68b871893d12/scratchpad'
const P = S + '/panel'
const BRIEF = S + '/PANEL-BRIEF.md'
const RULES = `Rules: do not edit any file under /home/user/learner, do not run training, do not use a GPU, do not spend money. ` +
  `You may read files, run read-only git commands (git -C /home/user/learner show/log/ls-tree), and search the web. ` +
  `Label every factual claim shown / suggested / untested. Keep the small card experiments and the village model separate.`

const ANGLES = [
  { key: 'minimal', title: 'Minimal adapter',
    angle: 'MINIMAL ADAPTER. Find the smallest, cheapest trained change that could plausibly beat both "no loop" and "re-run middle" by 3 points while keeping lap count meaningful. Every added part must justify itself. Prefer things that are exactly the base model at init and cheap at decode.' },
  { key: 'board', title: 'Board-centric',
    angle: 'BOARD-CENTRIC. Make the thinking board (K latent scratch slots) the central object: how slots are initialised, how each lap reads the context and the other slots, how it writes, how the frozen backbone later reads the board, and how the board persists across turns of a conversation. Think hard about what computation genuinely needs several read-write laps (multi-hop retrieval, state tracking, plan-then-check).' },
  { key: 'moe', title: 'MoE-of-thought experts',
    angle: 'MoE-OF-THOUGHT EXPERTS. Design the block around routed experts: lap-conditioned or content-routed "thought experts", possibly reusing LFM2.5\'s own pretrained experts (64 per layer, top-4) or a router over several copied backbone blocks. Address expert-selection collapse across laps and what this angle buys that a dense block cannot. If the evidence says this angle is weak, say so and propose its strongest version anyway.' },
  { key: 'refine', title: 'Iterative refinement with a self-check',
    angle: 'ITERATIVE REFINEMENT WITH A SELF-CHECK. Each lap produces a latent draft of the answer (or of the next tool call), checks it (for example by decoding it through the frozen LM head, measuring confidence or consistency with the context, or a learned verifier), and refines the board. Make the self-check signal concrete and trainable, and make lap k+1 depend on what the check found at lap k.' },
  { key: 'halt', title: 'Halting-first',
    angle: 'HALTING-FIRST. Start from WHEN and WHERE to think and HOW LONG: which positions get laps (every token, turn start, before tool calls, at uncertain tokens), the lap budget under the Mac speed rule, whether a learned halt is worth having at all given our own failed halt and the literature, and how to make the score rise with laps. Then design the block that best serves that compute policy.' },
  { key: 'contrarian', title: 'Contrarian / evidence-maximal',
    angle: 'CONTRARIAN / EVIDENCE-MAXIMAL. Ignore the starting recipe and propose the design the latest published evidence (through Oct 2026) most strongly supports for silent thinking on a frozen backbone, even if it departs from "a copy of a middle block + cross-attention board" (for example latent thought tokens fed back through the whole frozen model, a recurrent refiner emitting soft tokens like LRT, or a KV-cache coprocessor like differentiable cache augmentation). It must still think by looping in latent space without writing words.' },
]

const DESIGN_SCHEMA = {
  type: 'object',
  properties: {
    name: { type: 'string' },
    one_line: { type: 'string' },
    pilot_task: { type: 'string', description: 'village or assistant-chats, and why' },
    think_positions: { type: 'string', description: 'where and when laps run' },
    board_shape: { type: 'string' },
    params_pilot_m: { type: 'number', description: 'trainable params at Qwen3.5-0.8B, millions' },
    params_lfm_m: { type: 'number', description: 'added params at LFM2.5, millions' },
    mac_tok_s_2_agents: { type: 'number', description: 'estimated decode tok/s per agent with 2 agents on the Mac' },
    added_ttft_ms_per_turn: { type: 'number' },
    predicted_pilot_gain_vs_best_baseline: { type: 'number', description: 'points on the held-out metric' },
    predicted_lap8_minus_lap1: { type: 'number', description: 'points' },
    self_scores: { type: 'object', properties: { gain: { type: 'number' }, speed: { type: 'number' }, trainability: { type: 'number' }, decoration_risk: { type: 'number' } }, required: ['gain', 'speed', 'trainability', 'decoration_risk'] },
    top_failure_modes: { type: 'array', items: { type: 'string' } },
    file: { type: 'string' },
  },
  required: ['name', 'one_line', 'pilot_task', 'think_positions', 'board_shape', 'mac_tok_s_2_agents', 'predicted_pilot_gain_vs_best_baseline', 'predicted_lap8_minus_lap1', 'self_scores', 'top_failure_modes', 'file'],
}

const SCORE_ITEM = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    gain: { type: 'number' }, speed: { type: 'number' }, trainability: { type: 'number' }, decoration_risk: { type: 'number', description: '10 = loops very unlikely to be decoration' },
    speed_gate_pass: { type: 'boolean', description: 'keeps >= 30 tok/s per agent with 2 agents (as designed, or after an obvious cheap fix)' },
    strongest_point: { type: 'string' }, fatal_or_biggest_flaw: { type: 'string' },
    factual_errors: { type: 'array', items: { type: 'string' } },
  },
  required: ['id', 'gain', 'speed', 'trainability', 'decoration_risk', 'speed_gate_pass', 'strongest_point', 'fatal_or_biggest_flaw'],
}
const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    scores: { type: 'array', items: SCORE_ITEM },
    ranking: { type: 'array', items: { type: 'string' }, description: 'design ids best first' },
    ideas_worth_grafting: { type: 'array', items: { type: 'string' } },
    rationale: { type: 'string' },
  },
  required: ['scores', 'ranking', 'ideas_worth_grafting', 'rationale'],
}
const ATTACK_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['survives', 'wounded', 'dead'] },
    fatal: { type: 'array', items: { type: 'string' } },
    serious: { type: 'array', items: { type: 'string' } },
    fixes: { type: 'array', items: { type: 'string' } },
    kill_experiment: { type: 'string', description: 'the cheapest experiment that would show the attack is right' },
    probability_passes_pilot: { type: 'number', description: '0-1: beats A and B by >= 3 points AND score rises with laps' },
  },
  required: ['verdict', 'fatal', 'serious', 'fixes', 'kill_experiment', 'probability_passes_pilot'],
}

const W = { gain: 0.35, speed: 0.20, trainability: 0.20, decoration_risk: 0.25 }

phase('Design')
const designs = await parallel(ANGLES.map((a, i) => () => agent(
  `You are designer D${i + 1} on an independent design panel. Read the brief at ${BRIEF} first, then the research notes it lists ` +
  `(R4-frozen-workspace.md may still be being written; read it if present). Your angle: ${a.angle}\n\n` +
  `Work independently: do not look at other designers' files in ${P}. Check the code you rely on (the stage-1 Qwen3.5 runner and the Loop-1L ` +
  `code paths named in the brief) so that your mechanism is implementable in HF transformers 5.20.2 for Qwen3.5-0.8B (layer types, cache, masks) ` +
  `and portable to LFM2.5-24B-A2B. Do the arithmetic for parameter count and Mac speed explicitly.\n\n` +
  `Write your design (the 8 sections the brief asks for, 900-1,600 words) to ${P}/design-${a.key}.md, then return the structured summary ` +
  `with file = that path. ${RULES}`,
  { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA, effort: 'high' })))

const ok = designs.map((d, i) => d ? { ...d, id: `D${i + 1}`, key: ANGLES[i].key, title: ANGLES[i].title } : null).filter(Boolean)
log(`designs returned: ${ok.map(d => `${d.id} ${d.key} "${d.name}"`).join('; ')}`)
const roster = ok.map(d => `${d.id} (${d.title}): "${d.name}", file ${d.file}`).join('\n')

phase('Judge')
const LENSES = [
  { key: 'evidence', lens: 'an empirical ML researcher: weigh published evidence and this repo\'s own measured results most; punish claims that contradict them' },
  { key: 'systems', lens: 'a systems and training engineer: weigh Mac M1 Pro decode cost (bandwidth-bound, 4-bit MLX, MoE expert reads), memory, implementability in HF transformers for Qwen3.5 (Gated DeltaNet + attention) and LFM2.5 (short conv + GQA + MoE), and training stability from a frozen backbone' },
  { key: 'skeptic', lens: 'a skeptic whose job is to find designs whose loops will be decoration or whose gain will vanish against a strong LoRA baseline; weigh the stage-1 tie, the state-lab null results, Project Newt and the Loop-1L seed-0 numbers' },
]
const judgements = await parallel(LENSES.map(l => () => agent(
  `You are a judge with this lens: ${l.lens}. Read the brief at ${BRIEF}, the research notes it lists, and ALL of these designs:\n${roster}\n\n` +
  `Score every design 1-10 on: gain (expected gain on the pilot and on tau2), speed (Mac decode with 2 agents and per-turn latency; ` +
  `10 = no measurable cost), trainability (from a frozen backbone, fits 16 GB at 0.8B, stable), decoration_risk (10 = the laps are very ` +
  `unlikely to be decoration and the design makes that measurable). Set speed_gate_pass. Check each design's arithmetic and factual claims ` +
  `against the code and the notes and list errors. Rank them. Name ideas from any design worth grafting onto the winner. ${RULES}`,
  { label: `judge:${l.key}`, phase: 'Judge', schema: JUDGE_SCHEMA, effort: 'high' })))

const js = judgements.filter(Boolean)
const agg = ok.map(d => {
  const rows = js.map(j => j.scores.find(s => s.id === d.id)).filter(Boolean)
  const mean = k => rows.reduce((a, r) => a + r[k], 0) / Math.max(rows.length, 1)
  const axes = { gain: mean('gain'), speed: mean('speed'), trainability: mean('trainability'), decoration_risk: mean('decoration_risk') }
  const total = Object.keys(W).reduce((a, k) => a + W[k] * axes[k], 0)
  const gate = rows.filter(r => r.speed_gate_pass).length * 2 > rows.length
  return { id: d.id, key: d.key, name: d.name, file: d.file, axes, total, speed_gate: gate, n_judges: rows.length,
           flaws: rows.map(r => r.fatal_or_biggest_flaw), errors: rows.flatMap(r => r.factual_errors || []) }
}).sort((a, b) => b.total - a.total)
log('scores: ' + agg.map(a => `${a.id} ${a.key} ${a.total.toFixed(2)}${a.speed_gate ? '' : ' (speed gate FAIL)'}`).join(' | '))
const borda = {}
js.forEach(j => j.ranking.forEach((id, r) => { borda[id] = (borda[id] || 0) + (ok.length - r) }))
agg.forEach(a => { a.borda = borda[a.id] || 0 })
log('holistic Borda (judges\' own rankings): ' + Object.entries(borda).sort((x, y) => y[1] - x[1]).map(([k, v]) => `${k}=${v}`).join(' '))
const eligible = agg.filter(a => a.speed_gate)
const pool = eligible.length >= 3 ? eligible : agg
const top2 = pool.slice(0, 3)
const bordaTop = [...pool].sort((x, y) => y.borda - x.borda)[0]
if (bordaTop && !top2.find(t => t.id === bordaTop.id)) top2.push(bordaTop)
log('attacking: ' + top2.map(t => t.id).join(', '))

phase('Attack')
const ATTACKS = [
  { key: 'pilot', lens: 'PILOT KILLER. Argue that this design will NOT beat both "no loop" (A) and "re-run middle" (B) by >= 3 points on the Qwen3.5-0.8B pilot and/or that its score will NOT rise with lap count (the laps are decoration, the board is ignored, the gate stays shut, all work happens in lap 1, gains come from extra parameters). Use this repo\'s measured results (stage-1 tie, state-lab nulls and noise, Loop-1L seed 0, v1 2.3-of-8 loops) and the literature (Project Newt, frozen-backbone caps).' },
  { key: 'scale', lens: 'SCALE-UP KILLER. Argue that this design will fail on LFM2.5-24B-A2B and tau2 retail on the Mac: decode speed with 2 agents, per-turn latency over a multi-turn tau2 episode, MoE routing and short-conv state under looping, memory, distillation from the backbone\'s own thinking-ON answers (long verbose traces), RL via JOLT+ with a Sonnet judge (latent policies collapse), and implementation risk in HF transformers / mlx-lm.' },
]
const attacks = await pipeline(top2, d => parallel(ATTACKS.map(a => () => agent(
  `You are an adversarial reviewer. ${a.lens}\n\nTarget design ${d.id} "${d.name}": read ${d.file}. Also read the brief ${BRIEF} and the ` +
  `research notes it lists. Judges' biggest flaws for it: ${JSON.stringify(d.flaws)}. Be concrete and quantitative; separate fatal flaws from ` +
  `serious ones; for each, propose the fix that would survive it, and give the single cheapest experiment that would prove your attack right. ${RULES}`,
  { label: `attack:${a.key}:${d.key}`, phase: 'Attack', schema: ATTACK_SCHEMA, effort: 'xhigh' })))
  .then(rs => ({ id: d.id, key: d.key, name: d.name, file: d.file, attacks: rs.filter(Boolean).map((r, i) => ({ lens: ATTACKS[i].key, ...r })) })))

phase('Synthesize')
const synthesis = await agent(
  `You are the panel's synthesizer. Inputs:\n- Brief: ${BRIEF} and the research notes it lists.\n- Designs:\n${roster}\n` +
  `- Aggregated judge scores (weights gain .35, speed .20, trainability .20, decoration_risk .25): ${JSON.stringify(agg)}\n` +
  `- Judges' grafting ideas: ${JSON.stringify(js.map(j => j.ideas_worth_grafting))}\n- Judges' rationales: ${JSON.stringify(js.map(j => j.rationale))}\n` +
  `- Holistic Borda points from the judges' own rankings: ${JSON.stringify(borda)}\n- Attacks on the top designs: ${JSON.stringify(attacks)}\n\n` +
  `Pick the final design among the attacked ones. The weighted score and the judges' holistic rankings disagree (weighted favours speed), ` +
  `so weigh both, plus how each design survived its attacks and each attacker's probability_passes_pilot; graft fixes from its attacks and ` +
  `the best ideas from the others. Write ${P}/FINAL-DESIGN.md (2,000-3,500 words) with:\n` +
  `1. Decision and why it beat each other design (one paragraph per loser, citing scores and attacks).\n` +
  `2. Exact spec for the Qwen3.5-0.8B pilot implementation: which pilot task, where the block attaches (layer indices), shapes, init (what is ` +
  `copied, what is zero-init), how the backbone reads the board, when laps run, lap sampling in training, losses, optimizer groups and learning ` +
  `rates, what is frozen, eval lap counts, and the lesions/controls (zeroed board, shuffled board across examples, 1-lap, any trained-at-1-lap ` +
  `control) that separate "the loop works" from "extra parameters".\n3. Implementation notes for HF transformers 5.20.2 Qwen3.5 (cache, masks, ` +
  `position ids for slots, gradient checkpointing, memory at 16 GB) and the CPU equivalence tests the code must pass.\n` +
  `4. Proposed preregistered pass marks: PASS = block beats both A and B by >= 3 points AND the score rises with lap count; define "rises" ` +
  `precisely (lap counts, per-seed rule), the "wrong if" result, and a cheap futility stop after the first seed.\n` +
  `5. Scale-up plan to LFM2.5-24B-A2B and tau2 retail on the Mac: attach points, distillation target from thinking-ON rollouts (and what to ` +
  `measure first), RL via JOLT+ with Sonnet 5.5 reward, Mac speed check, pass marks.\n6. Open risks and every claim still to verify against code.\n` +
  `Then return a 300-word summary. ${RULES}`,
  { label: 'synthesize', phase: 'Synthesize', effort: 'xhigh' })

phase('Critic')
const critic = await agent(
  `You are a completeness critic. Read ${P}/FINAL-DESIGN.md, the brief ${BRIEF}, the research notes, and the design files in ${P}. ` +
  `List what is missing, wrong, or unverified: claims that contradict the repo's code or results, arithmetic errors, controls not included, ` +
  `ways the pilot could pass for the wrong reason (leakage, parameter count, compute), ways it could fail for a boring reason (bug, ` +
  `gate never opens, learning rate), anything that would make the Mac speed rule fail, and anything that would require opening the sealed ` +
  `village test (forbidden). Write ${P}/CRITIC.md and return the list, most important first. ${RULES}`,
  { label: 'critic', phase: 'Critic', effort: 'high' })

return { designs: ok.map(d => ({ id: d.id, key: d.key, name: d.name, one_line: d.one_line, file: d.file, mac_tok_s_2_agents: d.mac_tok_s_2_agents,
  predicted_pilot_gain_vs_best_baseline: d.predicted_pilot_gain_vs_best_baseline, predicted_lap8_minus_lap1: d.predicted_lap8_minus_lap1 })),
  scores: agg, top2: top2.map(t => t.id), attacks, synthesis, critic }
