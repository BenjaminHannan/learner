# Model explainer v2 (captivating cut, Oct 11)

The finished video is `animations/model-explainer-v2-narrated-1080p.mp4` in the project's shared folder (70.5 min, 1080p, too big for git).

What changed from the narrated v1 cut:
- a 42 s cold open (teaser) before Start here;
- the whole narration rewritten for someone who knows nothing about machine learning (same facts, honesty labels kept, checked by `tools/voice/check_script.py` and a fact-check pass);
- two new parts: Part 9 "Learning while it sleeps" (`ch11`) and Part 10 "Creative mode: what it does when it gets stuck" (`ch12`), both as of Oct 11;
- a synthesised music bed and sound effects under the voice (`tools/audio/`), levelled to -17 LUFS;
- a progress bar split into one segment per part (`main.js`), so changing one part no longer moves the bar in every later part.

How to rebuild: `animations/VOICE-RECIPE.md` in the shared folder (section "v2"). In short: write `narration/script/chNN.json`, make the voice with `tools/voice/tts.py`, pace with `tools/voice/pace.py`, render each part with `npx hyperframes@0.8.143 render` after `node tools/mkindex.mjs --only chNN`, build the voice with `tools/voice/compose.py` and the mix with `tools/audio/build_mix.sh`, then join the cold open and parts with `ffmpeg -f concat -c copy` and mux the audio.

Part order: ch00 ch01 ch03 ch04 ch05 ch06 ch07 ch08 ch09 ch11 ch12 ch14, then the end card.
