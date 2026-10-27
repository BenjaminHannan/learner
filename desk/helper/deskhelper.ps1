# deskhelper.ps1: screen-control CLI for Premonition on Windows. Same commands and JSON as the Mac deskhelper (deskhelper.swift).
# Windows PowerShell 5.1, built-in .NET only (UIAutomationClient, System.Windows.Forms, System.Drawing, user32 via Add-Type).
# Nothing to compile. Run:  powershell -NoProfile -ExecutionPolicy Bypass -File deskhelper.ps1 <command> [args]
#
#   check                          {"accessibility":true,"screenRecording":true}   (Windows needs no permission for any of this)
#   ask-permissions                same
#   look [--app NAME] [--max N]    {"app","pid","windows":[{"title","frame"}],"elements":[{"id","role","title","value","frame":[x,y,w,h]}]}
#                                  also saves id -> element info to %LOCALAPPDATA%\premonition-desk\last_look.json
#   press ID                       click / focus the element with that id from the last look
#   click X Y [--double] [--right]
#   type TEXT                      Unicode keystrokes (SendInput)
#   key COMBO                      ctrl/shift/alt/win + key name or letter (enter, tab, esc, space, backspace, delete, up, down, left, right, home, end, f1..f12);
#                                  cmd / command -> ctrl and option / opt -> alt, so Mac-style combos still work
#   scroll DY                      wheel lines, negative = down
#   open-app NAME                  focus a running app, else start it by its Start menu name (Get-StartApps), else Start-Process
#   screenshot PATH [--max 1280]   JPEG of the primary display, scaled
# Errors: {"error": "..."} with exit code 1. Password fields are reported with role SecureEdit and never read.

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Web.Extensions

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class DH {
  [StructLayout(LayoutKind.Sequential)] public struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Explicit)] public struct INPUTUNION { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; }
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public INPUTUNION u; }

  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetWindow(IntPtr h, uint cmd);
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint dx, uint dy, int data, UIntPtr extra);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] inputs, int size);
  [DllImport("user32.dll")] public static extern short VkKeyScan(char c);

  public static void Key(ushort vk, uint flags) {
    INPUT[] a = new INPUT[1];
    a[0].type = 1; a[0].u.ki.wVk = vk; a[0].u.ki.wScan = 0; a[0].u.ki.dwFlags = flags; a[0].u.ki.time = 0; a[0].u.ki.dwExtraInfo = IntPtr.Zero;
    SendInput(1, a, Marshal.SizeOf(typeof(INPUT)));
  }
  public static void Uni(char c) {
    INPUT[] a = new INPUT[2];
    a[0].type = 1; a[0].u.ki.wVk = 0; a[0].u.ki.wScan = (ushort)c; a[0].u.ki.dwFlags = 0x4;
    a[1].type = 1; a[1].u.ki.wVk = 0; a[1].u.ki.wScan = (ushort)c; a[1].u.ki.dwFlags = 0x4 | 0x2;
    SendInput(2, a, Marshal.SizeOf(typeof(INPUT)));
  }
  public static void Activate(IntPtr h) {
    if (IsIconic(h)) ShowWindow(h, 9);
    keybd_event(0x12, 0, 0, UIntPtr.Zero); keybd_event(0x12, 0, 2, UIntPtr.Zero); // a bare Alt tap lets SetForegroundWindow through
    SetForegroundWindow(h);
  }
}
"@

try { [void][DH]::SetProcessDPIAware() } catch { }  # real pixels everywhere: UIA rectangles, clicks and screenshots agree

$script:ser = New-Object System.Web.Script.Serialization.JavaScriptSerializer
$script:ser.MaxJsonLength = [int]::MaxValue
$script:cacheDir = Join-Path $env:LOCALAPPDATA 'premonition-desk'
$script:cacheFile = Join-Path $script:cacheDir 'last_look.json'

function Emit($obj, [int]$code = 0) {
  [Console]::Out.WriteLine($script:ser.Serialize($obj))
  [Console]::Out.Flush()
  exit $code
}
function Fail([string]$msg) { Emit @{ error = $msg } 1 }

