# B3G2 pair on this box: custom_io at 74d6e92c75f3a0ed6b3f1e49e13fefc5ed5d29d6; every file below was sha256-checked
models/b3g2.py a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce
models/writer.py f3a40ad58749bbc24a964942dc650c79864d6a74442628aac7d752730e73309e
g8a/caps.py 32862ae2d4e6e401fcad5bb6c5e54b0b8845019202dea73e2cb4c7efe5eea03e
g8a/caps_b3g2.json ee551d3aacbf9ec02d2ac7f5e7e6e12f44e15aba2c39f5f38c3f1e3ec12d7ed4
g8a/job.py a590e3f176159f531571b1e5ae95bd48d2160238cb999add5eb6be7734fe6a1a
g8a/configs.py 31287a25a6ad9cbf48973520f1174c788a3db5ce61f607265aa5ec8fa99bd5da
local_runner.py 0562a4bb065a02f6c048d919d68bb6d445f36e357518dc8826d9d545323db4ef
train.py e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d

PROF-PAIR cmd a4 (MEM 9000 MiB; queue --train-extra was ['--ckpt-every 100 --log-every 1 --resume']): /usr/bin/python -m custom_io.g8a.job --work /job/work/g8a --local --out /job/work/results/8aPTC3S-pc/pair/a4 --skills /job/work/data --big-data /job/work/data_big --data8a /job/work/data8a --rung 3M --seed 400 --arms B3G2 --b2-extra '{"eg_embed": true}' --cloze-long /job/work/b3-inputs/cloze_long.py --caps-file /job/work/b3-inputs/caps_b3g2.json --accum B3G2=4 --device cuda --train-extra '--log-every 1'
PROF-PAIR cmd a32 (MEM 3500 MiB; queue --train-extra was ['--ckpt-every 50 --log-every 1 --resume']): /usr/bin/python -m custom_io.g8a.job --work /job/work/g8a --local --out /job/work/results/8aPTC3S-pc/pair/a32 --skills /job/work/data --big-data /job/work/data_big --data8a /job/work/data8a --rung 3M --seed 400 --arms B3G2 --b2-extra '{"eg_embed": true}' --cloze-long /job/work/b3-inputs/cloze_long.py --caps-file /job/work/b3-inputs/caps_b3g2.json --accum B3G2=32 --device cuda --train-extra '--log-every 1'
PROF-PAIR the two commands are identical except --out and --accum: yes
