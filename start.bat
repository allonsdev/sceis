@echo off

REM === Start Django server ===
start cmd /k python manage.py runserver 8000

REM === Wait for server to start ===
timeout /t 3 > nul

REM === Open in Chrome ===
start chrome http://127.0.0.1:8000

exit
