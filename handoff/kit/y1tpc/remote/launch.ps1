# y1t BensPC helper (Answering-from-memory thread): start one command detached through WMI (Win32_Process.Create survives
# the ssh disconnect; the sleep research thread's tested pattern). Prints the WMI return value and the PID.
param([string]$Cmd)
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $Cmd; CurrentDirectory = 'C:\Users\benja\y1t\tree'}
"rc=$($r.ReturnValue) pid=$($r.ProcessId)"
