#!/usr/bin/env python3
"""which dry-run helper scripts differ between the scratch folder and the kit's dryrun-tools folder"""
import os
B = '/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox'
T = '/home/user/learner/.claude/worktrees/agent-ad724fe9f9d0de7d1/results/8a-g/vast-ptc3s/dryrun-tools'
for f in sorted(os.listdir(T)):
    a = os.path.join(B, f)
    if not os.path.isfile(a):
        print('NOT-IN-SCRATCH', f)
    elif open(a, 'rb').read() != open(os.path.join(T, f), 'rb').read():
        print('CHANGED', f)
print('--- in scratch, wanted for the b3sweep evidence, not yet in the kit:')
want = ['run_b3.sh', 'chain_final.sh', 'wait_for.sh', 'shim_test.sh', 'b3_quick.sh', 'helper_tests.sh', 'defaults_test.sh', 'quick_tests_b3.sh', 'fake_b3.sh', 'cmp_tools.py']
for f in want:
    print(('present ' if os.path.isfile(os.path.join(T, f)) else 'MISSING ') + f, '(scratch: %s)' % os.path.isfile(os.path.join(B, f)))
print(os.listdir(os.path.join(B, 'shimbin')))
