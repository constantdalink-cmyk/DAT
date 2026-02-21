@echo off
chcp 65001 >nul 2>&1

:MENU
cls
echo.
echo  ============================================================
echo                    DAT 紧急救援模式
echo  ============================================================
echo.
echo      [1] 显示磁盘信息
echo      [2] 重新扫描仓库
echo      [3] 命令提示符 (高级用户)
echo      [4] 重启电脑
echo.
echo  ------------------------------------------------------------
echo   状态: 未找到 DAT 仓库
echo.
echo   可能的原因:
echo     - 硬盘未被系统识别 (驱动问题)
echo     - 仓库所在分区已加密 (BitLocker)
echo     - 仓库文件已损坏或被删除
echo  ============================================================
echo.
set /p choice=请输入选项 [1-4]: 

if "%choice%"=="1" (
    echo.
    echo -------- 磁盘列表 --------
    echo list volume | diskpart
    echo --------------------------
    echo.
    pause
    goto MENU
)

if "%choice%"=="2" (
    echo.
    echo [INFO] 重新扫描...
    call X:\DAT\find_dat.cmd
    
    if defined DAT_ROOT (
        echo [OK] 找到仓库: %DAT_ROOT%
        echo.
        echo 按任意键启动...
        pause >nul
        "%DAT_ROOT%\Runtime\python.exe" "%DAT_ROOT%\Logic\bootstrap.py"
        if errorlevel 1 pause
    ) else (
        echo [ERROR] 未找到仓库
        pause
    )
    goto MENU
)

if "%choice%"=="3" (
    echo.
    echo 提示: 输入 EXIT 返回菜单
    echo.
    cmd.exe
    goto MENU
)

if "%choice%"=="4" (
    echo.
    echo 正在重启...
    wpeutil reboot
)

goto MENU