# English pilot: gaps before FREEZE (read-only audit, 2026-10-03)

Labels: shown = checked in a file or command this session; suggested = my proposal; untested = no run has measured it.
Paths are under `artifacts/cap256-launch/contextual-input-compare-v1/ENGLISH-PILOT-v1/` (call it P/) and `scripts/cap256_launch/` (call it S/).

## Checks run (shown)
- `python3 -m py_compile` passed for all 16 files: english_blind_paraphrase_sheet, feature_cache64, full_pilot_schedule, observe_generation48, ordered_begin_cap64, pilot_common, pilot_runtime, pilot_test_fixtures, pilot_tokenize_frames, zero_update_probe, eval_english_fresh_windows, execute_english_paraphrase_pilot_windows, score_english_free_answer, train_english_paraphrase_pilot_windows, test_english_pilot_stdlib, test_english_pilot_torch.
- `test_english_pilot_stdlib_v1.py`: 19 tests OK on the Mac. The Mac has no torch, so test_english_pilot_torch_v1.py (7 tests) was only compiled (untested).
- Hashes recomputed: v3 eval_items = e36d1cd2...961e (matches FRESH-EVAL-FREEZE-v1.json, P/FRESH-EVAL-DRAFT-v3/SHA256SUMS and the source_sha256 inside fresh_inputs_only_v1.json). Schedule = 090c30f3... (matches all three configs). Train, probe and eval runner hashes in CONFIGS-v1 match the files on disk. TRAIN-FRAMES-v2 = b7370471... (matches the configs and G0-STDOUT).
- Every file in S/ named above and in P/ is untracked in git (`git status` shows `??`). Suggested: commit before freeze so hashes are recoverable.

## Which eval draft is current
v3. Shown: FRESH-EVAL-FREEZE-v1.json points at FRESH-EVAL-DRAFT-v3/eval_items.json (frozen_at 2026-10-03T14:10Z, hash matches), and fresh_inputs_only_v1.json was built from that hash. v1 and v2 are superseded. Caveat: the CHANGELOG-v3.md header still says "pending owner freeze"; the freeze file is the later record.

## Gap table

