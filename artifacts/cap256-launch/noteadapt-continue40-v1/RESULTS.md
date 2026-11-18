# TRAIN-only duration continuation result

The fixed duration-only continuation completed: own saved v2 states at128 updates/4 visits to1280 updates/40 visits. All four arms performed exactly1152 additional updates; no TEST calls or optimizer reset.

| Seed | Placement | Native numeric exact + emitted EOS /32 | Fixed endpoint teacher-forced /32 | Fixed endpoint mean numeric CE | Fit wall seconds |
|---|---|---:|---:|---:|---:|
| 0 | notebook | 24 | 24 | 0.525649 | 271.016 |
| 0 | inline | 32 | 32 | 0.005608 | 267.015 |
| 1 | notebook | 20 | 20 | 0.715651 | 265.797 |
| 1 | inline | 32 | 32 | 0.041188 | 270.969 |

Independent saved-record recount verified4608 actual additional updates, visits5–40/order/cursors/masks/labels, all four full checkpoint hashes,128 native calls and128 valid terminal EOS observations. Teacher-forced and native correctness agree at aggregate endpoint counts; no additional models were run by the verifier. Online pass counts remain distinct from fixed-endpoint accuracy.

Runner03:40:05.619713–03:59:20.847269UTC,1155.227556 wall seconds. Fit total1074.797 seconds including load/save/reload; exact optimizer-only timer was not recorded. Endpoint phase76.625 seconds for128 native generations plus128 teacher-forced records and four reloads (1.670 native calls/second over that mixed phase).

Inline fits all32 TRAIN cases in both seeds; notebook retains8/12 errors. This supports a placement-dependent TRAIN fit gap under this fixed recipe, not a proven causal mechanism, unfamiliar-question improvement or learned writing. No TEST reuse, checkpoint selection, further extension or architecture change. Both original v2 and parent40 checkpoints are retained.

All four endpoints retain full model/Adam/parameter mapping/RNG. Per-arm saved state restore and durable final reload equality passed; .001 LR/zero decay/data/objective/4loops/masks unchanged.128 native TRAIN generations were made exactly once; independent verification made0 model calls.

The first offline recount attempt lacked its scorer dependency; supplying the unchanged pinned helper resolved it without any model rerun.22 relevant CPU unit tests,5 invalid protocol rejection checks and4 recursive state equality checks passed; independent runner/verifier source reviews passed.

Next decision: stop this run at40 visits as frozen. Root must select a separate protocol before further GPU work; a fresh question comparison or one controlled notebook diagnostic requires separate scientific selection. Consumed TEST is unavailable for reuse.

Resource closure: original matrix 417333248 bytes unchanged; new matrix 438202368 bytes, below512MiB; project 4159152128 bytes below100GiB; free 17817432064 bytes above1GiB. Owned lock released; no unrelated process stops. Original checkpoint/closed/frame hashes unchanged; old TEST files were not read.
