# Code review round 1: response

Review by the coordinator on 2026-10-20 (built-in code-review at high, on PR head `5ad2f788e`). Verdict:
**NOT CLEAN**, 2 blocking and 7 non-blocking findings. I reproduced both blocking findings by reading the
code, and the new regression tests fail on `5ad2f788e` and pass on the fix.

## Blocking: both fixed

| # | Finding | Fix | Regression test |
|---|---|---|---|
| B1 | `train.answer_with_gold` builds its episode with `_start` but never sets `episode.reader`, so `validate()`, `train_d`'s eval hook and the DEV readout crash with the flag on | Root fix as suggested: `_start` builds the reader memory when the flag is on (`answer()` rebuilds it only for the `wipe="store"` mask). `train.py`'s answer path is untouched | `test_validate_and_gold_cards_run_with_the_flag` (all three variants) |
| B2 | `_reader_memory` read `episode.reader` with no default, so `premonition_binding_probe.py`'s bare `SimpleNamespace(x=, valid=)` episode raised `AttributeError` **with the flag off**: a flag-off regression | `getattr(episode, "reader", None)`. With the flag on, a bare episode now fails loudly (`ValueError` from the decoder) instead of decoding without the new path | The flag-off bit-identity test now also covers `answer_with_gold`, `validate()` and the bare-episode `_greedy` path against 73b8e0224; plus `test_bare_episodes_are_refused_with_the_flag` |

## Non-blocking

| Finding | Status |
|---|---|
| `train_d` has no `config_overrides`, so treated can't launch | **Fixed.** Added `config_overrides=None`, passed to `MiniConfig.preset` (default unchanged; `train_toy` already had it). This touches `premonition/train.py` only to pass the flag through. **Coordinator: please confirm this is within the Q11a flagged path.** |
| `wipe="store"`: kept states still hold pre-window tokens, so W-store is unfair between arms | **Open, handled in the card.** RUN-CARD §2: W-store is not a readout; any wipe comparison uses W-full. The docstring of `_reader_kv` says so. A code fix is not possible without re-reading (which is W-full). |
| KV gathered on every loop and step | **Fixed.** Gathered once per batch, in `_start` (per question, `[Q, S, 2d]`). `_greedy` builds its decoder kwargs once, outside the token loop. Training loops still index the question subset of each loop. |
| `premonition_binding_probe.py:151`, `premonition_m02_answer_path.py:459` hand-copy the decoder and skip `reader_attn`, so they're silently wrong on flag-on models | **Open, not edited** (existing experiment files; `handoff/HANDOFF.md:33` forbids editing them). Neither is used by this card. Their other entry points (`_decode_logits` with three arguments, bare episodes) now fail loudly on flag-on models. |
| Guard: add `loops_mean`, `halt_rate`; `asked_rate` really means "fetched a real card" | **Fixed.** `summarize` adds both, defined as in `train.validate`, and the guard's own field is renamed `fetched_any_rate`. `train.validate`'s `asked_rate` is unchanged (not my file). |
| `_reader_memory` kwargs-dict indirection | **Kept, on purpose.** With the flag off it makes the decoder call exactly the old three-argument call. That keeps subclasses with three-argument `_decode_logits` overrides (`answer_path`, `address_reader`, scripts) working, and is part of what the bit-identity test checks. |

## Tests after the fix

- `tests/test_premonition_decoder_reader_kv.py`: 15 passed (12 before, plus 3 new; the bit-identity test gained 3 paths).
- On `5ad2f788e`'s `model.py` the new tests fail: the flag-off bit-identity test (bare-episode path) and the flag-on `validate` test.
- Every premonition test file run on its own, compared with the pristine 73b8e0224 tree: appended below once the run finishes.
