@echo off
:: 查找 DAT 仓库
:: 成功时设置 DAT_ROOT 环境变量

set DAT_ROOT=

for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist "%%D:\.DAT\dat.sig" (
        if exist "%%D:\.DAT\Runtime\python.exe" (
            if exist "%%D:\.DAT\Logic\bootstrap.py" (
                set DAT_ROOT=%%D:\.DAT
                goto :eof
            )
        )
    )
)