# TRAIN-only fixture source admission

This packet contains the 512 explicitly released existing human TRAIN records.
Each training target is the exact official human answer annotation, often a short
phrase. `evidence_text` preserves the older verbatim context sentence. The target
is not that sentence. These annotations do not qualify grammatical conversation,
notebook dependence, semantic improvement, generalization, or live user learning.

The builder verified the immutable registry, mixed-pairs and TRAIN annotation
hashes. Its first pass scanned JSON byte structure and decoded only identity,
split, source-path, source-hash and content-key metadata. It established all 100
reserved DEV identities, their two source documents and their passage keys before
decoding any TRAIN question, context or answer. Unknown TRAIN identities and any
reserved document/passage overlap fail admission. The second pass decoded only
the annotation allowlist's 512 TRAIN rows and verified question/context hashes,
official human answer offsets, source registry hashes and verbatim evidence.
The official raw corpus and human source documents were never opened.

`TRAIN-PACKET.json` is self-contained. Runtime `load_packet` requires external
packet and manifest SHA256 pins before decoding either file. It opens only that
packet and `TRAIN-MANIFEST.json`. Copied original registry and TRAIN annotation
metadata are reconstructed byte for byte and checked against their original
hashes, so a claimed source hash alone is insufficient. Per-row field hashes,
original mixed-pairs byte offsets/hashes, original evidence byte offsets and
official answer character offsets are retained.

There is no independent stop88 identity or passage exclusion registry available
in this cloud checkout. The assurance is therefore limited to the explicitly
released existing TRAIN512 allowlist and exact reserved DEV exclusions. No
separate stop88 overlap certificate is claimed, and no reserved panel was read.
The fixture must retain `actual_user_day=false` and
`model_authored_text_included=false`.

Twelve stdlib tests passed. They check poisoned reserved fields and unknown
nested payloads without content decoding, reject unknown identities and reserved
document/passage overlaps, reject source/label/provenance/metadata tampering, and
guard runtime file opens to the standalone packet and manifest. The raw result
and final loader/test source pins are in `VALIDATION-RAW-v1.txt` and
`VALIDATION-RECEIPT-v1.json`. `BUILD-RECEIPT.json` is preserved as the initial build
receipt; its earlier loader hash is superseded by the validation receipt.

No Torch module, optimizer, inference, training process, watcher job, queue entry,
git commit or push was launched by this worker. This report is documentation and
must never be used as training material. Independent verification is pending.
