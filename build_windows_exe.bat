@echo off
setlocal
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto err
py -3 -m PyInstaller --noconfirm --clean --windowed --onefile --name OpticalBench --add-data "assets;assets" app.py
if errorlevel 1 goto err
echo.
echo Finished: dist\OpticalBench.exe
pause
exit /b 0
:err
echo Failed. Review the errors above.
pause
exit /b 1
