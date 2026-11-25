I'm weighing whether a web search would actually change my answer, since the user capped me at five searches and I need to decide whether to spend any of them. I'm also listing the key feed-forward dynamic 3D Gaussian splatting papers I'd expect to cover.

I'm going through the candidate papers in each area: pose-free feed-forward 3D Gaussian splatting, slot-based and BEV world models, and the game-world models. I'm checking whether the pose-free methods are feasible at a small parameter count, since the ones I know of rely on large ViT backbones.

I'm considering whether to run a few targeted searches, since the limit is five. The checks that would matter most are the model size and speed of pose-free feed-forward 3D Gaussian splatting, how slot-based world models hold up, and whether WorldMem's memory bank really improves look-away-look-back consistency in Minecraft.

I'm deciding whether any of the five searches would actually move my answer, and leaning toward a small pair of checks: the size and speed of pose-free feed-forward 3D Gaussian splatting, and whether WorldMem's memory really helps with look-away-look-back consistency. My working pick is a staged, egocentric-memory design that starts from a slot-based base.

I'm settling on the design now: a patch grid for the static background, entity slots for moving objects with their ego-motion update learned from the action rather than hard-coded, and a foveal channel for text. The 3D pieces, a local voxel or BEV grid for terrain and Gaussian parameters with a render loss, will only be added if the test shows they're needed.

I'm checking the Crafter details now: the view is a 9x7 window that scrolls with the agent, so anything off-screen has to come from memory. The 64x64 render gives about 7.1 pixels per unit, which doesn't line up with 8x8 patches, so a patch grid would need to be resampled to fit the tile grid.

I'm treating the Crafter case as a top-down 2D map that shifts as the agent moves, which is the same idea as a BEV grid warped by ego-motion. On desktop the equivalent is a canvas offset by scrolling, and in Minecraft it's a full 3D rotation plus translation. That suggests one shared concept: a feature grid that is warped by a learned or known ego-motion transform, so the memory stays stable in the world frame.

I'm now on the Minecraft/Bedwars case, where the main needs are keeping track of enemies who move while out of view and getting the exact block edges right when bridging, since the edge sits at the crosshair and is best handled by the fovea.

I'm going through the bridging case: the edge is at the crosshair, so the fovea and a reflex policy handle it, and a 3D map isn't needed there. Terrain behind me still matters when I'm knocked back or backing off an edge mid-fight, so I'm thinking about a coarse occupancy grid around the feet, with cells about one block wide, which is the natural fit for Minecraft's voxel world.

I'm now checking the Minecraft case, where enemies are in view only part of the time. The player's position inside the block grid is offset by a sub-block amount that drifts over time, so I'd track that with learned ego-motion and correct it against visible block edges. Arrows and other fast projectiles move several blocks per frame and are tiny on screen, so they'd need their own tracking channel rather than the general map.

I'm now thinking about how mouse movement turns into camera rotation in Minecraft, since the exact conversion from mouse counts to yaw matters for aiming during fights.

I'm working out how the mouse-to-camera mapping behaves in Minecraft: the yaw per mouse count is a fixed formula of the sensitivity setting, so it reduces to one learnable gain. The field of view is the catch, since sprinting, speed effects, and drawing a bow all change it during play.

I'm noting that Minecraft's field of view shifts with sprinting, speed effects, and bow draws, though the FOV Effects setting can turn that off. Translation can't be read from WASD inputs because collisions, knockback, and sneaking change position, so I'd have to estimate it visually, which adds cost to both the 3D and BEV designs.

I'm now covering the shop UI as a separate 2D overlay layer, since a GUI dims the world and frees the cursor, so the 3D model shouldn't try to read it as geometry. On macOS desktop, I'm noting it's a 2D layered-window setup where small text needs close to full Retina resolution to stay readable.

I'm noting that on desktop the fovea should follow a learned gaze point that can move independently of the mouse, since reading text would otherwise mean dragging the pointer over everything and triggering hovers. In 3D games the crosshair already sits at screen center, so the fovea there is fixed, with a learned HUD crop on top of it.

I'm checking the desktop case: reading a page needs a gaze that moves independently of the cursor, so I'd run a loop of crops across the screen. Even so, a desktop has far more UI elements than the 64–128 slots allow, so I'm leaning on the static screen itself to serve as memory.

I'm now checking how scrolled-off content behaves on desktop: it stays put, so it persists in memory more reliably than Bedwars enemies. I also see that exact text can't live in the spatial state, so a fovea-based reader should pull out discrete tokens and store those in a separate facts lane.

I'm weighing which of the three domains is actually hardest: the fovea and the 3D map each solve a different piece, but what they share is keeping memory stable under ego-motion within a tight time budget. Camera turns and off-screen persistence are the sticking point; enemies in Bedwars move out of view, so their position is only a belief that decays over a second or two. Recurrent memories in video world models tend to lose track of objects when the camera turns around, so that's the piece I'd expect to break first.

I'm noting that rotation alone is the cheap part: a view-sphere bearing vector can be carried through a camera turn using just the mouse-to-angle gain, without needing depth or any 3D rendering. That means most of what a full 3D model would buy for fast turns can come from an ego-centric spherical representation instead.

I'm checking the translation side: at walking or sprinting speed the player moves only about a quarter-meter per tick, so parallax over a one-to-two second horizon stays small next to object distances of several meters. That means a coarse per-slot depth scalar plus a learned translation estimate should be enough, and dense metric 3D reconstruction from monocular RGB isn't needed for most of the persistence benefit. I'm leaning toward building on Candidate 2 with depth-and-bearing slots in an egocentric spherical frame, and the patch-grid memory could plausibly live on that same ego-sphere too.

I'm sketching a panoramic ego-sphere canvas as a third option: a coarse 360° feature map in yaw and pitch, where each cell holds features, a depth estimate, and a last-seen age. Yaw rotation becomes a simple index roll, so the memory stays exact under turns without any 3D rendering, and translation would be handled by a small learned warp conditioned on depth.

I'm settling on a single canvas that stays put under ego-motion: a wide feature map where the current view is written into a window that shifts with yaw and pitch in 3D, or with translation and scroll in 2D. I'm keeping the entity slots alongside it for bearing, depth, velocity, and age, with the gaze-driven fovea providing the sharp detail, and I'm checking whether this combined design covers the persistence cases.

I'm checking whether the ego-sphere idea holds up near the player: for static terrain right under and behind the player, translation causes large parallax, so a simple rotation-only warp won't be enough there, and that part starts to look as hard as the full 3D problem. Voxels in the block lattice might be the better fit for that close range.

The near-field case is where the ego-sphere runs out: when you're standing on a bridge edge, even 0.25 m of translation per tick shifts nearby block edges a lot in bearing. So the close range around the feet probably needs a small local occupancy grid instead, which is cheap, but it only works if ego-translation is accurate to roughly 0.2–0.3 blocks. A learned visual odometry from monocular RGB may drift past that quickly, especially after a knockback moves the player 2–3 blocks in under half a second.

