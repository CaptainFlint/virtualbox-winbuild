@echo off

cd /d %~dp0
for /f "tokens=3" %%i in ('findstr /B /R /C:"VBOX_VERSION_MAJOR *=" Version.kmk') do SET VBOX_VER_MJ=%%i
for /f "tokens=3" %%i in ('findstr /B /R /C:"VBOX_VERSION_MINOR *=" Version.kmk') do SET VBOX_VER_MN=%%i
for /f "tokens=3" %%i in ('findstr /B /R /C:"VBOX_VERSION_BUILD *=" Version.kmk') do SET VBOX_VER_BLD=%%i
for /f "tokens=6" %%i in ('findstr /C:"$Rev: " Config.kmk') do SET VBOX_REV=%%i
for /f "tokens=3" %%i in ('findstr /B /C:"VBOX_BUILD_PUBLISHER :=" LocalConfig.kmk') do SET VBOX_VER_PUB=%%i

set VERSION=%VBOX_VER_MJ%.%VBOX_VER_MN%.%VBOX_VER_BLD%%VBOX_VER_PUB%-r%VBOX_REV%
set VBOX_VER_MJ=
set VBOX_VER_MN=
set VBOX_VER_BLD=
set VBOX_VER_PUB=

del /q build-tmp.cmd 2>nul

echo @echo off>> build-tmp.cmd
echo call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.Cmd" /Release /x64 /win7>> build-tmp.cmd
echo color 07>> build-tmp.cmd
echo echo.>> build-tmp.cmd
echo echo ### %VERSION%: BUILDING x64 VERSION ###>> build-tmp.cmd
echo echo.>> build-tmp.cmd
echo set BUILD_TARGET_ARCH=amd64>> build-tmp.cmd
echo cscript configure.vbs --with-DDK=C:\WinDDK\7600.16385.1 --with-MinGW-w64=C:\Programs\mingw64 --with-MinGW32=C:\Programs\mingw32 --with-libSDL=C:\Programs\SDL\x64 --with-openssl=C:\Programs\OpenSSL\x64 --with-openssl32=C:\Programs\OpenSSL\x32 --with-libcurl=C:\Programs\curl\x64 --with-libcurl32=C:\Programs\curl\x32 --with-Qt5=C:\Programs\Qt\5.6.3-x64 --with-libvpx=C:\Programs\libvpx --with-libopus=C:\Programs\libopus --with-python=C:/Programs/Python>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd
echo call env.bat>> build-tmp.cmd
echo kmk>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd
echo kmk C:/Devel/VirtualBox-src/out/win.x86/release/obj/Installer/VirtualBox-%VERSION%-MultiArch_amd64.msi>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd

cmd /c build-tmp.cmd
if ERRORLEVEL 1 exit /b 1

del /q build-tmp.cmd 2>nul

echo @echo off>> build-tmp.cmd
echo call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.Cmd" /Release /x86 /win7>> build-tmp.cmd
echo color 07>> build-tmp.cmd
echo echo.>> build-tmp.cmd
echo echo ### %VERSION%: BUILDING x32 VERSION ###>> build-tmp.cmd
echo echo.>> build-tmp.cmd
echo set BUILD_TARGET_ARCH=x86>> build-tmp.cmd
echo cscript configure.vbs --with-DDK=C:\WinDDK\7600.16385.1 --with-MinGW-w64=C:\Programs\mingw64 --with-MinGW32=C:\Programs\mingw32 --with-libSDL=C:\Programs\SDL\x32 --with-openssl=C:\Programs\OpenSSL\x32 --with-libcurl=C:\Programs\curl\x32 --with-Qt5=C:\Programs\Qt\5.6.3-x32 --with-libvpx=C:\Programs\libvpx --with-libopus=C:\Programs\libopus --with-python=C:/Programs/Python>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd
echo call env.bat>> build-tmp.cmd
echo kmk>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd
echo kmk C:/Devel/VirtualBox-src/out/win.x86/release/bin/VirtualBox-%VERSION%-MultiArch.exe>> build-tmp.cmd
echo if ERRORLEVEL 1 exit /b ^1>> build-tmp.cmd

cmd /c build-tmp.cmd
if ERRORLEVEL 1 exit /b 1

del /q build-tmp.cmd AutoConfig.kmk configure.log env.bat 2>nul

echo.
echo ### BUILD COMPLETE ###
echo.
