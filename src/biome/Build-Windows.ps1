param([string]$Python = "python")
$ErrorActionPreference = 'Stop'
$buildEnv = Join-Path $PSScriptRoot 'build-env'
if (-not (Test-Path -LiteralPath (Join-Path $buildEnv 'Scripts/python.exe'))) {
    & $Python -m venv $buildEnv
    if ($LASTEXITCODE) { throw 'Cannot create the build environment' }
}
$buildPython = Join-Path $buildEnv 'Scripts/python.exe'
& $buildPython -m pip install -r (Join-Path $PSScriptRoot 'requirements-build.txt')
if ($LASTEXITCODE) { throw 'Cannot install build dependencies' }
& $buildPython -m PyInstaller --noconfirm --windowed --onedir --name BIOME --icon (Join-Path $PSScriptRoot "../../icon/BIOME_icon_256.ico") --distpath (Join-Path $PSScriptRoot 'dist') --workpath (Join-Path $PSScriptRoot 'build') --specpath (Join-Path $PSScriptRoot 'build') --paths $PSScriptRoot --add-data "$PSScriptRoot/index.html;." --add-data "$PSScriptRoot/project_sort.js;." --add-data "$PSScriptRoot/delivery_selector.js;." --add-data "$PSScriptRoot/delivery_selector.css;." --add-data "$PSScriptRoot/Select-Data.ps1;." --collect-all tzdata --collect-all oxmsg --collect-all reportlab --hidden-import check_location (Join-Path $PSScriptRoot 'desktop.py')
if ($LASTEXITCODE) { throw 'Build failed' }
$distribution = Join-Path $PSScriptRoot 'dist/BIOME'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README-Windows.txt') -Destination $distribution
& $buildPython (Join-Path $PSScriptRoot 'package_notices.py') $distribution
if ($LASTEXITCODE) { throw 'Cannot copy dependency notices' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '../../LICENSE') -Destination (Join-Path $distribution 'LICENSE.txt')
Write-Output "Portable application: $distribution"
