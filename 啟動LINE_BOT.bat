@echo off
chcp 65001 >nul
title LINE Bot + ngrok 一鍵啟動器
echo ========================================================
echo   正在啟動 LINE Bot (Python) 與 ngrok 連線通道...
echo ========================================================
echo.

cd /d "%~dp0"

echo [1/2] 正在新視窗啟動 Python 後端伺服器 (main.py)...
start "LINE Bot Python Server" cmd /k "cd /d "%~dp0" && python main.py"

echo 等待伺服器就緒...
timeout /t 3 /nobreak >nul

echo [2/2] 正在新視窗啟動 ngrok (端口 8000)...
start "ngrok Tunnel" cmd /k "cd /d "%~dp0" && .\ngrok.exe http 8000"

echo.
echo ========================================================
echo   全部啟動完成！
echo.
echo   請查看彈出的 [ngrok Tunnel] 視窗中的 Forwarding 網址：
echo   例如: https://xxxx.ngrok-free.dev
echo.
echo   將該網址加上 /callback 填入 LINE Developers Webhook URL
echo   例如: https://xxxx.ngrok-free.dev/callback
echo ========================================================
echo.
pause
