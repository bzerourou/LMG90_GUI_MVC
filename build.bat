@echo off
REM ================================================================
REM  build.bat — build minimal LMGC90_GUI (Windows)
REM ================================================================

if exist build  rmdir /s /q build
if exist dist   rmdir /s /q dist

pyinstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --console ^
    --noupx ^
    --name "LMGC90_GUI" ^
    --icon ico.png ^
    --collect-all pylmgc90 ^
    --collect-all numpy ^
    --collect-all PyQt6 ^
    --hidden-import pylmgc90 ^
    --hidden-import pylmgc90.pre ^
    --hidden-import numpy ^
    main.py

echo.
echo Exe : dist\LMGC90_GUI\LMGC90_GUI.exe
pause