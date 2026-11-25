# Bug hunt (read-only). Find real bugs in the code below that would make the scored run invalid or misleading.
Run: forecast4.py (harness) + imagine_head6.py (experimental imagine step), using wm_fit.py, sizes.py and the core
board_swarm.py. Intent: freeze EVERYTHING except imagine_out (new MLP), action_emb, cell.action_in, cell.action_pos;
train on k=1 real transitions through a frozen closed-form ridge readout; score k=1,3,5 rollouts on held-out worlds.
Check especially: (a) is anything else still trainable or still changing (BN/MoE/train-mode noise, refmean in train
mode, readout refit)? (b) does imagine_out get gradient, and does the action reach hn (action token + action context)?
(c) is the zero-init last layer + imagine_scale shape [R,D] broadcast right? (d) scoring/verdict bugs vs the marks
in the header comment of the request (E/B <= 0.80/0.90/0.95; 12/16 worlds pass both shuffle marks; std ratio 0.25-2;
pcs90 >= half; ceiling <= 0.70). (e) leakage of held-out data into training or readout fit.
For each finding: file:line, the bug, why it matters, a minimal fix. Label shown/suggested. Say "no bug found" per area
if none. <= 500 words.
