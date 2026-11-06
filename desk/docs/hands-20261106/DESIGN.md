# HANDS: a small brain that sees and moves

Date: 2026-11-06. Owner: HANDS. Step 1: design only. **Waiting for the lead's approval before any build.**

**Consent update from the lead, 2026-11-06:** Ben said YES to “learn from watching me”: local screen, mouse, and keyboard recording; pause for password fields and the secure-login window; use recordings only in sleep. Watching Ben is now a primary data source. The proposed watching setting remains OFF until T9 passes and the lead gives a separate go; the earlier ON default is deferred by the build approval. This document does not start a recorder; building and recording still wait for the lead's next approval.

Ben's aim: “Anything a human can do on a computer the AI should be able to do.”

Start with a small, honest piece of that aim: **see a picture, follow the current goal, move, look again.** The big brain chooses what to do. The small brain handles the next tiny move. A separate stop switch always gives Ben the controls back.

## 1. What we know, and what we do not

Labels used below:

- **SHOWN**: a cited paper reports a result, or the named local file contains the behavior. A paper's result is not a test on Ben's Mac.
- **SUGGESTED**: a design choice worth trying. It is not a measured result.
- **UNTESTED**: a claim we must test here before trusting it.

Tiny word key: a **weight** is one learned number; a **seed** makes the same test world again; **latency** is waiting time; **p95** means 95 out of 100 readings are at or below that number. **50 ms** is one twentieth of a second. A **held-out day** is saved experience the net is never allowed to study during training. A **lease** is the stop switch's short-lived permission to move.

**SHOWN, code read today:** the branch is always-on in ~/learner-ops/desk-always-on. The first successful repo check was git status --short --branch. It showed only desk/.build-noci.sh and desk/node_modules as untracked. Neither was changed. ~/learner-ops itself is not a Git repo. This design lives outside the app repo.

**SHOWN, local code:** desk/src/games/core/loop.js feeds adapter.features(adapter.rawFrame(...)) into a small MLP. The net returns one numbered move. schedule.js handles timed moves. intent.js validates a fixed list of calls and keeps the last call after two seconds, marking it stale. plan.js keeps steps and checks progress. reflex.js learns from saved day logs during sleep and keeps an older model for rollback.

**SHOWN, limits:** these “frames” are saved game numbers, not screen pixels. The existing sleep split is the first 80% versus last 20% of each day; it is not a whole unseen day. The local document desk/docs/two-speed-core.md also names a missing older-day check on the first night. We need stronger checks for the new net.

**SHOWN, Bedwars files:** desk/src/games/bedwars/core-iface.js has an asynchronous LiveLoop. Its README says “No real play loop yet”: session.play watches match status and logs. There is no finished, fast, local key-press path. Some older core documentation says live wiring is still missing; the newer LiveLoop exists, but real key control is still missing.

**SHOWN, important stop gap:** desk/src/hands.js says its idle-clock fallback cannot see Ben's input during Glim's action. Its tagged Mac input watcher can see it. A two-second Bedwars poll is also too slow. Neither fallback is enough for fast hands.

**UNTESTED:** pixel-to-action speed on this M1, screen-capture cost, Windows input release, GUI skill, and Minecraft skill. No pixel model exists or was benchmarked in this design step. No latency number below is presented as a measurement from Ben's machine.

## 2. Short research scan, 2024–2026

These are primary sources checked on 2026-11-06. This is a short scan, not a claim to cover every paper. No model, footage, or dataset was downloaded.