function Trim80([string]$s) {
  if ($null -eq $s) { return '' }
  $t = ($s -replace '[\r\n]+', ' ').Trim()
  if ($t.Length -gt 80) { return $t.Substring(0, 80) }
  return $t
}
function FrameArr($r) { return @([int][math]::Round($r.X), [int][math]::Round($r.Y), [int][math]::Round($r.Width), [int][math]::Round($r.Height)) }

# ---- flags -------------------------------------------------------------------------------------
function Take-Flag([System.Collections.ArrayList]$a, [string]$name) {
  $i = $a.IndexOf($name)
  if ($i -lt 0) { return $false }
  $a.RemoveAt($i); return $true
}
function Take-Value([System.Collections.ArrayList]$a, [string]$name) {
  $i = $a.IndexOf($name)
  if ($i -lt 0) { return $null }
  if ($i + 1 -ge $a.Count) { Fail "$name needs a value" }
  $v = [string]$a[$i + 1]
  $a.RemoveAt($i + 1); $a.RemoveAt($i)
  return $v
}
function Take-PosInt([System.Collections.ArrayList]$a, [string]$name, [int]$default) {
  $v = Take-Value $a $name
  if ($null -eq $v) { return $default }
  $n = 0
  if (-not [int]::TryParse($v, [ref]$n) -or $n -le 0) { Fail "$name needs a positive number" }
  return $n
}

# ---- windows and apps ----------------------------------------------------------------------------
function Get-ProcInfo([int]$procId) {
  $name = ''; $desc = ''
  try {
    $p = Get-Process -Id $procId -ErrorAction Stop
    $name = $p.ProcessName
    try { $desc = [string]$p.MainModule.FileVersionInfo.FileDescription } catch { $desc = '' }
  } catch { }
  return @{ name = $name; desc = $desc }
}
function Window-Pid([IntPtr]$h) { [uint32]$p = 0; [void][DH]::GetWindowThreadProcessId($h, [ref]$p); return [int]$p }

# The window to look at: the foreground window, but not Premonition's own (Ben is usually typing in it): the next visible window down.
function Front-Window {
  $h = [DH]::GetForegroundWindow()
  $guard = 0
  while ($h -ne [IntPtr]::Zero -and $guard -lt 60) {
    $guard++
    $procId = Window-Pid $h
    $info = Get-ProcInfo $procId
    $own = ($info.name -match '^(Premonition|electron)$')
    $titled = ([DH]::GetWindowTextLength($h) -gt 0)
    if (-not $own -and [DH]::IsWindowVisible($h) -and -not [DH]::IsIconic($h) -and $titled) { return $h }
    $h = [DH]::GetWindow($h, 2)  # GW_HWNDNEXT
  }
  Fail 'no front window'
}
function Match-Process([string]$name) {
  $q = $name.ToLower() -replace '\.exe$', ''
  $procs = @(Get-Process | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero })
  foreach ($mode in 1, 2, 3) {
    foreach ($p in $procs) {
      $cands = @($p.ProcessName.ToLower(), ([string]$p.MainWindowTitle).ToLower())
      foreach ($c in $cands) {
        if ($c -eq '') { continue }
        if ($mode -eq 1 -and $c -eq $q) { return $p }
        if ($mode -eq 2 -and $c.StartsWith($q)) { return $p }
        if ($mode -eq 3 -and $c.Contains($q)) { return $p }
      }
    }
  }
  return $null
}
function App-Label([int]$procId, [IntPtr]$h) {
  $info = Get-ProcInfo $procId
  if ($info.name -eq 'ApplicationFrameHost') {
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    $t = ''
    foreach ($w in @(Get-Process | Where-Object { $_.MainWindowHandle -eq $h })) { $t = [string]$w.MainWindowTitle }
    if ($t) { return $t }
  }
  if ($info.desc) { return $info.desc }
  return $info.name
}

