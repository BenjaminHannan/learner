Queue for custom_io/box/box.sh. Each NN-name.sh runs once on the box, from a frozen copy of custom_io/ taken when it starts.
Inside a job, `run NAME args...` runs one `python -m custom_io.train --data $D --out $J/w/$JOB/NAME args...`.
Header lines "# MEM <MiB>" and "# PAR <runs>" set the free-GPU need and the slots it takes.
