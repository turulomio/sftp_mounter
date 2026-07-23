"""
Automation script for binary preparation and packaging of SFTP Mounter.

This script performs two critical distribution tasks (Build Tooling):
1. **Dependency Preparation (`setup_binaries`)**: Downloads supporting tools required at runtime directly from official repositories:
   - The portable executable of `rclone` for Windows.
   - The `WinFsp` MSI installer (required for mounting in Windows).
   Subsequently, extracts the `rclone.exe` executable from its compressed archive (.zip) and stores it 
   in the local subfolder `sftp_mounter/bin/`.
2. **Independent Packaging (`run_packaging`)**: Invokes the `PyInstaller` tool to build a single portable executable binary (`.exe` in Windows)
   containing both compiled Python code and supporting binaries.

This script is exclusive for packaging for the Windows operating system.
"""

import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess

# Official download link to obtain the current/stable version of Rclone for Windows
RCLONE_WIN_URL = "https://downloads.rclone.org/rclone-current-windows-amd64.zip"

def get_latest_winfsp_url():
    """
    Dynamically obtains the download URL of the MSI installer for the latest stable version of WinFsp
    by querying the public GitHub API.
    In case of error or API rate limits, falls back to a static backup version (v2.0).
    
    Returns:
        str: Absolute download URL for the WinFsp MSI.
    """
    fallback_url = "https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.23075.msi"
    api_url = "https://api.github.com/repos/winfsp/winfsp/releases/latest"
    try:
        import json
        req = urllib.request.Request(
            api_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            assets = data.get("assets", [])
            for asset in assets:
                name = asset.get("name", "")
                if name.endswith(".msi") and "winfsp" in name:
                    url = asset.get("browser_download_url")
                    if url:
                        return url
    except Exception as e:
        print(f"Warning: Could not obtain the latest version of WinFsp from the GitHub API ({e}). Using fallback version.")
    return fallback_url

def download_file(url, target_path):
    """
    Downloads a remote file via an HTTP GET request with a custom User-Agent.
    
    Sets headers simulating a browser to avoid blocking by the destination HTTP server,
    which sometimes restricts basic Python automated clients.
    
    Args:
        url (str): Source URL address of the file.
        target_path (str): Absolute local path where the downloaded file will be saved.
        
    Returns:
        bool: True if the download was successful, False in case of network or permission error.
    """
    print(f"Downloading {url} -> {target_path}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
            # Copy the stream of bytes efficiently to the physical file
            shutil.copyfileobj(response, out_file)
        print("Download completed successfully.")
        return True
    except Exception as e:
        print(f"Error downloading: {e}")
        return False

def setup_binaries():
    """
    Manages the download and selective extraction of rclone and the WinFsp MSI installer.
    
    Creates the intermediate `build/bin` folder in the project root to avoid
    mixing third-party compiled binaries with source package files.
    In the case of Rclone, reads the downloaded .zip file and extracts only the program
    executable (`rclone.exe`), discarding manuals or other internal files.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bin_dir = os.path.join(project_root, 'build', 'bin')
    os.makedirs(bin_dir, exist_ok=True)

    rclone_exe_name = 'rclone.exe'
    rclone_path = os.path.join(bin_dir, rclone_exe_name)
    winfsp_path = os.path.join(bin_dir, 'winfsp.msi')

    # 1. Manage WinFsp
    if not os.path.exists(winfsp_path):
        print("Downloading the latest version of WinFsp...")
        winfsp_url = get_latest_winfsp_url()
        download_file(winfsp_url, winfsp_path)
    else:
        print("WinFsp MSI already exists in the build/bin folder.")

    # 2. Manage Rclone
    if not os.path.exists(rclone_path):
        print("Downloading the latest version of Rclone...")
        zip_path = os.path.join(bin_dir, 'rclone_temp.zip')
        rclone_url = RCLONE_WIN_URL
        
        if download_file(rclone_url, zip_path):
            try:
                print("Extracting rclone...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Look only for the executable file within the internal structure of the zip
                    for file_info in zip_ref.infolist():
                        filename = os.path.basename(file_info.filename)
                        if filename == rclone_exe_name:
                            with zip_ref.open(file_info.filename) as source, open(rclone_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                            break
                print("Extraction completed.")
            except Exception as e:
                print(f"Error extracting rclone: {e}")
            finally:
                # Clean up the temporary .zip file so as not to leave garbage in the repository
                if os.path.exists(zip_path):
                    os.remove(zip_path)
    else:
        print(f"Rclone binary already exists in {rclone_path}")

    # Copy the project's SVG logo to the build/bin folder
    logo_src = os.path.join(project_root, 'sftp_mounter', 'images', 'logo.svg')
    logo_dest = os.path.join(bin_dir, 'logo.svg')
    if os.path.exists(logo_src):
        shutil.copy2(logo_src, logo_dest)
        print("SVG logo copied to build/bin.")

def get_project_version() -> str:
    """
    Dynamically retrieves the project version defined in the pyproject.toml file.
    If any error occurs during reading, returns the default backup version '1.0.0'.
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        toml_path = os.path.join(project_root, 'pyproject.toml')
        if os.path.exists(toml_path):
            with open(toml_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('version ='):
                        parts = line.split('=')
                        if len(parts) >= 2:
                            return parts[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "1.0.0"

def run_packaging():
    """
    Executes final packaging via PyInstaller using subprocesses.
    
    First checks if `pyinstaller` is available in the current Python environment.
    If not installed, invokes pip to install it before proceeding.
    
    Meaning of declared PyInstaller options:
    - --onefile: Compiles and unifies the entire program into a single self-extracting portable binary.
    - --noconsole: Disables the background command console (cmd.exe) on Windows upon startup,
      showing only PySide6's graphical user interface GUI cleanly.
    - --name: Name of the generated final binary (e.g. SFTPMounter-v1.0.0).
    - --add-data: Injects the local 'build/bin' folder with downloaded support binaries into
      PyInstaller's internal virtual volume, exposing them under the 'bin' subdirectory.
    - --distpath / --workpath / --specpath: Custom paths to organize output directories.
    """
    print("Starting packaging with PyInstaller...")
    
    # Move execution context to the project root directory to resolve relative paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Get version for the output file name
    version = get_project_version()
    exe_name = f"SFTPMounter-v{version}"
    print(f"Detected version: {version} -> Output name: {exe_name}")

    # Verify presence of PyInstaller and install automatically if necessary
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller is not installed. Installing via pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # Use Windows path separator for add-data (';')
    separator = ';'
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", exe_name,
        f"--add-data=build/bin{separator}bin",
        "--icon=sftp_mounter/images/logo.ico",
        "--distpath", "dist",
        "--workpath", "build",
        "--specpath", ".",
        "sftp_mounter/main.py"
    ]
    
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("="*60)
        print("PACKAGING FINISHED SUCCESSFULLY.")
        print(f"The single executable is located in the 'dist/' folder at the project root")
        print("="*60)
    except subprocess.CalledProcessError as e:
        print(f"Error during packaging: {e}")

if __name__ == "__main__":
    if os.name != 'nt':
        print("Error: This packaging script is only compatible with Windows or Wine environments (os.name == 'nt').")
        sys.exit(1)

    print("Preparing dependencies for all-in-one distribution...")
    setup_binaries()
    run_packaging()
