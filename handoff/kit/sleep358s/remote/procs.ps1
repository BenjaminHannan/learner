# rsn-358s helper (sleep research thread): list every python.exe with its command line, one line each. Read only.
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object { "PROC $($_.ProcessId) $($_.CommandLine)" }
