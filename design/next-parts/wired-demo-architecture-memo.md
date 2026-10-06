# Wired-up CPU demo: architecture memo (design only, 2026-10-03)

**What this is:** a design for a small Python package (`premonition/wired_demo/`) that runs reader -> looped core -> tool calls -> notebook -> sleep night end to end on CPU. It is a **plumbing demo**. It proves only that the parts fit: interfaces, data flow, gradients, checkpoint round-trip, and a sleep step that changes weights. It must never be quoted as evidence that Premonition reads, reasons, calculates or learns. Every module docstring, CLI banner and checkpoint carries `claims: "plumbing only; toy data; not an eval"`.

Nothing here was run except a parameter count and a CPU timing check (section 1.10). Labels: **shown** = I checked it in code or ran it; **suggested** = reasoned, not run; **untested** = open.

Sources read: `scripts/sol_spatial_poc_ordered_v2.py`, `sol_spatial_attention_core.py`, `claude_fewex_net.py` (core), `sol_translator_grounding_v6.py` (reader + training loop), `sol_translator_english_v6.py` (`StatePrefix`, `FrozenEnglishDecoder`), `sol_translator_decoder.py`, `sol_stop_adapter.py` (`FinalLatent`), `sol_spatial_poc_ordered_train_api_v2.py` (`fixed4_training`), the reasoner design (knhc46 §3, §6), notebook-learning (u7gaif), sleep-replay (ols4wp), `premonition/audio/adapter.py` (qsg2yc), `calculator_tools.py` (critical-thinking-data-128-outputs).

---

## 1. Components and exact interfaces

Conventions: B = batch, T = LM tokens, N = workspace vectors, R = 8 registers, C = registry candidates (≤ 11), S = notebook slots (≤ 8). All trainable tensors are float32. Ids are int64. Masks are bool. The only width that must match the real model is d = 256 (core width, Workspace contract).

### 1.1 Workspace (contract, shared by every producer)
Matches the vision `workspace.py` / audio adapter layout (shown in `premonition/audio/adapter.py`):
```
@dataclass Workspace:
  tokens  float32 [B,N,256]   rows with valid=False are exactly 0; producers add NO role/modality tag
  segment int64   [B,N,2]     (role id, modality id) from SEGMENTS
  coords  float32 [B,N,3]     (row, col, time); -1 in a column = "no position" (learned null code, not offset 0)
  valid   bool    [B,N]       right padding only
  provenance: list[list[dict]]  host metadata (source string, char span, slot id); NEVER a model input
SEGMENTS = {question:0, notebook:1, example:2, tool_result:3, register:4, text:5, image:6, audio:7}
```
Text coords: question `(0, tok_idx, -1)`; notebook `(slot_idx, tok_idx, -1)` (row = entry, so entries stay separate); tool_result `(call_idx, tok_idx, -1)`. `Workspace.cat(a, b)` concatenates along N and re-pads; `validate()` checks dtypes, shapes, zero padding, role ∈ {0..3} for producer rows (register role is core-internal). Vision/audio plug in later by emitting the same dataclass with modality 6/7; nothing else changes.

### 1.2 TinyLM stand-in (frozen) — `tinylm.py`
Labelled `STAND-IN for frozen LFM2.5-1.2B` in class name, docstring and checkpoint.
- Tokenizer: word-level over the toy vocabulary plus single digits, `/`, `-`, `.`, `?`, specials `<bos> <eos> <pad> <unk>`; V ≤ 256. `encode(text) -> (ids: list[int], offsets: list[(start,end)])`, `decode(ids) -> str`. Offsets are required because the calculator registry maps literals to token indices (as in the real `build_registry`).
- Model: causal pre-LN transformer, D_lm = 128, 2 layers, 4 heads, MLP 512, tied head, max T = 64. 0.43M params (shown, count).
- Interface (identical method names used for the real LM wrapper):
  - `embed(ids int64 [B,T]) -> float32 [B,T,D_lm]`
  - `hidden(ids [B,T], attn_mask bool [B,T], layer:int=-1) -> float32 [B,T,D_lm]` (contextual states)
  - `logits_from_embeds(inputs_embeds [B,T',D_lm], attn_mask [B,T']) -> float32 [B,T',V]`
  - attributes `d_model, vocab_size, bos_id, eos_id, pad_id`; `fingerprint() -> sha256 of state_dict bytes`.
