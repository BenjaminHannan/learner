# rd-378g BensPC helper (Trustworthy notes thread; copied from the y1t kit): list every python.exe with its command line, one line each. Read only.
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object { "PROC $($_.ProcessId) $($_.CommandLine)" }