| Work | What the authors show | What it suggests for Glim; what remains untested |
|---|---|---|
| [SIMA, Google DeepMind, March 2024](https://deepmind.google/blog/sima-generalist-ai-agent-for-3d-virtual-environments/) | **SHOWN, authors:** an agent can follow language using screen images and keyboard/mouse actions across 3D games. Its early tasks are short. | **SUGGESTED:** use the same eyes-and-hands door for different games. **UNTESTED:** broad desktop work or our Mac's 50 ms goal. |
| [Cradle, Tan et al., 2024 preprint](https://arxiv.org/abs/2403.03186), [2025 publication](https://proceedings.mlr.press/v267/tan25h.html) | **SHOWN, authors:** a modular planner uses screenshots and low-level keyboard/mouse control for games and software. The [official code notes](https://github.com/BAAI-Agents/Cradle) that fast combat may require pausing for the large model. | **SUGGESTED:** keep planning and moving separate. **UNTESTED:** a slow screenshot/reason/tool loop meeting real-time play without pauses. |
| [TinyVLA, Wen et al., September 2024; revised 2025](https://arxiv.org/abs/2409.12514) | **SHOWN, authors:** compact vision/language policies improve robot-control speed and data efficiency versus their larger comparison model. | **SUGGESTED:** a small vision-to-move network can be useful. **UNTESTED:** transfer from robot tests to mouse precision or text entry. Do not copy its robot results as desktop speed. |
| [SmolVLA, Shukor et al., June 2025](https://arxiv.org/abs/2506.01844) | **SHOWN, authors:** a smaller robot policy separates prediction from action execution and runs them asynchronously. | **SUGGESTED:** keep capture, prediction, and input as separate workers. **UNTESTED:** a robot policy's weights or timing solving Glim's tasks. |
| [Real-Time Execution of Action Chunking Flow Policies, Black et al., June 2025](https://arxiv.org/abs/2506.07339) | **SHOWN, authors:** predicting the next short move list while the old one runs can reduce stops and tolerate model delay in robot/simulator tests. It does not erase observation delay. | **SUGGESTED:** use a persistent worker and a tiny, cancelable action queue. Start with one move per picture, not a long blind script. **UNTESTED:** benefit from longer chunks here. |
| [NitroGen, Magne et al., January 2026](https://arxiv.org/html/2601.02427v1) | **SHOWN, authors:** a 500M game policy learns from 40,000 hours across 1,000+ games. Labels come from visible controller overlays, not ordinary inverse dynamics. Evaluation pauses the game clock; real-time/asynchronous deployment is left for future work. | **SUGGESTED:** shared visual action models can span games. **UNTESTED:** its results proving live 20 Hz control. **Excluded here:** its weights and outside gameplay data. |
| [The Latent Bridge, Li and Shi, June 2026](https://arxiv.org/abs/2606.24470) | **SHOWN, authors:** a learned channel between slow and fast models helps some Atari tasks, but not every domain. Their models are billions of weights. | **SUGGESTED:** intent matters, and it needs a control test. Keep our simple, checked intent channel first. **UNTESTED:** a learned hidden channel helping this tiny net; it adds needless work for the first toy. |
| [Pixels to Keys, Pillai et al., September 2026](https://arxiv.org/abs/2609.37907) | **SHOWN, authors:** inverse-dynamics models infer inputs from video, but camera motion, delayed effects, and rare keys cause uneven errors. A high overall score can hide bad rare-action labels. | **SUGGESTED:** train our own label guesser in sleep, score each key separately, and allow “I cannot tell.” **UNTESTED:** reliable labels from Ben's particular footage. |
| [cua-speedrun, Aggarwal et al., September 2026](https://arxiv.org/html/2609.40284v1) | **SHOWN, authors:** their FastCUA path measures 2–28 ms from action to next observation. This excludes deciding the action. Very fast pictures can arrive before the app changes. | **SUGGESTED:** remove tool-launch and image-conversion delays; check that the app actually reacted. **UNTESTED:** total frame-to-action latency on this Mac. The two measurement directions are different. |
| [Self-Improving Video-to-Action Models, Ryu et al., October 2026](https://arxiv.org/abs/2610.24177) | **SHOWN, authors:** Mirror uses its own interaction video/action pairs to improve video-to-action mappings. | **SUGGESTED:** Glim's own attempts are useful data. **Excluded:** copying its interaction/training cycle while awake. Moving all updates to sleep is our proposal, **UNTESTED** here. |

**SUGGESTED decision:** build a much smaller purpose-made policy first. Do not load a second language brain, a world-video generator, or an outside gameplay model. Research supports the parts; it does not show that a tiny home-grown model can already do everything.

## 3. The proposed small brain

### Eyes and the goal card

**SUGGESTED inputs:**

- Capture only the task window at 60 pictures/s when fast hands owns it. Use a lasting native capture stream, not a fresh screenshot program for every move.
- Make decisions at **20 times/s**, one every 50 ms. Each decision takes the newest picture; drop older waiting pictures. One picture may be waiting, never a growing pile.
- Each picture has a **320 × 180 RGB overview** with padding to keep its shape. Also take a **192 × 192 RGB detail crop** at native pixel scale, around the current target or cursor. Keep the last four overviews and their times, about 150 ms of motion. Encode each new image once, caching past features in memory.
- The goal card contains a checked intent code, checked arguments, step ID, intent version, task-window ID, coordinate map, allowed keys, and a stop/deadline value. Examples: CLICK target=blue-circle; DRAG target=red-box destination=tray; TYPE text_ref=17; FIND_SCROLL target=green-star; or the existing Bedwars calls.
- A target can be a small picture patch or a checked screen region chosen from an earlier screenshot by the planner. It is not a hidden game coordinate or a DOM answer. A moved target must be found again in current pixels. New targets outside the detail crop are first located in the overview, then revisited with the detail crop.
- The plain target words remain on the goal card. The first toy uses a small fixed vocabulary and no extra language model. Exact text to type is an explicit task string, stored locally behind text_ref. The small brain chooses when/where to type and which next character; it does not invent the text.
- Cursor position, our own held keys, last action, and elapsed time are allowed bookkeeping. AX/DOM checks may guard privacy and focus; they must not supply task answers to the pixel policy.

**UNTESTED limitation:** tiny overview pictures will lose small text. The detail crop is a testable answer, not a promise. First toy targets must remain at least 12 overview pixels wide. Tiny menus, unseen words, multiple monitors, arbitrary text understanding, and arbitrary unseen games are later tests. Unknown intent means stop and ask the planner to choose another step.

### The little network

**SUGGESTED:** start with a roughly **6–10 million weight** model, hard limit 12M for the first toy. A small convolutional image reader keeps spatial maps, so a button's position is not lost. A small recurrent memory combines recent maps, the goal card, and past actions. Separate output heads choose movement, buttons/keys, and timing. “Head” just means a different answer box on the same net.

Use FP16 first. At 10M weights that is about 20 MB for weights; **UNTESTED** total worker-memory target is at most 512 MiB, including pictures, runtime, and work buffers. Count actual weights and measure actual memory after approval. There is no diffusion loop and no text-token generation on the fast path. Random initialization, every image-reader update, and every policy update happen inside sleep. Awake code loads fixed weights and runs inference only; use evaluation mode with no changing normalization statistics. Short-term memory can change; learned weights cannot.

On the **M1**, use a persistent local inference worker beside Glim's one existing brain. Try Core ML FP16 CPU/ANE execution first; if unsupported, measure a CPU or MLX/Metal version rather than assuming it is fast. Start training work with ~/learner-ops/nb2-venv or a uv venv, never system Python's missing torch. Export the tested artifact in sleep. It must pass beside the normal app and beside its existing brain when that brain is legitimately running. Do not start another brain for that test.

On **BensPC**, run capture → small net → input on Windows beside Minecraft. GPU FP16 is an option only while the GPU loan and user-idle gates allow it. The Mac sends goals, not 20 network round trips per second. Slow communication or a missing heartbeat makes the Windows worker stop. The fast path must not depend on SSH, the server truth log, or a server-side nudge.

### What comes out

**SUGGESTED:** one bounded packet per decision:

    frame_id, intent_version, window_id, lease_id
    mouse_dx, mouse_dy, wheel_dy
    desired_mouse_buttons, desired_keys
    next_character_from_text_ref_or_none
    time_to_go_ms, hold_ms, expires_at, confidence, stop

Mouse dx/dy is relative movement in desktop points; the worker maps it to display pixels and clips it to the task window. A click is a down then up transition. A drag keeps the chosen button down across fresh decisions. Key and button sets mean “what should still be held,” so the helper sends only changes. Start with a 50 ms hold limit; it needs a fresh decision to renew a hold. An independent expiry check releases Glim-owned keys and buttons if the next decision never comes. Do not release keys Ben owns.

For ordinary text, emit at most one checked Unicode character each tick into the verified field. Games use checked physical key codes. No clipboard dumps, secret typing, or long uninterruptible typing commands. Apply keyboard-layout mapping outside the learned net. Add scroll because “scroll to find” needs it.

Timing is a proposal, not permission to send a long script. Recheck a pending timed move on every new frame and cancel it on a changed intent, missing target, changed window, or user input. Normally execute only the next packet. Future chunk experiments may predict two packets but may not commit both blindly.

### Measured latency budget: what to measure, and the current blank

**No local pixel-to-action measurement exists yet.** Filling this blank requires the later approved toy build. The current core's reflexP95Ms measures only feature/rule/net work inside a simulated tick. Its test's “less than 5 ms” assertion does not include capture or OS input, and is not evidence for our full goal.

All rows here are **SUGGESTED engineering allowances**, not results. Measure the total directly; adding separate p95 values does not give a true p95.

| Part | Allowance | Local result today |
|---|---:|---|
| Frame produced → capture callback, including buffer delay | 8 ms | Unmeasured |
| Resize/crop, copies, local handoff | 4 ms | Unmeasured |
| Image reader + memory + action heads | 18 ms | Unmeasured |
| Focus/privacy/lease check and OS input call | 4 ms | Unmeasured |
| Wake-up and scheduling slack | 6 ms | Unmeasured |
| Planned total | 40 ms | Unmeasured |
| Extra room before the goal is missed | 10 ms | Unmeasured |

After approval, stamp frame production, capture arrival, model start/end, input send, and sandbox input receipt on one machine's monotonic clock. Capture timestamps need conversion to that clock and a checked mapping. Use the sandbox's receipt time for **frame → action**. Also report capture-arrival → action, visible-event → action, and action → changed-screen separately. A fast send is not proof that the app reacted. If a frame is dropped, still report the gap and missed deadline; do not hide slow work by counting only sent packets.

The pass goal is **p95 frame → action ≤ 50 ms**, p99 ≤ 75 ms, with at least 99% of required 20 Hz decisions meeting their 50 ms period. Report worst cases too; this is not a claim of a hard real-time OS guarantee. A sudden screen change can also wait for the next capture/decision, so visible-event reaction has its own p95 ≤ 100 ms mark. Measure 10 minutes after warm-up, and report cold-start cost separately, at a fixed display rate and power mode. Include normal Glim load, thermal state, CPU/GPU use, memory, and dropped frames.

**SHOWN elsewhere only:** FastCUA's 2–28 ms result concerns action → observation in its own environment, not our net. **UNTESTED here:** the 18 ms inference allowance and 40 ms total. If they fail, shrink the image reader/copies or reject this model. Do not rename a 10 Hz result “20 Hz.”

## 4. Plugging into the existing loop

**SUGGESTED changes after approval:** keep IntentChannel, PlanMemory, and ActionSchedule. Add a pixel-reflex boundary instead of pretending that pixels fit the old small MLP.

1. A capture worker provides a frame handle, timestamp, and coordinate map. Do not put image arrays into JSON on every tick.
2. The existing planner updates the checked goal card asynchronously. Calls can arrive seconds or a minute late; hands never waits for one during a tick. Tag replies with the originating step/version and discard replies for canceled tasks.
3. In loop.js and LiveLoop's current reflex branch, choose either the existing feature reflex or PixelReflex.predict(frameHistory, checkedIntent, ownInputState). The pixel API returns a packet and optional visible timing measurements; the old API still returns a numbered move. Use a wrapper to translate sandbox moves, not an implicit cast from a packet to an integer.
4. The pixel timing head estimates a visible gap/contact time and uncertainty. Feed supported gap measurements to ActionSchedule; its existing timing-correction hook can remain. Never give the pixel path adapter.timedTargets values derived from hidden game state. Where no visible gap exists, use a bounded, rechecked time-to-go proposal. One input arbiter resolves scheduled versus direct button commands; it must never fire the same jump/click twice.
5. Move plan progress checks to screenshot-visible completion checks or a pixel progress head trained in sleep. Existing privileged game state can grade/log outcomes, but cannot feed policy, timing, urgent rules, or progress in a run called “pixel only.” General focus/privacy checks are allowed.
6. A native input worker checks the stop switch and applies the packet. Log the chosen action, what was really applied, and why something was rejected. Saved image chunks live beside compact day records, not inside the old scalar-frame format.
7. Extend the sleep hook to train/export a pixel artifact and compare it with the old one. Keep the old feature reflex as a named baseline and optional explicit fallback; never quietly use it and count its success as pixel-model success.

The last intent may stay in IntentChannel when stale, as today. **SUGGESTED extra rule:** stale does not mean an endless held key. Every packet still expires. A safe, valid current step can continue while the brain thinks; stop at completion, surprise, missing target, or step timeout. Default step limit is 30 s for the toy. Longer game steps need explicit renewal. After Ben takes over, clear all pending work and require a new task lease; an old goal must not restart hands.

## 5. Ben's stop switch comes before the net

**SUGGESTED, required before real input:** a local native guard listens for physical mouse movement, mouse buttons, wheel, and keyboard input. Mac events sent by Glim keep the existing GLIM tag. Windows needs a proven way to separate physical input from Glim's marked/injected events. The native guard, not a JS promise or the neural model, owns input permission and held-key release.

Any Ben input first cancels the lease, flushes queued moves and timed moves, then releases only Glim-owned holds. Check the lease again immediately before every OS send. Resolve input/stop races in that same helper. Nothing waits for the next 50 ms policy tick. No automatic resume. Stop on focus loss, app/window change, screen lock, missing watcher, capture failure, or worker/connection failure too. While watching Ben, his input is what gets recorded; the action lease stays off throughout. Observation can resume after safe checks; autonomous control never resumes from a recording.

**UNTESTED stop target:** physical input → lease revoked and Glim holds released p95 ≤ 10 ms, maximum ≤ 20 ms in the toy; no new non-release Glim events after the revocation point. OS events already delivered cannot be pulled back. “Instant” means the earliest native callback can stop us, with the delay measured honestly. Test real-device input later as well as injected test events. Unknown input ownership means do not start.

Existing app permission/category rules still apply before a task starts. The net cannot approve actions, change permissions, send messages, publish, spend, or choose a new app. This design gives no permission to use Ben's controls now.

For any real-brain use later, use ~/learner-ops/bin/realmodel-lock.sh <owner> <cmd>. Never launch a second copy of Nanbeige on the active M1. No brain use was needed for this document. Sleep/training yields to Ben and runs outside the app's main process. It may pause and resume its saved job; it never updates deployed weights while awake.

For BensPC later: read GPU_LOAN.txt through the existing supported path; SOUND-5's approximate 16:45 ET end today is not permission by itself. Check both a free loan and no active user before acquiring anything. If busy, defer. Input, unlock, lost ownership, or a new loan stops our work. Stop only our own tracked processes by exact PID. This step did not contact BensPC or take its GPU.

## 6. Learning in sleep, in this exact order

The awake job is to act with fixed weights and keep allowed experience. The sleep job is to learn from that experience. **No awake gradients, optimizer steps, RL updates, encoder fitting, or self-modifying action rules.** Grow-then-squeeze is the only other allowed weight-change route; it is not used in the first toy. If used later, do that work in a scheduled sleep window as well, so every net still trains in sleep.

Keep this source order: first Glim's own outcome-labelled attempts; second Ben's paired demonstrations; third inverse-dynamics guesses. The first two are **primary sources**. Ben's normal allowed computer use should supply much of the paired data each day, rather than being a rare optional extra. Guessed labels remain secondary. The order is a trust/processing order, not a reason to postpone collecting Ben's approved demonstrations after build approval.

### First: Glim's own attempts, with outcomes

**SUGGESTED:** start with Glim acting in its own sandbox. Use the existing hand-rule controller for seed attempts, clearly tagged as Glim/rule actions. Carefully bounded random attempts in the sandbox can add failures. This keeps the toy runnable even if Ben later turns watching off. Do not explore randomly in real apps.

Each saved row points to local pictures and includes day/session/episode, frame and input times, checked intent/version, window and pixel map, held-state before/after, proposed and applied actions, policy hash, source, stop/privacy flags, and outcome. Outcomes include success, failure, timeout, wrong target, accidental click, and takeover. Keep truth/outcome files separate from the live input. End Glim's attempt on takeover. Ben's later activity can enter a separate demonstration session only when the watching setting is on and the privacy checks pass; never attach his keys to Glim's action labels.

In sleep, imitate verified successful steps, including successful recoveries, with more weight on clear outcomes. An episode failure must not mark every earlier move as wrong. Keep failures for outcome/error prediction and known bad-action examples, not as correct actions to copy. Optional slow-brain labels can judge visible clips under the realmodel lock; uncertain labels stay uncertain. Do not turn a reward number into an imaginary correct mouse move. Training from these fixed logs is supervised learning, not an awake RL loop.

### Second: watching Ben — primary data, agreed on 2026-11-06

**Authorization received:** the lead reports Ben's explicit YES. Do not ask him again for the same recording permission. Still do not build or record during Step 1. The following is the proposed behavior after the lead approves implementation and recording, and the recording guard passes its fake-data tests.

**SUGGESTED setting:** Settings → Learning → **Learn from watching me**, **OFF during the toy**, until T9 passes and the lead separately arms recording. Ben has agreed, so the earlier design intended ON after release; the lead's newer build order takes precedence. Do not silently turn it on for another user. Honor an existing explicit OFF and remember later changes. Beside the switch, say: “Saves this screen, mouse, and keys here. Learns during sleep. Pauses for passwords.” Show an always-visible recording dot, the current window, storage used, and a short paused reason. Give Pause, Resume, Off, and Delete this session controls. Off stops capture and input logging immediately, clears the unsaved RAM buffer, and persists across restarts. A later app launch does not undo OFF. No new per-session permission prompt is needed.

When ON, record Ben's foreground, supported safe app window while he uses it. This is normal passive collection, not a request that he perform special demos. Record one task window, not other displays, background windows, microphone, or clipboard. Pause after five seconds without physical input, on screen lock, or when no supported safe window is active. Glim cannot issue actions in a demonstration session. Stopping a recording never starts control. A live authorized task uses fresh screen frames and the current goal, never a playback of Ben's saved session.

**SUGGESTED recording rate and contents:**

- Screen: **20 frames/s**, at most **1280 × 720 RGB**, preserving aspect ratio. Hardware-encode locally as H.264 at a target **2–3 Mbit/s**, in short chunks no longer than 30 s. Keep a one-second RAM safety buffer before any chunk is committed. Record actual frame times and dropped-frame counts; do not invent missing frames.
- Detail: save a **192 × 192 native-pixel crop at 20 frames/s** around the physical cursor or focused non-secret field, with its screen map. Use the same privacy checks and a small separately compressed stream. This preserves tiny text that the overview loses. The trained policy still gets its 320 × 180 overview plus detail crop. The exact codec/cost is **UNTESTED**.
- Mouse: save physical x/y, movement, button down/up, and wheel events with monotonic timestamps. Coalesce movement to **at most 120 samples/s** while preserving movement endpoints. Do not drop button or wheel transitions; include the last held state in each frame record.
- Keyboard: save each physical **key down/up transition**, modifiers, layout, and permitted non-secret text-composition/commit events at the event's actual rate. There is no fake fixed typing rate. Do not log repeated copies of a held key. Filter secrets before event serialization. A complete held-state snapshot at each frame helps align actions to pictures.
- Context: save safe app identity, local window/session IDs, window bounds, display scale, privacy-state generation, timestamps, source=Ben, and frame/event alignment. Do not store window titles, URLs, file paths, or document text as extra metadata. Visible non-secret content remains in the approved screen recording.

In sleep, read these paired screen/input sessions as a main source for both the pixel policy and label guesser. Infer task/intent labels only then; mask uncertain goals rather than pretending Ben's intent is known. Correct text examples can come from allowed visible typing. Balance batches across tasks and rare keys so a long day of ordinary typing does not erase game skills. Keep Ben's source flag distinct from Glim's attempts. Outcome labels for demos are verified or unknown, never automatically “success because Ben did it.”

**Required privacy behavior:** pause both screen streams and every mouse/keyboard log before saving when a password field is focused, secure keyboard entry is active, a sign-in/password-manager/system-auth window appears, or Glim's private secure-login form is open. Block the whole login window, not just the password characters. Wire an explicit pause signal from the app's login form before it appears. Use browser password-field and native accessibility secure-field signals where available. Use an app/window allowlist and pause the whole session when field/window safety is unknown. OCR or a neural “looks like a password” guess is not the main guard.

Privacy checks happen before bytes reach the logger, encoder, or training queue. Frame/event chunks stay briefly in RAM, tagged with the checked focus/window generation; discard pending chunks across a login transition, including a one-second pre-transition buffer. No save or automatic resume while safety is unknown. Resume only after a safe view and Ben pressing Resume. Tests must cover the first frame of a popup and focus races, not just an already-open password box. Perfect secret detection in arbitrary apps is **UNTESTED**; unsupported apps remain unrecordable.

**SUGGESTED disk budget and retention:** use a private local directory outside cloud sync, repo history, and telemetry; restrictive file permissions and the machine's existing disk protection. Never transfer Ben's recordings to BensPC or any model service. BensPC can receive an approved trained artifact later, not his raw desktop sessions. Keep **at most seven days**, a **hard 3 GiB/day** of new recording bytes, and **12 GiB total** for source clips, input logs, pseudo-labels, thumbnails, and held-out/audit clips combined. The detail stream counts too. Model bundles have a separate **1 GiB** cap for current/candidate/previous artifacts. Keep at least **10 GiB free** on the machine. These are proposed caps, not measured usage.

At 2–3 Mbit/s, the overview alone uses about 0.9–1.35 GB/hour in decimal units. Detail/event overhead is additional; **UNTESTED** until measured. The byte caps, not a guessed hours estimate, decide when to stop. Delete expired chunks and their derived files first. At the total cap remove the oldest unpinned data; if pinned tests prevent enough space, or the daily/free-space cap is reached, pause collection and show why. Never block Ben's work or delete his personal files. Pinning does not bypass caps or extend the seven-day retention without a new choice. The sleep experiment must finish within that window or collect a new sealed day.

Off keeps existing allowed data until its normal expiry; Delete also removes selected clips, events, labels, and derived caches and excludes them from queued sleep jobs. A net trained on deleted data needs rollback to a clean model or a later clean rebuild; deleting a file does not magically erase learned weights.

**Recordings are used only in sleep.** While awake, the recorder may check privacy, timestamp, encode, save, show recording status, and enforce storage limits. It may not replay/analyze saved footage, make task labels, retrieve it into chat or the planner, train any net, or issue actions from it. Sleep may process the recordings and train frozen candidates, but still cannot press keys or play games. A candidate must pass the seatbelt before later awake use. This keeps “watching me” separate from “doing something for me.”

### Third: guess labels for allowed video

“Inverse dynamics” means: **look before and after, then guess which move caused the change.**

**SUGGESTED:** in sleep, train a separate small label-guessing net from Glim's own paired pictures and actual applied input, then Ben's approved paired demonstrations as a primary source. The guesser can see nearby future frames because it works offline. The acting net sees only the past/current frames. Give the guesser the window scale, keyboard mapping, and mouse sensitivity; split tests by whole session/day.

Then label only allowed unlabelled clips: Glim's own saved video or footage Ben supplies. For Minecraft/Bedwars, **no VPT weights, VPT labeler, NitroGen, MineRL, or other outside gameplay data or gameplay-pretrained weights.** Train the labeler and encoder locally in sleep from the allowed sources. No public GUI dataset is proposed for the first toy; dataset list: **none**.

Use per-key precision/recall, macro-F1, click transition F1, mouse error, and coverage on held-out paired sessions. Do not let “no key pressed” dominate the score. Admit a pseudo-label only above a confidence threshold fixed on validation data: accepted key/click labels need ≥95% precision, and accepted mouse labels need median error ≤5% of the window's short side. Report how much footage was rejected. Unknown typing, invisible clicks, menus, cuts, lag, and camera/input ambiguity get masks, not invented ground truth. Do not guess exact passwords or invisible text. Cap pseudo-labelled samples at 25% of each batch initially and give them half the weight of paired labels.

**UNTESTED:** enough accurate labels or useful Minecraft skills emerging from small local data. If the labeler fails, use paired Glim/Ben data only. Ben can always turn watching off; that must not disable Glim's existing tools.

### Sleep's keep-or-undo check

**SUGGESTED:** train a candidate copy; never overwrite today's acting net. Split by whole days and sessions before making windows, augmentations, or pseudo-labels. Keep a complete older day that never enters any optimizer, including the encoder and inverse-dynamics optimizer. Keep a second untouched audit set so repeated model choices do not wear out the same test. Freeze thresholds before looking at either test.

Replay the saved held-out clips in sleep to compare action labels, timing, and safety decisions with yesterday's model. These are offline checks, not a claim that a new action would have succeeded. No games or new task rollouts run in sleep. Export and benchmark the whole artifact, including image reader and runtime format. Weight hashes must stay fixed throughout every awake session.

At first there is no old pixel net, so the hand rule is the safe default. No automatic promotion on night one without an older held-out day. Keep a candidate quarantined until the next approved daytime sandbox test. For later joint image-reader/action updates, accept or reject the **whole bundle**; mixing a new encoder with old heads can silently break them.

Keep the previous artifact, schema, mappings, data manifest, and hashes. Switch atomically only between sessions, with no held keys. A crash, failed check, missing older day, or harmful candidate keeps the previous bundle. Test rollback with bad labels and a broken artifact. Export/quantization must not bypass the seatbelt.

## 7. First toy on the Mac: pass marks fixed now

**SUGGESTED experiment, UNTESTED results:** no build or run happens in this design step. The lead must approve the design first. Freeze this file's hash before collecting test outcomes. Failed marks stay failed; changes need a new marked experiment.

### A small playground

One local sandbox window, fake content only, with actual pixels rendered in real time:

1. Click a requested button among decoys. Success: the intended button receives the click, no decoy clicked, within 30 s.
2. Drag a shape into its matching tray. Success: it lands inside and the mouse is released, within 30 s.
3. Fill a requested field with a supplied 8–20 character string. Success: exact text in the right field, no edits to other fields, within 30 s.
4. Scroll to a requested item and click it. Success: the right item receives the click, within 30 s.
5. A pixel-rendered **Sparks quest**, using desk/src/games/adapters/sparksquest.js and the existing realtime.js game. Add only the view/input wrapper after approval. Success: finish its six-checkpoint goal without dying, within 60 s of real clock time. Include its existing surprise/replan situation. The game must not pause for inference.

Vary positions, colors, decoys, layouts, scroll distances, target sizes, and in-game hazards. The scorer may read sandbox truth after actions; the pixel policy must not. Input receipt and the resulting screen are both logged. Start with sandbox-routed events that cannot touch Ben's desktop; later the native-helper test targets only that sandbox window with a valid lease.

Use **seeds 101, 202, 303** with **10 episodes per GUI task per seed**, and **10 Sparks episodes per seed**, per controller: 120 GUI episodes plus 30 game episodes. GUI/game content streams are identical across controllers. Use fixed seed streams for training/initialization too, log them, and keep test scenes out of training. Report each task and each seed, not just a pooled score. Use paired episode comparisons and a 95% bootstrap interval over paired episodes; with only three seed groups, these are toy evidence, not a broad generalization claim.

### Same jobs, four controllers

- **A: slow brain alone.** The existing single Nanbeige instance sees screenshots through Glim's existing eyes path and emits direct actions. No fast task policy, rule teacher, speculative replay, or paused game. Its first-token delay counts. Use realmodel-lock for every real-model command, only when allowed. No model download, second brain, or paid API. Run serially on the Mac when Ben is away. If unavailable, report this comparison incomplete; a stand-in cannot pass this mark.
- **B: existing hand-rule reflex.** Use the unchanged Sparks fallback and its normal feature inputs. For GUI, write a small declared rule controller in the later sandbox, with visible target geometry and exact text from the goal card. There is no existing GUI rule reflex to pretend we already have. Name that addition plainly. This is an intentionally strong reference; its extra structured inputs are listed. Also run a screenshot-only rule variant if feasible, but do not substitute it for B after seeing scores.
- **C: yesterday's pixel model W0**, with fixed weights.
- **D: the candidate pixel model W1 after one more sleep**, with fixed weights.

For B/C/D, give the same checked tactical goal sequence on the same clock, independent of the controller's secret state. First do this controlled comparison to isolate hands; then run a separate smaller end-to-end check with the real slow planner and C/D. No claimed end-to-end success may come solely from supplied perfect goals. All controllers share input bounds, deadlines, scoring, and stop guards. Randomize controller order to reduce warm-up/temperature bias. Slow-brain delays include measured long tails; do not assume the old 0.5–2 s stand-in is accurate.

### Show that sleep helped

Before W0 exists, set aside a whole older collection day H using Glim's rule-controlled attempts. It never becomes training data. A later day D1 supplies paired attempts for the first sleep to make W0. Awake day D2 uses fixed W0 in the sandbox and collects its attempts/outcomes; the next sleep makes W1 from allowed training days. No new games run during either sleep.

The following awake test session compares W0/W1 on sealed H task instances and on the fresh seed suite above. Split any near-duplicate source video by session before choosing days. H replay checks happen offline; closed-loop success requires these awake sandbox runs. W1 remains a test candidate until all keep marks pass. If days of data do not exist yet, wait and report “not enough days”; relabelling neighboring frames as different days is not a valid test.

### The marks, and exactly what proves them wrong

| ID | Pass mark, fixed before the run | Result that proves it wrong |
|---|---|---|
| T1: useful GUI hands | W1 ≥90% pooled GUI success, each of four tasks ≥80%, and each seed's pooled GUI score ≥80%. | Any listed score below its mark, including wrong-field or decoy actions counted as failures. |
| T2: real-time game | W1 ≥70% Sparks goal success pooled, each seed ≥60%; the game runs against wall time. | Lower score in any required bucket, or any clock pause to wait for the agent. |
| T3: comparisons | W1 GUI score no more than 5 percentage points below B; Sparks no more than 10 points below B. Against A: W1 game score ≥20 points higher and successful GUI median completion time ≤half A's, with W1 GUI success no more than 5 points lower. | Any bound missed. If A has no GUI successes, report that explicitly and use its 30 s capped time per episode for a separate capped-time comparison; do not invent a success-time median. Missing real A runs leave this mark incomplete. |
| T4: hands move quickly | 20 decisions/s with ≥99% periods met; ≥10 and target 20 **applied, non-noop action packets/s** on a 60 s continuous target-tracking/typing probe. Reach 20/s within 1% tolerance for the full target. A hold refresh, empty packet, or down/up pair does not count as two decisions. | Below 10 useful packets/s fails minimum; 10–<19.8 means partial speed only, not the full goal. Excess repeated clicks or junk text fails usefulness rather than improving the count. Report actual per-task rates; do not force idle GUIs to click 20 times/s. |
| T5: quick reactions | Directly measured p95 frame→sandbox input receipt ≤50 ms; p99 ≤75 ms; visible-event→receipt p95 ≤100 ms; frame drops <1%, in a 10 min mixed task run under normal Glim load. Repeat beside its one existing brain only when allowed. | Any mark missed, timestamps lacking a checked clock mapping, counting inference time alone, or omitting the loaded run. Cold starts and worst stalls must be listed. |
| T6: sleep improved it | W1 fresh-suite aggregate success ≥10 points above W0, paired 95% interval for the gain above zero, no task drops >2 points. On H, action macro-F1 and timing error do not worsen; closed-loop H success drops ≤2 points. W1 still passes speed and stop marks. | Gain too small/uncertain, any forbidden H use in training, any harmful bucket, slower than budget, or replay label accuracy presented as closed-loop success. |
| T7: obeys the goal | In 30 paired goal-switch scenes per seed, a switch changes the required target/action; W1 follows it ≥90%. Shuffled/old intent lowers correct-target success by ≥20 points. Old-version packets never execute. | Any bound missed, shuffled intent having little effect, or one stale-version packet applied. This would show the net is ignoring the goal card. |
| T8: Ben wins | 100 random takeover times per seed during motion, drag, held movement, and typing. Lease revoke/release p95 ≤10 ms, max ≤20 ms; zero non-release events after revocation, zero stuck Glim holds, zero automatic resume. Test missing watcher, worker crash, focus loss, and lost link too. | Any forbidden event, stuck hold, missed timing bound, fallback to idle-only detection, or automatic restart. Native-device tests still required before desktop deployment. |
| T9: recording guard | With fake passwords only, 30 transitions per seed: password focus, secure-login popup, app switch, unknown field, and pause/delete. Zero private pixels/keys reach disk, model, labels, or logs; no auto-resume. ON is the agreed default; explicit OFF persists and stops logging immediately. Exercise seven-day expiry, 3 GiB/day, 12 GiB total, and low-free-space stops with small test caps. Saved footage has zero awake readers except storage/recording-status controls, and cannot feed input commands. | One leaked secret/frame/key, accepting an unknown context, recording after OFF, overriding stored OFF, exceeding a cap, awake footage analysis, or an action sourced from a recording. Fake-data guard tests and the lead's build approval must precede recording Ben. |
| T10: fixed weights and undo | Encoder/policy/labeler hashes unchanged throughout awake runs; no awake training API/optimizer loaded. Bad-label candidates and broken exports rejected 3/3 seeds; rollback restores old hashes and output traces. | One awake weight/statistics update, accepted bad artifact, missing previous bundle, or mismatched rollback. |

Also report mouse overshoot, extra clicks, exact-text error, key/button holds, action-to-screen delay, and timing error for jump events. Count timeouts, crashes, invalid actions, and stop violations; do not delete bad trials. A fixed-goal toy pass proves a small skill set, not “can use any computer.”

## 8. After the toy

**SUGGESTED gates, in order:**

1. **Real Mac input, sandbox only.** After toy pass, prove the native takeover path with physical devices while Ben has chosen a test window. His demonstration consent is already received; recording still waits for implementation approval and the recording guard. If the machine is in use, defer the control test.
2. **Ordinary apps with fake files.** Click, drag, type, scroll in TextEdit and a local test webpage; then another app/layout not used in training. Use temp profiles and throwaway logins. Pass the same success, latency, privacy, and takeover marks before access to personal work. Existing quiet browser/file tools remain useful; screen hands is another route, not a reason to force every task through pixels.
3. **Better sleep data.** Use both own successful attempts and Ben's approved demonstrations as the main daily data. Then add trustworthy inverse-dynamics labels. Improve exact text, tiny targets, moved windows, and unseen layouts. If a bigger teacher is needed, grow and squeeze in sleep, then re-run the full bundle checks. Do not promise broad skill from a few toy episodes.
4. **Minecraft on a free BensPC.** Check GPU_LOAN.txt and user activity, obtain the existing resource lease, and run the small policy beside the client. First use a private practice world: look/stop, walk to a visible block, turn, jump, place, recover. Keep the Windows physical-input guard active. Prove camera sensitivity, held-key release, capture timing, and local frame→input speed before combat.
5. **Bedwars last.** Plug into the existing session/LiveLoop and 9-call vocabulary. Build the missing local capture/action driver through the intended client control path, after checking it produces normal client input. Never substitute truthkit velocity nudges. Use Ben-supplied footage and Glim's own allowed attempts only. Server truth grades hits, placements, falls, and outcomes after the fact; it never supplies hidden positions/reach to the pixel policy. First prove safe solo skills, then a controlled opponent, then a complete match. A one-player practice model is not a Bedwars win.

No spending, upload, publication, live recording, remote resource use, source edit, training, or app build belongs to this step. This design is the only intended new file. Before any later build, re-run git status, preserve other agents' changes, and run the required full desk suite in desk/:

    perl -e 'alarm 900; exec @ARGV' node --test

The known failures to distinguish are thinking-cap/Warmer flakes, the 8192-token check, and agentbench, realpath, login1-electron, fake-sleepmode scripts. No suite was run for this design-only change. Later commits must contain only our hunks. If the lead later authorizes pushing the build, use the supplied bounded push command:

    perl -e 'alarm 150; exec @ARGV' git push git@github.com:BenjaminHannan/learner.git always-on:always-on

**Stop here. Ben's recording agreement was received from the lead on 2026-11-06. Lead approval is still needed before implementation or recording.**

## 9. Five lines for Ben

The big brain picks the job.  
The small brain looks at the screen and makes tiny moves.  
We try it in a safe little playground first.  
You said yes to watching; it saves things here and learns in sleep.  
Touch the mouse or keys, and it lets go.

## Approved build amendment, 2026-11-06

The lead approved sections 3–7, with T1–T10 frozen after these explicit changes: recordings 12 GiB total/3 GiB per day/seven days; model bundles at most 1 GiB; pause below 10 GiB free. Build (a) stop/lease and sandbox, (b) pixel/capture/input and sleep/export, then (c) fake-data recorder. Recording Ben remains OFF until T9 passes and a separate lead go. App wiring defaults OFF until the toy passes. Train only at night or after five minutes idle on the M1, using under about 2 GB RAM while Ben is active; yield to his input. Controller A uses the realmodel lock and Ben-away gate. No BensPC use without the loan line. Report at milestone (a) and at the end; commit and push.

## Retention

Lead amendment, 2026-11-06: Ben authorized automatic deletion of Glim's own recordings, with no per-delete prompt. This is additive to the frozen T9 checks. Ben recording remains OFF until T9 passes and the lead gives a separate go.

After a sleep has trained on a clip and its candidate has been judged, accepted or rejected, mark the clip spent. At that sleep's end delete its raw frames, input events, and pseudo-labels unless it belongs to the small keep-set. An interrupted or unjudged sleep cannot mark clips spent. Keep a frozen, never-trained audit/held-out set plus useful replay clips, with reason tags audit / rare / high-loss / untrained. Keep at most 2 GiB total.

The keep value is a fixed formula, never a model choice: 1000 × audit + 20 × rarity + 20 × min(max(loss,0),10)/10 + 5 × freshness. Rarity is half of (1/app-count + 1/action-count) over the indexed clips. Freshness is max(0,1-age-in-days/7). Loss is a measured post-sleep loss, not prose from a model. Order ties by creation time, then clip ID. Prefer rare or high-loss trained clips; retain recent untrained clips unless an age or space backstop applies. An untrained clip may leave the keep-set without being deleted. Reject an audit-set addition that cannot fit; do not silently change the frozen audit set.

Backstops: at most seven days for anything untrained, at most 3 GiB new bytes/day, 12 GiB total, and pause below 10 GiB free. On space pressure remove oldest spent clips, then lowest-value eligible clips before pausing. The daily-ingestion counter is not reset by deleting files. Files outside our recording root are never candidates. Do not delete Ben's personal files.

Delete only exact paths listed in a clip index beneath the real recording root. Reject symlink escapes, paths through symlink directories, traversal, and outside-root entries. Never delete by glob. Append clip ID, actual bytes, reason spent / over-cap / expired, and paths to retention.log; log progress for interrupted deletes. Ben's Delete this session cancels queued work and deletes its indexed files immediately.

Additional T9 fake-data pass checks: spent non-keep clips are gone after fake sleep; keep-set <=2 GiB; no untrained clip deletion except expired or over-cap backstop (or Ben's explicit Delete this session); outside files untouched; index/log byte totals match disk. Any outside delete, unjustified untrained delete, or oversized keep-set fails T9. No test of this amendment has run before its hash is recorded.

## Password recording amendment — 2026-11-06

Ben changed the rule: do not pause or blank the screen for password focus or the secure-login window. Save the visible pixels continuously, including these windows. This supersedes the earlier screen-pause requirements and the earlier privacy part of T9. Do not treat secure focus as a screen pause reason. Ordinary OFF, user pause, unsupported capture, lock, and disk backstops still apply.

Only literal secret key data is masked. While a trusted focus signal says secure/password field, save one event {type: secret_typed, n_keys, duration_ms}; never key codes, characters, composed text, or clipboard contents for those secret characters. Flush this count on field exit, stop, or clip end. Enter and Tab remain normal control-key events; ordinary keys after leaving the field are recorded normally. If field classification is unknown, keep screen pictures but mask literal keyboard events conservatively. No OCR/text extraction from secure segments enters labels or textual model inputs. The policy never receives a secret string as an intent or action target; mask supervised character losses for secret spans. Visible pixels are intentionally preserved as Ben requested; this is not a claim that saved videos contain no visible secrets.

Revised frozen T9 privacy text: use fake-password canaries to prove zero literal secret characters in saved event logs, labels, or structured/text model inputs; prove recording continues through password focus and the secure-login window with frames present. Preserve OFF/no-auto-resume, caps, mathematical keep-set/retention/scope/log checks, no awake footage readers, and no actions from recordings. Recorder-first build order stands. Ben recording remains OFF until the lead checks T9 and gives a separate go.

## Lean recorder amendment — 2026-11-06

The lead supersedes password-field detection and secret aggregation: do not build either. Record the keyboard events the macOS event tap actually receives. Optionally note Secure Event Input on/off using IsSecureEventInputEnabled(). Screen recording continues unchanged. T9 secret check is one fake-password canary typed into a real NSSecureTextField, followed by a byte search across every saved file, expecting zero literal hits. A normal-field control must prove the tap actually receives ordinary text; an unavailable or empty tap cannot pass. This test proves that native field path only, not every possible website/widget. All retention, cap, OFF, no-awake-reading and no-action checks remain. Ben recording still OFF pending T9 review and a separate lead go.

## Premonition identity amendment — 2026-11-06

The lead replaces both standalone app identities and the proposed Python-Glim integration with Premonition.app. The recorder and native canary run in isolated roles of the existing /Applications/Premonition.app/Contents/MacOS/Premonition executable, bundle com.electron.premonition-desk. A small entry selector runs before chat/main.js or model startup. The native code is loaded in those Premonition processes, not a separately identified Swift executable. This uses the actual app identity for TCC. It adds no second brain and does not restart the running chat.

The install remains OFF. recorderctl start --fake uses only generated pictures; stop persists OFF and terminates the recorder role and its encoder. There is no launchd auto-resume. Real capture additionally requires the lead's separate release file. Existing retention/caps and the frozen latest T9 criteria remain unchanged. The native-field canary requires Ben idle for five minutes, stops on physical input/focus loss, and may not be counted passed when deferred. No password detector or field pause is added. Settings integration and the sleep reader remain later work; the command is the current OFF switch. Any future chat/brain restart still uses realmodel-lock.sh after five idle minutes. The standalone apps are retired only after the replacement's preflight and fake stop/retention checks.


## Dated run authorization — 2026-11-06

The lead reports that Ben is away and explicitly waives the five-minute idle wait for the native fake-password canary. `recorderctl canary --ben-confirmed-away` passes only this explicit confirmation to the test. The default wait and immediate physical-input/focus-loss stops remain. No brain lock or Glim restart is involved. T9 criteria are unchanged.

After a canary PASS, the lead separately authorizes one 120-second real-desktop cost measurement in a fresh scratch directory. A separate Premonition recorder role captures the main display at 1280×720, up to 20 fps, with the regular H.264 VideoToolbox overview and 192×192 detail crop. The scratch path records no keyboard text, stops on physical input, enforces a 128 MiB bound and 10 GiB free-space floor, and deletes its two exact generated video paths at completion. CPU/RAM/byte-count results alone survive. This authorization does not create the regular recording release or turn the setting on.