- Frozen: built, then given a one-off "pretrain" of ~300 CPU steps of next-token loss on toy-world sentences (so the prefix route has a language to steer; a random frozen LM would make the talker test meaningless), saved as a fixture, then `requires_grad_(False)` and `eval()` for good. Gradients still flow *through* it to the prefixes.
- Real swap: `LFMBackbone` implements the same five members over HF `AutoModelForCausalLM` (`get_input_embeddings()`, `output_hidden_states=True`, `inputs_embeds=`), bf16, D_lm = LFM config `hidden_size` (check the config; I did not open it). Only `reader.lm_width` and `prefix.lm_width` change. The tokenizer offsets come from the HF fast tokenizer (`return_offsets_mapping=True`, as `calculator_tools.build_registry` already requires).

### 1.3 ContextualReader — `reader.py`
Same block as `HumanInputProjection` (v6, shown): `LayerNorm(D_lm) -> Linear(D_lm,32) -> GELU -> Linear(32,256)`, applied per token, output zeroed where invalid. 12.8k params.
- `forward(lm_states float32 [B,T,D_lm], valid [B,T], role:str, coord_rows int|[B]) -> Workspace` with N = T.
- Input is `lm.hidden(ids, mask)` (contextual), not `lm.embed(ids)`. The v6 code in this repo feeds input embeddings; CURRENT.json names a `contextual` arm. That "contextual = LM hidden states" is my reading (**suggested**); a flag `source="hidden"|"embed"` keeps both.
- Called once per segment (question, each notebook entry, each tool result) so segments do not see each other inside the LM; mixing happens only in the core.

### 1.4 LatentCore — `core.py`
Follows `Net.step` (shown): `z = h + e; z = blocks(z); h = LN(z)`, h0 = 0, the same 2 blocks reused every loop.
- Constructor: `LatentCore(d=256, heads=8, mlp=512, blocks=2, registers=8, n_loops=4)`. 1.05M params (shown, count). Dense MLP (real core: MoE 8 experts / top-2; see decision D3).
- Input assembly `e = ws.tokens + seg_emb[role] + seg_emb[modality] + pos(coords)`; `seg_emb = Embedding(8,256)` zero-init; `pos` = sinusoidal code of row (128 dims) and col (128 dims), learned null vector where a column is -1. Then R = 8 learned register vectors are appended with role = register. So the core sees `[B, N+8, 256]`.
- Attention: bidirectional, key padding mask from `valid` (registers always valid).
- `forward(ws: Workspace, n_loops:int|None=None) -> CoreOut(tokens float32 [B,N,256], registers float32 [B,8,256], valid [B,N])`. Loss is taken after the last loop only, like `fixed4_training` (shown). `n_loops` is configurable at call time; training uses 4.
- Notebook is read only through this attention: notebook entries are Workspace rows with role = notebook.

### 1.5 Action heads — `heads.py`
Register r has a fixed job (decision D5): reg0 → kind and arith op; reg1 → ptr_a; reg2 → ptr_b; reg3 → slot; reg4 → span start; reg5 → span end; regs 6-7 free. All 8 go to the prefix adapter.
- `kind = Linear(256,4)(reg0)` → logits [B,4] over {CALC, NOTE_WRITE, ANSWER, DONE}
- `arith = Linear(256,4)(reg0)` → logits [B,4] over {ADD, SUB, MUL, DIV}
- Pointer scores: `score[b,c] = <Wq_f reg_f, Wk cand[b,c]> / 16`, masked to -inf where the candidate is absent.
  - candidates for ptr_a, ptr_b: registry entries, `cand = mean of core token states over the entry's token indices` → [B,C,256], C ≤ 8 literals + 3 results
  - slot: notebook entries (mean of their tokens) plus a learned NEW vector → [B,S+1,256]
  - span start/end: question token states → [B,Tq,256]
