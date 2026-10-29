# Mac check-in adapter selection

The external Mac check-in implementation previously accepted an adapter when its sidecar named the same HF model. That did not exclude pending or failed served checks or bind the adapter bytes.

`sleepmlx.mac_checkins` prepares and explicitly installs a patch that invokes the configured LFM3 worker environment's central `sleepmlx.day_adapter --json` selector. Only regular canonical current/previous artifacts inside the configured sleep home are accepted. Unknown profiles, ambiguous base arguments, malformed output, selector failures and timeouts use the base model. The patch also corrects the default daytime model description and removes the obsolete claim that daytime chat never uses an adapter.

The external sources were prepared read-only, reviewed, and installed with original/prepared SHA256 verification and backups at `/Users/ben-hannan/learner-ops/premonition-checkin-backup-20261029-2150`. No model service, scheduler or check-in was started or stopped. Already running Python processes retain imported code until their next normal restart.

Validation: 16 synthetic tests across `test_mac_checkins`, `test_mac_runtime` and `test_day_adapter` passed, including actual selector subprocesses against isolated files, canonical path restrictions, pending/failed/mismatched exports, timeout/failure fallback, changed-input refusal and install rollback. No mail, calendar or production memory was accessed by the tests.
