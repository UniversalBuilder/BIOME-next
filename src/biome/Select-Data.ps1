param([ValidateSet('file','folder')][string]$Kind = 'file', [ValidateSet('data','workspace','backup','restore','receive')][string]$Purpose = 'data')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class BiomeDialogWindow {
    [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr context);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr window);
}
'@
[void][BiomeDialogWindow]::SetProcessDpiAwarenessContext([IntPtr](-4))
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles()
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$owner.Opacity = 0.01
$owner.StartPosition = 'CenterScreen'
$owner.Width = 1
$owner.Height = 1
$owner.Show()
$owner.Activate()
[void][BiomeDialogWindow]::SetForegroundWindow($owner.Handle)
try {
    if ($Kind -eq 'folder') {
        $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialog.Description = if ($Purpose -eq 'workspace') { 'Choisir un catalogue BIOME ou son dossier parent selon l’action demandée' } elseif ($Purpose -eq 'backup') { 'Choisir où conserver la sauvegarde BIOME' } elseif ($Purpose -eq 'restore') { 'Choisir le dossier parent du nouveau catalogue restauré' } elseif ($Purpose -eq 'receive') { 'Choisir un dossier séparé pour les images originales' } else { 'Choisir le dossier des données, séparé du catalogue' }
        $dialog.ShowNewFolderButton = $true
        $result = $dialog.ShowDialog($owner)
        $selected = $dialog.SelectedPath
    } else {
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = if ($Purpose -eq 'restore') { 'Choisir une sauvegarde BIOME' } elseif ($Purpose -eq 'receive') { 'Choisir un original à conserver' } else { 'Choisir un fichier de données à référencer' }
        if ($Purpose -eq 'restore') { $dialog.Filter = 'BIOME backup (*.zip)|*.zip' }
        $dialog.CheckFileExists = $true
        $dialog.Multiselect = $false
        $result = $dialog.ShowDialog($owner)
        $selected = $dialog.FileName
    }
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
        @{ location = $selected; name = [System.IO.Path]::GetFileName($selected.TrimEnd('\')) } | ConvertTo-Json -Compress
    } else { @{ cancelled = $true } | ConvertTo-Json -Compress }
} finally {
    if ($dialog) { $dialog.Dispose() }
    $owner.Close()
    $owner.Dispose()
}
