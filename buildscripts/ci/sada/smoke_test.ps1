# Sada CI smoke test: start the freshly built app on the Windows runner, take
# screenshots of the first-launch dialog and of the main window, and collect the
# app's log files. Results go to $env:GITHUB_WORKSPACE\smoke and are published to
# the ci-logs branch by publish_ci_log.sh.

$ErrorActionPreference = "Continue"

$workspace = $env:GITHUB_WORKSPACE
$exe = Join-Path $workspace "build.install\bin\Sada.exe"
$out = Join-Path $workspace "smoke"
New-Item -ItemType Directory -Force -Path $out | Out-Null

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$sig = @"
using System;
using System.Runtime.InteropServices;
public static class SadaWin32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@
Add-Type -TypeDefinition $sig -ErrorAction SilentlyContinue

function Save-Screenshot([string]$name) {
    $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bmp.Size)
    $path = Join-Path $out $name
    $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Host "screenshot: $path"
}

function Start-Sada([string]$label, [int]$waitSeconds) {
    Write-Host "== starting Sada ($label)"
    $p = Start-Process -FilePath $exe -PassThru -WorkingDirectory (Split-Path $exe)
    Start-Sleep -Seconds $waitSeconds
    $p.Refresh()
    if ($p.HasExited) {
        Write-Host "Sada exited early with code $($p.ExitCode)"
        "exited early: $($p.ExitCode)" | Out-File -Append (Join-Path $out "status.txt")
        return $null
    }
    "running after $waitSeconds s ($label): pid $($p.Id), title '$($p.MainWindowTitle)'" | Out-File -Append (Join-Path $out "status.txt")
    if ($p.MainWindowHandle -ne [IntPtr]::Zero) {
        [SadaWin32]::ShowWindow($p.MainWindowHandle, 3) | Out-Null   # maximize
        [SadaWin32]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
        Start-Sleep -Seconds 3
    }
    return $p
}

function Stop-Sada($p) {
    if ($p -and -not $p.HasExited) {
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }
    Get-Process -Name "Sada" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}

"display: $([System.Windows.Forms.SystemInformation]::VirtualScreen)" | Out-File (Join-Path $out "status.txt")

if (-not (Test-Path $exe)) {
    "Sada.exe not found at $exe" | Out-File -Append (Join-Path $out "status.txt")
    Get-ChildItem (Join-Path $workspace "build.install") -Recurse -Depth 2 | Select-Object -First 80 FullName | Out-File -Append (Join-Path $out "status.txt")
    exit 0
}

# 1) First launch: the first-launch setup dialog should appear over the dark main window
$p = Start-Sada "first launch" 45
Save-Screenshot "01-first-launch.png"
Stop-Sada $p

# 2) Mark the first-launch setup as done (settings live in %APPDATA%\Sada\Sada.ini),
#    then start again to see the main window
$ini = Join-Path $env:APPDATA "Sada\Sada.ini"
New-Item -ItemType Directory -Force -Path (Split-Path $ini) | Out-Null
$lines = @()
if (Test-Path $ini) { $lines = @(Get-Content $ini) }
$lines = @($lines | Where-Object { $_ -notmatch '^hasCompletedFirstLaunchSetup=' })
$idx = [Array]::IndexOf($lines, '[application]')
if ($idx -ge 0) {
    $new = @($lines[0..$idx]) + @('hasCompletedFirstLaunchSetup=true')
    if ($idx + 1 -le $lines.Count - 1) { $new += @($lines[($idx + 1)..($lines.Count - 1)]) }
    $lines = $new
} else {
    $lines += @('', '[application]', 'hasCompletedFirstLaunchSetup=true')
}
Set-Content -Path $ini -Value $lines -Encoding UTF8

$p = Start-Sada "main window" 40
Save-Screenshot "02-main-window.png"

# 3) Keyboard check: Ctrl+N (new project) then a short pause, then another screenshot
[System.Windows.Forms.SendKeys]::SendWait("^n")
Start-Sleep -Seconds 8
Save-Screenshot "03-after-ctrl-n.png"
Stop-Sada $p

# 4) Collect log files and the settings the app wrote
$logDir = Join-Path $out "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
foreach ($root in @($env:LOCALAPPDATA, $env:APPDATA)) {
    $base = Join-Path $root "Sada"
    if (Test-Path $base) {
        Get-ChildItem $base -Recurse -Include *.log, *.txt -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 6 |
            ForEach-Object {
                $dest = Join-Path $logDir ($_.Directory.Name + "_" + $_.Name)
                Get-Content $_.FullName -Tail 1500 | Out-File $dest
            }
        Get-ChildItem $base -Recurse -Depth 3 -ErrorAction SilentlyContinue | Select-Object FullName, Length |
            Out-File (Join-Path $out "appdata-tree.txt") -Append
    }
}
if (Test-Path $ini) { Copy-Item $ini (Join-Path $out "Sada.ini") }

Write-Host "smoke test done"
exit 0
