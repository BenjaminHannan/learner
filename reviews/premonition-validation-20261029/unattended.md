# Premonition improvement session

User authorized work until returning, approximately four hours from 2026-10-29 19:56:08 UTC. Stop new work at **23:56:08 UTC**, or when the user says they are back. A status question does not end the session. Heartbeat `premonition-improvement-session` runs every fifteen minutes until that deadline; pause it at completion. Prefer Terra for routine implementation/testing/packaging and Sol for harder model/evaluation work.

## Workspace and authorization

- Work only in `/Users/ben-hannan/Desktop/projects/premonition-reliability`, branch `codex/premonition-learn-and-sleep-20261029`. The original beautiful-model checkout has extensive existing changes and is preserved.
- Chat and sleep on Ben's Mac must remain **LFM3**. Apex provisioning was cancelled. No rented compute, unrelated jobs killed, third-party messages, or experimental production adapter promotion.
- BENSPC through SSH/Tailscale is authorized for disposable tests. Its GPU is occupied; Windows tests use two CPU threads. BENSPC is not Jacob's laptop.

## Published and installed

- PR288 merged to main as `4d6ed44560ed04e39417fda23787c221450455b7`. Installed Mac1.2.2 runs cached native LFM3 behind gateway8090 and uses lfm3_mps sleep against the standard HF LFM3 checkpoint. Chat's QAD GGUF is a distilled variant; exact underlying weight equivalence and learned-fact transfer have not been established (lfm3-gguf-transfer.md). There is no accepted production adapter, so chat serves base weights.
- Windows1.2.2 is published and was downloaded back from the public URL and hash checked:122830994 bytes, SHA256 `4c45a0d64f9c6311c8d2c53fbb7029d29349ee1fe7f5d67716ba3c1455d0c9af`. Feed:desk/dist/latest.json on main. Jacob must click **Update now**; installation on his device was not observed. Older builds may need **Check for updates** rather than waiting five minutes.
- Backups/manifests:`/Users/ben-hannan/learner-ops/premonition-lfm3-backup-20261029-154045`. Public service restored healthy after the private native smoke at20:50UTC. No pause obligation remains.
- Published validation:sleepmlx221, sleepmode127, Node437 passed/1 skipped, real Electron209. LFM training/save/reload/export/serving plumbing passed. Hidden creative proposals use the same LFM3 fast alias for measured open ideation/story/poetry; constrained plans skip the extra pass.

## Next source batch under review

Draft PR290:<https://github.com/BenjaminHannan/learner/pull/290>. Source commits through `725c03c0`; **not deployed** yet. Version1.2.3 is prepared but the feed remains1.2.2. The external Mac check-in selector patch alone is installed on disk with backups; existing imported processes have not been restarted.

1. Learn cancellation and deadlines, truthful partial/failed starts, child deadline inheritance, protected skill-note storage, and stale saved-card retirement. Frozen b3754930 passed Python235, Node454/1 skipped and actual Electron213. Train-phase checkpoints keep their immutable training snapshot until the next run boundary.
2. Research provenance is record-only:app-assigned origin, observed source-read IDs, exact visible quotes, expiry and durable prepare/body/commit ledger. Audit reports pending/stale/unavailable states. **Attribution is not truth verification; training admission is unchanged.** Contract:research-provenance-contract-v1.json. Full Node508/1 skipped before final durability changes; latest memory36/evidence11 and Python provenance+lessons41 focused checks passed.
3. Windows sleep candidates now have immutable held snapshots, private authenticated engine/grader processes, confirmed cleanup, and an accepted manifest. Unknown cleanup blocks public resume. Unbound legacy exports are preserved but quarantined. Chronology/watermark prevents older pending adapters replacing newer accepted ones. Candidate19/controller28 and Python private+sleepcheck22 focused tests passed. Full frozen integration verification pending.

Full frozen tests passed:Node529/1 skipped and actual Electron213 at32944833, sleepmlx258 including finalization binding at efb035ac, sleepmode127. The draft composer now resizes when panels change chat width; focused actual Electron3/3 passed at bf6a5b38. Full serialized-request context budgeting and active-note edit protection are committed; context-native-tokenizer.json records a real template/tokenizer-only check. Mac check-in/runtime/selector focused16 passed at725c03c0. Native CUA inspection was unavailable because the Mac is locked; no unlock or production UI changes attempted.

Actual native Metal private smoke passed:general8/8 and synthetic held1/1 on/off with an all-zero adapter; both owned children exited, journal removed, public LFM3 restored, entire diary tree byte/hash unchanged. Actual Windows CPU private smoke also passed8/8 and1/1 on/off in~15s, two CPU threads, no GPU,~1.86GiB peak sampled server RAM, both children exited. This proves plumbing only and does not establish training fit on Jacob's8GB laptop. Reports:private-real-smoke.md/.json and private-windows-cpu-smoke.md/.json.

Actual LFM3 research Agent smoke passed3/3:one browser read, one correctly attributed saved card, exact quote, committed ledger, verified:false. Production memory unused. The production diary grew from other traffic during the interval, so no unchanged-diary claim is made; none of the three synthetic fixture strings occurred in appended raw records.

Durable finalizations now bind version/grader/night. Legacy or stale uncommitted passes block without mutating checkpoint/weights; exact already-committed outcomes and valid saved rejections finish idempotently. README and finalization-grader-binding.md document the explicit re-gate limitation.

## Learning experiments

- Twelve-step paired replay:no held-out gain. Continuation replay stays off.
- Fixed64-step prompt control:training0→4/4, held0→3/4, monitor4→4/12, but one previously correct spatial answer became wrong. Strict retention criterion failed; nothing promoted. Runtime209s.
- First continuation attempt aborted after12.2s on sustained pressure2; only the owned diagnostic group was stopped. Public LFM stayed healthy. Resource failure, not a quality result.
- Separate guarded continuation64 retry matched initial hash/full identity/baseline outputs and generated32teacher continuations, but stopped279.8s on pressure2 after32updates (evaluations0/12 only). Publichealth200, owned process group exited. No64endpoint, no quality verdict. Cache/partial reports preserved.
- A500s completion plan/restorer is prepared but no public pause was performed: native processing_slots1 and3 established connections revealed unknown active inference. Actual retry is deferred, and public service stays alive. No polling or interruption of that traffic.
- Offline grader audit found numeric/punctuation false negatives and adversarial false positives. Production GRADER remainsstrict3, old reports unchanged. Sol is prototyping strict4 quantity/punctuation and shared Node/Python grading binding outside the checkout; review and test before application. This cannot retroactively make the failed control pass.

## Next actions

Review strict4 prototype and Windows pending-verdict revision binding; apply only after focused tests and independent review. Rerun affected full suites and real private Windows check after protocol changes. Then freeze final1.2.3 source and have Terra build/verify the Windows ZIP using /private/tmp/premonition-win123-prep/verify.py. Root handles publication and local installation. Release/install only after checks pass. Continue useful work within the authorized window, keeping experimental learning disabled unless broader independent evidence supports it. At the deadline save installed/published revisions, limitations and recovery obligations, then pause the heartbeat.
