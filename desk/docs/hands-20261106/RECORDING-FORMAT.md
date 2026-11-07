# Recorder file format

Clips are stored under `~/learner-ops/hands-recorder/recordings/`. `clip-index.json` lists finished clips. Each clip has an overview MP4, a 192×192 detail MP4 and an event JSONL file. The source combines the connected displays into the overview; `capture_boundary` rows name the display IDs and their combined bounds. The aspect ratio is preserved with black padding. The video has a nominal 20 frames per second.

Events use `t`, milliseconds on the Mac's monotonic uptime clock. Frame rows also have `receiveMonotonicMs` and `frameId`. `videoClock.firstFrameMonotonicMs` in the clip index anchors the first video frame; `frameId` is the submitted frame ordinal. Video and input timing is not proven by the nominal rate. The index records a measured `offsetMs` only if an actual calibration file exists. A single offset does not establish that later frames have no timing drift; use the individual frame events and treat timing as approximate until independently checked.

Retention removes indexed clips as limits require and records deletion operations in `retention.log`. The default limits are 12 GiB total, 6 GiB per day, seven days, and a pause below 10 GiB free. An index entry with `offsetMs: null` has no measured calibration.
