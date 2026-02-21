@echo off
wpeinit

echo.
echo  ====================================
echo       DAT 系统急救 - 正在启动
echo  ====================================
echo.

echo [DAT] 初始化磁盘...
(echo rescan
 echo list volume) | diskpart >nul 2>&1

echo [DAT] 搜索仓库...
call X:\DAT\find_dat.cmd

if not defined DAT_ROOT goto FALLBACK

echo [DAT] 仓库: %DAT_ROOT%

if exist "%DAT_ROOT%\Core\rescue.exe" (
    echo [DAT] 启动救援程序...
    "%DAT_ROOT%\Core\rescue.exe"
    if errorlevel 1 goto FALLBACK
    goto END
)

echo [DAT] rescue.exe 未找到！
goto FALLBACK

:FALLBACK
call X:\DAT\fallback.cmd

:END
