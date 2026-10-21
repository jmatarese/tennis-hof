# First-time setup on Windows. From the repo folder, run:
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
#
# Safe to run again at any time; it only installs what is missing.
$ErrorActionPreference = "Stop"

function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                "$env:USERPROFILE\.local\bin"
}

if (-not (Have git)) { winget install --id Git.Git -e --source winget }
if (-not (Have gh))  { winget install --id GitHub.cli -e --source winget }
if (-not (Have uv))  { powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex" }
Refresh-Path

# Everything else lives in Python, so it is the same on every OS.
uv run hof setup
exit $LASTEXITCODE
