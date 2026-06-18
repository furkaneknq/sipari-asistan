@echo off
REM Bu wrapper build.bat'i cagirir ve hata olsa bile pencereyi
REM mutlaka acik tutar. Kullanici cift tiklayacagi dosya budur.

cd /d "%~dp0"
cmd /k "build.bat"