| # | Item the protocol needs | Status | Evidence | Smallest next action | Where |
|---|---|---|---|---|---|
| 1 | Parent checkpoints (seeds 0, 1) sha | DONE (pinned in config) | ROOT-DECISIONS-v1 item 1; TRAIN-CONFIG-v1 parents | none; file bytes still need the PC preflight (item 20) | - |
| 2 | UNPINNED: parent delta receipt `ef4e8e77...7e69` (full hash) | UNCLEAR | Only the abbreviated reference appears locally (CONSUMER-LOCAL-MATERIALIZATION-RECEIPT-v1.json line 13). No full file found by this audit. | Fetch full file from project library, `shasum -a 256`, check it starts `ef4e8e77`, add to the freeze record. Or write down that the train bank hash f2f5cce3... alone governs and drop the dependency. | Mac CPU |
| 3 | TRAIN bank hash | DONE | f2f5cce3... in all configs and schedule | none | - |
| 4 | UNPINNED: full native token-ID arrays, 96 TRAIN frames | DONE | NATIVE-G0-v1/TRAIN-FRAMES-v2.json: 96 frames with input_ids and labels, caps 64/48, sha b7370471... | Confirm the "96+96 with zero violations" claim: STDOUT says max input 59, max target 38, fresh over_64 = 0 (shown). | Mac CPU (done) |
| 5 | Tokenizer pin and native lengths <= 64/48 | DONE for TRAIN and for fresh inputs | G0-STDOUT.json (UTF-16 encoded; the file reads oddly with cat): 96 frames, 102 fresh inputs, max 59 incl EOS, over_64 = 0; tokenizer.json df1d8d5e..., config 2a52ec01..., special_tokens_map 742aefe2.... Same values are in the config feature_identity. | Minor: the freeze file cites NATIVE-TOKEN-LENGTHS-v1 measured on v2, and says TR-F2 in v3 was not re-measured. G0 ran on the v3-derived fresh_inputs (source_sha256 matches v3), so this looks covered, but G0-STDOUT does not print the TR-F2 length. Add one line of the TR-F2 token count to the freeze record. Also re-save G0-STDOUT as UTF-8 (hash change, so do it before the freeze). Also fresh OUTPUT length: the 48-token limit is a generation cap, no gold-length check is stored (suggested: log max gold answer tokens). | Mac CPU |
| 6 | Fresh eval set hash | DONE | FRESH-EVAL-FREEZE-v1.json | none | - |
| 7 | Fresh inputs file hash | DONE | 126d89f3... in EVAL-CONFIG-DRAFT-v1 | none | - |
| 8 | Schedule file (G6) | DONE | english_full_pilot_schedule_v1.py; FULL-PILOT-SCHEDULE-v1.json 090c30f3...; per-seed hashes b3b83ed7... and 66058fab...; 2304 updates, 72 per pass, order identical across arms | Re-run the generator and diff against the file (a determinism check). The stdlib tests likely cover this; I did not read them. | Mac CPU |
| 9 | G1 serializer 63/47 caps | DONE (by a different route) | Frames carry 64/48 caps in TRAIN-FRAMES-v2; the protocol's suggested file english_clean_train_input_v2.py was not looked for under SMALL-TRAIN-QUALIFICATION-PREPARATION-v1/ | Record in the freeze file which serializer produced TRAIN-FRAMES-v2 and its hash. | Mac CPU |
| 10 | G2 cap64 adapter | DONE (code), untested on torch | S/english_ordered_begin_cap64_v1.py compiles; covered by torch tests | Run test_english_pilot_torch_v1.py on the PC and keep the output | PC |
| 11 | G3 observer 48 | DONE (code), untested on torch | S/english_observe_generation48_v1.py | same | PC |
| 12 | G4 feature cache 64 | DONE (code), untested on torch | S/english_feature_cache64_v1.py | same | PC |
| 13 | G5 zero-update probe | DONE (code) / probe NOT RUN | S/english_zero_update_probe_v1.py; PROBE-CONFIG-v1 (dispatch_allowed true, cap 2400 s) | Run Stage A on the PC after torch tests pass | PC |
| 14 | G7 training worker | DONE (code), untested | S/train_english_paraphrase_pilot_windows_v1.py, sha 7b052a0b... matches TRAIN-CONFIG; train config has dispatch_allowed false | Torch tests on PC; no GPU training until freeze | PC |
| 15 | G8 driver | DONE (code); hash not pinned | S/execute_english_paraphrase_pilot_windows_v1.py, sha 70641947...; it is not named in any config or in the freeze file | Add driver sha (and scorer sha, below) to the freeze record | Mac CPU |
| 16 | G9 eval runner | DONE (code), untested | S/eval_english_fresh_windows_v1.py sha 5fe7fd52... matches EVAL-CONFIG | Torch tests on PC | PC |
| 17 | G10 scorer | DONE (code), hash not pinned | S/score_english_free_answer_v1.py sha f203eeae...; stdlib-only; verdict logic ceil(N/8), harm ceil(N/16), UNDERFIT-VOID, seal check exist | Protocol section 6 says the scorer hash is frozen before any endpoint is generated, but no file records it. Write it into a freeze addendum. Also check the scorer uses all 96 items and the 40/48 gate (ROOT-DECISIONS items 7 and 10). I read only the function list, not the bodies. | Mac CPU |
| 18 | G11 proposition sheet | UNCLEAR | S/english_blind_paraphrase_sheet_v1.py builds a blind sheet from the eval items' propositions (asserted_facts); no separate PARAPHRASE-PROPOSITION-SHEET-v1.json exists. Independent rater (ROOT-DECISIONS item 8) is not yet named or run; S1 is secondary and cannot decide PASS/FAIL. | Decide that eval_items asserted_facts is the checklist and note it in the freeze addendum. | Mac CPU |
| 19 | G12 tests | DONE for stdlib (19 OK), untested for torch (7 tests) | see checks | Run torch tests on PC | PC |
| 20 | G13 resource accounting | MISSING (expected: written after Stage B) | no RESOURCE-ACCOUNTING-v1.json | Not a freeze blocker; produced after Stage B | PC |
| 21 | Stale pending fields in EVAL-CONFIG-DRAFT-v1 | MISSING | 4 endpoint states have `PENDING-STAGE-B-ENDPOINT` shas; config is named DRAFT, `dispatch_allowed` false | Expected until training ends. Eval config must be re-hashed after endpoints exist, and the freeze addendum should say so. Importantly, seal-before-Gold needs the scorer hash fixed first. | PC (after training) |
| 22 | Config hashes for the three config files | DONE | CONFIGS-v1/SHA256SUMS | Include the SHA256SUMS hash in the freeze record | Mac CPU |
| 23 | TRAIN data status string ("not checked training data") | DONE by decision | ROOT-DECISIONS item 9: the receipt governs, do not edit the pinned file | none | - |
| 24 | Adapter and LM provenance in configs | UNCLEAR | Configs point to bootstrap-English-s0.pt (sha e8092da2...) and CACHED-LFM-ORIGINAL-PROVENANCE.json; the protocol text (section 3.3) lists a different set of files. I did not check that these hashes exist or match on the PC. | On the PC, `sha256sum` the adapter and the model snapshot against the config values (the preflight probably does this; confirm in the probe code). | PC |
| 25 | Protocol text itself still says DRAFT and lists decisions D1 to D9 as open | MISSING | PROTOCOL-DRAFT-v1.md header; the answers are in ROOT-DECISIONS-v1.md only; the 14 USD vs 10 USD conflict is overridden by "All of it" (Ben, 12:39Z) | Write PROTOCOL-FROZEN-v1 as a short addendum that folds in ROOT-DECISIONS, the exact hashes above, and the N=96 thresholds (primary subset sizes per section 7; they are not in the root file). | Mac CPU |
| 26 | Budget and compute availability | UNCLEAR | ROOT-DECISIONS says local 5070 Ti, GPU hold ended 11:59:58Z; configs show spend cap 0.00 USD (local). I did not check the live PC state (no SSH allowed). | Before the probe: confirm no live owner of the shared worker lock and GPU free. | PC |

## Mac CPU versus PC
- Mac CPU, quick: items 2, 5 (one line), 9, 15, 17, 18, 22, 25 (all are hashing or writing a freeze addendum).
- PC needed: torch tests (10 to 16, 19), Stage A probe (13), checkpoint and model sha preflight (1, 24), later the training and the eval config re-hash (21).

## Top 5 gaps (suggested priority)
1. No freeze record pins the scorer, driver, blind-sheet and common/runtime hashes. FRESH-EVAL-FREEZE-v1.json covers only data. Protocol section 6 requires the scorer hash fixed before any generation.
2. The torch half of the code (cap64 adapter, observer, feature cache, probe, worker, eval) has never run: 7 torch tests exist but need the PC. Stage A has not run either.
3. The protocol is still a DRAFT with open decisions. The answers live in ROOT-DECISIONS-v1.md, and N=96 thresholds per primary subset are not written down numerically.
4. The parent-delta receipt `ef4e8e77...` is still only an abbreviated reference, and parent and model sha preflight on the PC is untested here.
5. Eval config still holds four PENDING endpoint shas, and the S1 rater and proposition checklist are not set up (secondary only).

Also noted: G0-STDOUT.json is UTF-16, and everything in S/ and P/ is uncommitted.
