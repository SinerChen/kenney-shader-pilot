@echo off
setlocal
set "APPDATA=%~dp0runtime\AppData"
if not exist "%APPDATA%" mkdir "%APPDATA%"
start "" "%~dp0tools\godot\Godot_v4.6.1-stable_win64.exe" --project-manager
endlocal
