@echo off
setlocal
set "APPDATA=%~dp0runtime\AppData"
if not exist "%APPDATA%" mkdir "%APPDATA%"
start "" "%~dp0tools\godot\Godot_v4.6.1-stable_win64.exe" --editor --path "%~dp0projects\fps" --scene "res://pilot/F01.tscn"
endlocal
