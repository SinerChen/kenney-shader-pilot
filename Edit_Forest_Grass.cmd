@echo off
setlocal
set "APPDATA=%~dp0runtime\AppData"
if not exist "%APPDATA%" mkdir "%APPDATA%"
start "" "%~dp0tools\godot\Godot_v4.6.1-stable_win64.exe" --path "%~dp0forest_grass_lab\project" --editor --scene res://scenes/L1.tscn
endlocal
