#!/bin/bash
# regenerate: (1) the FROZEN script from the frozen template (must be byte-identical to the committed a2232b5a...), (2) the new script from the current template into gen/ptc3s_box.new.sh
B=/tmp/claude-0/-home-user-learner/3367cbbf-5394-5200-b7a8-86f8e7226d4b/scratchpad/ptcbox
mkdir -p $B/gen
cd $B || exit 1
TEMPLATE=$B/ptc3s_box.template.frozen.sh python3 gen_box.py $B/gen/frozen_regen.sh
echo "frozen regenerated: $(sha256sum $B/gen/frozen_regen.sh | cut -c1-64)  committed: $(sha256sum $B/ptc3s_box.frozen.sh | cut -c1-64)"
python3 gen_box.py $B/gen/ptc3s_box.new.sh
sha256sum $B/gen/ptc3s_box.new.sh
bash -n $B/gen/ptc3s_box.new.sh && echo "bash -n new: ok"
wc -c $B/gen/ptc3s_box.new.sh
