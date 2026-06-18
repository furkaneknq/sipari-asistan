@echo off
REM ====================================================================
REM   Siparis Asistani - Windows Build Script
REM   Cift tiklayarak calistir. Yonetici izni gerekmez.
REM ====================================================================

setlocal EnableExtensions
title Siparis Asistani - Build

REM Bu dosyanin bulundugu klasor
set "INSTALLER_DIR=%~dp0"
REM Sondaki ters bolu varsa tut
if "%INSTALLER_DIR:~-1%"=="\" set "INSTALLER_DIR=%INSTALLER_DIR:~0,-1%"

REM Proje koku = installer\windows\..\..
for %%I in ("%INSTALLER_DIR%\..\..") do set "PROJECT_ROOT=%%~fI"

echo.
echo ============================================================
echo   Siparis Asistani - Windows kurulum derleme
echo   Installer dir: %INSTALLER_DIR%
echo   Project root : %PROJECT_ROOT%
echo ============================================================
echo.

REM Hicbir sey olmazsa bile kapanmasin diye butun cikislari etiketleyelim
set "STEP=baslangic"

REM -------- 0) Klasor yapisi dogrulamasi --------
set "STEP=klasor yapisi"
echo [0/6] Klasor yapisi kontrol ediliyor...
if not exist "%PROJECT_ROOT%\order_tracking\main.py" (
    echo.
    echo [HATA] order_tracking\main.py bulunamadi:
    echo        %PROJECT_ROOT%\order_tracking\main.py
    echo.
    echo Beklenen klasor yapisi:
    echo    %PROJECT_ROOT%\
    echo        installer\windows\build.bat       ^(bu betik^)
    echo        order_tracking\main.py            ^(eksik^)
    echo        order_tracking\requirements.txt
    echo.
    echo Cozum: ZIP'i acarken 'order_tracking' ve 'installer' klasorleri
    echo AYNI ust dizinde olmali. Suanki yapida birinin yeri yanlis.
    echo.
    goto :error_exit
)
if not exist "%PROJECT_ROOT%\order_tracking\requirements.txt" (
    echo [HATA] order_tracking\requirements.txt bulunamadi.
    goto :error_exit
)
echo       OK

REM -------- 1) Python kontrolu --------
set "STEP=Python tespiti"
echo [1/6] Python aranyor...
set "PY="
where py >nul 2>nul
if not errorlevel 1 (
    set "PY=py -3"
    goto :py_ok
)
where python >nul 2>nul
if not errorlevel 1 (
    set "PY=python"
    goto :py_ok
)
echo.
echo [HATA] Python bulunamadi.
echo   1) https://www.python.org/downloads/ adresinden Python 3.10+ indir
echo   2) Kurarken "Add Python to PATH" kutusunu MUTLAKA isaretle
echo   3) Kurulum bittikten sonra bu betigi tekrar calistir
goto :error_exit

:py_ok
echo       OK: %PY%

REM -------- 2) venv --------
set "STEP=venv olusturma"
set "VENV_DIR=%PROJECT_ROOT%\order_tracking\.venv"
echo [2/6] Sanal ortam: %VENV_DIR%
if not exist "%VENV_DIR%\Scripts\python.exe" (
    %PY% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [HATA] venv olusturulamadi.
        goto :error_exit
    )
    echo       Yeni venv olusturuldu.
) else (
    echo       Mevcut venv kullanilacak.
)
set "VPY=%VENV_DIR%\Scripts\python.exe"

REM -------- 3) pip ve bagimliliklar --------
REM --prefer-binary  : source-build'i tercih etme (C++ build tools gerektirmesin)
REM --no-cache-dir   : eski hatali wheel cache'lerini bypass et
set "PIPFLAGS=--prefer-binary --no-cache-dir"

set "STEP=pip kurulumu"
echo [3/6] pip guncelleniyor...
"%VPY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [HATA] pip guncellenemedi. Internet baglantisini kontrol et.
    goto :error_exit
)

