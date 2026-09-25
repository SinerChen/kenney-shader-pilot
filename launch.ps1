param(
    [ValidateSet('P01','P02','P03','F01','F02')][string]$Scene = 'P01',
    [ValidateSet(1,2,3)][int]$Level = 1,
    [switch]$Editor
)
$pilotRoot = $PSScriptRoot
$pilotKit = if ($Scene.StartsWith('P')) { 'platformer' } else { 'fps' }
$pilotEngine = Join-Path $pilotRoot 'tools\godot\Godot_v4.6.1-stable_win64.exe'
$pilotAppData = Join-Path $pilotRoot 'runtime\AppData'
New-Item -ItemType Directory -Force -Path $pilotAppData | Out-Null
$env:APPDATA = $pilotAppData
$pilotArguments = @('--path', (Join-Path $pilotRoot ('projects\'+$pilotKit)))
if ($Editor) { $pilotArguments += '--editor' }
$pilotArguments += @(('res://pilot/'+$Scene+'.tscn'),'--',('--level='+$Level))
& $pilotEngine @pilotArguments
