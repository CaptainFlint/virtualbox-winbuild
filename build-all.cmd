@echo off

del /q build-tmp.cmd 2>nul

echo.
echo ### BUILDING x64 VERSION ###
echo.

echo @echo off>> build-tmp.cmd
echo call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.Cmd" /Release /x64 /win7>> build-tmp.cmd
echo color>> build-tmp.cmd
echo set BUILD_TARGET_ARCH=amd64>> build-tmp.cmd
echo set INCLUDE=C:\Programs\curl\x64\include;%%INCLUDE%%>> build-tmp.cmd
echo set LIB=C:\Programs\curl\x64;%%LIB%%>> build-tmp.cmd
echo set LIBPATH=C:\Programs\curl\x64;%%LIBPATH%%>> build-tmp.cmd
echo set PATH=C:\Programs\Qt\4.8.7-x64\bin;%%PATH%%>> build-tmp.cmd
echo set QMAKESPEC=win32-msvc2010>> build-tmp.cmd
echo cscript configure.vbs --with-DDK=C:\WinDDK\7600.16385.1 --with-MinGW-w64=C:\Programs\mingw64 --with-MinGW32=C:\Programs\mingw32 --with-libSDL=C:\Programs\SDL\x64 --with-openssl=C:\Programs\OpenSSL\x64 --with-libcurl=C:\Programs\curl\x64 --with-Qt4=C:\Programs\Qt\4.8.7-x64 --with-python=C:\Programs\Python>> build-tmp.cmd
echo call env.bat>> build-tmp.cmd
echo kmk>> build-tmp.cmd
echo kmk C:/Devel/VirtualBox-src/out/win.x86/release/obj/Installer/VirtualBox-5.0.16-r105871-MultiArch_amd64.msi>> build-tmp.cmd

cmd /c build-tmp.cmd

del /q build-tmp.cmd 2>nul

echo.
echo ### BUILDING x32 VERSION ###
echo.

echo @echo off>> build-tmp.cmd
echo call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.Cmd" /Release /x86 /win7>> build-tmp.cmd
echo color>> build-tmp.cmd
echo set BUILD_TARGET_ARCH=x86>> build-tmp.cmd
echo set INCLUDE=C:\Programs\curl\x32\include;%%INCLUDE%%>> build-tmp.cmd
echo set LIB=C:\Programs\curl\x32;%%LIB%%>> build-tmp.cmd
echo set LIBPATH=C:\Programs\curl\x32;%%LIBPATH%%>> build-tmp.cmd
echo set PATH=C:\Programs\Qt\4.8.7-x32\bin;%%PATH%%>> build-tmp.cmd
echo set QMAKESPEC=win32-msvc2010>> build-tmp.cmd
echo cscript configure.vbs --with-DDK=C:\WinDDK\7600.16385.1 --with-MinGW-w64=C:\Programs\mingw64 --with-MinGW32=C:\Programs\mingw32 --with-libSDL=C:\Programs\SDL\x32 --with-openssl=C:\Programs\OpenSSL\x32 --with-libcurl=C:\Programs\curl\x32 --with-Qt4=C:\Programs\Qt\4.8.7-x32 --with-python=C:\Programs\Python>> build-tmp.cmd
echo call env.bat>> build-tmp.cmd
echo kmk>> build-tmp.cmd
echo kmk C:/Devel/VirtualBox-src/out/win.x86/release/bin/VirtualBox-5.0.16-r105871-MultiArch.exe>> build-tmp.cmd

cmd /c build-tmp.cmd

del /q build-tmp.cmd 2>nul

echo.
echo ### BUILD COMPLETE ###
echo.
