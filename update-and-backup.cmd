@echo off
chcp 65001 > nul
powershell.exe -NoLogo -NoProfile -File "%~dp0update.ps1" -Push
set "updateExitCode=%errorlevel%"
echo.
if not "%updateExitCode%"=="0" (
    echo 更新に失敗しました。上のエラーを確認してください。
) else (
    echo 処理が完了しました。
)
pause
exit /b %updateExitCode%
