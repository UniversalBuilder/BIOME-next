$ErrorActionPreference = 'Stop'
$application = Join-Path $PSScriptRoot 'dist/BIOME/BIOME.exe'
if (-not (Test-Path -LiteralPath $application)) {
    throw 'La version autonome doit être construite avec Build-Windows.ps1 ou extraite depuis le ZIP portable.'
}
Start-Process -FilePath $application -WorkingDirectory (Split-Path -Parent $application) -WindowStyle Hidden