# ---- UI Automation tree -----------------------------------------------------------------------------
$script:tw = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$script:cr = New-Object System.Windows.Automation.CacheRequest
foreach ($pr in @([System.Windows.Automation.AutomationElement]::NameProperty, [System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.AutomationElement]::BoundingRectangleProperty, [System.Windows.Automation.AutomationElement]::IsOffscreenProperty, [System.Windows.Automation.AutomationElement]::IsPasswordProperty, [System.Windows.Automation.AutomationElement]::HelpTextProperty, [System.Windows.Automation.AutomationElement]::AutomationIdProperty)) { $script:cr.Add($pr) }
$script:cr.Add([System.Windows.Automation.ValuePattern]::Pattern)
$script:cr.Add([System.Windows.Automation.ValuePattern]::ValueProperty)
$script:cr.TreeScope = [System.Windows.Automation.TreeScope]::Element

$script:actionable = @('Button', 'CheckBox', 'RadioButton', 'ComboBox', 'Edit', 'Hyperlink', 'ListItem', 'MenuItem', 'TabItem', 'TreeItem', 'Slider', 'SplitButton', 'Spinner', 'DataItem')
$script:textRoles = @('Edit', 'ComboBox', 'Spinner')
$script:leafRoles = @('Button', 'CheckBox', 'RadioButton', 'ComboBox', 'Edit', 'MenuItem', 'TabItem', 'Slider', 'SplitButton', 'Spinner', 'Hyperlink')
$script:visited = 0
$script:budget = 2500
$script:textCount = 0
$script:maxText = 40
$script:found = New-Object System.Collections.ArrayList
$script:sw = [System.Diagnostics.Stopwatch]::StartNew()
$script:screenRect = [System.Windows.Forms.SystemInformation]::VirtualScreen

function Cached-Value($el) {
  try {
    $o = $null
    if ($el.TryGetCachedPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$o)) { return [string]$o.Cached.Value }
  } catch { }
  return ''
}
function Visible-Rect($c) {
  try {
    if ($c.IsOffscreen) { return $null }
    $r = $c.BoundingRectangle
    if ($r.IsEmpty -or $r.Width -le 0 -or $r.Height -le 0) { return $null }
    $vs = $script:screenRect
    if ($r.X + $r.Width -le $vs.X -or $r.Y + $r.Height -le $vs.Y -or $r.X -ge $vs.X + $vs.Width -or $r.Y -ge $vs.Y + $vs.Height) { return $null }
    return $r
  } catch { return $null }
}
function Role-Of($c) { return ([string]$c.ControlType.ProgrammaticName) -replace '^ControlType\.', '' }
function Label-Of($el, $c) {
  $n = Trim80 ([string]$c.Name)
  if ($n) { return $n }
  $h = Trim80 ([string]$c.HelpText)
  if ($h) { return $h }
  $role = Role-Of $c
  if ($script:leafRoles -contains $role -and $role -ne 'Edit') {
    $v = Trim80 (Cached-Value $el)
    if ($v) { return $v }
  }
  return ''
}

function Walk($el, [object[]]$path, [int]$depth) {
  if ($script:visited -ge $script:budget -or $depth -gt 30 -or $script:sw.ElapsedMilliseconds -gt 14000) { return }
  $script:visited++
  $descend = $true
  try {
    $c = $el.Cached
    $role = Role-Of $c
    $rect = Visible-Rect $c
    if ($null -ne $rect) {
      if ($role -eq 'Text') {
        $v = Trim80 ([string]$c.Name)
        if ($v -and $script:textCount -lt $script:maxText) {
          $script:textCount++
          [void]$script:found.Add(@{ path = $path; role = 'Text'; label = $v; value = ''; frame = $rect; isText = $true })
        }
      } elseif ($script:actionable -contains $role) {
        $label = Label-Of $el $c
        $keep = $true
        if ($role -eq 'ListItem' -or $role -eq 'DataItem' -or $role -eq 'TreeItem') { $keep = ($label -ne '') }
        if ($role -eq 'Edit' -or $role -eq 'ComboBox') { $keep = $true }
        if ($keep) {
          $value = ''
          $outRole = $role
          if ($c.IsPassword) { $outRole = 'SecureEdit'; $value = '' }  # never read a password field
          elseif ($script:textRoles -contains $role) { $value = Trim80 (Cached-Value $el) }
          [void]$script:found.Add(@{ path = $path; role = $outRole; label = $label; value = $value; frame = $rect; isText = $false })
          if ($script:leafRoles -contains $role -and ($label -ne '' -or $script:textRoles -contains $role)) { $descend = $false }
        }
      }
    }
  } catch { }
  if (-not $descend) { return }
  $i = 0
  try { $ch = $script:tw.GetFirstChild($el, $script:cr) } catch { $ch = $null }
  while ($null -ne $ch) {
    if ($script:visited -ge $script:budget) { break }
    Walk $ch (@($path) + $i) ($depth + 1)
    $i++
    try { $ch = $script:tw.GetNextSibling($ch, $script:cr) } catch { $ch = $null }
  }
}

