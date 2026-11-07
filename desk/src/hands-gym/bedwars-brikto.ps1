param([ValidateSet('launch','quit','status')][string]$Command='status',
      [ValidateSet('BotHands1','BotIdle1')][string]$Name='BotHands1',
      [string]$Root='C:\Users\Public\bedwars1', [switch]$InTask)
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
if ($Root -ne 'C:\Users\Public\bedwars1') {throw 'Only the dedicated BEDWARS1 root is allowed'}
$taskName="BEDWARS1-$Name"
$namePattern='(?:^|\s)"?-Dbw\.name='+[regex]::Escape($Name)+'(?:"|\s|$)'
function Get-OwnedClient {
    Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq 'javaw.exe' -and $_.ExecutablePath -eq "$Root\jdk8\bin\javaw.exe" -and $_.CommandLine -match $namePattern
    }
}
if ($Command -eq 'status') {
    Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'javaw.exe' -and $_.CommandLine -like "*$Root*"} |
        Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress
    exit 0
}
if ($Command -eq 'quit') {
    Get-OwnedClient |
        ForEach-Object {Stop-Process -Id $_.ProcessId -Force; Write-Output "stopped owned PID $($_.ProcessId)"}
    exit 0
}
if (-not $InTask) {
    if (Get-OwnedClient) {
        throw 'Owned client already running'
    }
    $consoleUser=(Get-CimInstance Win32_ComputerSystem).UserName
    if (-not $consoleUser) {throw 'No interactive Windows session available for OpenGL'}
    $principal=New-ScheduledTaskPrincipal -UserId $consoleUser -LogonType Interactive -RunLevel Limited
    $arguments="-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Root\bedwars-brikto.ps1`" -Root `"$Root`" -Command launch -Name $Name -InTask"
    $action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
    $settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    $existing=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing -and ($existing.Actions.Arguments -notlike "*-File `"$Root\bedwars-brikto.ps1`"*" -or $existing.State -eq 'Running')) {
        throw 'Refusing to overwrite an unrecognized or running scheduled task'
    }
    Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Settings $settings -Force | Out-Null
    Start-ScheduledTask -TaskName $taskName
    Write-Output "started owned task $taskName"
    exit 0
}
$profile="$Root\clients\$Name"
New-Item -ItemType Directory -Force "$profile\mods","$Root\mod" | Out-Null
Copy-Item "$Root\bwbridge189.jar" "$profile\mods\bwbridge189.jar" -Force
@'
fancyGraphics:false
renderDistance:2
maxFramerate:20
enableVsync:false
guiScale:1
particles:2
entityShadows:false
pauseOnLostFocus:false
soundCategory_master:0.0
fullscreen:false
useVbo:true
fboEnable:true
viewBobbing:false
lang:en_US
snooperEnabled:false
resourcePacks:[]
'@ | Set-Content "$profile\options.txt" -Encoding ASCII
$spec=Get-Content "$Root\bedwars-runtime.json" -Raw | ConvertFrom-Json
$arguments=@($spec.arguments | ForEach-Object {$_.Replace('C:\Users\timot\bedwars1',$Root).Replace('BotHands1',$Name)})
$digest=[System.Security.Cryptography.MD5]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes("OfflinePlayer:$Name"))
$digest[6]=($digest[6] -band 15) -bor 48
$digest[8]=($digest[8] -band 63) -bor 128
$arguments[[Array]::IndexOf($arguments,'--uuid')+1]=([BitConverter]::ToString($digest)).Replace('-','').ToLowerInvariant()
$java="$Root\jdk8\bin\javaw.exe"
$argumentLine=($arguments | ForEach-Object {'"'+$_.Replace('"','\"')+'"'}) -join ' '
$process=Start-Process -FilePath $java -ArgumentList $argumentLine -WorkingDirectory $Root -PassThru -WindowStyle Hidden -RedirectStandardOutput "$Root\$Name.out" -RedirectStandardError "$Root\$Name.err"
$process.PriorityClass='BelowNormal'
$process.Id | Set-Content "$Root\$Name.pid"
Add-Type -Namespace Bedwars1 -Name OwnedWindow -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool ShowWindow(System.IntPtr handle, int command);
'@
for ($attempt=0; $attempt -lt 30 -and -not $process.HasExited; $attempt++) {
    $process.Refresh()
    if ($process.MainWindowHandle -ne [IntPtr]::Zero) {[void][Bedwars1.OwnedWindow]::ShowWindow($process.MainWindowHandle,0); break}
    Start-Sleep -Milliseconds 500
}
$process.WaitForExit()
exit $process.ExitCode
