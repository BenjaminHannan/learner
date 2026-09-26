set -e
cd /home/user/learner
J=/tmp/claude-0/-home-user-learner/b1bf6f96-27ff-5ea3-ba3e-ed03f56d91d3/scratchpad/c371b/j
A=artifacts/claude-rd371b-20260926
# training data
for i in 0 1 2 3 4 5 6 7; do test -s $J/train_out.$i.jsonl; done
cp $J/train_in.jsonl $A/data/judge_train_in.jsonl
cat $J/train_out.{0,1,2,3,4,5,6,7}.jsonl > $A/data/judge_train_out.jsonl
python3 scripts/claude_rd371b_data.py --pair $A/data/judge_train_in.jsonl:$A/data/judge_train_out.jsonl --out $A/data/ck
sha256sum $A/data/judge_train_in.jsonl $A/data/judge_train_out.jsonl $A/data/ck/train.jsonl $A/data/ck/dev.jsonl $A/data/ck/summary.json $A/data/dev_in.jsonl $A/data/dev_out.jsonl > $A/SEAL-train.sha256.txt
# key
mkdir -p $A/key
printf '%s\n' '# rd-371b key (TEST-ONLY): notepanel371b greedy notes + two blind judges; key = both ok / both unsupported, rest excluded.' 'Sealed before the checker trains. Never train, tune, read or quote; scripts print counts only.' > $A/key/README.md
cp $J/panel_in.jsonl $A/key/panel_in.jsonl
cp $J/panel_out_A.jsonl $A/key/judge_A.jsonl
cp $J/panel_out_B.jsonl $A/key/judge_B.jsonl
python3 $J/key.py $A/key/panel_in.jsonl $A/key/judge_A.jsonl $A/key/judge_B.jsonl $A/key/key.jsonl > $A/key/key_counts.json
cat $A/key/key_counts.json
(cd $A/key && sha256sum README.md panel_in.jsonl judge_A.jsonl judge_B.jsonl key.jsonl key_counts.json > SEAL.sha256.txt)
