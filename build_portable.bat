@echo off
echo ================================================
echo   Building AeroBeam v1.2.4 Portable Version
echo ================================================
echo.

where pyinstaller >nul 2>nul
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Building AeroBeam.exe...
pyinstaller wing_stress.spec --clean --noconfirm

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo Creating portable folder...
if exist AeroBeam_Portable rmdir /s /q AeroBeam_Portable
mkdir AeroBeam_Portable

REM Copy from dist\AeroBeam if it exists, otherwise from dist
if exist "dist\AeroBeam" (
    xcopy dist\AeroBeam\* AeroBeam_Portable\ /E /I /Y
) else (
    xcopy dist\* AeroBeam_Portable\ /E /I /Y
)

REM Copy AeroBeam.ico next to the exe so iconbitmap finds it at runtime
if exist "AeroBeam.ico" (
    copy /Y "AeroBeam.ico" "AeroBeam_Portable\AeroBeam.ico"
) else if exist "web\AeroBeam.ico" (
    copy /Y "web\AeroBeam.ico" "AeroBeam_Portable\AeroBeam.ico"
)

echo.
echo ================================================
echo   SUCCESS! AeroBeam v1.2.4 Portable Build
echo ================================================
echo.
echo Portable version created in: AeroBeam_Portable
explorer AeroBeam_Portable
pause
