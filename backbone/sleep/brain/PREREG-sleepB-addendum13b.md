# Sleep-B addendum 13b: keep the LoRA frozen in the whole-model arm (written 2026-10-25 ~16:40Z, after the --q4-eval code, before the fix code and before any addendum-13 run)

Labels: shown / suggested / untested. Amends addendum 13 (sealed, unchanged). Not the village model, not the card experiments.

## What was found (shown, CPU, while building --q4-eval, commit 107137a57d)
The delta arms (ab_ob_full, ab_ob_full_s, ab_ob_local) were meant to train only the fp32 full-rank change with the LoRA frozen.
With the pinned peft (0.21.2), leaving `pm.disable_adapter()` sets `requires_grad=True` on every LoRA tensor again. That happens
at the replay generation before night 1, so each night's Trainer also trains the LoRA, at the delta's lr. On the tiny smoke model:
0 trainable LoRA tensors right after the freeze, 124 after one `disable_adapter()` exit; the Trainer holds 186 tensors (62 delta +
124 LoRA), and max |lora_B| is 4.3e-5 after night 1. `result["trainable_params"]` was counted right after the freeze, so it hid this.
- So addendum 2's and 3's delta arms (ab_ob_full 57.5, ab_ob_full_s 63.5, ab_ob_local 53.5) trained the LoRA next to the delta.
  How much of their recall the LoRA carried is unknown (untested). Their write-ups get this caveat.

## Change (for addendum 13's run only)
- New flag `--freeze-lora` (default off; old arms unchanged, checked by the selftest and a smoke diff): each Trainer sets
  `requires_grad=False` on every LoRA tensor before it collects its parameters, so only the delta trains. LoRA B stays zero, so the
  model is exactly W + delta, as addendum 13 describes. Allowed only with the delta arms.
- Addendum 13's run uses `--arm ab_ob_full_s --freeze-lora --q4-eval`. Everything else in addendum 13 (conditions, pass marks,
  compute) is unchanged. F0 and Q0 are then the true pre-sleep model in bf16 and 4-bit.
- `q4_eval.lora_B_nonzero` must be False in the run's JSON; if it is True, S1 is not judged.
- **Reported, not marked:** F against addendum 3's 63.5. A large drop would suggest the LoRA carried part of addendum 3's gain.
