@echo off
REM Predictive Agents 一键运行（双击即可）
REM 用法：双击此文件，或在命令行输入 run

powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
pause
