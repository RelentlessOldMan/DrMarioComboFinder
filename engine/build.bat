@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cd /d %~dp0
for /f %%v in ('powershell -NoProfile -ExecutionPolicy Bypass -File next_version.ps1') do set VER=%%v
echo DrMarioComboFinder engine %VER%
cl /nologo /O2 /openmp /std:c++17 /EHsc /DDM_VERSION=\"%VER%\" dm.cpp /Fe:dm.exe >build.log
type build.log
