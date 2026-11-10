@echo off
setlocal
set "VS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
call "%VS%\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set "CMAKE=%VS%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
"%CMAKE%" -S "%~dp0." -B "%~dp0core\build-win" -G Ninja -DCMAKE_BUILD_TYPE=Release || exit /b 1
"%CMAKE%" --build "%~dp0core\build-win"
