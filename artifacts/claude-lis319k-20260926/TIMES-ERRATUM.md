# Times erratum (reading thread, written 2026-09-26T15:00:27Z)
Some PASSMARKS headers give estimated times ("~13:55", "~14:20", "~14:25", "~14:30"). They were guesses, not clock
readings. The registration times are the git commit times on main (UTC):
- lis-319k PASSMARKS 6bd125ee5 13:40:05; readpanel319k seal cb0689501 13:57:38; lis-319k fallback 707a10ca4 14:07:29
- lis-319j 72705d893 14:06:22; lis-319f2 89a4a975b 14:07:07; lis-319t 9a5c36070 14:24:54
All were committed before any read of readpanel371c or readpanel319k reached this thread (none has yet, at this writing).
