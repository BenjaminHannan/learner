# Astra prompt: why the vector reader misses owners named in earlier turns (Thread manager, 2026-09-28T01:23Z)

The vread test (thinker reads a frozen 1B's vectors and writes pointer fact cards) came back a narrow FAIL at ffd6950be.
The Thread manager offered Ben a diagnosis prompt for Astra at 00:4x UTC; Ben answered "yes" at 01:23:01 UTC
(cmsg_01FuvegZXjMmeUzStiEFVnEWK9D7Y7ongQPJWow74awJgd). Everything below the line is the prompt.

---

# Diagnosis only: why does the vector reader miss owners named in earlier turns?

**Rules for this task:** read only. No edits, no commits, no training, no tests, no GPU, no rentals. Don't run the models. Small read-only scripts that count things in the saved files are fine (CPU). Never open readpanel320 or any other sealed test panel.

**Background**
Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first. Ben (a high-school senior) reads the summary at the end.

The build reads each chat turn for facts. The normal reader is MiniCPM5-1B with a LoRA adapter, which writes facts as text. The vread test tried Ben's idea instead: the 1B stays frozen and one of its layers' token vectors goes into a small looped net (the "thinker", 2 blocks at width 512). The thinker writes fact cards whose owner and value are pointers to exact word spans in the prompt, which holds the turn, the assistant's previous reply and up to 6 earlier turns. Both arms trained on the same Luna chats with code-made labels and were scored once on the same dev split (1,444 turns, 211 dialogs).

Result (artifacts/claude-vread-20260927/RESULTS.md):
- Vector reader, own save bar 0.97: 1,098 right saves of 1,230 against the LoRA reader's 924 at 0.995, with 4 wrong-save turns against 1. It missed V2 by 1 turn.
- At the same bar the readers are close on facts about people named in the current turn (0.995: 948 vs 924, 1 wrong each).
- **The gap is backref,** where the owner is named only in an earlier turn ("she", "my boss"): 81 vs 88 of 136 at the arms' own bars, 63 vs 88 at 0.995 and 81 vs 112 at 0.97. Under the history rule, all 5 extra wrong saves had the owner pointer on the wrong earlier person.
- The loop never ran a second round: the learned stop fired after round 1 on every dev turn (median stop probability 0.999). The training loss reached 0.0027.
- Layer 12 was picked on a calibration slice cut from train, by right minus extra saves over all families. The per-layer totals are in RESULTS.md. The vector arm trained on 11,217 rows and the LoRA arm on 12,447, because the calibration slice came out of the vector arm's train. One seed per arm.

**The question**
Which cause best explains the backref gap? Consider at least these, and add any the files point to:
1. **Layer:** layer 12's vectors may not carry "who 'she' refers to" as well as another layer, and it was chosen on all families, not backref.
2. **One round:** the stop head learned to quit after round 1, so the thinker never gets a second pass to link a pronoun to an earlier name.
3. **Too little practice:** backref rows may be rare in the vector arm's train, or rarer than in the LoRA arm's after the calibration cut.
4. **The pointer head itself:** the owner pointer may favour spans in the current turn, or struggle with long histories (for example, misses rising with distance back to the named person).
5. **Seed noise:** one seed each. Say whether the gap is too large for that.

**Files**
- artifacts/claude-vread-20260927/: RESULTS.md, PASSMARKS.md, DATA.md, bar.json, verdict.json, RECOUNT.md, scores/*.json, data/rows.json.xz and data/dialogs.json.xz (train, calibration and dev rows with families and gold cards), run/out/vec_dev_reads.jsonl and vec_cal_reads.jsonl (every card with its owner_tokens and value_tokens, rounds and stop probability), run/out/lora_dev_reads.jsonl, run/out/vec/layers.json and layers_log.jsonl, run/out/vec_train.log.
- scripts/claude_vread_model.py, claude_vread_data.py and claude_vread_score.py; scripts/claude_lis319_common.py (prompt and history format); artifacts/claude-lis320-20260926/PASSMARKS.md (what backref means).
- Background on the loop net: scripts/claude_rsn358a_run.py and artifacts/claude-relnet-20260927/RESULTS.md.

**What to send back**
- For each cause: the evidence from the files, labelled **shown** (counted in the files), **suggested** (fits but not proven) or **untested**. Give counts as "x of N". Examples: backref share in each arm's train, misses by distance to the named person, where the wrong owner pointers land, and whether any saved file separates the layers on backref.
- Your ranking of the causes, and what can't be told from the saved files.
- **One change** to test next, only one. Give its pass marks fixed in advance, the result that would prove it wrong, and the fresh data it needs. The dev split has been scored once and is used up, but new Luna chats are arriving (lis-320 chunks 11 onward on origin/builder-outbox).
- Keep this reader test separate from the small card experiments and from the village model. Don't mix their results.
- A plain-language summary for Ben, 6 lines at most.
