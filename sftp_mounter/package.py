"""
Automation script for binary preparation and packaging of SFTP Mounter.

This script performs two critical distribution tasks (Build Tooling):
1. **Dependency Preparation (`setup_binaries`)**: Downloads supporting tools required at runtime directly from official repositories:
   - The latest portable executable of `rclone` for Windows.
   - The latest `WinFsp` MSI installer (required for mounting in Windows).
   - **Explicit Integrity Verification**: Calculates local SHA-256 hashes of downloaded binaries and verifies them against official release SHA-256 checksums before packaging.
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
import json
import re
import hashlib


def calculate_sha256(file_path: str) -> str:
    """
    Calculates the SHA-256 hash of a file in 64KB chunks.
    
    Returns:
        str: Lowercase hex digest string of SHA-256 hash.
    """
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def get_latest_winfsp_info():
    """
    Dynamically obtains the download URL and expected SHA-256 hashes for the latest stable WinFsp release
    by querying the public GitHub API.
    
    Returns:
        tuple: (msi_download_url, list_of_expected_sha256_hashes)
    """
    fallback_url = "https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.23075.msi"
    fallback_hashes = ["073a70e00f77423e34bed98b86e600def93393ba5822204fac57a29324db9f7a"]
    api_url = "https://api.github.com/repos/winfsp/winfsp/releases/latest"
    try:
        req = urllib.request.Request(
            api_url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            body = data.get("body", "")
            assets = data.get("assets", [])
            msi_url = ""
            for asset in assets:
                name = asset.get("name", "")
                if name.endswith(".msi") and "winfsp" in name:
                    msi_url = asset.get("browser_download_url")
                    break
            
            expected_hashes = [h.lower() for h in re.findall(r'[a-fA-F0-9]{64}', body)]
            if msi_url:
                return msi_url, expected_hashes
    except Exception as e:
        print(f"Warning: Could not obtain the latest WinFsp release info from GitHub API ({e}). Using fallback.")
    return fallback_url, fallback_hashes


def get_latest_rclone_info():
    """
    Dynamically obtains the download URL and expected SHA-256 hash for the latest Rclone Windows ZIP release
    by querying the public GitHub API and downloading asset SHA256SUMS.
    
    Returns:
        tuple: (zip_download_url, expected_sha256_hash)
    """
    api_url = "https://api.github.com/repos/rclone/rclone/releases/latest"
    try:
        req = urllib.request.Request(
            api_url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            zip_url = ""
            zip_name = ""
            sha_url = ""
            for asset in data.get("assets", []):
                name = asset.get("name", "")
                if "windows-amd64.zip" in name:
                    zip_url = asset.get("browser_download_url")
                    zip_name = name
                elif "SHA256SUMS" in name:
                    sha_url = asset.get("browser_download_url")

            expected_sha = ""
            if sha_url:
                s_req = urllib.request.Request(
                    sha_url,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(s_req, timeout=10) as s_resp:
                    content = s_resp.read().decode('utf-8')
                    for line in content.splitlines():
                        if zip_name in line or "windows-amd64" in line:
                            parts = line.split()
                            if parts and len(parts[0]) == 64:
                                expected_sha = parts[0].lower()
                                break
            if zip_url:
                return zip_url, expected_sha
    except Exception as e:
        print(f"Warning: Could not obtain latest Rclone release info from GitHub API ({e}). Using fallback.")
    
    fallback_url = "https://downloads.rclone.org/rclone-current-windows-amd64.zip"
    return fallback_url, ""


def download_file(url, target_path):
    """
    Downloads a remote file via an HTTP GET request with a custom User-Agent.
    
    Args:
        url (str): Source URL address of the file.
        target_path (str): Absolute local path where the downloaded file will be saved.
        
    Returns:
        bool: True if the download was successful, False in case of network error.
    """
    print(f"Downloading {url} -> {target_path}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("Download completed successfully.")
        return True
    except Exception as e:
        print(f"Error downloading: {e}")
        return False


def setup_binaries():
    """
    Manages downloading latest binaries of WinFsp and Rclone, verifying their referential integrity (SHA-256),
    and extracting rclone.exe into build/bin directory.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bin_dir = os.path.join(project_root, 'build', 'bin')
    os.makedirs(bin_dir, exist_ok=True)

    rclone_exe_name = 'rclone.exe'
    rclone_path = os.path.join(bin_dir, rclone_exe_name)
    winfsp_path = os.path.join(bin_dir, 'winfsp.msi')

    # 1. Download & Verify WinFsp
    print("=" * 60)
    print("1/2 Processing WinFsp latest release & verifying SHA-256 integrity...")
    winfsp_url, winfsp_expected_hashes = get_latest_winfsp_info()
    winfsp_temp = os.path.join(bin_dir, 'winfsp_temp.msi')
    
    if download_file(winfsp_url, winfsp_temp):
        winfsp_sha256 = calculate_sha256(winfsp_temp)
        print(f"Calculated WinFsp MSI SHA-256: {winfsp_sha256}")
        
        if winfsp_expected_hashes and winfsp_sha256 not in winfsp_expected_hashes:
            os.remove(winfsp_temp)
            raise RuntimeError(f"WinFsp SHA-256 referential integrity check failed!\nExpected: {winfsp_expected_hashes}\nGot: {winfsp_sha256}")
        
        print("[✓] WinFsp MSI referential integrity verified successfully!")
        if os.path.exists(winfsp_path):
            os.remove(winfsp_path)
        shutil.move(winfsp_temp, winfsp_path)
    else:
        raise RuntimeError("Failed to download WinFsp MSI binary.")

    # 2. Download & Verify Rclone
    print("=" * 60)
    print("2/2 Processing Rclone latest release & verifying SHA-256 integrity...")
    rclone_url, rclone_expected_sha = get_latest_rclone_info()
    zip_path = os.path.join(bin_dir, 'rclone_temp.zip')
    
    if download_file(rclone_url, zip_path):
        rclone_zip_sha256 = calculate_sha256(zip_path)
        print(f"Calculated Rclone ZIP SHA-256: {rclone_zip_sha256}")
        
        if rclone_expected_sha and rclone_zip_sha256 != rclone_expected_sha:
            os.remove(zip_path)
            raise RuntimeError(f"Rclone ZIP referential integrity check failed!\nExpected: {rclone_expected_sha}\nGot: {rclone_zip_sha256}")
            
        print("[✓] Rclone ZIP referential integrity verified successfully!")
        
        try:
            print("Extracting rclone.exe...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    filename = os.path.basename(file_info.filename)
                    if filename == rclone_exe_name:
                        with zip_ref.open(file_info.filename) as source, open(rclone_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        break
            print("Extraction of rclone.exe completed successfully.")
        except Exception as e:
            raise RuntimeError(f"Error extracting rclone.exe from verified zip archive: {e}")
        finally:
            if os.path.exists(zip_path):
                os.remove(zip_path)
    else:
        raise RuntimeError("Failed to download Rclone ZIP binary.")

    # Copy the project's SVG logo to the build/bin folder
    logo_src = os.path.join(project_root, 'sftp_mounter', 'images', 'logo.svg')
    logo_dest = os.path.join(bin_dir, 'logo.svg')
    if os.path.exists(logo_src):
        shutil.copy2(logo_src, logo_dest)
        print("SVG logo copied to build/bin.")


def get_project_version() -> str:
    """
    Dynamically retrieves the project version defined in the pyproject.toml file.
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
    """
    print("Starting packaging with PyInstaller...")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    version = get_project_version()
    exe_name = f"SFTPMounter-v{version}"
    print(f"Detected version: {version} -> Output name: {exe_name}")

    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller is not installed. Installing via pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

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
        print("=" * 60)
        print("PACKAGING FINISHED SUCCESSFULLY.")
        print(f"The single executable is located in the 'dist/' folder at the project root")
        print("=" * 60)
    except subprocess.CalledProcessError as e:
        print(f"Error during packaging: {e}")


if __name__ == "__main__":
    if os.name != 'nt':
        print("Error: This packaging script is only compatible with Windows or Wine environments (os.name == 'nt').")
        sys.exit(1)

    print("Preparing dependencies for all-in-one distribution...")
    setup_binaries()
    run_packaging()
