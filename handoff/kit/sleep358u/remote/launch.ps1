# rsn-358u helper (sleep research thread): start one command detached through WMI (Win32_Process.Create survives the ssh
# disconnect; PowerShell Start-Process children died with the session in 358i3). Prints the WMI return value and the PID.
param([string]$Cmd)
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $Cmd; CurrentDirectory = 'C:\Users\benja\rsn358u'}
"rc=$($r.ReturnValue) pid=$($r.ProcessId)"
