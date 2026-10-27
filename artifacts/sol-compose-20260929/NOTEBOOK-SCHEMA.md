# NotebookState: concrete joined boundary

```python
@dataclass(frozen=True)
class NotebookState:
    translated: FloatTensor  # [batch, fact_vectors, 64]
    mask: BoolTensor         # [batch, fact_vectors], True = real vector
```

Implementation: `scripts/sol_compose_notebook.py`. Consumed by `Composer.encode(inputs, memory=notebook_state)` and `BaseContextAdapter.encode(tokens, slots, notebook_state)`; reasoner attention reads notebook key/value vectors on each round. Raw text does not enter the stop/export or output translator API.

Ingest boundary: `NotebookStore.append(raw_utf8_bytes, origin='verified_human', source_ref=..., origin_evidence=...)`. Stores exact bytes + SHA256 + provenance. Origin attestation must come from a trusted human/source-ingest pipeline; this store cannot establish human authorship by inspecting text. Symbolic tables use `origin='symbolic_code'`, generator hash + seed as evidence. Generated/model-origin prose is rejected. Facts are inputs, never copied into output targets by this driver.

A learned input translator takes the human prompt and verified human notebook facts and emits prompt vectors plus NotebookState. Retrieval is learned attention within the reasoner. Candidate fact retrieval and chunking must not implement answer logic or task routing. In the bounded implementation, ten symbolic table rows are notebook facts, the expression row is the prompt. Each fact is translated into one 64-wide record vector. Both input pathways are trained from symbolic supervision.

Output boundary: `FinalStateTranslator.forward(final_state: FloatTensor[B,T,64])`. No NotebookState, source-text, tokens, record answers, source logits, provenance store or raw notebook argument. Existing source/SleepMoE cores use `BaseContextAdapter` for learned notebook attention and d256-to-d64 latent export. Composer exports `state.board` directly. Geometry in source/SleepMoE must remain call-specific; state selections retain dr/dc and remove the same batch rows from memory.

Serializable packet: reasoner state_dict, translator state_dict when trained, arm/config, seed, round cap, notebook SHA256 and provenance references, explicit latent state tensors, mask, and learned-stop rounds. No raw-text pointer is attached to output translator. Raw notebook belongs to ingest/reasoner services only. Runtime checkpoint schema is `sol_compose.joined.v1`.

Provided ByteFactEncoder accepts exact UTF-8 and emits this shape. It is UNTRAINED and is NOT used to train or score English by this symbolic job. Replace it with the approved thin learned English input translator. Grammatical English additionally needs an approved learned state-to-English decoder, human-origin training text and independent evaluation. No English or benchmark win is claimed here.
