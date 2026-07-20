import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess

# Official download links for dependencies
WINFSP_MSI_URL = "https://github.com/winfsp/winfsp/releases/download/v2.0/winfsp-2.0.23075.msi"
RCLONE_WIN_URL = "https://downloads.rclone.org/v1.66.0/rclone-v1.66.0-windows-amd64.zip"
RCLONE_LINUX_URL = "https://downloads.rclone.org/v1.66.0/rclone-v1.66.0-linux-amd64.zip"

def download_file(url, target_path):
    print(f"Descargando {url} -> {target_path}...")
    try:
        # User-Agent to avoid blocking
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("Descarga completada con éxito.")
        return True
    except Exception as e:
        print(f"Error al descargar: {e}")
        return False

def setup_binaries():
    bin_dir = os.path.join(os.path.dirname(__file__), 'bin')
    os.makedirs(bin_dir, exist_ok=True)

    rclone_exe_name = 'rclone.exe' if os.name == 'nt' else 'rclone'
    rclone_path = os.path.join(bin_dir, rclone_exe_name)
    winfsp_path = os.path.join(bin_dir, 'winfsp.msi')

    # 1. Handle WinFsp (Only needed for Windows bundle)
    if not os.path.exists(winfsp_path) and os.name == 'nt':
        print("Descargando WinFsp Installer...")
        download_file(WINFSP_MSI_URL, winfsp_path)
    elif os.name == 'nt':
        print("WinFsp MSI ya existe en la carpeta bin.")

    # 2. Handle Rclone
    if not os.path.exists(rclone_path):
        print("Descargando Rclone...")
        zip_path = os.path.join(bin_dir, 'rclone_temp.zip')
        
        # Select URL based on OS (can package on Linux or Windows)
        rclone_url = RCLONE_WIN_URL if os.name == 'nt' else RCLONE_LINUX_URL
        
        if download_file(rclone_url, zip_path):
            try:
                print("Extrayendo rclone...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Find rclone.exe or rclone within the archive structure
                    for file_info in zip_ref.infolist():
                        filename = os.path.basename(file_info.filename)
                        if filename == rclone_exe_name:
                            # Extract to bin/rclone[.exe]
                            with zip_ref.open(file_info.filename) as source, open(rclone_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                            break
                print("Extracción completada.")
            except Exception as e:
                print(f"Error al extraer rclone: {e}")
            finally:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
    else:
        print(f"Rclone binary ya existe en {rclone_path}")

    # Set execute permissions on Unix
    if os.name != 'nt' and os.path.exists(rclone_path):
        os.chmod(rclone_path, 0o755)

def run_packaging():
    print("Iniciando empaquetado con PyInstaller...")
    
    # Change working directory to the directory containing this script
    package_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(package_dir)

    # Check if pyinstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller no está instalado. Instalándolo vía pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # Determine add-data syntax (';' for Windows, ':' for Linux)
    separator = ';' if os.name == 'nt' else ':'
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", "SFTPMounter",
        f"--add-data=bin{separator}bin",
        "--distpath", "../dist",
        "--workpath", "../build",
        "--specpath", "..",
        "main.py"
    ]
    
    print(f"Ejecutando: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("="*60)
        print("EMPAQUETADO FINALIZADO CON ÉXITO.")
        print(f"El ejecutable único se encuentra en la carpeta 'dist/' en la raíz del proyecto")
        print("="*60)
    except subprocess.CalledProcessError as e:
        print(f"Error durante el empaquetado: {e}")


if __name__ == "__main__":
    print("Preparando dependencias para distribución todo-en-uno...")
    setup_binaries()
    
    # Pack if argument --pack is supplied, or by default
    run_packaging()
