@echo off
:MENU
cls
echo.
echo  ============================================
echo            DAT 紧急救援模式
echo  ============================================
echo.
echo    [1] 显示磁盘信息
echo    [2] 重新搜索仓库
echo    [3] 命令行 (高级用户)
echo    [4] 重启电脑
echo.
echo  --------------------------------------------
echo    状态: 未找到 DAT 仓库 / rescue.exe
echo.
echo    可能原因:
echo    - 硬盘未被识别（缺少驱动）
echo    - 仓库所在盘已加密 (BitLocker)
echo    - rescue.exe 被删除或损坏
echo  ============================================
echo.
set /p choice=请选择 [1-4]:

if "%choice%"=="1" (
    echo.
    echo ---- 磁盘列表 ----
    (echo list volume) | diskpart
    echo.
    pause
    goto MENU
)
if "%choice%"=="2" (
    echo.
    echo [DAT] 重新搜索...
    call X:\DAT\find_dat.cmd
    if defined DAT_ROOT (
        echo [DAT] 找到: %DAT_ROOT%
        if exist "%DAT_ROOT%\Core\rescue.exe" (
            echo [DAT] 启动救援程序...
            "%DAT_ROOT%\Core\rescue.exe"
        ) else (
            echo [DAT] rescue.exe 不存在
        )
    ) else (
        echo [DAT] 未找到仓库
    )
    pause
    goto MENU
)
if "%choice%"=="3" (
    echo.
    echo 输入 EXIT 返回菜单
    cmd.exe
    goto MENU
)
if "%choice%"=="4" (
    wpeutil reboot
)
goto MENU
