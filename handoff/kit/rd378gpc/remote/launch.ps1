# rd-378g BensPC helper (Trustworthy notes thread; copied from the y1t kit): start one command detached through WMI
# (Win32_Process.Create survives the ssh disconnect). Prints the WMI return value and the PID.
param([string]$Cmd)
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $Cmd; CurrentDirectory = 'C:\Users\benja\rd378g2\tree'}
"rc=$($r.ReturnValue) pid=$($r.ProcessId)"