function Resolve-Path-Element([IntPtr]$h, [object[]]$path) {
  $root = [System.Windows.Automation.AutomationElement]::FromHandle($h)
  $cur = $root.GetUpdatedCache($script:cr)
  foreach ($idx in @($path | Select-Object -Skip 1)) {
    $ch = $script:tw.GetFirstChild($cur, $script:cr)
    for ($k = 0; $k -lt [int]$idx -and $null -ne $ch; $k++) { $ch = $script:tw.GetNextSibling($ch, $script:cr) }
    if ($null -eq $ch) { return $null }
    $cur = $ch
  }
  return $cur
}

# ---- commands ------------------------------------------------------------------------------------
function Cmd-Look([string]$appName, [int]$max) {
  $script:sw.Restart()
  $h = [IntPtr]::Zero
  if ($appName) {
    $p = Match-Process $appName
    if ($null -eq $p) { Fail "no running app matches '$appName'" }
    $h = $p.MainWindowHandle
  } else { $h = Front-Window }
  $procId = Window-Pid $h
  $root = [System.Windows.Automation.AutomationElement]::FromHandle($h).GetUpdatedCache($script:cr)
  $title = Trim80 ([string]$root.Cached.Name)
  $winInfo = New-Object System.Collections.ArrayList
  $wd = @{ title = $title }
  try { $wd.frame = FrameArr $root.Cached.BoundingRectangle } catch { }
  [void]$winInfo.Add($wd)

  Walk $root @(0) 0

  $actionableFound = @($script:found | Where-Object { -not $_.isText })
  $textFound = @($script:found | Where-Object { $_.isText })
  $chosen = New-Object System.Collections.ArrayList
  foreach ($e in $actionableFound) { if ($chosen.Count -lt $max) { [void]$chosen.Add($e) } }
  foreach ($e in $textFound) { if ($chosen.Count -lt $max) { [void]$chosen.Add($e) } }
  $sorted = @($chosen | Sort-Object @{ Expression = { $_.frame.Y } }, @{ Expression = { $_.frame.X } })

  $elements = New-Object System.Collections.ArrayList
  $cache = New-Object System.Collections.ArrayList
  $id = 0
  foreach ($e in $sorted) {
    $id++
    $fa = FrameArr $e.frame
    [void]$elements.Add(@{ id = $id; role = [string]$e.role; title = [string]$e.label; value = [string]$e.value; frame = $fa })
    [void]$cache.Add(@{ id = $id; path = @($e.path); role = [string]$e.role; label = [string]$e.label; frame = $fa })
  }
  try {
    New-Item -ItemType Directory -Force -Path $script:cacheDir | Out-Null
    $json = $script:ser.Serialize(@{ pid = $procId; hwnd = [int64]$h; elements = $cache })
    [System.IO.File]::WriteAllText($script:cacheFile, $json, (New-Object System.Text.UTF8Encoding($false)))
  } catch { Fail ("could not write look cache: " + $_.Exception.Message) }
  Emit @{ app = (App-Label $procId $h); pid = $procId; windows = $winInfo; elements = $elements }
}

