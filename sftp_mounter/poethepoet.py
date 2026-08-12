"""
Poe the Poet task script handlers for SFTP Mounter.
"""

import sys
import subprocess


def print_release_steps():
    """
    Prints the step-by-step checklist for building and creating a release.
    """
    steps = """
============================================================
           SFTP MOUNTER - RELEASE CHECKLIST
============================================================

1. Check for updates of external dependencies:
   - Check the latest Rclone version at: https://github.com/rclone/rclone/releases
   - Check the latest WinFsp version at: https://github.com/winfsp/winfsp/releases
   - If updates are available, update the download links in:
     sftp_mounter/package.py

2. Increment project version number in the following locations:
   - pyproject.toml -> [tool.poetry] version = "X.Y.Z"
   - sftp_mounter/main.py -> app.setApplicationVersion("X.Y.Z")
   - sftp_mounter/package.py -> VERSION = "X.Y.Z"

3. Verify translations & English defaults:
   - Ensure all new strings are translated in sftp_mounter/i18n.py
   - Ensure English is set as the default/fallback language.

4. Run syntax verification checks:
   - poetry run python -m py_compile sftp_mounter/*.py

5. Test the application locally:
   - poetry run sftp-mounter

6. Build the standalone Windows executable:
   - poetry run python sftp_mounter/package.py
     (Creates the redistributable dist/SFTPMounter-vX.Y.Z.exe)

7. Commit changes & create a Git release tag:
   - git add .
   - git commit -m "Release version X.Y.Z"
   - git tag -a vX.Y.Z -m "Version X.Y.Z"
   - git push origin main --tags

============================================================
"""
    print(steps)


def setup_wine_python():
    """
    Downloads and installs Python 3.10 and dependencies in Wine environment.
    Copies required PySide6 DLLs and plugins into Python root directory under Wine.
    """
    commands = [
        "wget -q https://aka.ms/vs/17/release/vc_redist.x64.exe -O vc_redist.x64.exe",
        "wine vc_redist.x64.exe /quiet /norestart",
        "rm -f vc_redist.x64.exe",
        "wget -q https://www.python.org/ftp/python/3.10.8/python-3.10.8-amd64.exe -O python-windows.exe",
        "wine python-windows.exe /quiet InstallAllUsers=1 PrependPath=1",
        "rm -f python-windows.exe",
        "wine python -m pip install --upgrade pip setuptools wheel",
        "wine python -m pip install PySide6",
        "wine python -m pip install .",
        'wine cmd /c copy /y "C:\\Program Files\\Python310\\lib\\site-packages\\PySide6\\*.dll" "C:\\Program Files\\Python310"',
        'wine cmd /c xcopy /e /i /y "C:\\Program Files\\Python310\\lib\\site-packages\\PySide6\\plugins" "C:\\Program Files\\Python310\\plugins"'
    ]
    for cmd in commands:
        print(f"--> Executing: {cmd}")
        res = subprocess.run(cmd, shell=True)
        if res.returncode != 0:
            print(f"Error executing command: {cmd}")
            sys.exit(res.returncode)


def build_windows_wine():
    """
    Executes the PyInstaller packaging script under Wine.
    """
    cmd = "wine python sftp_mounter/package.py"
    print(f"--> Executing: {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        sys.exit(res.returncode)


def run_wine():
    """
    Runs SFTP Mounter main script under Wine.
    """
    cmd = "wine python sftp_mounter/main.py"
    print(f"--> Executing: {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        sys.exit(res.returncode)


def test():
    """
    Runs the unit test suite under Wine Windows environment.
    """
    cmd = "wine python -m unittest discover tests"
    print(f"--> Executing: {cmd}")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        sys.exit(res.returncode)


def release():
    """
    Displays release checklist steps.
    """
    print_release_steps()
