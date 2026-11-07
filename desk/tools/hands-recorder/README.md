# Glim's recorder

The recorder runs locally inside Premonition. `~/learner-ops/hands-recorder/recorderctl start` starts real capture when the lead release file is present; `stop` turns it off. The saved switch stays on through a host restart and starts the recorder when Premonition opens, including at login. `status` reports the running host. No audio is recorded.

The source combines all connected displays into a 1280×720 video, including the pointer, and logs keyboard and mouse events with the Mac's monotonic clock. Main and detail video are H.264; the target is 250 and 50 kbit/s. Actual disk use depends on the screen and is measured separately. Display layout changes are recorded in the event stream. Each clip index includes the first frame's monotonic time; an offset is included only after a real calibration has been measured. A fixed offset alone does not prove per-frame alignment if frames are late or missing.

The recorder pauses if less than 10 GiB remains free; it also has a 6 GiB daily and 12 GiB total cap. It retries after a disk pause. Retention can remove indexed clips at the configured limits. `preflight` checks the existing macOS Screen Recording and Input Monitoring grants without requesting them. The `permissions` commands explicitly request missing macOS grants.

`start --fake` records generated test pictures. `canary` runs the fake-field test. The installer can target a staging bundle using `HANDS_RECORDER_BUNDLE`; sign the final bundle with the existing app identifier after adding the native helpers.
