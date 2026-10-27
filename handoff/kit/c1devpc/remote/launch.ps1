# c1-dev BensPC helper (Everyday chat thread): start one command detached through WMI (Win32_Process.Create survives
# the ssh disconnect; the y1t and sleep358s kits' tested pattern). Prints the WMI return value and the PID.
param([string]$Cmd)
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $Cmd; CurrentDirectory = 'C:\Users\benja\lis301\work\c1dev\tree'}
"rc=$($r.ReturnValue) pid=$($r.ProcessId)"
