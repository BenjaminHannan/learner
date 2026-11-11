# Model explainer with a voice (picture hand-off)

`project/` is the editable HyperFrames video (all words, numbers and timings in `project/content/*.json`), with the caption timings already moved to fit the narration
(`project/narration/` holds the spoken script and the timing plan; the speech itself is made on the cloud box).
This folder exists so another machine can render the silent picture chunks:

    cd animations/model-explainer-voice/project
    bash mac-render.sh ch14        # one chunk first, to see how long it takes
    bash mac-render.sh             # all chunks, written to ../renders-mac/

Chunks: ch00 ch01 ch03 ch04 ch05 ch06 ch07 ch08 ch09 ch14 end. The cloud box mixes the voice into the joined video.
Do not edit anything in `project/content` or `project/chapters`: the narration is timed to exactly this content.
