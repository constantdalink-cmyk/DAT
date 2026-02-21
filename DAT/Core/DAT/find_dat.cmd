@echo off
set DAT_ROOT=
for %%D in (C D E F G H I J K L M N O P Q R S T U V W X Y Z) do (
    if exist "%%D:\.DAT\dat.sig" (
        if exist "%%D:\.DAT\Core\rescue.exe" (
            set DAT_ROOT=%%D:\.DAT
            goto :eof
        )
    )
)