I'm concluding that exact block-edge geometry only matters in view, since people near edges rely on sneaking, glancing down, and a rough sense that the void is a couple of blocks away. So off-screen terrain only needs a coarse walkable-or-void map, with the fovea handling precise edges.

I'm thinking about a polar ego-BEV: 16 yaw sectors by 4 range rings, each marked floor, void, or wall, so yaw turns become an exact roll along the angular axis. Since there's no ground-truth 3D to supervise it, I'd train the grid from pixels, using a JEPA-style objective that predicts future features after the player looks away and back.

I'm thinking about how to train the grid without ground truth, since there's no metric 3D to supervise it against. The training signal would come from the agent's own future observations and outcomes, like falling into the void, which shows up on screen. I'm also weighing depth pseudo-labels from a pretrained offline teacher, but that might clash with the from-scratch requirement, so I'd flag it as an option rather than a default.

I'm checking whether the eval-only use of ground-truth positions from a local server would count as a violation of the no-privileged-input rule, since it's only an oracle for gating and never fed into training or inference.

I'm working out how to score the persistence test using only pixels, without server logs or any privileged positions. The plan is to compare the predicted target bearing against where the enemy actually reappears after a look-back, with time-to-reacquire as a second measure.

I'm settling the evaluation question: ground truth for scoring will come from the test harness's own scripted opponent path on a local server, or from hand-labelled held-out frames, and never from anything the agent sees or trains on.

I'm now weighing the candidates one at a time, starting with a 2D patch grid plus recurrent memory that has no slots and no geometry. It's the simplest option, with one code path across all three domains and a proven recipe on Crafter, but its memory is unstructured, so nothing guarantees it stays stable across a 180° flick.

I'm weighing Candidate 1's memory against the persistence requirement: an unstructured patch grid has no addressable handle for a specific enemy, so re-finding a target after a turn means relearning its identity from appearance alone, and two same-coloured enemies could get confused.

I'm now weighing Candidate 2, the slot-plus-fovea design without a renderer. Its appeal is that slots match what the Command Frame needs for targeting and avoidance, they stay cheap enough for parallel dreaming, and age and confidence give explicit permanence, all without differentiable-rendering complications. The first weak spot I'm noting is that learning slots from scratch on textured scenes is notoriously unreliable.

I'm weighing the slot-based design's weak points now: learning slots from scratch on textured scenes may not segment reliably without strong pretrained features, and slots can swap identities when objects cross. Slots also fit objects poorly as a representation for "stuff" like terrain, walls, or a dense page, and it's unclear how they'd capture something as simple as the absence of floor over a bridge gap. Without any geometric grounding, the learned 3D coordinates have no training signal forcing them to be metric.

I'm noting that the slot-based design's "position" fields could be free latent variables with no metric meaning, so I'd need a self-supervised consistency loss: rotating a slot by a known ego-motion should predict where it reappears. Matching slots to detections at 20 Hz is cheap, but a learned recurrent attention update that uses last step's slots as queries looks better. The cost of a few cross-attention layers over up to 256 patch tokens seems to fit the frame budget, though that's a guess I haven't tested. I'd keep slots as the base design but restrict them to discrete things, not terrain or dense pages.

I'm now assessing Candidate 3, the dynamic 3D Gaussian design. Its main appeal is that the rigid transform gives exact equivariance under ego-motion, and rendering lets the model tell an occluded enemy from one that is gone: a blob behind a pillar is predicted hidden, so not seeing it isn't evidence that it left. The render loss also ties the slot positions to real images, so the geometry stays metric without labels.

I'm now looking at where the dynamic 3D Gaussian design breaks down: with only 64 to 256 blobs, the renderer can't reproduce a Minecraft scene, so the photometric loss gets dominated by background and pushes the blobs to smear over terrain instead of holding objects. I'd also have to deal with scale ambiguity, since monocular depth is only fixed up to a scale set by the translation estimate.

I'm looking at the gradient problem for the object-level blobs: each one only gets a useful signal where it overlaps the image, so a predicted position that is off by more than its footprint gives almost nothing to correct it. Feed-forward pixel-aligned splatting sidesteps this by tying each Gaussian to a pixel, so the gradient reaches the network that predicts position from image features rather than the blob directly.

I'm now listing the remaining failure modes for the dynamic 3D Gaussian design: blobs should be spawned aligned to pixel rays with only depth predicted, since free-floating blobs are hard to train. Monocular input entangles object motion, camera motion, and depth, and Minecraft's dynamic FOV, view bobbing, and damage tilt add unmodelled camera motion that would corrupt the ego-motion estimate.

I'm checking the rendering cost: 256 Gaussians at low resolution should be under a millisecond, so the real expense is training backprop through sequences. Then I'm noticing a tension in the candidate itself: comparing the real frame against a predicted view seems to need a render every tick, which conflicts with rendering only during training.

I'm noting that the predicted view at each tick would only need projected blob tokens rather than rasterised pixels, which would resolve the tension with rendering only during training. I'm also flagging that soft Gaussians don't fit hard block edges, so the fovea would have to handle those.

I'm noting that the rigid transform itself could be applied to slots just as well, so the real edge of the dynamic Gaussian design is the render-based training signal. Without terrain in 3D, though, the pillar occlusion argument falls apart, and only a combined slot-plus-occupancy setup would recover it.

I'm settling the verdict on Candidate 3: I'd keep the rigid ego-transform on slots in the base design anyway, so C3's real extra value is the Gaussian extent and opacity parameters, the differentiable render loss, and the larger blob count. The gate should compare "C2 plus ego-transform" against C3 to isolate those. I'd defer C3 and only build it if it clears that test.

I'm now weighing Candidate 4, the voxel/BEV grid with entity slots and a fovea. It seems to get the split between terrain and objects right, since a blocky world is already a voxel lattice, destructible terrain becomes simple cell updates, and the grid can supply the pillars and void needed for occlusion reasoning. The main weakness I see is that lifting monocular RGB into such a grid needs either depth or learned attention-based lifting with known intrinsics.

I'm now looking at the practical weak spots of the voxel/BEV grid: lifting a single monocular camera into it without depth labels risks the grid never becoming truly geometric. Sub-block ego-translation would also keep resampling the memory and blur it, so the fix I'm considering is to anchor the grid to the world and move only the agent pose inside it, shifting by whole cells.

Now I'm checking whether a 2.5D height-field BEV, storing a floor height or nothing per column, is enough for Bedwars' bridges and towers, since that would avoid a full 3D voxel grid. I think it probably is, because the maps are mostly islands joined by bridges and overhangs are rare, though a full voxel grid might be feasible if it stays small and sparse.

