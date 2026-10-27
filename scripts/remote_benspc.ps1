[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Preflight", "Test", "Pilot", "Launch", "Supervise", "Status", "Files", "Stop")]
    [string] $Action,

    [string] $ProjectPath = "C:\Users\benja\beautiful-model",
    [int] $MinFreeMiB = 12000,
    [int] $GpuIndex = 0,
    [ValidateRange(1, 600)]
    [int] $PilotSeconds = 600,
    # run.py arguments for Pilot, Launch and Supervise.
    [string] $PilotArgsText = "",
    [string] $RunId = ""
)

$ErrorActionPreference = "Stop"
$PythonPath = "C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe"
$AllowedRoot = "C:\Users\benja\"

function Get-SafeProjectPath {
    $candidate = [IO.Path]::GetFullPath($ProjectPath.Replace('/', '\'))
    if (-not $candidate.StartsWith($AllowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "ProjectPath must stay below $AllowedRoot"
    }
    if ($candidate.TrimEnd('\') -eq $AllowedRoot.TrimEnd('\')) {
        throw "ProjectPath may not be the user-profile root"
    }
    return $candidate
}

function Get-GpuState {
    if ($MinFreeMiB -le 0) {
        throw "MinFreeMiB must be positive"
    }
    if ($GpuIndex -lt 0) {
        throw "GpuIndex must be nonnegative"
    }
    $smi = (Get-Command nvidia-smi.exe -ErrorAction Stop).Source
    $memoryText = & $smi "--id=$GpuIndex" "--query-gpu=memory.free,memory.used,memory.total" "--format=csv,noheader,nounits"
    if ($LASTEXITCODE -ne 0) {
        throw "nvidia-smi memory query failed"
    }
    $memory = @((($memoryText | Select-Object -First 1) -split ',') | ForEach-Object { [int]$_.Trim() })
    $nameText = & $smi "--id=$GpuIndex" "--query-gpu=name" "--format=csv,noheader"
    if ($LASTEXITCODE -ne 0) {
        throw "nvidia-smi name query failed"
    }
    return [pscustomobject]@{
        Name = (($nameText | Select-Object -First 1).Trim())
        FreeMiB = $memory[0]
        UsedMiB = $memory[1]
        TotalMiB = $memory[2]
    }
}

function Assert-Ready {
    param(
        [switch] $RequireProject,
        [switch] $ReportGpu,
        [switch] $RequireGpuCapacity
    )

    $project = Get-SafeProjectPath
    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        throw "Expected Python is missing: $PythonPath"
    }
    if ($RequireProject -and -not (Test-Path -LiteralPath $project -PathType Container)) {
        throw "Remote project is missing. Run the sync command first: $project"
    }
    $version = (& $PythonPath --version 2>&1 | Select-Object -First 1)

    # Host output remains visible without contaminating callers that assign
    # the function's sole pipeline result ($project).
    Write-Host "HOST=$env:COMPUTERNAME"
    Write-Host "PYTHON=$PythonPath"
    Write-Host "PYTHON_VERSION=$version"
    Write-Host "REMOTE_PROJECT=$project"
    Write-Host "REMOTE_PROJECT_EXISTS=$(Test-Path -LiteralPath $project -PathType Container)"

    if ($ReportGpu -or $RequireGpuCapacity) {
        $gpu = Get-GpuState
        Write-Host "GPU_INDEX=$GpuIndex"
        Write-Host "GPU_NAME=$($gpu.Name)"
        Write-Host "GPU_FREE_MIB=$($gpu.FreeMiB)"
        Write-Host "MIN_FREE_MIB=$MinFreeMiB"
        if ($gpu.FreeMiB -lt $MinFreeMiB) {
            Write-Host "PILOT_GPU_READY=false"
            Write-Host "PILOT_GPU_STATUS=LOW_VRAM"
            if ($RequireGpuCapacity) {
                throw "Refusing to start a GPU run: GPU free memory $($gpu.FreeMiB) MiB is below required $MinFreeMiB MiB. No process was stopped."
            }
        }
        else {
            Write-Host "PILOT_GPU_READY=true"
            Write-Host "PILOT_GPU_STATUS=READY"
        }
    }
    return $project
}

function Invoke-FastTests {
    $project = Assert-Ready -RequireProject
    $tests = Join-Path $project "tests"
    if (-not (Test-Path -LiteralPath $tests -PathType Container)) {
        throw "No tests directory exists at $tests"
    }

    $oldCudaVisible = $env:CUDA_VISIBLE_DEVICES
    try {
        # Fast checks are deliberately CPU-only even when the GPU gate passes.
        $env:CUDA_VISIBLE_DEVICES = "-1"
        Push-Location -LiteralPath $project
        try {
            # test_remote_runner exercises the POSIX coordinator with `sh`,
            # fake ssh, and fake scp. It is covered by the local suite and is
            # intentionally excluded on native Windows; every portable Python
            # model/storage/task test runs here as an importable package module.
            $modules = @(Get-ChildItem -LiteralPath $tests -Filter "test_*.py" -File |
                Where-Object { $_.Name -ne "test_remote_runner.py" } |
                Sort-Object Name |
                ForEach-Object { "tests." + $_.BaseName })
            if ($modules.Count -eq 0) {
                throw "No portable unittest modules found under $tests"
            }
            & $PythonPath -B -m unittest -v @modules
            if ($LASTEXITCODE -ne 0) {
                throw "Remote unittest failed with exit code $LASTEXITCODE"
            }
        }
        finally {
            Pop-Location
        }
    }
    finally {
        $env:CUDA_VISIBLE_DEVICES = $oldCudaVisible
    }
}

function New-PilotRuntime {
    param(
        [string] $Path = (Join-Path ([IO.Path]::GetTempPath()) ("beautiful-model-runtime-" + [guid]::NewGuid().ToString("N") + ".json"))
    )
    $json = @{
        python = $PythonPath
        shared_roots = @()
        import_roots = @()
        hard_bytes = 100000000000
        steady_bytes = 80000000000
        budget_scope = "remote_project_and_registered_roots_only"
        global_100gb_enforced = $false
        note = "Temporary BensPC runtime config; 100GB/80GB bounds apply only to the remote project/accounted roots. Host-global aggregation is not enforced. No install or download."
    } | ConvertTo-Json -Depth 4
    # Windows PowerShell 5.1's Set-Content -Encoding UTF8 emits a BOM, while
    # run.py opens JSON as plain UTF-8. Write BOM-less UTF-8 explicitly.
    [IO.File]::WriteAllText($Path, $json, (New-Object Text.UTF8Encoding($false)))
    return $Path
}

function Invoke-Pilot {
    $project = Assert-Ready -RequireProject -RequireGpuCapacity
    $runPy = Join-Path $project "run.py"
    if (-not (Test-Path -LiteralPath $runPy -PathType Leaf)) {
        throw "run.py is missing at $runPy"
    }
    if ($ProjectPath -match '[\s\"]') {
        throw "Pilot ProjectPath must not contain whitespace or quotes"
    }

    $pilotTokens = @(Get-RunTokens)
    $runtime = New-PilotRuntime
    $oldCudaVisible = $env:CUDA_VISIBLE_DEVICES
    try {
        $env:CUDA_VISIBLE_DEVICES = [string]$GpuIndex
        $arguments = @("-B", $runPy, "--runtime", $runtime) + $pilotTokens
        Write-Output "PILOT_LIMIT_SECONDS=$PilotSeconds"
        if ($pilotTokens.Count -eq 0) {
            Write-Output "PILOT_ARGS=<run.py default>"
        }
        else {
            Write-Output "PILOT_ARGS=$PilotArgsText"
        }

        # This helper never inspects, kills, pauses, or reprioritizes pre-existing
        # processes. On timeout it terminates only the exact child PID it started.
        $process = Start-Process -FilePath $PythonPath -ArgumentList $arguments -NoNewWindow -PassThru
        # Windows PowerShell only records ExitCode for a -PassThru process whose
        # handle was opened before exit; without this every exit code is $null.
        $null = $process.Handle
        if (-not $process.WaitForExit($PilotSeconds * 1000)) {
            Stop-Process -Id $process.Id -Force -ErrorAction Stop
            throw "Pilot exceeded its explicit $PilotSeconds-second limit; only pilot PID $($process.Id) was terminated."
        }
        $process.WaitForExit()
        if ($null -eq $process.ExitCode) {
            throw "Pilot exit code could not be read"
        }
        if ($process.ExitCode -ne 0) {
            throw "Pilot failed with exit code $($process.ExitCode)"
        }
    }
    finally {
        $env:CUDA_VISIBLE_DEVICES = $oldCudaVisible
        # Remove only the temporary runtime file created by this invocation.
        if (Test-Path -LiteralPath $runtime -PathType Leaf) {
            Remove-Item -LiteralPath $runtime -Force
        }
    }
}

function Get-RunTokens {
    $tokens = @($PilotArgsText -split ' ' | Where-Object { $_ -ne "" })
    foreach ($token in $tokens) {
        if ($token -notmatch '^[A-Za-z0-9_./:=,+-]+$') {
            throw "Unsafe run.py argument rejected: $token"
        }
    }
    return $tokens
}

function Get-RunDirectory {
    param(
        [string] $Project,
        [switch] $MustExist
    )
    if ($RunId -notmatch '^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}\z') {
        throw "RunId must be 1-64 characters of [A-Za-z0-9_-] and must not start with '-'"
    }
    $runDir = Join-Path $Project ".runtime\runs\$RunId"
    if ($MustExist -and -not (Test-Path -LiteralPath $runDir -PathType Container)) {
        throw "Unknown run: $runDir does not exist"
    }
    return $runDir
}

function Write-NewJson {
    param([string] $Path, $Value)
    # BOM-less UTF-8 (see New-PilotRuntime). The rename publishes a complete
    # file and fails instead of replacing an existing one.
    $temporary = "$Path.tmp"
    [IO.File]::WriteAllText($temporary, ($Value | ConvertTo-Json -Depth 4), (New-Object Text.UTF8Encoding($false)))
    [IO.File]::Move($temporary, $Path)
}

function Read-RunJson {
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    return ([IO.File]::ReadAllText($Path) | ConvertFrom-Json)
}

function Format-StartTime {
    param($Process)
    return $Process.StartTime.ToUniversalTime().ToString("o")
}

function Get-LiveRunProcess {
    # Returns the run's process only while its PID still names the process
    # recorded in run.json (same start time and command line), else $null.
    param($Run)
    if ($null -eq $Run -or $null -eq $Run.pid -or -not $Run.process_start_time -or -not $Run.command_line) {
        return $null
    }
    try {
        $process = [Diagnostics.Process]::GetProcessById([int]$Run.pid)
        # Holding the handle pins the PID: it cannot be reused by another
        # process between these checks and a Kill by the caller.
        $null = $process.Handle
        if ($process.HasExited) {
            return $null
        }
        $started = Format-StartTime $process
    }
    catch {
        return $null
    }
    if ($started -cne [string]$Run.process_start_time) {
        return $null
    }
    $cim = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($process.Id)"
    if ($null -eq $cim -or $cim.CommandLine -cne [string]$Run.command_line) {
        return $null
    }
    return $process
}

function Invoke-Launch {
    $project = Assert-Ready -RequireProject -RequireGpuCapacity
    if (-not (Test-Path -LiteralPath (Join-Path $project "run.py") -PathType Leaf)) {
        throw "run.py is missing below $project"
    }
    if ($project -match '[\s"]') {
        throw "Launch ProjectPath must not contain whitespace or quotes"
    }
    $tokens = @(Get-RunTokens)
    $runDir = Get-RunDirectory $project
    # Without -Force this fails on an existing directory: runs never overwrite.
    $null = New-Item -ItemType Directory -Path $runDir
    $null = New-PilotRuntime -Path (Join-Path $runDir "runtime.json")

    $shell = Join-Path $PSHOME "powershell.exe"
    $commandLine = "`"$shell`" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Action Supervise -ProjectPath `"$project`" -RunId $RunId -GpuIndex $GpuIndex"
    if ($tokens.Count -gt 0) {
        $commandLine += " -PilotArgsText `"$($tokens -join ' ')`""
    }
    # Windows OpenSSH can terminate processes in the session's job object when
    # the connection closes. A WMI-created process is outside that job.
    $created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $commandLine
        CurrentDirectory = $project
    }
    if ($created.ReturnValue -ne 0) {
        throw "Win32_Process.Create failed with code $($created.ReturnValue); nothing was started"
    }

    $runJson = Join-Path $runDir "run.json"
    $exitJson = Join-Path $runDir "exit.json"
    $deadline = (Get-Date).AddSeconds(60)
    while (-not (Test-Path -LiteralPath $runJson -PathType Leaf)) {
        if (Test-Path -LiteralPath $exitJson -PathType Leaf) {
            throw "Run $RunId failed to start: $([IO.File]::ReadAllText($exitJson))"
        }
        if ((Get-Date) -gt $deadline) {
            throw "Supervisor PID $($created.ProcessId) wrote no run.json within 60 s; see $runDir"
        }
        Start-Sleep -Milliseconds 500
    }
    $run = Read-RunJson $runJson
    Write-Output "RUN_ID=$RunId"
    Write-Output "RUN_DIR=$runDir"
    Write-Output "PID=$($run.pid)"
    Write-Output "PROCESS_START_TIME=$($run.process_start_time)"
    Write-Output "COMMAND_LINE=$($run.command_line)"
}

function Invoke-Supervise {
    # Started detached by Invoke-Launch. The only writer of run.json and
    # exit.json; it holds run.py's handle so the exit code can be recorded.
    $project = Get-SafeProjectPath
    $runDir = Get-RunDirectory $project -MustExist
    try {
        $tokens = @(Get-RunTokens)
        $env:CUDA_VISIBLE_DEVICES = [string]$GpuIndex
        # Unbuffered so status sees current lines; UTF-8 so printing a
        # non-cp1252 character to a redirected stdout cannot crash the run.
        $env:PYTHONUNBUFFERED = "1"
        $env:PYTHONIOENCODING = "utf-8"
        $arguments = @("-B", (Join-Path $project "run.py"), "--runtime", (Join-Path $runDir "runtime.json")) + $tokens
        $process = Start-Process -FilePath $PythonPath -ArgumentList $arguments -WorkingDirectory $project -NoNewWindow -PassThru `
            -RedirectStandardOutput (Join-Path $runDir "stdout.log") -RedirectStandardError (Join-Path $runDir "stderr.log")
        $null = $process.Handle
        $cim = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($process.Id)"
        $commandLine = $null
        if ($null -ne $cim) {
            $commandLine = $cim.CommandLine
        }
        Write-NewJson (Join-Path $runDir "run.json") ([ordered]@{
            run_id = $RunId
            pid = $process.Id
            process_start_time = (Format-StartTime $process)
            command_line = $commandLine
            started_at = (Get-Date).ToUniversalTime().ToString("o")
            gpu_index = $GpuIndex
            run_args = $tokens
            supervisor_pid = $PID
        })
        $process.WaitForExit()
        $result = [ordered]@{ exit_code = $process.ExitCode; ended_at = (Get-Date).ToUniversalTime().ToString("o") }
    }
    catch {
        $result = [ordered]@{ exit_code = $null; ended_at = (Get-Date).ToUniversalTime().ToString("o"); error = $_.Exception.Message }
    }
    Write-NewJson (Join-Path $runDir "exit.json") $result
}

function Invoke-Status {
    $runDir = Get-RunDirectory (Get-SafeProjectPath) -MustExist
    $run = Read-RunJson (Join-Path $runDir "run.json")
    $exit = Read-RunJson (Join-Path $runDir "exit.json")
    Write-Output "RUN_ID=$RunId"
    Write-Output "RUN_DIR=$runDir"
    if ($null -ne $run) {
        Write-Output "PID=$($run.pid)"
        Write-Output "STARTED_AT=$($run.started_at)"
    }
    if ($null -ne (Get-LiveRunProcess $run)) {
        Write-Output "STATE=alive"
    }
    elseif ($null -eq $run -and $null -eq $exit) {
        Write-Output "STATE=unknown"
    }
    else {
        Write-Output "STATE=exited"
    }
    if ($null -ne $exit -and $null -ne $exit.exit_code) {
        Write-Output "EXIT_CODE=$($exit.exit_code)"
    }
    else {
        Write-Output "EXIT_CODE=unknown"
    }
    if ($null -ne $exit -and $exit.error) {
        Write-Output "ERROR=$($exit.error)"
    }
    try {
        $gpu = Get-GpuState
        Write-Output "GPU_INDEX=$GpuIndex"
        Write-Output "GPU_USED_MIB=$($gpu.UsedMiB)"
        Write-Output "GPU_FREE_MIB=$($gpu.FreeMiB)"
        Write-Output "GPU_TOTAL_MIB=$($gpu.TotalMiB)"
    }
    catch {
        Write-Output "GPU_STATUS=unavailable: $($_.Exception.Message)"
    }
    foreach ($name in @("stdout.log", "stderr.log")) {
        Write-Output "--- $name (last 20 lines) ---"
        $log = Join-Path $runDir $name
        if (Test-Path -LiteralPath $log -PathType Leaf) {
            try {
                Get-Content -LiteralPath $log -Tail 20
            }
            catch {
                Write-Output "(unreadable: $($_.Exception.Message))"
            }
        }
    }
}

function Invoke-Files {
    # Lists what fetch may copy: the run directory's files and every existing
    # artifacts/<name> that run.py printed to stdout.
    $project = Get-SafeProjectPath
    $runDir = Get-RunDirectory $project -MustExist
    if ($null -ne (Get-LiveRunProcess (Read-RunJson (Join-Path $runDir "run.json")))) {
        throw "Run $RunId is still alive; fetch it after it exits (status shows progress)"
    }
    foreach ($file in @(Get-ChildItem -LiteralPath $runDir -File | Sort-Object Name)) {
        if ($file.Name -match '^[A-Za-z0-9_-][A-Za-z0-9_.-]*\z') {
            Write-Output "RUNFILE=$($file.Name)"
        }
    }
    $stdout = Join-Path $runDir "stdout.log"
    if (Test-Path -LiteralPath $stdout -PathType Leaf) {
        $names = @([regex]::Matches([IO.File]::ReadAllText($stdout), 'artifacts/([A-Za-z0-9_-][A-Za-z0-9_.-]*)') |
            ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
        foreach ($name in $names) {
            if (Test-Path -LiteralPath (Join-Path $project "artifacts\$name") -PathType Leaf) {
                Write-Output "ARTIFACT=artifacts/$name"
            }
        }
    }
}

function Invoke-Stop {
    $runDir = Get-RunDirectory (Get-SafeProjectPath) -MustExist
    $run = Read-RunJson (Join-Path $runDir "run.json")
    if ($null -eq $run) {
        throw "run.json is missing; refusing to stop anything"
    }
    $process = Get-LiveRunProcess $run
    if ($null -eq $process) {
        Write-Output "STATE=exited"
        Write-Output "Nothing was stopped: PID $($run.pid) is not running with the recorded start time and command line."
        return
    }
    # Only this verified PID; the pinned handle rules out PID reuse.
    $process.Kill()
    [void]$process.WaitForExit(30000)
    Write-Output "STOPPED_PID=$($process.Id)"
}

switch ($Action) {
    "Preflight" { [void](Assert-Ready -ReportGpu); break }
    "Test"      { Invoke-FastTests; break }
    "Pilot"     { Invoke-Pilot; break }
    "Launch"    { Invoke-Launch; break }
    "Supervise" { Invoke-Supervise; break }
    "Status"    { Invoke-Status; break }
    "Files"     { Invoke-Files; break }
    "Stop"      { Invoke-Stop; break }
}
