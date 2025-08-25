# build_ptau217_exe.ps1 — builds a single EXE for Windows
param(
  [string]$Name = "pTau217App",
  [string]$Script = "run_ptau217_app.py"
)

Write-Host "== Building $Name from $Script ==" -ForegroundColor Cyan

# Ensure Python & pip
function Get-PythonCmd {
  $candidates = @('python', 'py -3', 'py')
  foreach ($c in $candidates) {
    try { $v = & $c --version 2>$null; if ($LASTEXITCODE -eq 0 -or $v) { return $c } } catch {}
  }
  return $null
}
$py = Get-PythonCmd
if (-not $py) { Write-Error "Python not found in PATH."; exit 1 }

# Venv
$venv = Join-Path $PSScriptRoot ".venv-build"
if (!(Test-Path $venv)) { & $py -m venv $venv }
$pyv = Join-Path $venv "Scripts\python.exe"

# Install pyinstaller
& $pyv -m pip install --upgrade pip
& $pyv -m pip install pyinstaller

# Build single-file exe
& $pyv -m PyInstaller --onefile --name $Name $Script
Write-Host "Build complete. EXE at: $(Join-Path $PSScriptRoot "dist\$Name.exe")" -ForegroundColor Green
