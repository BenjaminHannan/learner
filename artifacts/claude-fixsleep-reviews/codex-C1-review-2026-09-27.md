# Owner review of Codex C1 (live adapter bypass), Fix-sleep thread, 2026-09-27T03:57:01Z (date -u)
Read: artifacts/codex-retention-20260927/PASSMARKS.md (C1 section; c7c8221a0), implementation/retention.py and
test_retention.py (697f18b58), RUN-NOTE.md. C1 had not reported when this was written.

1. Not a sleep verdict. C1's own marks say a PASS is "software behavior only" and must not be read as F1-F5,
   automatic routing, rewording, new-skill improvement or a dl-9 result (PASSMARKS C1, last paragraph). Agreed. It
   cannot fill H-B or SLEEP02D: nothing is trained and no forgetting is measured. Its RESULTS should repeat that line.
2. Model revision matches this thread's kits: MiniCPM5-1B 87179e5c1f455ef22e6223592d2d61351b525bfc. Its LoRA wrapper
   says it keeps claude_blurt2.add_lora's state_dict names and arithmetic, and the tests import add_lora directly.
   Ask: sha256-check the dl-5 adapters used as fixtures against the sidecars in artifacts/claude-dl5-20260926/gpu/
   (dl5-S-s8.json, dl5-S-s9.json) and name them finding-only, as the marks already say.
3. Relation to dl-9: complementary, not a duplicate. dl-9 tests whether a LEARNED switch can pick on/off per
   question without losing the learning; it assumes "off" means the plain base answer and gets that by reusing the
   unwrapped base's stored answers. C1 tests the other half: that a live wrapper with the adapter inactive gives
   exactly the base's answer. C1 has no switch; dl-9 has no live serving. A build would need both.
4. Gap (adversarial): the real-model parity mark asks for bit-identical logits on the Mac (MPS or CPU, bf16). A
   mismatch can only be blamed on the bypass if the unwrapped base, run twice under the same settings, is itself
   bit-identical. I did not find such a repeat control in retention.py or its tests. Ask, before the real-model run:
   add a base-vs-base repeat first and report the device; if the repeat differs, the real-model part is INCONCLUSIVE
   (device nondeterminism), not FAIL. A CPU pass does not cover MPS or CUDA serving.
5. Provenance flag, not C1's problem: PASSMARKS says "Luna-written data is permitted by Ben's subsequent
   clarification". I found no such clarification in the repo; the standing rule this thread follows is Ben's 16:39
   "Use GLM" (GLM or code only). C1 uses no such data; any later use needs the Thread manager's check first.
Verdict on the design: sound as a software test; results count once its numbers are rechecked here.
