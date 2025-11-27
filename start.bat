@echo off
title LAWIANDREW CHAT BASLANGIC SISTEMI V 1.0

echo.
echo ---------------------------------------
echo         LAWIANDREW CHAT
echo             V 5.0.0
echo          BETA 1.2.3.xcz
echo. ---------------------------------------

:: Sunucuyu yeni bir pencerede başlat
start cmd /k "title CHAT SUNUCUSU & node server.js"

:: Ngrok tünelini yeni bir pencerede başlat
start cmd /k "title NGROK TUNELI & ngrok http 3000"

echo Sunucu ve Ngrok tüneli yeni pencerelerde baslatildi.
echo Bu pencereyi kapatabilirsiniz.
pause > nul
exit