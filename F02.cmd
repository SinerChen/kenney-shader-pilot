@echo off
setlocal
set "APPDATA=%~dp0runtime\AppData"
"%~dp0tools\godot\Godot_v4.6.1-stable_win64.exe" --path "%~dp0projects\fps" "res://pilot/F02.tscn"
endlocal