function Do-Click([int]$x, [int]$y, [bool]$right, [bool]$double) {
  [void][DH]::SetCursorPos($x, $y)
  Start-Sleep -Milliseconds 30
  $down = 0x2; $up = 0x4
  if ($right) { $down = 0x8; $up = 0x10 }
  [DH]::mouse_event($down, 0, 0, 0, [UIntPtr]::Zero)
  [DH]::mouse_event($up, 0, 0, 0, [UIntPtr]::Zero)
  if ($double) {
    Start-Sleep -Milliseconds 40
    [DH]::mouse_event($down, 0, 0, 0, [UIntPtr]::Zero)
    [DH]::mouse_event($up, 0, 0, 0, [UIntPtr]::Zero)
  }
}

function Cmd-Press([int]$id) {
  if (-not (Test-Path $script:cacheFile)) { Fail 'no saved look; run look first' }
  $obj = $script:ser.DeserializeObject([System.IO.File]::ReadAllText($script:cacheFile))
  $entry = $null
  foreach ($e in $obj['elements']) { if ([int]$e['id'] -eq $id) { $entry = $e } }
  if ($null -eq $entry) { Fail "no element with id $id in the last look" }
  $fr = @($entry['frame'] | ForEach-Object { [int]$_ })
  $cx = [int]($fr[0] + $fr[2] / 2); $cy = [int]($fr[1] + $fr[3] / 2)
  $role = [string]$entry['role']
  $h = [IntPtr][int64]$obj['hwnd']
  # text fields: focus through UI Automation when it is still the same element, then fall back to a click
  if ($role -eq 'Edit' -or $role -eq 'ComboBox' -or $role -eq 'SecureEdit') {
    try {
      $el = Resolve-Path-Element $h @($entry['path'])
      if ($null -ne $el) {
        $el.SetFocus()
        Emit @{ ok = $true; id = $id; method = 'focus' }
      }
    } catch { }
  }
  # everything else: a real click on its centre (patterns like Invoke can block on dialogs), after bringing its window forward
  try { [DH]::Activate($h); Start-Sleep -Milliseconds 80 } catch { }
  Do-Click $cx $cy $false $false
  Emit @{ ok = $true; id = $id; method = 'click' }
}

$script:vk = @{
  'enter' = 0x0D; 'return' = 0x0D; 'tab' = 0x09; 'esc' = 0x1B; 'escape' = 0x1B; 'space' = 0x20; 'backspace' = 0x08; 'delete' = 0x2E; 'del' = 0x2E;
  'up' = 0x26; 'down' = 0x28; 'left' = 0x25; 'right' = 0x27; 'home' = 0x24; 'end' = 0x23; 'pageup' = 0x21; 'pagedown' = 0x22; 'insert' = 0x2D
}
$script:extended = @(0x26, 0x28, 0x25, 0x27, 0x24, 0x23, 0x21, 0x22, 0x2D, 0x2E)

function Key-Tap([int]$vk) {
  $ext = 0
  if ($script:extended -contains $vk) { $ext = 0x1 }
  [DH]::Key([uint16]$vk, [uint32]$ext)
  [DH]::Key([uint16]$vk, [uint32]($ext -bor 0x2))
}

function Parse-Combo([string]$combo) {
  $parts = @($combo.ToLower().Split('+') | Where-Object { $_ -ne '' })
  if ($combo.EndsWith('++') -or $combo -eq '+') { $parts += 'plus' }
  $mods = New-Object System.Collections.ArrayList
  $key = $null
  foreach ($p in $parts) {
    switch ($p) {
      { $_ -in 'ctrl', 'control', 'cmd', 'command', 'meta' } { if (-not $mods.Contains(0x11)) { [void]$mods.Add(0x11) } }
      { $_ -in 'alt', 'opt', 'option' } { if (-not $mods.Contains(0x12)) { [void]$mods.Add(0x12) } }
      'shift' { if (-not $mods.Contains(0x10)) { [void]$mods.Add(0x10) } }
      { $_ -in 'win', 'windows', 'super' } { if (-not $mods.Contains(0x5B)) { [void]$mods.Add(0x5B) } }
      'fn' { }
      default { $key = $p }
    }
  }
  if ($null -eq $key) { return $null }
  $code = $null
  if ($key -eq 'plus') { $code = 0xBB; if (-not $mods.Contains(0x10)) { [void]$mods.Add(0x10) } }
  elseif ($script:vk.ContainsKey($key)) { $code = [int]$script:vk[$key] }
  elseif ($key -match '^f([1-9]|1[0-2])$') { $code = 0x70 + [int]$Matches[1] - 1 }
  elseif ($key.Length -eq 1) {
    $r = [int][DH]::VkKeyScan($key[0])
    if ($r -eq -1) { return $null }
    $code = $r -band 0xFF
    if (($r -band 0x100) -ne 0 -and -not $mods.Contains(0x10)) { [void]$mods.Add(0x10) }
  } else { return $null }
  return @{ mods = $mods; code = [int]$code }
}