I'm settling on a canvas-style design for the stuff side: a low-res feature map wider than the current view, where each frame's patch tokens get written at an offset from a learned ego-motion estimate. In Crafter that offset would be a whole-tile shift, and on desktop it would follow the camera motion.

I'm settling on a panoramic canvas for the stuff channel, with each frame's patch tokens written at a yaw/pitch offset, so rotation becomes an exact shift. Translation would need a learned, depth-aware residual warp plus age decay, and the things channel gets the same shift applied to its slots, with audio able to seed bearing-only detections.

I'm treating the fovea as gaze-driven rather than tied to the cursor: one or two native-resolution crops, with free saccades on desktop and a learned HUD crop, and any text read out verbatim as discrete tokens rather than stored in slots or the canvas. I'm also weighing whether Candidate 5 is really better or just more complicated, and I'm leaning toward seeing it as Candidate 2 scoped to things, with Candidate 1's grid given an ego-shift.

I'm checking the panoramic canvas for pitfalls: pure yaw is an exact horizontal roll, but pitch isn't a simple vertical shift if the canvas is stored in camera-relative coordinates. If I index it by world-frame direction in a gravity-aligned, yaw-anchored frame, the canvas never needs rotating at all, and only the camera's yaw and pitch change.

I'm working out how the yaw and pitch state gets tracked: yaw should integrate exactly from mouse deltas, pitch saturates at ±90°, and gain error only matters per flick rather than accumulating over many turns.

I'm checking whether the drift from an imprecise yaw gain stays bounded: the error scales with net rotation and could reach tens of degrees over many turns, so it would need re-anchoring. I'm thinking the canvas can be re-registered every tick by matching current patches to the canvas at the predicted spot, and that the gain itself can be learned from a rotate-in-place calibration episode, which should make this cheap to fix.

I'm now checking the translation case, where near-field bearings shift a lot: strafing past a pillar 3 m away at about 5 m/s moves its bearing by roughly 95°/s. So a canvas that only fixes rotation would leave near content stale, and the weak spot is exactly the nearby enemy behind cover.

I'm checking the range problem for the close-quarters fights, since at 3 m a strafe swings bearings by nearly 100°/s and a bearing-only slot would go stale almost at once. Each slot would need a learned range, so that its 3D position in the ego frame can be updated under translation. The range could be learned without labels by predicting where a slot reappears after a move, and apparent size offers a cheap cue for known-height entities like players.

I'm now weighing whether the stuff channel should be a panoramic canvas or a local BEV map. The canvas handles distant content well since parallax is small there, but near-field terrain under translation would need a local 2.5D map to stay accurate.

I'm weighing a unified ego-polar map with log-range rings: near cells stay fine enough for strafing and knockback, while far cells stay coarse for distant landmarks. Under yaw the azimuth axis needs no transform, but near cells would still need a warp when I translate.

I'm working out whether a world-axis-aligned local Cartesian grid, scrolled by whole cells, would be cleaner for the near field than a polar map. With that setup, rotation is just a pointer update and translation is an integer scroll, so nothing ever needs interpolating. In Minecraft the axes would match the block lattice, and the agent's yaw relative to it could be learned from block edges.

I'm settling on a base design that keeps things minimal: slots with ego-transformed positions, a single local grid for the stuff channel, and a gaze-driven fovea. The panoramic far-field and the world-anchored BEV would be added later only if they clear the complexity gate, starting with whichever upgrade promises the most value for the cost.

I'm settling on a concrete base: a recurrent patch grid for stuff, plus 32–64 thing-slots with ego-frame bearing and log-range, shifted each tick by a learned ego-motion transform, and a gaze-driven fovea that reads text verbatim as discrete tokens. The stuff memory and the splat loss stay as upgrades that have to beat this base at equal latency.

I'm settling on Candidate 5 as my pick: it's Candidate 2 with three adjustments, and I want to be clear about what those are, especially the first, which limits slots to things like movers, projectiles, interactables, and attended UI widgets while terrain stays in the patch grid with recurrent memory.

I'm laying out the three changes to the base: slots hold only things, they carry ego-frame bearing and log-range and get the rigid ego-transform step without any Gaussians or renderer, and the fovea is driven by gaze and reads text as discrete tokens that bypass the slots. For training the slot positions without a renderer, I'm considering latent prediction of next-frame features at each slot's projected location, plus an ego-equivariance consistency check, though I'm also weighing where that could go wrong.

I'm now considering how to make the slot training workable without a renderer: motion residuals, meaning whatever the ego-motion prediction fails to explain, could supply the objectness signal, so the model learns what counts as a thing from surprise rather than from a hand-written rule. I also need to start thinking about the gating test against the occlusion case.

I'm now laying out the test design: a "LAB-3" suite with three sub-tests on held-out Minecraft/Bedwars maps, with every arm matched on parameter count, training frames, and p99 latency per tick. I'm running three seeds per arm on paired episodes, and comparing the control, my base pick, and the two upgrade variants.

I'm sizing up the cost of the five-arm test: at 5-15M parameters with low-res frames, each arm-seed might take a GPU-day or two, so 15-30 GPU-days total is a lot for one consumer card. I'm considering shrinking it by recording one offline dataset of about 3.6M frames and training perception and fast physics purely by prediction, without rendering.

I'm sketching the offline gate: scripted camera manoeuvres on recorded held-out episodes, run first because it's cheap and paired, with a small closed-loop check only afterward. The first sub-test, Look Away & Look Back, checks whether an opponent that leaves view is still tracked when the agent turns back.

I'm specifying the first sub-test, Look Away & Look Back: an opponent is visible for at least half a second, then the camera yaws 120-180° away for a hold of 0.5 to 4 seconds, with the agent strafing in half the trials before turning back. The check is whether the predicted bearing and presence of the target at the tick before it reappears match where it actually shows up, counting a hit when the angular error is within 10° for holds up to 2 seconds.

I'm working through the problem of free-moving opponents: over a two-second hold a sprinting enemy could end up almost anywhere around me, so a fixed 10° tolerance can't be the bar for them. I'll split the test into static targets that check pure geometric persistence, constant-velocity movers that check velocity coasting, and free movers scored on calibrated probability coverage instead.

I'm setting the readout up so the baseline gets a fair shot: a small frozen probe, the same for every arm, trained on labelled look-back frames to read the target's bearing from the model's state. I'm also noting a label-free alternative, where the prediction error on the look-back frame's patch tokens serves as the metric instead.

I'm settling on a behavioural metric for the look-back test, since the arms have different latent spaces and a probe-free comparison is needed. I'm considering pre-aim error: after the turn back, how far the crosshair sits from the target and how many ticks pass before it lands on it, measured the same way for every arm.

I'm weighing the look-back test's primary metric, between a probe that reads bearing from each arm's state and a behavioural pre-aim error. The pre-aim option needs no probe and works the same for every arm, but it also picks up policy learning, so I'm thinking about whether that trade-off is worth it for a perception gate.

