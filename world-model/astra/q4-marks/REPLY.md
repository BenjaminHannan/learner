**The marks are fair for action-conditioned frame prediction: PARTIAL is meaningful, and PASS is a stretch.** With your blend gains, the three error caps are about **0.77, 0.80, and 0.79 of copy error**. So k=5 isn’t an easy pass despite the 0.95 cutoff: it requires roughly the same gain over copy after five feedback steps as k=1 does after one.

The k=1 shuffle gate is the mark most likely to be too hard. Frequent frame changes needn’t be *action-dependent*, and visually equivalent actions dilute the shuffle penalty. I’d keep 1.25× in 12/16 worlds as a demanding action-sensitivity criterion, average over repeated shuffles, and report paired uncertainty across worlds. Treat the std band as a collapse check; predeclare how rare actions and near-zero real std count.

**Loophole:** an exact copy fails, but an action-specific screen shift plus shrinkage could beat both baselines, suffer under shuffling, and have plausible change std without predicting state-dependent interactions. The frozen readout makes decoded accuracy meaningful; it doesn’t establish that imagined boards match real boards internally.

**One extra control:** fit one image translation and shrink coefficient per action on train worlds, then roll that predictor out with the same action sequences. A held-out gain over it on moved windows would be evidence beyond action-specific motion templates.

**Subjective odds under the proposed marks:** PASS 20%, PARTIAL only 40%, FAIL 40%. The redraw result establishes decodability, not how much future motion is predictable.