function Cmd-Key([string]$combo) {
  $pc = Parse-Combo $combo
  if ($null -eq $pc) { Fail "unknown key combo: $combo" }
  foreach ($m in $pc.mods) { [DH]::Key([uint16]$m, [uint32]0); Start-Sleep -Milliseconds 10 }
  Key-Tap $pc.code
  Start-Sleep -Milliseconds 10
  for ($i = $pc.mods.Count - 1; $i -ge 0; $i--) { [DH]::Key([uint16]$pc.mods[$i], [uint32]0x2) }
  Emit @{ ok = $true }
}

function Cmd-Type([string]$text) {
  $n = 0
  foreach ($ch in $text.ToCharArray()) {
    if ($ch -eq "`r") { continue }
    elseif ($ch -eq "`n") { Key-Tap 0x0D }
    elseif ($ch -eq "`t") { Key-Tap 0x09 }
    else { [DH]::Uni($ch) }
    $n++
    if ($n % 20 -eq 0) { Start-Sleep -Milliseconds 15 }
  }
  Emit @{ ok = $true; chars = $text.Length }
}

function Cmd-OpenApp([string]$name) {
  $q = ($name.Trim().ToLower()) -replace '\.exe$', ''
  $p = Match-Process $q
  if ($null -ne $p) {
    [DH]::Activate($p.MainWindowHandle)
    Emit @{ opened = (App-Label $p.Id $p.MainWindowHandle); pid = [int]$p.Id }
  }
  $launched = $false
  # the Start menu name (also finds Store apps): shell:AppsFolder\<AppID>
  try {
    $apps = @(Get-StartApps)
    $hit = $null
    foreach ($mode in 1, 2, 3) {
      foreach ($a in $apps) {
        $n = ([string]$a.Name).ToLower()
        if (($mode -eq 1 -and $n -eq $q) -or ($mode -eq 2 -and $n.StartsWith($q)) -or ($mode -eq 3 -and $n.Contains($q))) { $hit = $a; break }
      }
      if ($null -ne $hit) { break }
    }
    if ($null -ne $hit) {
      Start-Process -FilePath 'explorer.exe' -ArgumentList ('shell:AppsFolder\' + $hit.AppID)
      $launched = $true
    }
  } catch { }
  if (-not $launched) {
    try { Start-Process -FilePath $name -ErrorAction Stop; $launched = $true } catch { Fail "app not found: $name" }
  }
  # wait for its window
  $deadline = (Get-Date).AddSeconds(12)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 300
    $p = Match-Process $q
    if ($null -ne $p) {
      try { [DH]::Activate($p.MainWindowHandle) } catch { }
      Emit @{ opened = (App-Label $p.Id $p.MainWindowHandle); pid = [int]$p.Id }
    }
  }
  Emit @{ opened = $name; pid = 0; note = 'started; no window seen yet' }
}

