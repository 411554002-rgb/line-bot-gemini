@echo off
cd /d "%~dp0"
echo Starting Python LINE Bot Server...
start "LINE_Bot_Server" cmd /k "python main.py"
timeout /t 3 /nobreak >nul
echo Starting ngrok tunnel...
start "ngrok_Tunnel" cmd /k "ngrok.exe http 8000"
echo.
echo ==============================================
echo   LINE Bot and ngrok launched successfully!
echo   Please check the ngrok window for public URL.
echo ==============================================
echo.
pause