@echo off
rem rsn-358u helper (sleep research thread): step 7's evals, one checkpoint after another
cd /d C:\Users\benja\rsn358u
for %%R in (%*) do call C:\Users\benja\rsn358u\handoff\kit\sleep358u\remote\eval1.cmd %%R
