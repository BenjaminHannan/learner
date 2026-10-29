# Blocked finalization preflight

An obsolete or malformed uncommitted gate decision needs an explicit re-gate. Previously the chunk worker loaded the entire training model before discovering that the saved decision could not be used, and repeated chunks could repeat that allocation.

The worker now reads the immutable checkpoint and invokes the same read-only admission guard used by finalization before reading the diary, checking model preload memory or allocating a backend. Blocked decisions retain their files and return zero steps, no quiz, a resumed flag and the existing explicit re-gate explanation. Current bound decisions, exact already-committed completions and valid saved rejections continue through their existing completion paths. Dry runs do not inspect or repair existing night checkpoints.

Validation: all 25 worker and finalization-binding tests pass in6.603s. New cases fail if a blocked decision reads the diary, checks model allocation memory or loads a backend; they compare every saved home-file hash before/after. Separate current/committed/rejection fixtures reach the backend boundary and preserve the checkpoint. No model, service or production data was used.