I'm now defining the per-sub-test metrics, all read on the first frame where the target is visible again. For T1 it's the pre-aim angular error, passed if it's within 10°. For T2, the pillar occlusion test, I'm checking whether presence stays above 0.5 while the opponent is hidden, along with the predicted emergence side and timing, and whether identity holds when two similar opponents cross.

I'm working out the pass criteria for the three sub-tests, and I want them fixed before any runs so the numbers can't drift afterward. The bar is that the 3D upgrade has to beat the base model by a set margin on at least two of the three sub-tests, measured at the same per-tick latency, parameter count, and training frames, without regressing on the others.

I'm setting the pass criteria for the upgrade against the base: a relative drop in failure rate of at least 25% on two of the sub-tests, no sub-test worse by more than 5%, and equal p99 tick time enforced by trimming the other layers. I'm also requiring that the base beats the no-slot control by the same margin, or the base isn't picked and the control stays.

I'm setting the pass criteria for the upgrade so they hold on at least two of the three sub-tests, and I'm proposing absolute thresholds for the first sub-test's static and constant-velocity targets, which I'll mark as my own untested judgment calls. I'm also noting the conditions that would prove the pick wrong: the control matching the base, the base missing the absolute marks, or slot identity collapsing in more than a fifth of the seeds.

I'm setting the remaining gates: for T2, presence has to hold in at least 90% of occlusions up to 1.5 seconds, identity switches stay under 5% when look-alike opponents cross, and the ghost rate stays at or below 10%. For T3, the void-behind queries need to be right at least 90% of the time after a knockback, with a scripted retreat fall rate under 5% and bridging no worse than the control.

I'm setting the Fast Hands tick budget so every arm gets the same p99 cap, around 4 ms with the batch-K dream search running alongside. For the desktop tasks I'll hold verbatim text reading and Crafter score to no lower than the control, and I'm keeping the threshold numbers labelled as my own untested proposal.

I'm now settling on the hardest bottleneck: the tension between sharp text, which needs native-resolution pixels, and persistence of moving enemies behind me, which needs a stable memory. Of the four, I think the camera-turn persistence case is the hardest, since the needed information is off-screen and so it's a belief problem rather than a resolution one, where sharper geometry gives diminishing returns.

I'm noting that projectiles are the next concern: at 20 Hz a full-charge arrow could cover roughly three blocks per tick, which is sub-patch for a coarse grid. I'm also taking the broader point that no single representation covers everything, since text needs lossless 2D pixels, terrain needs an occupancy lattice, and opponents need identity slots, so at least three channels are required.

I'm deciding whether to spend any of the five searches, and I'm checking for results on compact, dynamic Gaussian object-centric world models that run in real time for control, such as the driving and manipulation Gaussian world model work.

I'm checking whether papers like GWM, ManiGaussian, or the slot-based Gaussian work would shift me toward the blob-based arm, specifically whether any small, object-centric dynamic Gaussian model trained from monocular video beats slot baselines for control. I also recall GWM relying on a diffusion transformer over many Gaussians with depth or multi-view reconstruction, which makes me doubt it fits a 4 ms budget.

I'm considering WorldMem as a lead: its pose-indexed memory bank would support the idea that ego-motion-indexed memory beats implicit memory, though it relies on a large diffusion model with ground-truth poses. I'm weighing whether checking it would actually change my decision, and I think it would only reinforce one claim about C1's failure mode rather than flip the pick. I'm also starting to look at slot world models trained from scratch on complex visuals, beginning with SOLD.

I'm checking whether the slot-based world model papers would change anything. SOLD shows a slot agent beating DreamerV3 on relational manipulation, but only with simple visuals and a pretrained SAVi encoder. OC-STORM needs pretrained segmentation features and a few annotated frames to work on complex scenes. So slot discovery from scratch looks like a hidden cost for the slot-based arm, though checking these wouldn't flip my pick.

I'm noting that the feed-forward pose-free splatting papers, NoPoSplat, Splatt3R and AnySplat, plus the dynamic variants like BTimer, STORM, DGS-LRM, MoVieS and 4DGT, all lean on large ViT backbones and hundreds of thousands of pixel-aligned Gaussians trained on posed multi-view data. That makes them look far too heavy for a 4 ms tick, which is a point against that whole branch.

I'm thinking about whether a couple of targeted searches are worth the cost, since they'd only change my view if they showed a compact, object-level Gaussian model that runs under a tight tick budget. So far I recall nothing like that; the pose-free feed-forward and dynamic Gaussian models I know all rely on big backbones and posed multi-view training. I'd spend two or three searches at most, mainly to confirm their model sizes.

I'm planning to verify a few key papers with targeted searches: the pose-free feed-forward Gaussian splatting models, WorldMem's pose-indexed memory, and whether OC-STORM and SOLD depend on pretrained segmentation. If any of them contradict what I remember, especially a compact, real-time dynamic Gaussian model, that would change my judgment.

I'm planning four targeted searches: one on the pose-free feed-forward Gaussian splatting models, one on WorldMem's pose-indexed memory, one on whether OC-STORM depends on pretrained segmentation, and one for any compact, object-centric dynamic Gaussian world model that might run under a tight tick budget. That last one is the search that could actually change my judgment on the Gaussian arm.

I'm planning to check how the citation indices will line up once the search results come back, since they're returned through code as a list of dicts.

I'm considering how to cite the search results, since they come back through code as a list of dicts and the indexing isn't obvious. I'll print a numbered list so I can reference each result accurately.

I'm mapping out the next rule: every cited claim has to start from a subject and main verb that no clause of the source uses, so a reworded sentence doesn't count as a copy. For example, I'd write that the model's demonstrated scale, a large ViT backbone trained on posed multi-view data, sits far from a small real-time budget, rather than echoing the source's wording.

I'm keeping my cited claims as my own judgment about how each search result bears on Candidate 1, and I'm planning to mark each paper as checked online with its link, or as from memory and unchecked.

I'm settling the base pick now: a narrowed version of Candidate 2 that models only things, with ray and range in the ego frame and Candidate 3's rigid transform, running on Candidate 1's patch grid for stuff plus a gaze fovea that reads text verbatim. I'm weighing whether Candidate 4 as specified could still work.

I'm weighing whether Candidate 4 should be the base instead of my narrowed Candidate 2, since it already splits stuff into a grid from things in 16 to 32 slots, with a fovea. The difference is that it lifts stuff into a 3D or BEV grid, which suits blocky Minecraft and void awareness. Against that, lifting from monocular RGB without depth labels at 5 to 15M parameters from scratch is the hard, unproven part, and the desktop path makes a third code path, so I'd start without it.

Now I'm settling on the fit question: on a 20 Hz tick with 16 GB, all four candidates should run in principle, though that is still an assumption I haven't verified.

