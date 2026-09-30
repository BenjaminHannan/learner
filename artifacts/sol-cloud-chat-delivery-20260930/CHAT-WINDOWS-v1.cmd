@echo off
setlocal
echo Premonition joined chat. Sleep and training are disabled.
echo This fitted TRAIN diagnostic is not qualified for general conversation.
set "PREMONITION_CHAT_PYTHON=C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe"
set "PREMONITION_CHAT_RUNTIME=C:\Users\benja\sol-cloud-exposure16-r5-r1"
set "PYTHONPATH=%PREMONITION_CHAT_RUNTIME%;%PREMONITION_CHAT_RUNTIME%\scripts;C:\Users\benja\lis300\venv\lib\site-packages"
set "PYTHONUTF8=1"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "OMP_NUM_THREADS=2"
"%PREMONITION_CHAT_PYTHON%" -B "%~dp0scripts\sol_cloud_chat_nosleep_v1.py" --runtime-root "%PREMONITION_CHAT_RUNTIME%" --seed 0 --device cuda --connected-resume "C:\Users\benja\sol-translator-tiny-v12\artifacts\sol-translator-20260929\tiny-v12-s0\connected-resume.pt" --connected-resume-sha256 5858bd5dc4446d78bc49e04149740f98c9adce0e7938089728eec009c33d4b55 --max-new-tokens 32 %*
exit /b %errorlevel%
