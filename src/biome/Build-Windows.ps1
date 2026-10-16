param([string]$Python = "python")
$ErrorActionPreference = 'Stop'
$buildEnv = Join-Path $PSScriptRoot 'build-env'
if (-not (Test-Path -LiteralPath (Join-Path $buildEnv 'Scripts/python.exe'))) {
    & $Python -m venv $buildEnv
    if ($LASTEXITCODE) { throw 'Création de l’environnement impossible' }
}
$buildPython = Join-Path $buildEnv 'Scripts/python.exe'
& $buildPython -m pip install -r (Join-Path $PSScriptRoot 'requirements-build.txt')
if ($LASTEXITCODE) { throw 'Installation des dépendances impossible' }
& $buildPython -m PyInstaller --noconfirm --windowed --onedir --name BIOME --icon (Join-Path $PSScriptRoot "../../icon/BIOME_icon_256.ico") --distpath (Join-Path $PSScriptRoot 'dist') --workpath (Join-Path $PSScriptRoot 'build') --specpath (Join-Path $PSScriptRoot 'build') --paths $PSScriptRoot --add-data "$PSScriptRoot/index.html;." --add-data "$PSScriptRoot/project_sort.js;." --add-data "$PSScriptRoot/Select-Data.ps1;." --collect-all tzdata --collect-all oxmsg --collect-all reportlab --hidden-import check_location (Join-Path $PSScriptRoot 'desktop.py')
if ($LASTEXITCODE) { throw 'Compilation impossible' }
$distribution = Join-Path $PSScriptRoot 'dist/BIOME'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README-Windows.txt') -Destination $distribution
& $buildPython (Join-Path $PSScriptRoot 'package_notices.py') $distribution
if ($LASTEXITCODE) { throw 'Copie des notices impossible' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot '../../LICENSE') -Destination (Join-Path $distribution 'LICENSE.txt')
Write-Output "Version autonome : $distribution"
