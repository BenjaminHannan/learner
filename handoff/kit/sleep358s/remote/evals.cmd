@echo off
rem rsn-358s helper (sleep research thread): step 7's evals, one checkpoint after another
cd /d C:\Users\benja\rsn358s
for %%R in (%*) do call C:\Users\benja\rsn358s\handoff\kit\sleep358s\remote\eval1.cmd %%R
