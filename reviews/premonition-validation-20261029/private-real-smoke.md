# Actual native private-check smoke — 2026-10-29

The real native LFM3 private engine and actual HTTP-only Python grader completed successfully at **20:50 UTC**, with both child processes stopped before the controller returned. This closes the structural real-engine smoke gap in `private-check-handoff.md`. It establishes process, authentication, snapshot, HTTP grading and cleanup plumbing. **The adapter is all zero: this provides no evidence of learning quality and nothing was promoted.**

The controller used the existing `~/learner-ops/lfm3/llama.cpp/build/bin/llama-server`, existing `LFM3-1.7B-QAD-Q4_0.gguf` base, Metal, context 2048, one slot, and Python 3.12 from the existing speedbench environment. The grader ran from this checkout through its actual `python -m sleepmlx served-check --server ... --cards ... --private-check-id ...` CLI. Import profiling recorded 160 modules and **no Torch, Transformers, MLX, TensorFlow or Safetensors backend imports in the grader**.

The 33,184-byte zero GGUF has SHA256 `9ca2b1a50743a3847b23497ea2899986b39d8f6ddbb917ed7e19e63b603876af`. Its source Safetensors contained two tensors / 32,768 data bytes, all zero. The original fixture's held file lacked `status: held_out`, so this run wrote a fresh isolated one-card synthetic snapshot with the accepted schema. Its prompt only asked the model to repeat the supplied city Paris. The controller copied and hash-checked both inputs into its protected private job directory. Source and held hashes remained unchanged after shutdown.

| Result | Observed |
|---|---|
| General questions | 8/8 adapter on, 8/8 adapter off |
| Synthetic held card | 1/1 adapter on, 1/1 adapter off |
| Grader verdict | `ok: true`, no reasons; 2.6 seconds |
| Controller verdict | `processStopped: true` |
| Check ID | `5165c60a-074f-4e0c-804b-c2763d0431af` |
| Owned engine | PID 34113, exit 0 at 20:50:43.669 UTC |
| Owned grader | PID 34121, exit 0 at 20:50:43.617 UTC |
| Idle gate | Clean before and after the check |
| Job cleanup | No journal and no remaining private job entries |

The engine loaded only on a random loopback port with the controller's unique alias and private key. It was never attached to the public gateway. The final OS PID checks found neither private child present.

To honor the single-model memory constraint, the supervisor paused only the verified public native engine PID 9553 after writing and fsyncing a durable restart obligation. The gateway stayed live. After private shutdown, it launched the existing `serve.sh --autostart` through detached Python `subprocess.Popen(start_new_session=True, stdin=DEVNULL, stdout=log, stderr=STDOUT)`. Public native engine PID 34175 and both `/v1/models` routes were healthy again by **20:50:45.944 UTC**: port 18080 advertised `lfm3`; gateway 8090 advertised `lfm3`, `lfm3-fast`, `lfm3-auto`. `restoreRequired` is false. The original public configuration was used.

The sampler observed normal memory pressure throughout (level 1), unchanged swap use of 1337.12 MiB, and private engine RSS 1,221,840 KiB (~1.17 GiB). The grader sample was 35,552 KiB and the Node controller stayed below 61 MiB. These are bounded samples, not a claimed exact peak or a full GPU allocation measurement.

The entire production diary tree was byte/hash identical before and after: **58 files, 52,885,758 bytes, 41,971 newline characters** in each snapshot. No user content, production adapter, settings, or accepted manifest was changed; normal public service PID/log bookkeeping changed during restoration. No model training, commit, push or deployment occurred.

Regression validation at smoke time: **27 controller tests and 22 Python private-HTTP/sleepcheck tests passed**. No production controller or grader edit was required by this smoke. A subsequent Root-requested CPU resource cap adds `-t 2` only for CPU checks; its regression also confirms unchanged Metal arguments. The updated controller suite passes 28 tests. The module hash in the actual-run JSON identifies the pre-cap module that was exercised; the cap does not change the Metal invocation used here.

Evidence: `private-real-smoke.json` records sanitized process, hash, resource, import and restore facts. The local full audit/obligation remain under `/private/tmp/premonition-private-native-mlpmv6y7`. The review artifact deliberately omits private keys, server command lines and per-file diary names/hashes.

Reproduction helpers are `private-real-smoke.cjs` and `private-real-smoke.py`. The Python supervisor requires the exact expected public LFM3 day command and healthy public services, writes a durable obligation before pausing, bounds the controller, and restores only after confirmed private cleanup. The Node helper defaults to the included `fixtures/private-zero-lfm3/fixture.json` and exact 33 KiB GGUF used above; set `PREMONITION_ZERO_FIXTURE` for another compatible zero fixture descriptor. The included held card is synthetic. Coordinate the compute slot before rerunning. Home-relative paths, the included fixture default and an additional fail-closed restoration guard were applied to these helpers after this successful run and syntax checked; they do not change the production Metal code exercised above.
