# Installs PiP Crop into Firefox through AutoConfig. AutoConfig files live in
# the Firefox installation folder, so this needs an elevated (Administrator)
# PowerShell. Run it from the folder that has pipcrop.js next to it (the
# release zip, or dist\firefox-autoconfig after "python tools\build.py").
#
#   powershell -ExecutionPolicy Bypass -File install.ps1
#   powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall
#   powershell -ExecutionPolicy Bypass -File install.ps1 -FirefoxDir "D:\Apps\Firefox"
param(
    [string]$FirefoxDir = "$env:ProgramFiles\Mozilla Firefox",
    [switch]$Uninstall,
    # for a portable Firefox in a user-writable folder
    [switch]$SkipAdminCheck
)
$ErrorActionPreference = "Stop"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $SkipAdminCheck -and -not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script from an elevated (Administrator) PowerShell."
}
if (-not (Test-Path (Join-Path $FirefoxDir "firefox.exe"))) {
    throw "firefox.exe not found in '$FirefoxDir'. Pass -FirefoxDir with the folder that contains firefox.exe."
}

$prefFile = Join-Path $FirefoxDir "defaults\pref\autoconfig.js"
$targets = @($prefFile, (Join-Path $FirefoxDir "pipcrop.cfg"), (Join-Path $FirefoxDir "pipcrop.js"))

if ($Uninstall) {
    foreach ($f in $targets) { if (Test-Path $f) { Remove-Item $f -Force; Write-Host "removed $f" } }
    Write-Host "PiP Crop removed. Restart Firefox."
    return
}

if ((Test-Path $prefFile) -and -not ((Get-Content $prefFile -Raw) -match "pipcrop\.cfg")) {
    throw "Another AutoConfig is already configured in $prefFile. Merge it by hand (load pipcrop.js from your existing .cfg)."
}

$src = $PSScriptRoot
if (-not (Test-Path (Join-Path $src "pipcrop.js"))) {
    throw "pipcrop.js not found next to this script. Use the release zip, or run 'python tools\build.py' and then dist\firefox-autoconfig\install.ps1."
}
New-Item -ItemType Directory -Force (Split-Path $prefFile) | Out-Null
Copy-Item (Join-Path $src "defaults\pref\autoconfig.js") $prefFile -Force
Copy-Item (Join-Path $src "pipcrop.cfg") (Join-Path $FirefoxDir "pipcrop.cfg") -Force
Copy-Item (Join-Path $src "pipcrop.js") (Join-Path $FirefoxDir "pipcrop.js") -Force
foreach ($f in $targets) { Write-Host "installed $f" }
Write-Host "Done. Restart Firefox (close every Firefox window first)."
