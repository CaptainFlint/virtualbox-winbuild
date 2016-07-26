@echo off

set VERSION=5.1.2-r108956

del /q build-tmp.cmd 2>nul

echo.
echo ### BUILDING x64 VERSION ###
echo.

echo @echo off>> build-tmp.cmd
echo call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.Cmd" /Release /x64 /win7>> build-tmp.cmd
echo color 07>> build-tmp.cmd
echo set BUILD_TARGET_ARCH=amd64>> build-tmp.cmd
echo cscript configure.vbs --with-DDK=C:\WinDDK\7600.16385.1 --with-MinGW-w64=C:\Programs\mingw64 --with-MinGW32=C:\Programs\mingw32 --with-libSDL=C:\Programs\SDL\x64 --with-openssl=C:\Programs\OpenSSL\x64 --with-libcurl=C:\Programs\curl\x64 --with-Qt5=C:\Programs\Qt\5.6.1-x64 --with-python=C:\Programs\Python>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd
echo call env.bat>> build-tmp.cmd
echo kmk>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd
echo kmk C:/Devel/VirtualBox-src/out/win.x86/release/obj/Installer/VirtualBox-%VERSION%-MultiArch_amd64.msi>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd

cmd /c build-tmp.cmd
if ERRORLEVEL 1 exit /b 1

del /q build-tmp.cmd 2>nul

echo.
echo ### BUILDING x32 VERSION ###
echo.

echo @echo off>> build-tmp.cmd
echo call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.Cmd" /Release /x86 /win7>> build-tmp.cmd
echo color 07>> build-tmp.cmd
echo set BUILD_TARGET_ARCH=x86>> build-tmp.cmd
echo cscript configure.vbs --with-DDK=C:\WinDDK\7600.16385.1 --with-MinGW-w64=C:\Programs\mingw64 --with-MinGW32=C:\Programs\mingw32 --with-libSDL=C:\Programs\SDL\x32 --with-openssl=C:\Programs\OpenSSL\x32 --with-libcurl=C:\Programs\curl\x32 --with-Qt5=C:\Programs\Qt\5.6.1-x32 --with-python=C:\Programs\Python>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd
echo call env.bat>> build-tmp.cmd
echo kmk>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd
echo kmk C:/Devel/VirtualBox-src/out/win.x86/release/bin/VirtualBox-%VERSION%-MultiArch.exe>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd

cmd /c build-tmp.cmd
if ERRORLEVEL 1 exit /b 1

del /q build-tmp.cmd 2>nul

echo.
echo ### BUILD COMPLETE ###
echo.