set "STEP=requirements yukleme"
echo [3/6] requirements.txt yukleniyor (birkac dakika surebilir)...
"%VPY%" -m pip install %PIPFLAGS% -r "%PROJECT_ROOT%\order_tracking\requirements.txt"
if errorlevel 1 (
    echo [HATA] Bagimliliklar yuklenemedi. Yukaridaki pip ciktisini oku.
    echo.
    echo Olasi cozumler:
    echo   1^) Python surumun cok yeni olabilir. 3.11 veya 3.12 onerilir.
    echo      python --version ile bak; 3.13 / 3.14 bazi wheel'lerde sorun cikarir.
    echo   2^) Internet kesintili. Yeniden dene.
    echo   3^) order_tracking\.venv klasorunu sil, betigi tekrar calistir.
    goto :error_exit
)

set "STEP=PyInstaller yukleme"
echo [3/6] PyInstaller ve Pillow yukleniyor...
"%VPY%" -m pip install %PIPFLAGS% pyinstaller pillow
if errorlevel 1 (
    echo [HATA] PyInstaller / Pillow yuklenemedi.
    goto :error_exit
)

REM -------- 4) Ikon --------
set "STEP=ikon uretimi"
echo [4/6] Uygulama ikonu uretiliyor...
"%VPY%" "%INSTALLER_DIR%\build_icon.py"
if errorlevel 1 (
    echo [UYARI] Ikon uretilemedi; varsayilan ikonla devam edilecek.
)

REM -------- 5) PyInstaller --------
set "STEP=PyInstaller derleme"
echo [5/6] PyInstaller ile EXE derleniyor...
cd /d "%PROJECT_ROOT%"
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

"%VPY%" -m PyInstaller "%INSTALLER_DIR%\order_tracking.spec" --noconfirm --clean
if errorlevel 1 (
    echo [HATA] PyInstaller basarisiz. Yukaridaki ciktiyi oku.
    goto :error_exit
)

if not exist "%PROJECT_ROOT%\dist\SiparisAsistani\SiparisAsistani.exe" (
    echo [HATA] Beklenen EXE bulunamadi:
    echo        %PROJECT_ROOT%\dist\SiparisAsistani\SiparisAsistani.exe
    goto :error_exit
)

echo.
echo ============================================================
echo   PyInstaller tamam.
echo   %PROJECT_ROOT%\dist\SiparisAsistani\SiparisAsistani.exe
echo ============================================================
echo.

REM -------- 6) Inno Setup (opsiyonel) --------
set "STEP=Inno Setup"
echo [6/6] Inno Setup araniyor...
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe"      set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo.
    echo ------------------------------------------------------------
    echo   Inno Setup bulunamadi.
    echo   Sadece dist\SiparisAsistani\ klasoru olusturuldu.
    echo
    echo   Tek dosyalik kurulum .exe icin Inno Setup 6 indir:
    echo     https://jrsoftware.org/isdl.php
    echo   Sonra bu betigi tekrar calistir.
    echo ------------------------------------------------------------
    goto :ok_exit
)

echo       OK: %ISCC%
"%ISCC%" /Q "%INSTALLER_DIR%\installer.iss"
if errorlevel 1 (
    echo [HATA] Inno Setup derleme hatasi. Yukariyi oku.
    goto :error_exit
)

echo.
echo ============================================================
echo   BASARILI! Kurulum dosyasi:
echo   %INSTALLER_DIR%\Output\SiparisAsistaniSetup.exe
echo ============================================================

:ok_exit
echo.
echo Bitti. Bu pencereyi kapatabilirsin.
pause
endlocal
exit /b 0

:error_exit
echo.
echo ============================================================
echo   HATA olustu. Adim: %STEP%
echo   Lutfen yukaridaki ciktiyi okuyup destege gonder.
echo ============================================================
echo.
pause
endlocal
exit /b 1
