# AT-1 code on this box: custom_io at 6e72a5fae514a343c217c4d95cde37bc3b587c8e; every file below was sha256-checked
train.py e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d
models/b3at.py 5b10aac1f20914baa72dfea114379682e6ddfc1dbdee2f749a546760e7fc1768
models/b3g2.py a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce
models/writer.py f3a40ad58749bbc24a964942dc650c79864d6a74442628aac7d752730e73309e
models/b3.py f3ef34d9f13256ccee1ca7dd47efc32cb7eaf51e3a09c4221e3be4c0858804c8
g8a/configs.py 343700363ae14cc31dcdbc705a9258b9c8384e48adac5d175997d1fbfbcef875
g8a/job.py d4d422aab845d0ed36396bdef7129f74fd6bca1205ae224feac20e324148c662
local_runner.py 0562a4bb065a02f6c048d919d68bb6d445f36e357518dc8826d9d545323db4ef
g8a/caps.py 433475405ae7263579ebf4b9633916842567a5b1b1f3a8930311945e504f62d3
g8a/caps_b3g2.json ee551d3aacbf9ec02d2ac7f5e7e6e12f44e15aba2c39f5f38c3f1e3ec12d7ed4
queue_local/8aAT-3M-s400-pc.txt 2cc320741260eb522b85c7e647b9cab235d06903484179cde1ab9be9571d475a

CMD 8aAT-3M-s400 mem 9000 MiB: /usr/bin/python -m custom_io.g8a.job --work /job/work/g8a --local --out /job/work/results/8aPTC3S-pc/8aAT-3M-s400 --skills /job/work/data --big-data /job/work/data_big --data8a /job/work/data8a --rung 3M --seed 400 --arms AT --b2-extra '{"eg_embed": true}' --cloze-long /job/work/b3-inputs/cloze_long.py --caps-file /job/work/b3-inputs/caps_b3g2.json --accum AT=32
