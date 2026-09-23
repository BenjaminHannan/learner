SMOKE TEST — running your three read-only checks.
First check complete — running the remaining two.
Second check complete — running the last one.
`df -g /`:
```
Filesystem     1G-blocks Used Available Capacity iused     ifree %iused  Mounted on
/dev/disk3s1s1       460   12        18    41%  484014 194767840    0%   /
```

`uptime`:
```
21:39  up 2 days, 13:29, 3 users, load averages: 25.99 31.23 41.01
```

`git log --oneline -1`:
```
e3fbf3c51 261: builder reply, sealed marks, results, scorer
```

SMOKE-OK
