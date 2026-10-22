# TRAIN-only cross-placement diagnostic

The frozen2×2 comparison reused all128 preserved own-route predictions and made exactly128 new off-diagonal generations on the same32TRAIN cases. Four fixed40-visit checkpoints;0updates; noTEST calls or checkpoint copies. Literal question/history information, sourceorder, tokenizer/masks/decoder/reset/fixed4loops unchanged.

| Seed | Trained placement | Own route /32 | Cross route /32 | Paired wins | Paired losses |
|---|---|---:|---:|---:|---:|
|0|notebook|24|1|0|23|
|0|inline|32|1|0|31|
|1|notebook|20|1|1|20|
|1|inline|32|1|0|31|

Both notebook-trained seeds improving inline: false. All cross-route conditions score1/32, against own-route24/20 notebook and32/32 inline. This shows strong trained-route sensitivity/placement specialization. It does not identify a unique causal component, prove broken notebook logic or establish generalization. No further fitting or extra variants dispatched. Follow-up should use the saved code/input traces for one prospectively selected controlled diagnostic, not another blind duration extension.

First prediction04:09:59.609331UTC; runner04:09:48.383247–04:10:56.064172UTC, exit0,67.680925wall seconds (~1.891 calls/s including4model reloads).127/128valid terminalEOS, remaining output scoredincorrect. Saved stop reasons: {"max_new_tokens_without_EOS": 1, "observed_EOS": 127}.

CPU input qualification verified all128intended frames against preserved opposite-route frames: inline≤36questiontokensinclEOS and emptynotes; notebook≤10querytokensinclEOS and≤26notebooktokens. Sourceorder/masks unchanged; allcheckpoint and preserveddiagonal hashes unchanged. Independent saved-record recount verified IDs/pairing/inputframes/native contract/strictnumeric+actuallyemittedEOS;0modelcalls by verifier.5strictEOS CPUtests plus literal mapping/invalid-protocol checks passed; independent source+plan+verifier reviews passed.

Output 376832 bytes within64MiB; project 4159610880 bytes within100GiB; free 16970072064 bytes above1GiB. Previous438202368-byte continuation matrix retained unchanged, no checkpoint copies. Owned lock released; no spend.

Pre-call commit ead390351840cc7879aea6a7ff113501ec7d863f; planSHA 8f95852fa8b99d4b4561194b185c1f4e7af55e71bdd0a1cc7577f2152621623a. Private rawinputs/outputs remain onPC; Git contains only code/counts/hashes/receipts.
