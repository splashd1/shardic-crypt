@echo off
REM build_windows.bat
REM
REM Builds standalone Windows .exe files for the GUI and both CLI
REM programs using PyInstaller. MUST be run on Windows -- PyInstaller
REM does not cross-compile, so there is no way to produce a working
REM Windows .exe from Linux or macOS. If you don't have a Windows
REM machine handy, use the GitHub Actions workflow instead
REM (.github/workflows/build.yml in this project), which builds this
REM for you on a real Windows runner and hands you the .exe as a
REM downloadable artifact.
REM
REM Requires on the build machine: Python 3.9+ (from python.org, with
REM "Add to PATH" checked during install) and internet access for pip.

setlocal

echo [*] Installing build-time dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet pyinstaller cryptography argon2-cffi

echo [*] Building VaultTool-GUI.exe (windowed, no console) ...
python -m PyInstaller --onefile --windowed --name VaultTool-GUI vault_gui.py

echo [*] Building vault-create.exe (console) ...
python -m PyInstaller --onefile --name vault-create vault_create.py

echo [*] Building vault-recover.exe (console) ...
python -m PyInstaller --onefile --name vault-recover vault_recover.py

echo [*] Building vault-create-prime.exe (console) ...
python -m PyInstaller --onefile --name vault-create-prime vault_create_prime.py

echo [*] Building vault-recover-prime.exe (console) ...
python -m PyInstaller --onefile --name vault-recover-prime vault_recover_prime.py

echo.
echo [+] Done. Executables are in the dist\ folder:
echo     dist\VaultTool-GUI.exe        (double-click GUI, includes Shardic-Prime tab)
echo     dist\vault-create.exe         (CLI)
echo     dist\vault-recover.exe        (CLI)
echo     dist\vault-create-prime.exe   (CLI, shardic-prime)
echo     dist\vault-recover-prime.exe  (CLI, shardic-prime)
echo.
echo These run standalone on any Windows 10/11 x64 machine -- no Python,
echo no pip packages, nothing else needs installing there.

endlocal