Now I'm estimating whether the compute fits the 4 ms tick, working from roughly 10M parameters over about 400 tokens, which comes to something like 8 GFLOPs per tick on a 5070 Ti.

Checking whether Fast Hands on the Mac might sidestep the GPU contention with Big Brain's batched dreams, since the small model's latency spikes come from sharing the same card.

Now I'm looking at Candidate 3's main risk: its camera model needs intrinsics and a field of view that aren't known, and mouse gain is unknown too. That part is cheap to fix by learning the gains and FOV from in-place spins, but Minecraft's dynamic FOV and view bobbing would add camera changes that nothing logs, so I'd have to either turn those off or model them.

I'm working through the third risk on the monocular feed-forward Gaussian approach: the published versions lean on large backbones, posed multi-view training data, and dense pixel-aligned Gaussians, which is the part I'm least sure can be made to fit a 5-15M model without depth or pose labels.

I'm weighing the 3D-Gaussian render loss as the most serious trap: with around 256 blobs, the splats can't explain a frame the way dense pixel-aligned Gaussians do, so the photometric loss either smears them into the background or collapses their opacity. The fix is to render only features or masks at blob locations, which turns it into a slot model with a projection consistency loss, close to my Candidate 5, so the Gaussian machinery adds little and that's why I'm deferring it.

I'm now weighing the remaining Gaussian risks: 256 soft blobs can't carry a sharp block lattice, so terrain has to stay in the grid, but then the blobs lose the occlusion reasoning that rendering was supposed to give. I'm also checking slot identity, since duplicate blobs on one enemy, ID swaps at crossings, and spawn-kill thrash would need standard fixes and the ID-switch metric as a watch.

I'm now checking the remaining Candidate 3 risks: the projection for comparing predictions to the frame has to run at runtime, so I'd compare projected blob tokens rather than rasterised pixels. Unseen enemies need their position uncertainty to grow with time since last observation, so the Brain sees the age and variance instead of a falsely precise blob. I'm also flagging the assumption that thing-slots can be learned from scratch at this size without a pretrained segmenter, since if that fails I'd fall back to the grid with attention readout.

I'm checking the remaining assumptions that would flip the pick: whether the camera mapping is stable enough for the ego-transform variants to keep their consistency, and whether the from-scratch constraint rules out any frozen depth or segmentation component I'd otherwise lean on.

I'm settling the assumptions that would flip the pick: whether thing-slots can be learned from scratch without a pretrained segmenter, whether off-screen terrain needs exact edges or only coarse awareness, and whether the camera mapping is stable enough for the ego-transform variants to keep their consistency. I'll then write a compact critique of the item-1 points, keeping it to short bullets.

I'm settling on how to label each claim in the critique, sorting facts from this message as shown, reasoning and literature as suggested, and predictions as untested, with a short check on any paper lead to mark whether I verified it online or am recalling it from memory.

I'm working out how to label each claim, and whether one label per bullet is enough or every sentence needs its own tag. A table could fit the five candidates across the same four attributes, though the cells would need to stay short.

I'm now laying out how to present the comparison: a short paragraph per candidate, or a table, with the word budget split across the critique, the five-way comparison, the sub-test table, and the assumptions.

I'm lining up four searches to check the papers on the Minecraft memory-consistency and pose-free Gaussian splatting side of the comparison before writing the critique.

I'm planning four searches to check the Minecraft memory-consistency work and the dynamic feed-forward Gaussian splatting papers, starting with MoVieS for motion-aware 4D reconstruction from monocular video, then the object-centric world model OC-STORM and whether any object-centric Gaussian splatting approach handles dynamic scenes in real time.

I'm about to run a few searches to verify the Minecraft memory-consistency work and the dynamic feed-forward Gaussian splatting papers, so I'll write the code to pull out the relevant sentences from each result.



I've confirmed WorldMem from its paper: it keeps a memory bank of frames and their states, like poses and timestamps, and that memory is what keeps 3D spatial consistency once the context window gets short. It also relies on ground-truth actions and poses, and that's a big difference from the small model I'm thinking about, which would have to learn egomotion itself. Now I'm starting on MoVieS.

I'm checking MoVieS as well: it does feed-forward 4D from monocular video on a large pretrained transformer backbone, trained on big static, dynamic, and point-tracking datasets, so that route also depends on heavy pretraining rather than a small from-scratch model. A newer compact-Gaussian paper, C4G, uses timestamp-conditioned Gaussian query tokens, which could be a useful lead for the compact-representation idea, though I don't yet know its scale.

I'm weighing whether a fifth search on C4G would actually change my judgment. If it turned out to use only a few hundred Gaussians with a small model running in real time from monocular video without poses, that would help C3, but I expect it still leans on a large pretrained backbone and thousands of Gaussians. I'll check the abstract for scale and backbone details, since it's the closest lead to compact dynamic Gaussians.

I'm noting that OC-STORM's object features come from a frozen pretrained segmenter (Cutie/SAM2) plus a few human-annotated frames, so its win on visually complex games doesn't come from training from scratch. That supports the risk that slot discovery from scratch could fail for my object-centric ideas. I'm also considering DreamScene4D, which builds per-object Gaussians from monocular video but through per-scene optimisation, so it isn't real-time either.

I'm going to run one last search on C4G, looking for its scale and backbone details, since it's the lead most relevant to compact dynamic Gaussians.



I'm noting C4G: a feed-forward dynamic reconstruction method that uses learnable query tokens in place of per-pixel prediction, needs no ground-truth poses, uses far fewer Gaussians, and holds up across large temporal gaps. It makes the "compact learned blob queries" idea from C3 look more plausible than I had assumed, since query-token Gaussians without poses seem to beat per-pixel feed-forward dynamic approaches.

The search turned up C4G, which changes one of my earlier judgments: the query-token Gaussians without poses look more plausible than I'd assumed for C3. Still, its scale, backbone size, and training data aren't confirmed from the snippets, and it's an offline multi-frame reconstruction model, not a 20 Hz streaming control model. So the trap (c) call moves from "probably fatal" to "open, not cheap," and I'd still defer, though it's the lead that would matter.

I'm now going through the citable passages for the comparison: WorldMem's memory bank and its reliance on stored poses and timestamps, MoVieS's large pretrained transformer backbone trained on static, dynamic, and point-tracking data, and OC-STORM's frozen segmentation model that takes object features from a few annotated frames. I'm also flagging C4G's claim of beating per-pixel feed-forward dynamic 3DGS without ground-truth poses, with fewer Gaussians and robustness to large temporal gaps, and I'll likely leave out the DreamScene4D passage to keep the answer short.

I'm drafting the cited claims for WorldMem, with a subject and verb that don't reuse the source's wording, and I'll keep each claim attached to its own point.

I'm working out the forgetting-risk citation for Candidate 1: I need a claim that a Minecraft video simulator had to keep past frames tagged with camera pose before its look-back views stayed consistent, and I'll keep the caveat that it relied on true poses and a large generator, so it may not carry over.

