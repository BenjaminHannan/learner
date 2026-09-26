# Frame spec note, lis-319f (2026-09-26): mode FORMER

Additive to frame-spec.md. New fact mode:
- `FORMER`: it was true and no longer is ("used to work at Brindle", "was a midwife for 50 years", "my old roommate
  Asuka", "lived in Vell till last year"). Things that were true once and stay true (born in, grew up in, went to school
  at, a birthday, "my ex-wife Dana" as ex_wife) keep ASSERT. A value that carries the time itself ("retired judge") keeps
  ASSERT.
The write compiler saves only ASSERT and CORRECT, so FORMER facts are held and never saved as current (no code change).
Why: the old modes could not say "used to"; training labels taught former jobs as current (checked 09-26 12:05 UTC).