function Cmd-Screenshot([string]$rawPath, [int]$max) {
  $path = $rawPath
  if ($path.StartsWith('~')) { $path = Join-Path $env:USERPROFILE $path.Substring(1).TrimStart('\', '/') }
  $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
  $src = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
  try {
    $g = [System.Drawing.Graphics]::FromImage($src)
    try { $g.CopyFromScreen($b.X, $b.Y, 0, 0, $src.Size) } finally { $g.Dispose() }
    $longest = [math]::Max($b.Width, $b.Height)
    $ratio = 1.0
    if ($longest -gt $max) { $ratio = [double]$max / [double]$longest }
    $w = [math]::Max(1, [int][math]::Round($b.Width * $ratio))
    $h = [math]::Max(1, [int][math]::Round($b.Height * $ratio))
    $dst = New-Object System.Drawing.Bitmap($w, $h)
    try {
      $g2 = [System.Drawing.Graphics]::FromImage($dst)
      try {
        $g2.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g2.DrawImage($src, 0, 0, $w, $h)
      } finally { $g2.Dispose() }
      $dir = Split-Path -Parent $path
      if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
      $codec = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' } | Select-Object -First 1
      $ep = New-Object System.Drawing.Imaging.EncoderParameters(1)
      $ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter([System.Drawing.Imaging.Encoder]::Quality, [long]70)
      $dst.Save($path, $codec, $ep)
    } finally { $dst.Dispose() }
    $scale = [math]::Round([double]$b.Width / [double]$w, 4)
    Emit @{ path = $path; width = $w; height = $h; scale = $scale }
  } finally { $src.Dispose() }
}

# ---- main ------------------------------------------------------------------------------------------
if ($args.Count -lt 1) { Fail 'usage: deskhelper check|ask-permissions|look|press|click|type|key|scroll|open-app|screenshot' }
$command = [string]$args[0]
$rest = New-Object System.Collections.ArrayList
for ($i = 1; $i -lt $args.Count; $i++) { [void]$rest.Add([string]$args[$i]) }

try {
  switch ($command) {
    'check' { Emit @{ accessibility = $true; screenRecording = $true } }
    'ask-permissions' { Emit @{ accessibility = $true; screenRecording = $true } }
    'look' {
      $app = Take-Value $rest '--app'
      $max = Take-PosInt $rest '--max' 150
      Cmd-Look $app $max
    }
    'press' {
      $n = 0
      if ($rest.Count -lt 1 -or -not [int]::TryParse([string]$rest[0], [ref]$n)) { Fail 'usage: press ID' }
      Cmd-Press $n
    }
    'click' {
      $right = Take-Flag $rest '--right'
      $double = Take-Flag $rest '--double'
      $x = 0.0; $y = 0.0
      $ci = [System.Globalization.CultureInfo]::InvariantCulture
      if ($rest.Count -lt 2 -or -not [double]::TryParse([string]$rest[0], [System.Globalization.NumberStyles]::Float, $ci, [ref]$x) -or -not [double]::TryParse([string]$rest[1], [System.Globalization.NumberStyles]::Float, $ci, [ref]$y)) { Fail 'usage: click X Y [--double] [--right]' }
      Do-Click ([int][math]::Round($x)) ([int][math]::Round($y)) $right $double
      Emit @{ ok = $true }
    }
    'type' {
      if ($rest.Count -lt 1) { Fail 'usage: type TEXT' }
      Cmd-Type (($rest.ToArray()) -join ' ')
    }
    'key' {
      if ($rest.Count -lt 1) { Fail 'usage: key COMBO' }
      Cmd-Key (($rest.ToArray()) -join '')
    }
    'scroll' {
      $dy = 0.0
      if ($rest.Count -lt 1 -or -not [double]::TryParse([string]$rest[0], [System.Globalization.NumberStyles]::Float, [System.Globalization.CultureInfo]::InvariantCulture, [ref]$dy)) { Fail 'usage: scroll DY' }
      [DH]::mouse_event(0x800, 0, 0, [int]([math]::Round($dy) * 120), [UIntPtr]::Zero)
      Emit @{ ok = $true }
    }
    'open-app' {
      if ($rest.Count -lt 1) { Fail 'usage: open-app NAME' }
      Cmd-OpenApp (($rest.ToArray()) -join ' ')
    }
    'screenshot' {
      $max = Take-PosInt $rest '--max' 1280
      if ($rest.Count -lt 1) { Fail 'usage: screenshot PATH [--max 1280]' }
      Cmd-Screenshot ([string]$rest[0]) $max
    }
    default { Fail "unknown command: $command" }
  }
} catch {
  Fail ([string]$_.Exception.Message)
}
