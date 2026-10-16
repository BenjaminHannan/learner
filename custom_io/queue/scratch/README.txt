Scratch A/B screen queue (Oct 16). The box for it is launched with
  python3 custom_io/box/vast.py create --offer ID --maxpar 1 --qsub /scratch --br claude/project-thread-2zeaoc
so it polls only this folder, on this branch, one run at a time. 41..46 = base_s100, arm_s100, base_s101, arm_s101,
base_s102, arm_s102. Each job trains, then writes readout.json (custom_io/scratch_readout.py) beside RESULT.json.
