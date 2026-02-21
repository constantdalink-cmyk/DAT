@echo off
chcp 65001 >nul 2>&1
title DAT 系统急救

echo.
echo  ============================================
echo          DAT 系统急救 - 启动中...
echo  ============================================
echo.

:: 初始化 WinPE
wpeinit

echo [INFO] 初始化磁盘...
(echo rescan
 echo list volume) | diskpart >nul 2>&1

:: 延迟等待磁盘识别
timeout /t 2 /nobreak >nul

:: 查找 DAT 仓库
call X:\DAT\find_dat.cmd

if defined DAT_ROOT (
    echo [OK] 找到仓库: %DAT_ROOT%
    echo.
    goto LAUNCH
) else (
    echo [ERROR] 未找到 DAT 仓库
    goto FALLBACK
)

:LAUNCH
echo [INFO] 启动 Python 环境...
"%DAT_ROOT%\Runtime\python.exe" "%DAT_ROOT%\Logic\bootstrap.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Python 执行失败，进入救援模式
    goto FALLBACK
)
goto END

:FALLBACK
call X:\DAT\fallback.cmd

:END