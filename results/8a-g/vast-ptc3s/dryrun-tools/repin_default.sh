#!/bin/bash
# default-path (PROFILE unset) checks of the re-pinned script: marker comparison with the first script's full dry run and with the PROFILE-commit script's default run; offline kit tests on the new default log
P=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad
B=$P/ptcbox
O=$B/repin_out
mkdir -p $O
cd $B || exit 1
{ echo "first script (dry_final4.log) against the re-pinned script (dry_p8_default_repin.log):"; python3 -I cmp_logs.py dry_final4.log dry_p8_default_repin.log
  echo "PROFILE-commit script (dry_p4_default.log) against the re-pinned script:"; python3 -I cmp_logs.py dry_p4_default.log dry_p8_default_repin.log; } > $O/default_vs_first_script_markers_pin_ca542f77.txt 2>&1
cat $O/default_vs_first_script_markers_pin_ca542f77.txt
grep -v '^R|' dry_p8_default_repin.log | cut -c1-600 > $O/default_run_pin_ca542f77.log
bash run_fake_default.sh $B/dry_p8_default_repin.log > $O/fake_vast_test_pin_ca542f77_default_log.txt 2>&1
grep -E 'A script after|A args|C collect|D .*checkpoint.pt|kit_bug|^1 |^2 ' $O/fake_vast_test_pin_ca542f77_default_log.txt | cut -c1-220