- `ActionLogits`: kind [B,4], arith [B,4], ptr_a [B,C], ptr_b [B,C], slot [B,S+1], start [B,Tq], end [B,Tq]. Heads total 0.40M (shown, count).
- Decoding is greedy argmax per field, with hard host masks: ptr_b ≠ ptr_a (the real calculator refuses DUPLICATE_REFERENCE), end ≥ start, end − start < 12.

### 1.6 PrefixAdapter and Talker — `talker.py`
- `PrefixAdapter(state=256, lm_width=D_lm, hidden=32)`: per-register map `Linear(256+8,32) -> GELU -> Linear(32,D_lm)`, shared weights, a one-hot register index is the extra 8 inputs (the same idea as `StatePrefix`'s geometry inputs). Output `prefix float32 [B,8,D_lm]`, 1:1 with registers, no pooling (reasoner design talker). 12.7k params.
- `Talker(lm, adapter)`:
  - `loss(registers [B,8,256], target_ids [B,Tt] with -100 pad) -> scalar`: `[prefix ; embed(<bos> + shifted target)]` → `lm.logits_from_embeds` → CE. Same layout as `human_loss` (shown).
  - `generate(registers, max_tokens=8) -> list[str]`: greedy, stop at `<eos>`.
- Target text is the rendered answer value, e.g. `"12"` or `"7/2"`. The talker runs only on the ANSWER step.

### 1.7 Calculator — `tools.py`
Port of the real registry rules (shown in `calculator_tools.py`), with one labelled extension:
- `build_registry(question:str, tok) -> list[Entry]`. Integer literals by the real regex; at most 8; |v| ≤ 1e6; `Entry(id="literal:i", value:Fraction, token_indices, char_span, source="literal")`.
- **Operands point only into the registry**: question literals plus prior results (`result:k`, at most 3). Notebook numbers are never operands (real pipeline constraint). In the toy world the notebook steers *which* literal and *which* op get picked (section 3).
- `execute(op, ref_a:int, ref_b:int, registry, call_index) -> Trace(status OK|ERROR, value:Fraction|None, error_code)`. ADD/SUB as in the real code; **MUL/DIV are a demo extension** (the real pipeline has NONE/ADD/SUB only), added so Fraction exactness gets tested. Exact `fractions.Fraction`, never float. DIV by 0 gives `ERROR DIV_BY_ZERO`. MAX_CALLS = 4.
- Result re-entry: the host renders `"= 7/2"` (or `"= ERR"`), runs TinyLM to get hidden states, then the reader with role tool_result and coords row = call_index. That gives new Workspace rows, and the host appends a registry entry `result:k` whose token_indices point at those rows.
- `render(Fraction) -> "7/2" | "12" | "-3"`; `parse` is its exact inverse.

### 1.8 Notebook — `notebook.py`
- Host object (plain software, no weights): `Notebook(slots: list[Entry(slot_id:int, text:str, source:"taught"|"model_write", version:int)])`, cap S = 8, each entry ≤ 12 tokens. Rules follow `fable_notebook_contract.py`: an edit supersedes and keeps history; `snapshot()` / `hash()`; `write_lock` context manager.
- `to_workspace(tok, lm, reader) -> Workspace` gives the rows for every slot: role notebook, coords (slot, tok, -1).
- `apply_write(slot_choice:int, span:(s,e), question_text, question_offsets) -> WriteTrace`. The new text is the exact question substring covering tokens s..e. If `slot_choice == S_cur` (NEW) the entry is appended (refused when full); otherwise that slot is superseded (edit). The model proposes; the host validates and writes (notebook design §4).
- Pair-test-friendly: `Notebook.from_facts(list[str])`, plus `with_fact_changed(slot, text)`, which returns a copy that differs in exactly one entry.

### 1.9 SleepReplay — `sleep.py`
- `ExperienceRecord(episode_spec, step_targets, class_:"A_correct"|"B_corrected", checker:"V1-key", checker_hash, day:int, family:str, input_hash)`. Records are verified by recomputing every CALC with `tools.execute` and comparing the final value with the generator key. That makes them V1-key in the sleep design's terms; the demo never claims V2.
- `Buffer`: per-family cap, dedup by input hash, store per night.
- `assemble_mix(day_records, store, anchor, U) -> list`: shares 50% day (A:B ≤ 1:2), 30% earlier nights (uniform per night), 20% anchor set (fixed generator items). Shares are fixed in config.
- `night(model, mix, steps=32, lr=1e-4, arm="S"|"PF"|"F0"|"SU") -> NightReport(updates, examples, loss_before, loss_after, trainable_hash_before/after, lm_fingerprint, notebook_hash)`. Only reader, core, heads and adapter are updated. `F0` makes no update. `PF` = day records only, same step count. `SU` = unchecked attempts. Controls hook: `arms_matched(reports)` asserts equal `updates` and equal distinct-example counts. The night holds `notebook.write_lock` (sleep cannot write the main notebook).

### 1.10 Size and speed
| part | params | trainable |
|---|---|---|
| TinyLM stand-in | 0.43M | no |
| reader | 0.013M | yes |
| core (2 blocks × 4 loops, d 256) | 1.05M | yes |
| action heads | 0.40M | yes |
| prefix adapter | 0.013M | yes |
| **total** | **≈1.9M** (1.48M trainable) | |
CPU timing (shown, this container, 4 threads): one forward+backward of the core at B = 8, N = 56, 4 loops takes 0.11 s. With the talker, a step should take about 0.15 s, so 300 steps take about 45 s (suggested).

---

## 2. One episode: control flow

```
host: question text q, notebook NB, registry REG = build_registry(q)
ws  = reader(lm.hidden(q)) [role question]  ⊕  NB.to_workspace()  [role notebook]
for call in 1..4:
    out  = core(ws, n_loops=4)                         # [B,N+8,256]
    act  = heads(out, REG, NB, q)  -> argmax per field  # ActionLogits -> Action
    CALC(op,a,b):   tr = tools.execute(op,a,b,REG,call); ws ⊕= reader(lm.hidden("= "+render(tr.value))) [tool_result]; REG += result:call
    NOTE_WRITE(slot,s,e): NB.apply_write(...); ws = rebuild notebook rows from NB (the edit is visible next step)
    ANSWER(a):      value = REG[a].value  (exact, from the structured pointer)
                    text  = talker.generate(out.registers)  (LM rendering, checked separately)
                    return Answer(value, text, trace)
    DONE:           return NoAnswer(trace)                  # statement turns (e.g. "Remember: ...")
budget exhausted -> return Fail("MAX_CALLS")
```
**Action vocabulary (exact):** `CALC(op∈{ADD,SUB,MUL,DIV}, ptr_a∈REG, ptr_b∈REG)`, `NOTE_WRITE(slot∈{0..S-1, NEW}, start∈q, end∈q)`, `ANSWER(ptr∈REG)`, `DONE`. NOTE_READ is not an action, because reading happens by attention every loop (decision D6).

Each call re-runs the core from h0 = 0 on the grown Workspace. Like the reasoner design's `resume(workspace + tool_result)`, there is no hidden state carried between calls.

**Training signal (teacher forcing):** the generator gives each episode a gold action list. The host executes the gold actions to build the Workspace seen at every step. That flattens an episode into independent steps, each a pair (Workspace, gold Action). Loss per step:
`L = CE(kind) + [CALC] (CE(arith)+CE(ptr_a)+CE(ptr_b)) + [WRITE] (CE(slot)+CE(start)+CE(end)) + [ANSWER] (CE(ptr_a) + 0.5·talker CE)`.
Fields that do not apply are masked out. ANSWER reuses the ptr_a head. Optimizer: AdamW lr 1e-3, wd 0.01, clip 1.0, batch 8 steps, group by padded length. Gradients reach the reader through the core, and reach the adapter through the frozen LM. The LM gets none.

**Overfit target (suggested):** 48 training episodes (16 per template), about 110 steps in all, 300 updates. Pass marks are in section 4 (T13). Inference uses argmax and no sampling, so it is deterministic.

---

## 3. Toy world (plumbing data, not an eval)

**This is toy data written for plumbing tests. It is not an evaluation, it is not drawn from any panel, and no result on it supports a capability claim.** It is generated in code (`toyworld.py`, seeded) with no external files. Names: Ana, Ben, Cy, Dee. Colours: red, blue. Items: pens, cards. Numbers 1-20.

Notebook facts look like `"<Name> likes <colour>."` plus 0-2 distractor facts about other names. Question literals always include one count per colour, so the notebook decides which literal is the right operand. The operands themselves stay in the question.

| id | template (example) | gold actions | exercises |
|---|---|---|---|
| T1 calc + read | NB: "Ana likes red." Q: "Ana has 7 red pens and 4 blue pens. She buys 3 more pens of the colour she likes. How many?" Verb picks the op: buys → ADD, loses → SUB, "each of N boxes holds" → MUL, "shares equally with K" → DIV (Fraction answers allowed, e.g. 7/2). | CALC(ADD, lit0, lit2); ANSWER(result:1) | calculator, notebook read, Fraction |
| T2 two calls + read | NB: "Dee likes blue." Q: "Cy has 6 red and 9 blue cards. Cy gives away 2 cards of the colour Dee likes, then gets 5 more. How many of that colour?" | CALC(SUB, lit1, lit2); CALC(ADD, result:1, lit3); ANSWER(result:2) | prior-result pointer, multi-call |
| T3 write, then read | Turn A: "Remember: Ana likes blue." (NB has "Ana likes red." in slot 0 → edit; if Ana is absent → NEW) | NOTE_WRITE(slot0 or NEW, span "Ana likes blue."); DONE | write, edit, DONE |
| | Turn B (same session, same host notebook): a T1 question about Ana | CALC(..., blue literal, ...); ANSWER | later read of a model-written note |

**Pairs:** every T1/T2 world is generated twice with the question byte-identical and the notebooks differing in exactly one fact (red ↔ blue). The gold operands differ. The generator asserts this, plus: answer ≠ every stated literal, no answer or intermediate in the notebook, all values within ±1e6.

**Sleep night in the toy world:** day = 16 fresh T1/T2 episodes attempted with frozen weights → checker → records A or B (B uses the generator's gold trace). Earlier-night store = the previous night's records. Anchor = 8 fixed training episodes. U = 32, night = 32 updates.

---

## 4. CPU tests (`tests/test_wired_demo.py`, pytest; `-m slow` for T13-T14)

| # | name | asserts |
|---|---|---|
| T1 | `test_workspace_contract` | reader output: tokens [B,N,256] f32, segment [B,N,2] i64 ∈ SEGMENTS, coords [B,N,3] f32, valid bool; padded rows exactly 0; a Workspace built by hand as audio (modality 7) passes `validate()` and runs through the core |
| T2 | `test_shapes_end_to_end` | for B ∈ {1,3}: LM hidden [B,T,128]; core tokens [B,N,256], registers [B,8,256]; every ActionLogits field has its stated shape; prefix [B,8,D_lm]; talker logits [B,8+Tt,V] |
| T3 | `test_padding_invariance` | one item alone vs. the same item in a padded batch: action logits equal within 1e-5 |
| T4 | `test_n_loops_configurable` | n_loops ∈ {1,4,6} run; the core has exactly one set of block weights (param count independent of n_loops); outputs differ between 1 and 4 |
| T5 | `test_grad_reaches_every_trainable_module` | one combined loss over a batch with CALC, NOTE_WRITE and ANSWER steps → every trainable parameter has a finite, nonzero grad (reader, seg_emb, null-pos, registers, both blocks, every head, adapter) |
| T6 | `test_frozen_lm_no_grad` | all LM params `requires_grad=False`, `.grad is None` after backward; LM fingerprint unchanged after 5 optimizer steps; adapter grad nonzero (gradient flowed *through* the LM) |
| T7 | `test_calculator_exact` | Fraction exactness: 1/3+1/3+1/3 == 1; 7÷2 renders "7/2" and parses back; registry literal indices match the real regex on 10 strings; DIV by 0, a duplicate ref, a 5th call, \|v\| > 1e6 and a notebook-number ref each give the stated error codes; no float appears anywhere in a trace (type check) |
| T8 | `test_tool_result_reenters` | after CALC, N grows by the number of result tokens, those rows have role 3, and the registry's new `result:k` token_indices point at them |
| T9 | `test_notebook_write_edit` | NEW appends; slot choice supersedes and keeps history; span text equals the exact question substring; full notebook refuses; next-step Workspace contains the new text and not the stale one |
| T10 | `test_notebook_pair_plumbing_untrained` | the two members of a pair produce different Workspaces and (with random weights) different action logits; with the notebook emptied, both members give identical logits (the input is identical by construction) |
| T11 | `test_checkpoint_roundtrip` | save → load into a fresh build → action logits and talker output identical bit-for-bit; strict state_dict load; loading with a different LM fingerprint or constructor config raises; notebook + sleep store JSON round-trip |
| T12 | `test_sleep_night_updates` | arm S: trainable hash changes, LM fingerprint unchanged, notebook hash unchanged (write lock held; a write attempt inside the night raises); F0: trainable hash unchanged; S vs PF: `arms_matched` true; mix shares within ±1 record of 50/30/20; every record has checker "V1-key" and a checker hash |
| T13 | `test_overfit_toy_world` (slow, ≤ 120 s) | 300 updates, seed 0. Pass: step loss in the last 20 updates ≤ 0.3 × the first 20; action exact-match on the training steps ≥ 90%; talker CE drops ≥ 30% (exact talker text is reported, not gated). Fails if: action loss ends above 0.5 × start, which means a wiring fault (masks, pointer candidates or teacher forcing) |
| T14 | `test_notebook_pair_trained` (slow, reuses the T13 model) | on the 16 training pairs: ≥ 14 of 16 pairs give the gold, and therefore different, ptr operands for both members. Fails if: ≤ 8, meaning notebook rows do not reach the pointer heads. This is plumbing on training pairs only: memorising both notebooks passes it, so it says nothing about reading new notes |
| T15 | `test_smoke_e2e_under_60s` | one fresh process, 4 threads: build, LM fixture load (or a 300-step pretrain if missing), 40 training updates, a T3 write turn then a read turn, one day + one 32-update night, save and reload; finishes in < 60 s with peak RSS < 2 GB (well under 15 GB) |

The training loop also checks every step that LM grads are None (as `ground()` does) and raises if not.

---

## 5. Real vs stand-in vs what the demo proves

| component | real | demo | demo proves | does not prove |
|---|---|---|---|---|
| LM | frozen LFM2.5-1.2B, bf16 | TinyLM 0.43M, word-level, briefly pretrained on toy text, frozen | the frozen-LM gradient path and interface (shown once T6 runs) | anything about LFM behaviour, real tokenization of numbers, or bf16 effects (untested) |
| reader | thin projection 32-wide (v6); "contextual" input (suggested) | same block, fed TinyLM hidden states | Workspace production per segment | the reader collision issue in reasoner-design F3 (untested) |
| core | ~9M, d 256, 2 blocks × 4 loops, MoE 8/top-2, relative bias, ordered position codes, no padding | 1.05M dense, same loop rule, sinusoidal row/col codes, key padding | loops share weights; n_loops configurable; notebook and tool rows are attended | MoE routing, the real position scheme, depth benefit (untested) |
| registers / prefix | today: answer-slot pooling to 8 prefixes (`StatePrefix`); reasoner design proposes 8 registers (untested) | 8 registers, 1:1 adapter | register → prefix → LM wiring | that registers beat pooling (untested; it is C-series work) |
| action heads | do not exist; the real model writes calls as LM text | 7 argmax heads on registers | a structured, decidable action interface | that the real text-call route works the same way |
| calculator | ADD/SUB integers, registry of question literals + results | the same rules + MUL/DIV, Fraction | exact arithmetic, pointer constraint enforced (T7) | operand choice quality on real questions |
| notebook | host JSONL contract; read via notebook channel; model writes not yet built (N4) | in-memory, span-copy writes | read/write/edit plumbing; pair-test mechanics | reading skill on fresh facts (the real 0/8 result stands) |
| sleep | design only (ols4wp), GPU, 256 updates | 32 CPU updates, V1-key toy records, arms F0/PF/SU | the night runs, changes weights, keeps the LM and notebook fixed, arms are matched (T12) | learning, retention, plasticity (P1-P4 untested) |

**Honest limits.**
- Overfitting 48 toy episodes shows that gradients and targets are wired. It does not show generalisation. Held-out pairs may be reported but are not gated, and any number there is **untested** evidence of nothing beyond the toy world.
- The demo's structured pointer heads sidestep the real model's open problem: the number must cross the prefix bottleneck into LM text (reasoner design F2). The demo's ANSWER value comes from a pointer, so "correct value" in the demo is not comparable to the real model's final-answer accuracy.
- A tiny pretrained LM on toy text can render short numbers easily. The LFM may behave very differently.
- Writes copy a question span. The notebook design's N4 proposes writes as generated `NOTE{...}` text, which is much harder.
- Padding plus masks replaces the real core's "prefix padding only, physically remove masked facts" rule. Equivalence is **untested**.

---

## 6. Decisions at forks (pick; why)

- **D1 Workspace segment layout:** `segment [B,N,2]` with one SEGMENTS table (not separate `role`/`modality` tensors). It matches the vision and audio producers already written; `.role` and `.modality` accessors keep the reasoner design's view.
- **D2 Role/modality embedding:** one zero-init `Embedding(8,256)` looked up twice. It is equivalent to two tables at the same ids, with one fewer part.
- **D3 Dense MLP instead of MoE:** MoE adds routing and an aux loss but no interface. It stays out to keep the model under 3M and tests fast; `mlp_kind="moe"` is left as a stub.
- **D4 Registers instead of answer-slot pooling:** heads and talker need a fixed-size readout, and the reasoner design already names 8 registers. Pooling would need answer-slot masks the toy world does not have.
- **D5 Fixed register jobs:** a fixed register per head field, which is simpler than a cross-attention action decoder and is easy to probe.
- **D6 No NOTE_READ action:** the real core reads the notebook by attention every round (`begin_latent` concatenates it). An explicit read action would be a second, untested route.
- **D7 Operands only from the question + prior results:** this is the real pipeline's constraint. The toy world makes the notebook steer operand choice, so the pair test still bites without notebook operands.
- **D8 MUL/DIV added, labelled demo-only:** needed for a non-trivial Fraction test; the real tool set stays ADD/SUB until someone decides otherwise.
- **D9 Writes by span copy:** exact and decidable on CPU. Generated-text writes (notebook design Q1/Q2) remain Ben's decision for the real model, and this demo does not settle them.
- **D10 Re-run the core from h0 each call:** it matches the `resume(workspace + tool_result)` contract and avoids hidden state between calls.
- **D11 Loss after the last loop only, n_loops = 4:** this matches `fixed4_training`; random-depth training (C4) is a later single change.
- **D12 Pretrain TinyLM briefly, then freeze:** a frozen random LM gives the talker nothing to steer. The pretrain is a fixture, not part of the system under test.
- **D13 Sleep records are V1-key only:** the toy generator knows the answers, so claiming V2-check would be false.
- **D14 Pad + key mask instead of physical slicing:** batching on CPU needs it; T3 guards it.

Open questions, best sent outside before building: D4 (registers vs pooling) and D9 (span vs text writes) each change what the demo can later be compared with. An Astra prompt could ask whether they block a later swap to the real pipeline (read-only, no runs).