Next I'm weighing MoVieS for the comparison: it's built on a large pretrained transformer backbone, so its size and training data are the next things to check against a 5-15M model.

I'm lining up the forgetting-risk evidence for Candidate 1 next: WorldMem's memory bank stores past frames together with their poses and timestamps to keep 3D consistency, and its results rely on ground-truth poses. Then I'm checking MoVieS, which is built on a large pretrained transformer backbone and trained on mixed static, dynamic, and point-tracking data, to see how far its scale sits from a 5-15M model.

I'm checking the last piece of evidence against the C4G result, a claim that across multiple benchmarks it beats existing feed-forward dynamic 3DGS methods without needing ground-truth poses, using far fewer Gaussians and holding up across large temporal gaps. I'll keep that as a comparison point rather than a verdict, since the snippets don't show its training scale.

I'm checking the C4G result again: it reportedly beats per-pixel dynamic-splat predictors with learned query tokens that decode Gaussians, without needing poses and with far fewer Gaussians. That's the one finding that moves my view on C3, so I'll keep it as a lead rather than a verdict.

I'm working out how to phrase the C4G lead for Candidate 3 so it isn't just a reworded copy of the source sentence. The idea is that a query-token design, with no supplied camera poses and a much smaller Gaussian count, reportedly came out ahead of per-pixel dynamic-splat predictors, which gives the compact-blob premise some outside support. I'll keep that as a lead rather than a verdict, since the snippets don't show its training scale.

I'm settling on C4G as outside support for the compact-blob premise in C3: a pose-free design that uses far fewer Gaussians and still holds up over large temporal gaps. I still need to write the claim so it doesn't mirror the source's sentence structure, and I'm keeping it as a lead rather than a verdict.

I'm planning where the citations go, since the word budget is tight: WorldMem and OC-STORM under the forgetting and object-centric candidates, and MoVieS and C4G under the comparison. Each one gets a "checked online" note and its link, and I'm dropping the DreamScene4D reference to keep it short.

I'm noting that the remaining minimal references are a from-memory mention of DreamerV3 on Crafter and a note on driving BEV models needing calibrated cameras and 3D labels, both flagged as unchecked. For the Minecraft facts like dynamic FOV, view bobbing, and mouse gain, I'll label them as suggested from memory.

Now I'm settling on the labels for each claim, with the cited passages and links checked against the sources, and the remaining items marked from memory.

Next I'm weighing the bottleneck that matters most for this design: the model has to keep track of objects after they leave the view, so I'll frame the critique around that.

I'm weighing the last few critique points: the hardest bottleneck is tracking things that move out of view while the agent turns, since that information is simply not on screen, and I'm treating text, block edges and projectiles as resolution problems a sharp crop can handle. Unseen opponents keep moving, so after a second or two the honest state is a widening guess rather than precise geometry. Finally, no single representation fits everything: grids lose identity, slots can't hold void or long text, and blobs can't hold hard edges.

I'm settling on Candidate 2 narrowed onto Candidate 1's patch grid as the build, with the Gaussian splats deferred until the gate in section 3 says 3D has earned a place.

I'm weighing whether the Candidate 2 discussion should lean on the object-centric evidence, and I'm also checking how the cited claim about a visually bus-driven object-centric world model fits the narrowed design.

I'm weighing whether Candidate 3's Gaussian blobs earn a place, since their rendering step is the only part here that tells "hidden behind a pillar" apart from "gone." The catch is that the camera-transform benefit I'd credit to them doesn't actually need Gaussians, and it could run on Candidate 2's slots instead.

I'm weighing Candidate 4 now: a voxel/BEV grid with entity slots is the only option that stores void and natively fits destructible blocks, but lifting a single uncalibrated camera into that grid without depth labels is the weak point, since driving-style BEV models depend on calibrated rigs and 3D supervision.

I'm weighing the Candidate 5 design now: it keeps 32–64 slots for moving things only, with terrain left to the patch grid, and each slot is moved by the logged mouse delta and a learned translation, with uncertainty growing as time since it was last seen increases.

I'm settling on the gate design now: Candidate 5 goes up against three arms, the patch-grid control, a coarse 2.5D ego-map variant, and the Gaussian-splat variant, all trained on the same data with matched parameter counts and compared on p99 latency.

I'm setting up the gate's sub-tests now: the look-away-and-back case, where the opponent is seen, then the agent turns away for up to two seconds, and success means re-aiming within 10 degrees on the first frame the opponent reappears, in at least 80% of trials. The pillar-occlusion case checks whether presence holds through a short hide, a crossing look-alike, and a permanent departure.

I'm laying out the pass thresholds for the bridge test and the upgrade rule: an alternative has to cut failures by at least 25% versus Candidate 5 on two sub-tests, with no regressions and stable training across seeds. I'm also noting the falsifier: if the control arm comes within margin of Candidate 5, the slots haven't earned their place.

I'm setting the pass bar now: if the simplest arm comes within margin of the slot design, the slots haven't earned their place, and if the splat arm clears the rule where the slots miss the absolute marks, then I'd build the splats. I'm also weighing the calibration trap for the Candidate 3 path: the mouse-to-angle mapping should be cheap to learn from spinning in place, but the game's field-of-view changes and view bobbing have to be learned as residuals or switched off. Translation is the harder trap, since WASD doesn't give position, so that error has to be estimated visually and it leaks into every blob.

I'm checking the monocular training risk for the Gaussian path: the published dynamic-splat recipe relies on a large pretrained backbone and broad data, and the closest pose-free evidence I found (C4G) suggests blob budgets can stay small, though that was an offline abstract and may not carry over to a small streaming model.

I'm checking the remaining critique points: the main risk is that blobs without terrain lose their occlusion advantage unless the grid is added too. Identity collapse looks manageable with predict-then-match updates, and I'm flagging the internal inconsistency in step (b) versus step (c), where the fix is to compare against projected blob tokens rather than rasterised pixels.

I'm checking the assumptions, starting with whether the slots can be learned from scratch at this size and using the motion the egomotion model can't explain as the objectness signal. If that fails, I'd fall back to Candidate 1 or a frozen pretrained teacher run offline. I'm also noting that off-screen terrain only needs about one block of awareness, and that if blind retreats dominate deaths, the grid has to become the base instead.

I'm settling on the owner summary: keep a short list of tracked things with a remembered direction and rough distance that updates as the agent moves, plus a coarse full-screen view and a small sharp window for text and edges. That avoids the hardest part of the 3D blobs, learning true shape from a single flat screen. The plan is one fixed test run identically on every design, adding a terrain map or blobs only if they cut failures by a quarter, and dropping tracking altogether if the plain baseline does as well.

Now I'm estimating the word count of the whole write-up, section by section, and it comes to about 1,285 words. That's too long, so I'm planning cuts across the candidates, the trap notes, and the assumptions to get it under 1,100.

