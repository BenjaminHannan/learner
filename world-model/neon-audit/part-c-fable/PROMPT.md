# Part C Review Prompt — Visual Perception & Spatial State for a Two-Speed World Model

```text
<background>
We are designing the visual perception and spatial world-model state for a from-scratch real-time agent ("Premonition") that must operate across three very different domains: (1) a 2D top-down survival game testbed (Crafter, 16x16 to 64x64 frames), (2) 3D first-person Minecraft Survival and fast-paced local-server Bedwars PvP (bridging over voids, enemy tracking behind pillars/behind your back, projectiles, audio cues, shop UI), and (3) everyday macOS desktop computer use (browsers, code editors, sharp small text, scrolling menus).

Audience: an engineer who will pick the cleanest spatial architecture and gating experiment, plus the project owner who reads the final plain-language summary.

Why this matters: pure 2D frame-by-frame pixel prediction wastes capacity on background textures and forgets enemies the instant the camera turns away; meanwhile, naive 3D Gaussian Splatting (hundreds of thousands of static blobs) is too slow for 20+ Hz live control, breaks on dynamic destructible worlds, and destroys sharp desktop UI text. We want to pick the best spatial representation — and a rigorous test so any 3D complexity has to earn its keep.
</background>

<system_under_test>
The broader agent architecture (proposed conceptual design, all untested at 3D scale):
- **Two-Speed Mind:**
  - **Fast Hands (Reflex/Motor Loop):** ~5M-15M parameters, must run at >=20 Hz (target <=4 ms per motor tick) for smooth aiming, WASD, bridging, dodging, clicking, and typing.
  - **Big Thinking Brain:** ~500M total parameters (4-wide MoE, small active params per tick), running slower persistent ticks (~4-10 Hz live) with a persistent ~64-row vector workspace (holding separate lanes for facts, conversation, goals, and compressed world summaries), a real-time clock dt, batched parallel dream states K sharing one set of weights, a continuous effort slider buying wall-clock search time, and an offline Sleep phase.
- **Brain-to-Hands Command Frame:** The Big Brain sends an interruptible structured packet ("Who / What / Where+Avoid / When / How"): learned Target Query (appearance + optional spatial anchor), Desired Change (plus exact verbatim text reference + offset for typing), Avoid Query, Expiry/Urgency, Action-Family Bias, and Caution. Fast Hands re-finds the target every tick and sends back command status + inputs sent + observed progress + decision-relevant surprise + compressed world summary.
- **Two-Speed World Model:** Fast Physics (0.1-1s, conditioned on timed motor inputs and dt) + Slow Plot (2-30s, event/milestone level conditioned on commands), with within-model stochastic outcome sampling (world/enemy variability) separated from independently bootstrapped heads (epistemic model ignorance). Dream rollouts run directly in compact state space (never decoding full pixels on every branch); pixel/visual decoding runs only during training and on demand for a live human-facing visualization ("Tesla Reality View").
</system_under_test>

<owner_rules>
- Local consumer compute ($0): 1x RTX 5070 Ti (16 GB VRAM) + Mac M1 Pro / M3 (plus possible university cluster later).
- Hard real-time motor budget: Fast Hands + perception update must stay >=20 Hz (aiming for <=4 ms motor tick, and low p99 capture-to-input latency even while Big Brain search runs).
- All perception, tracking, and world-model components must be learned (no hardcoded game coordinates, memory reading, or OS-cheat shortcuts; camera motion may use the agent's own logged mouse/WASD actions or learned egomotion).
- Desktop UI text, numbers, and small buttons must remain crisp and readable (never smeared by lossy 3D reconstruction).
- Any added architectural complexity (especially 3D splats) must earn its keep on an objective held-out test at equal compute/latency.
</owner_rules>

<candidates>
All untested at 3D scale. Each is described neutrally by its mechanism only.

1. **Multi-Scale 2D Patch Grid + Recurrent Spatial Memory (No Explicit Slots or 3D Geometry):**
   A coarse full-screen 2D patch token grid (e.g., 8x8 or 16x16 patches) paired with a sharp high-resolution 2D local crop around the crosshair/cursor and HUD. Temporal persistence across turns and occlusions is handled implicitly by a recurrent/transformer memory state conditioned on logged mouse/movement actions and audio tokens. Fast Physics rolls forward the 2D patch/memory latents directly.

2. **Universal Tracked Object Slots + Sharp 2D Crosshair/HUD Fovea (2D/3D Learned Slots, No Splat Renderer):**
   Fast Perception maintains 64-128 persistent learned object slots updated at 20+ Hz, each carrying: meaning/appearance vector, position & size (2D on desktop, learned 3D coordinates or depth+bearing in 3D games), velocity, presence/confidence, and last-seen age (via clock dt). Brain "Who/Avoid" queries match directly against these slots; only the top 8-16 salient/surprising slots enter the Big Brain's workspace. Paired with a sharp 2D fovea crop for crosshair aim, HUD numbers, and crisp desktop text. Fast Physics predicts next slot states + fovea tokens.

3. **Compact Dynamic 3D Gaussian Object Splats (64-256 Learned 3D Blobs) + Sharp 2D Crosshair/HUD Fovea (for 3D Games; Candidate 2 for Desktop/2D):**
   Upgrades Candidate 2's tracked slots in 3D games into 64-256 compact dynamic 3D Gaussian blobs in a player-centered 3D mental map (3D position, scale/orientation, velocity, opacity/confidence, appearance, meaning). Every 50ms tick: (a) rigid 3D camera transform rotates/shifts all blobs using egomotion/mouse-WASD delta (giving free geometric consistency and behind-the-back object permanence; directional audio can also wake/place off-screen danger blobs); (b) one feed-forward neural pass compares the real 2D frame against the predicted view to refine visible blobs, spawn new blobs, and coast occluded blobs by velocity; (c) Fast Physics dreams directly on the 64-256 blobs, while a lightweight differentiable 2D splat projector renders frames only during training (anchoring 3D geometry to real images) and on demand for live visualization. A separate sharp 2D fovea handles exact crosshair aim, block edges, HUD, and shop UI.

4. **Hybrid Coarse Local 3D Voxel / Bird's-Eye-View (BEV) Grid + Dynamic Entity Slots + Sharp 2D Fovea:**
   Separates static/destructible 3D terrain (represented as a compact player-centered coarse 3D/BEV feature grid shifted by egomotion, suited to blocky worlds like Minecraft bridges and pillars) from dynamic moving agents/projectiles (16-32 tracked object slots with position, velocity, confidence, and audio hooks), plus the sharp 2D crosshair/HUD fovea.
</candidates>

<question>
One decision: Which visual/spatial representation (Candidates 1, 2, 3, 4, or a better alternative) is the strongest practical design for Premonition's Fast Perception & Fast Physics across 2D Crafter, 3D Minecraft/Bedwars, and macOS Desktop — specifically evaluating whether compact dynamic 3D Gaussian object splats (Candidate 3) are genuinely worth building or whether a cleaner alternative wins on 16 GB consumer hardware at >=20 Hz?

Please give:
1. A sharp technical critique in <=10 lines: what is the hardest real bottleneck across Crafter, Minecraft/Bedwars, and Mac desktop (camera turns + behind-the-back persistence, exact block-edge/bridge geometry, moving opponents/projectiles, or sharp text/UI)? Does one representation handle all of them cleanly, or where do cracks appear?
2. For each of Candidates 1, 2, 3, and 4: strongest reason it wins, strongest failure mode / hidden cost (compute, training instability, gradient/differentiable-rendering traps, egomotion calibration errors), whether it fits the 20 Hz + 16 GB rules, and keep / defer / drop. Add a Candidate 5 if you have a better design.
3. Your clear pick for the base architecture AND the exact head-to-head gating test ("Look Away & Look Back" / occlusion / bridge-edge test) that any 3D upgrade must beat at equal milliseconds per tick to earn its complexity — with pass marks fixed in advance and what result would prove your pick wrong.
4. Any major hidden traps in Candidate 3 (e.g., unknown camera intrinsics/FOV or uncalibrated mouse-to-angle scaling, block-world sharp edges vs. soft Gaussians, training a feed-forward 3DGS predictor from monocular RGB without ground-truth depth/pose, slot-identity collapse) and whether they are fixable cheaply or fatal.
5. Up to 3 assumptions that would change your pick if false.
6. A plain-language summary of 4-6 sentences for the owner (no unexplained jargon).

Label every claim shown, suggested, or untested. "Shown" is only for facts stated in this message. You have web search (at most 5 searches); use it only if checking a specific recent paper on feed-forward dynamic 3DGS / slot world models / BEV-world models would genuinely change your judgment, and mark each paper "checked online" with its link or "from memory, unchecked". Papers are leads only; note when a finding may not carry over to a 5M-15M real-time consumer model. Do not propose game-memory cheats or hand-coded rules.

Length: about 900-1,100 words before the owner summary. Everything you produce in this reply, including reasoning before the answer, counts toward one output limit. Use the reasoning space to settle the hard decisions, and write the answer once.
</question>
```
