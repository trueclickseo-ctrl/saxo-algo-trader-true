@echo off
:: ============================================================
:: ATOS — Fix File Permissions for Kashif user
:: ============================================================
:: Right-click this file → "Run as administrator" (ONE TIME ONLY)
:: This grants full read/write access to user Kashif on all
:: project files so all agents and tools can modify code.
:: ============================================================

echo.
echo ========================================
echo  ATOS — Fixing File Permissions
echo ========================================
echo.

icacls "E:\saxobackup\SaxoTrader\files" /grant "Kashif:(OI)(CI)F" /T

if %ERRORLEVEL% EQU 0 (
    echo.
    echo  SUCCESS — Kashif now has full access to all project files.
    echo.
) else (
    echo.
    echo  FAILED — Make sure you right-clicked and chose "Run as administrator"
    echo.
)

pause