I'm checking the word count against the 1,100 target and planning cuts to the candidates, the trap notes, and the assumptions.

I'm checking the 20-run budget next: 4 arms across 5 seeds on one GPU, which I'd estimate at a few hours per run and roughly 3–5 days total, though that's unverified.

I'm checking the gate's readout: the presence-held metric can't apply to the arm without a presence variable, so every arm needs the same readout head and training budget to keep the comparison fair.

I'm deciding how the sub-tests get measured, and I'll use the same small probe for every arm so the comparison stays fair, since the patch-grid arm has no presence variable to read directly. The probe reads presence, bearing, and floor-behind from each arm's state and is trained on a separate labelled set. I'm keeping the checks simple: bearing counts as correct if it lands within 10° of where the opponent actually reappears, and the bridge test passes if the floor-behind probe is right at least 90% of the time and the scripted retreat falls no more than 5% of the time.

I'm checking how the free-moving opponents should be scored, since the stationary and constant-velocity cases don't test whether the model overstates its confidence about where a moving target has gone.

I'm checking the C1 failure mode next: pure frame-by-frame pixel prediction forgets what's off-screen, which is the gap the bridge and pillar tests are meant to expose.

I'm checking how the citations should be formatted, so I'll use the index numbers from my earlier search results for WorldMem, MoVieS, OC-STORM, and C4G.

I'm weighing the WorldMem evidence for Candidate 1's forgetting risk, since its look-back consistency in Minecraft video depended on storing past frames with their camera poses and timestamps.

I'm checking whether the citation I plan to use for Candidate 1's forgetting risk holds up, since WorldMem's memory bank stores past frames with their poses and timestamps, and that mechanism is what keeps its look-back views consistent. The catch is that its test conditions supplied ground-truth poses and the model is far larger than mine, so the evidence may not carry over.

I'm checking the MoVieS recipe for dynamic splats from a single camera, which leans on a large pretrained backbone and broad mixed training data, including point-tracking. I'm weighing whether that dependence is a realistic cost for a small streaming model.

I'm noting the citation and wording choices for the WorldMem and MoVieS claims, keeping each one tied to what its source actually says. I'm also adding the checked-online link for WorldMem and marking the unchecked items as from memory.

I'm checking the user's question about the hardest bottleneck across Crafter, Minecraft/Bedwars, and desktop, and whether one representation holds up in all three. Crafter and desktop are flat, so their camera motion is just a tile shift or a scroll, which makes them easier than Minecraft's full 3D turns.

I'm settling on the bottleneck question: the hardest real problem is keeping track of moving things that are behind the agent, since that is the only case where the needed information is off-screen, and only Bedwars stresses it because Crafter and the desktop are flat. Text, block edges, and most projectiles are visible when they matter, so that part is a resolution and frame-rate problem a sharp crop can handle. Unseen opponents keep moving, so after a second or two the honest state is a widening guess, and a precise 3D estimate there would be false confidence.

I'm weighing whether to defer the Gaussian splats and build a narrowed version of the query-token approach on the patch grid instead, with any 3D upgrade having to pass a test first.

I'm weighing Candidate 1 as the control and likely scene backbone: one code path covers all three domains without calibration, but its memory has no built-in sense of turning, so the Who/Avoid queries have nothing persistent to hold onto.

I'm weighing Candidate 3, the Gaussian blobs, and leaning toward deferring it, since rendering a predicted view is the only part where it would clearly earn its cost.

I'm weighing Candidate 3 against the cost of training. The Gaussian blobs only buy a clear benefit in the rendering step, since predicting a view is the one thing that could tell "hidden behind a pillar" from "gone." The main benefit I'd hoped for, the rigid camera transform, doesn't actually need Gaussians, so it can run on Candidate 2's slots. What's genuinely new is the render loss, and 256 blobs can't account for a Minecraft frame without either smearing over the terrain or letting a background decoder do all the work while the blob opacities collapse. Runtime looks fine; training stability is the open risk.

I'm weighing whether a coarse height map or a full 3D grid is the realistic choice here, since lifting an uncalibrated camera into a grid without depth labels is unproven and drift blurs the grid at each resample.

I'm working out the gating test for the pick: four arms on held-out maps and skins, comparing the current patch-grid baseline against the narrowed slot design, with the 3D upgrade only considered if it clears that bar.

I'm setting the four arms against each other on held-out maps and skins, with Candidate 5 as arm B, a coarse height-map variant as arm C, and the Gaussian splat design as arm D. Every arm gets the same training data, parameter budget, and a fixed latency cap on the same GPU, across five seeds. Scoring truth stays with the test script and hand labels, away from the agent.

I'm laying out the gating test: three sub-tests on held-out maps, covering whether the opponent's bearing is still tracked after a turn away, whether identities survive a pillar occlusion without ghosts after a true exit, and whether the bot knows if there is floor behind it on a narrow bridge. Each has a pass mark, and free-moving opponents get scored on whether the predicted region actually contains them.

I'm setting the pass rule for the upgrade: a 3D variant has to cut failures by at least 25% on two sub-tests without hurting the others, and the four arms need to train stably across seeds. I'm also flagging the outcomes that would change my plan, such as the baseline matching the pick, or the slot approach collapsing from scratch.

I'm working through the calibration costs for each camera setting: learning a gain per axis and the field of view is cheap, but Minecraft's sprint and bow FOV changes, view bobbing, and damage tilt would need a learned residual or the game's options menu. Translation is medium cost, since WASD gives no real position under collisions or knockback, so I'd have to estimate it visually and every blob would inherit that error.

I'm weighing the remaining Candidate 3 risks: blob-versus-terrain occlusion only matters if blobs are made to carry terrain, and identity collapse looks cheap to monitor with a swap metric.

I'm now reviewing the assumptions behind the design, starting with whether thing-slots can be learned from scratch at this model size using unexplained motion as the signal for what counts as an object. I'm also checking whether the off-screen terrain needs are small enough to rely on, and whether logged mouse deltas reliably map onto camera angle.

I'm now trimming the draft toward its word target by cutting the last bullet in section 1, tightening the candidate paragraphs, and shortening the section 3 preamble and the trap list.

I'm checking whether the per-tick budget claim holds, since I've been writing "fits" without a real number behind it. I'll make the budget explicit as "fits 20 Hz and 16 GB" in each candidate, and for Candidate 5 note that it's Candidate 2 with fewer slots. The claim needs a rough per-tick estimate before I can stand behind it.

I'm double-checking the links I cited: WorldMem, OC-STORM, MoVieS (using the PDF form since that's what came back), and C4G.

I'm checking that the search citations I planned are worded in my own words rather than copied, and that the search count stays at five or fewer.

I'm double-checking the citation wording against the sources, making sure my phrasing about WorldMem's memory bank is my own and not a clause-for-clause copy.

