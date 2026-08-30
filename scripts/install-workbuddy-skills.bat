@echo off
setlocal

for %%I in ("%~dp0..") do set "ROOT=%%~fI"

if defined WORKBUDDY_SKILLS_DIR (
  set "DEST=%WORKBUDDY_SKILLS_DIR%"
) else (
  set "DEST=%USERPROFILE%\.workbuddy\skills"
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)

%PY% "%ROOT%\scripts\sync-workbuddy-skills.py"
if errorlevel 1 exit /b %ERRORLEVEL%

if not exist "%DEST%" mkdir "%DEST%"
if errorlevel 1 exit /b %ERRORLEVEL%

for /d %%D in ("%ROOT%\workbuddy-skills\*") do (
  if exist "%DEST%\%%~nxD" rmdir /s /q "%DEST%\%%~nxD"
  if errorlevel 1 exit /b 1
  xcopy "%%~fD" "%DEST%\%%~nxD\" /E /I /Y >nul
  if errorlevel 1 exit /b 1
)

echo Installed WorkBuddy skills to %DEST%
echo NOTE: 'ai-berkshire-tools' is a shared dependency of the other AI Berkshire
echo       skills (tool resolution chain step 2). Keep it installed alongside them.
echo NOTE: Skills with the same name at the destination are overwritten.
echo Restart WorkBuddy (or refresh its skill list) to pick up new skills.
