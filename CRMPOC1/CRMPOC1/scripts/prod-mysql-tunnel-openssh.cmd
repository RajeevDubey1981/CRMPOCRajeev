@echo off
REM Double-click or run from cmd. Enter indcooladmin SSH password when asked.
REM Leave this window open. Test: netstat -ano ^| findstr "3307"
ssh -o ServerAliveInterval=30 -L 127.0.0.1:3307:127.0.0.1:3306 -N indcooladmin@97.74.83.211
pause
