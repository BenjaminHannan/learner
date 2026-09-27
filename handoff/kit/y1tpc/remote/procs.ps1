# y1t BensPC helper (Answering-from-memory thread): list every python.exe with its command line, one line each. Read only.
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object { "PROC $($_.ProcessId) $($_.CommandLine)" }
