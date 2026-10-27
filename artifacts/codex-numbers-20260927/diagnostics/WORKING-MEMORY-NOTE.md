# Working memory clarification from Ben's brainstorm

Ben asked whether the reasoner already gets to write cards as temporary memory. No candidate has been registered or trained at this point.

SHOWN in the specific 358i import chain: the small number-puzzle loop is a recurrent grid network (`claude_rsn358a_run.py` Net.step/loop_train/loop_rounds). It retains and updates hidden vectors h between rounds. There is no CardStore, scratch-card write action, explicit branch snapshot, or feeding its decoded expression back as the next input in this implementation. It would be incorrect to describe it as having no temporary memory.

SHOWN in the inspected broader code: `premonition/model.py` has a CardWriter which encodes non-question input lines and a Think loop that retrieves from that store. This is a different implementation from 358i. This observation does not establish what every other experimental wrapper supports.

SHOWN in design documents: `design/research/2026-09-18-novel-mechanisms.md` describes writing intermediate results to episode-scoped scratch cards; `design/v3/30-modes/384b-revert-and-retry.md` proposes retaining thought snapshots and using abandoned paths when reverting, including a prospective small-loop version. Neither proposal is wired into the 358i runner inspected here.

SUGGESTED next question: whether the small loop can learn to preserve useful partial calculations and revise them using its available state; whether an explicit writable card workspace helps is UNTESTED. Memory capacity, arithmetic skill, and learned branch selection are separate hypotheses. Adding storage and changing the teaching objective simultaneously would obscure which helped; a single experiment must name and freeze its intervention.

UNTESTED: these small-puzzle findings say anything about the 1B chat model, the joined build, or a complete memory-enabled reasoner.