I'm checking the OC-STORM comparison against its source, making sure the wording about the frozen segmenter is my own and not a copied clause.

I'm checking the MoVieS citation wording against its source so the phrasing about its pretrained backbone and mixed training corpora stays in my own words rather than copied clause for clause.

I'm reworking the MoVieS citation so it doesn't just swap synonyms for the source sentence. The plan is to open with a different subject, something like nothing in the recipe being small or self-taught, and name the pretrained backbone and the mixed training sets with point-tracking labels as what sits underneath it.

I'm checking the MoVieS wording again, since my last attempt still mirrored the source's "built upon" structure. A from-scratch 5–15M network sits far from that setting, which leans on a large pretrained backbone and big static, dynamic, and point-tracking training sets, so the citation needs a different subject and verb.

I'm rechecking the MoVieS citation so that it opens on a different subject, a 5–15M from-scratch network, and doesn't just restate the source's "built upon" structure. I'm also confirming that the C4G claim describes its query design in my own words and doesn't copy the source clause.

I'm checking the C4G citation wording against its source, making sure the claim about pose-free, low-Gaussian, temporally robust results is phrased in my own words and not copied clause for clause. I'll also confirm the search count stays at five and that the caveats I'm adding are my own judgment rather than something the results said.

I'm checking the range-learning line: range comes from whatever makes the look-back predictions correct, with no depth labels, which stands in for the render loss. I'm also keeping the slot count at 32 to 64 rather than the brief's 64 to 128, and I'm leaving out the earlier p99 note since the preamble already covers the contended-run case.

I'm reviewing which bottleneck matters most: keeping track of moving objects behind the agent is the one where the needed information is off-screen, and only Bedwars stresses it.

I'm weighing Candidate 1's memory against the Who/Avoid queries, since its recurrent state has no built-in sense of turning and gives those queries nothing persistent to hold onto.

I'm checking the WorldMem and C4G citations against their sources and noting which caveats are my own judgment.

I'm weighing Candidate 3 on the grounds that rendering a predicted view is the only way here to distinguish "hidden behind a pillar" from "gone," but its main advantage, the rigid camera transform, doesn't require Gaussians and could run on Candidate 2's slots. The genuinely new piece is the render loss, and 256 blobs seem too few to explain a Minecraft frame.

I'm weighing Candidate 4 now: it's the only option that stores void space and matches Crafter's bird's-eye layout, but lifting a single uncalibrated camera into a grid without depth labels looks unproven, and it doesn't help with desktop.

I'm settling on Candidate 5 as the pick, with slots reserved for movers, projectiles, and interactables while terrain stays in the patch grid. Each slot carries a viewing direction and a learned range, updated by the logged mouse delta and a learned translation, with uncertainty growing as it goes unseen.

I'm settling the pick as Candidate 5, with the gating test comparing four arms on held-out maps and skins under an equal p99 tick budget.

I'm setting up the gating test: four arms on held-out maps, each tuned to the same p99 tick budget and run over 5 seeds, with every arm read through a shared probe. Scoring truth stays with the test script and never reaches the agent. I'm also laying out two sub-tests, look-away-and-back and pillar occlusion, each with its setup and pass mark.

I'm setting the upgrade rule: C or D must beat B, and B must beat A, with at least 25% fewer failures on two sub-tests, no sub-test more than 5% worse, Crafter and desktop reading not worse, and 4 of 5 seeds training cleanly. I'm also noting that these thresholds are my own proposals rather than something already checked.

I'm now on the failure conditions: if A matches B, I'd ship Candidate 1; if the splats pass the rule while B misses the absolute marks, I'd build them; and if B collapses in two or more seeds, slots trained from scratch aren't viable. Next I'm checking the Candidate 3 traps, starting with camera calibration, which looks cheap: one gain per axis plus field of view, learnable from spinning in place, though sprint, bow zoom, bobbing, and damage tilt would need a learned residual or the game's options. Translation looks harder, since WASD doesn't give position and has to be estimated visually.

I'm weighing whether C4G's pose-free, low-Gaussian query design actually lends support to the blob premise, since it's offline reconstruction of unknown scale, so the evidence is weaker than it first looks.

I'm checking the remaining trade-offs: whether the blob approach only wins if the blobs carry terrain, how identity could drift between updates, and whether the training-time render step conflicts with the per-tick comparison. I'm also noting that the assumption list is where the pick could still change.

I'm checking the remaining assumptions: whether slots can be learned from scratch at this size, whether off-screen terrain really needs only a one-block margin, and whether mouse deltas map stably to camera angle.

I'm trimming the word count by folding the labels line into the verdict and dropping the Bedwars note from the first section.

I'm tightening the C1 and C3 notes: C1 gets one code path and nothing to calibrate, with its memory lacking any sense of turning, and I'm adding the caveat that its test used ground-truth poses and a much larger model. For C3, the render loss is the genuinely new part, and it either smears blobs over terrain or lets a background decoder absorb everything while opacity collapses.

I'm cutting the word count toward the limit: folding the labels line into the verdict, trimming the Candidate 1 and Candidate 5 notes, and tightening the preamble to the held-out comparison of the four arms.

I'm now reworking the comparison setup: four arms on held-out maps and skins, with each arm resized to the same p99 tick budget and run across 5 seeds. Every arm gets read through the same small probe, since the baseline has no slots, and the scoring truth stays with the test script and never reaches the agent.

I'm trimming the word count now, including shortening the note on free-moving opponents so the false-confidence guard stays in without eating the budget.

I'm tightening the word count now: the Bedwars note and the translation bullet are going, and the scoring-honesty line is shortened so the guard against false confidence stays in.

I'm merging the translation point into the camera bullet: rotation is cheap to learn by spinning in place, while movement is harder because WASD doesn't give position under collisions or knockback, so it has to be estimated visually.

I'm tightening the word count: the Bedwars note in the budget line stays out, and the C4 description gets trimmed to its key points, since the split between terrain and movers plus the fact that Crafter is already a bird's-eye grid carry it.

I'm trimming the remaining sections now, cutting the per-candidate bullets and tightening the comparison preamble, then checking the verdict and the upgrade rule against the word budget.

I'm tightening the remaining sections: C1 keeps its scene-backbone link to C5's grid, and I'm settling on a final length around 1,120 to 1,150 words with a plain-language summary at the end.

I'm drafting the plain-language summary now, keeping it free of jargon and wrapping it up with the choice between the simpler tracked-objects design and the 3D blob system.

I'm settling on a final version: the 3D blob system waits, and the simpler tracked-objects design goes first, with the terrain map and blobs added only if they cut failures by at least a quarter.

I'm settling the citations now: the Hollow Knight claim rests on the benchmark and game results I've already noted, so I'll attach those sources directly and keep the wording plain.

I'm running a final check on the write-up for length and tightness before I finalize it.

