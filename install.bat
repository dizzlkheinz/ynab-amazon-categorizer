@echo off
REM YNAB Amazon Categorizer - Installation Script for Windows
REM This script downloads and sets up the YNAB Amazon Categorizer

setlocal enabledelayedexpansion

set "REPO=dizzlkheinz/ynab-amazon-categorizer"
set "INSTALL_DIR=%USERPROFILE%\AppData\Local\Programs\ynab-amazon-categorizer"
set "CONFIG_DIR=%USERPROFILE%\AppData\Local\ynab-amazon-categorizer"

echo 🎯 Installing YNAB Amazon Categorizer...

REM Create directories
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

REM Check if curl is available
curl --version >nul 2>&1
if errorlevel 1 (
    echo ❌ curl is required but not found. Please install curl or download files manually.
    echo    You can download curl from: https://curl.se/windows/
    pause
    exit /b 1
)

REM Get latest release info
echo 📡 Getting latest release information...
curl -s "https://api.github.com/repos/%REPO%/releases/latest" > temp_release.json

REM Extract version (basic parsing - could be improved)
for /f "tokens=4 delims=," %%a in ('findstr "tag_name" temp_release.json') do (
    set "VERSION=%%a"
    set "VERSION=!VERSION:"=!"
    set "VERSION=!VERSION: =!"
)
del temp_release.json

if "!VERSION!"=="" (
    echo ❌ Could not get latest version information
    pause
    exit /b 1
)

echo 📦 Latest version: !VERSION!

REM Download executable
set "EXECUTABLE_NAME=ynab-amazon-categorizer.exe"
set "DOWNLOAD_URL=https://github.com/%REPO%/releases/download/!VERSION!/%EXECUTABLE_NAME%"

echo ⬇️  Downloading executable...
curl -L -o "%INSTALL_DIR%\ynab-amazon-categorizer.exe" "%DOWNLOAD_URL%"

if errorlevel 1 (
    echo ❌ Failed to download executable
    pause
    exit /b 1
)

REM Download .env.example
echo ⬇️  Downloading configuration template...
curl -L -o "%CONFIG_DIR%\.env.example" "https://github.com/%REPO%/releases/download/!VERSION!/.env.example"

REM Add to PATH (user-level)
echo 🔧 Adding to PATH...
setx PATH "%PATH%;%INSTALL_DIR%"

echo ✅ Installation complete!
echo.
echo 📋 Next steps:
echo 1. Copy the configuration template:
echo    copy "%CONFIG_DIR%\.env.example" "%CONFIG_DIR%\.env"
echo.
echo 2. Edit the configuration file with your YNAB credentials:
echo    notepad "%CONFIG_DIR%\.env"
echo.
echo 3. Restart your command prompt and run the program:
echo    ynab-amazon-categorizer.exe
echo.
echo 📚 For setup instructions, visit: https://github.com/%REPO%#readme
echo.
pause