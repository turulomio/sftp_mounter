"""
Script de automatización para la preparación de binarios y empaquetado de SFTP Mounter.

Este script realiza dos tareas críticas de distribución (Build Tooling):
1. **Preparación de Dependencias (`setup_binaries`)**: Descarga directamente de repositorios oficiales
   las herramientas que la aplicación requiere en tiempo de ejecución:
   - El ejecutable portable de `rclone` (según el sistema operativo Windows o Linux).
   - El instalador MSI de `WinFsp` (necesario únicamente para empaquetados destinados a Windows).
   Posteriormente, extrae el ejecutable `rclone` desde su archivo comprimido (.zip) y lo almacena 
   en la subcarpeta local `sftp_mounter/bin/`.
2. **Empaquetado Independiente (`run_packaging`)**: Invoca la herramienta `PyInstaller` para
   construir un único binario ejecutable portable (`.exe` en Windows o binario ejecutable en Linux)
   que contiene en su interior tanto el código Python compilado como los binarios de soporte.

Para nuevos desarrolladores:
- Ejecutar este archivo directamente (`python sftp_mounter/package.py`) descargará y empaquetará
  todo automáticamente en la carpeta raíz `dist/`.
- No es necesario pre-instalar `PyInstaller` o descargar manualmente `rclone` / `WinFsp`.
- Presta especial atención al flag `--add-data` que indica a PyInstaller qué carpetas debe inyectar
  en el ejecutable para que `Mounter` las resuelva dinámicamente con `sys._MEIPASS`.
"""

import os
import sys
import shutil
import urllib.request
import zipfile
import subprocess

# Enlaces de descarga oficiales para obtener las versiones corriente/estable más recientes
RCLONE_WIN_URL = "https://downloads.rclone.org/rclone-current-windows-amd64.zip"
RCLONE_LINUX_URL = "https://downloads.rclone.org/rclone-current-linux-amd64.zip"

def get_latest_winfsp_url():
    """
    Obtiene la URL de descarga del instalador MSI de la última versión estable de WinFsp
    consultando de forma dinámica la API pública de GitHub.
    En caso de error o límite de tasa de la API, cae en una versión estática de respaldo (v2.0).
    
    Returns:
        str: URL absoluta de descarga para el MSI de WinFsp.
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
        print(f"Advertencia: No se pudo obtener la última versión de WinFsp desde la API de GitHub ({e}). Usando versión de respaldo.")
    return fallback_url

def download_file(url, target_path):
    """
    Descarga un archivo remoto a través de una petición HTTP GET con User-Agent personalizado.
    
    Establece cabeceras simulando un navegador para evitar bloqueos por parte del servidor HTTP
    de destino que a veces restringe a clientes automatizados básicos de Python.
    
    Args:
        url (str): Dirección URL de origen del archivo.
        target_path (str): Ruta local absoluta donde se guardará el archivo descargado.
        
    Returns:
        bool: True si la descarga fue exitosa, False en caso de error de red o permisos.
    """
    print(f"Descargando {url} -> {target_path}...")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
            # Copiar el stream de bytes de forma eficiente al archivo físico
            shutil.copyfileobj(response, out_file)
        print("Descarga completada con éxito.")
        return True
    except Exception as e:
        print(f"Error al descargar: {e}")
        return False

def setup_binaries():
    """
    Gestiona la descarga y extracción selectiva de rclone y el instalador MSI de WinFsp.
    
    Crea la carpeta intermedia `build/bin` en la raíz del proyecto para evitar
    mezclar binarios compilados de terceros con el código fuente del paquete.
    En el caso de Rclone, lee el archivo .zip descargado y extrae únicamente el archivo 
    del programa ejecutable (`rclone` o `rclone.exe`) descartando manuales u otros archivos internos.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bin_dir = os.path.join(project_root, 'build', 'bin')
    os.makedirs(bin_dir, exist_ok=True)

    rclone_exe_name = 'rclone.exe' if os.name == 'nt' else 'rclone'
    rclone_path = os.path.join(bin_dir, rclone_exe_name)
    winfsp_path = os.path.join(bin_dir, 'winfsp.msi')

    # 1. Gestionar WinFsp (Solo requerido para empaquetar para el entorno Windows)
    if not os.path.exists(winfsp_path) and os.name == 'nt':
        print("Descargando la última versión de WinFsp...")
        winfsp_url = get_latest_winfsp_url()
        download_file(winfsp_url, winfsp_path)
    elif os.name == 'nt':
        print("WinFsp MSI ya existe en la carpeta build/bin.")

    # 2. Gestionar Rclone
    if not os.path.exists(rclone_path):
        print("Descargando la última versión de Rclone...")
        zip_path = os.path.join(bin_dir, 'rclone_temp.zip')
        rclone_url = RCLONE_WIN_URL if os.name == 'nt' else RCLONE_LINUX_URL
        
        if download_file(rclone_url, zip_path):
            try:
                print("Extrayendo rclone...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Buscar únicamente el archivo ejecutable dentro de la estructura interna del zip
                    for file_info in zip_ref.infolist():
                        filename = os.path.basename(file_info.filename)
                        if filename == rclone_exe_name:
                            with zip_ref.open(file_info.filename) as source, open(rclone_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                            break
                print("Extracción completada.")
            except Exception as e:
                print(f"Error al extraer rclone: {e}")
            finally:
                # Limpiar el archivo .zip temporal descargado para no dejar basura en el repositorio
                if os.path.exists(zip_path):
                    os.remove(zip_path)
    else:
        print(f"Rclone binary ya existe en {rclone_path}")

    # En sistemas UNIX, es mandatorio otorgar permisos explícitos de ejecución al binario (chmod +x)
    if os.name != 'nt' and os.path.exists(rclone_path):
        os.chmod(rclone_path, 0o755)

def get_project_version() -> str:
    """
    Recupera de forma dinámica la versión del proyecto definida en el archivo pyproject.toml.
    Si ocurre algún error en la lectura, retorna la versión de respaldo por defecto '1.0.0'.
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
    Ejecuta el empaquetado final a través de PyInstaller utilizando subprocesos.
    
    Verifica previamente si `pyinstaller` se encuentra disponible en el entorno de Python actual.
    Si no está instalado, invoca a pip para instalarlo antes de proceder.
    
    Significado de las opciones de PyInstaller declaradas:
    - --onefile: Compila y unifica todo el programa en un único binario portable autoextraíble.
    - --noconsole: Deshabilita la consola de comandos de fondo (cmd.exe) en Windows al arrancar,
      haciendo que solo se visualice la interfaz de usuario GUI de PySide6 de forma limpia.
    - --name: Nombre que tendrá el binario final generado (ej. SFTPMounter-v1.0.0).
    - --add-data: Inyecta la carpeta local 'build/bin' con los binarios de soporte descargados 
      dentro del volumen interno virtual de PyInstaller, exponiéndolos bajo el subdirectorio 'bin'.
    - --distpath / --workpath / --specpath: Rutas personalizadas para organizar los directorios de salida.
    """
    print("Iniciando empaquetado con PyInstaller...")
    
    # Mover el contexto de ejecución al directorio raíz del proyecto para resolver rutas relativas
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    # Obtener versión para el nombre del archivo de salida
    version = get_project_version()
    exe_name = f"SFTPMounter-v{version}"
    print(f"Versión detectada: {version} -> Nombre de salida: {exe_name}")

    # Verificar presencia de PyInstaller e instalar automáticamente si es necesario
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller no está instalado. Instalándolo vía pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # El separador de rutas add-data difiere según el SO (';' en Windows, ':' en Linux)
    separator = ';' if os.name == 'nt' else ':'
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--noconsole",
        "--name", exe_name,
        "--icon=sftp_mounter/logo.ico",
        f"--add-data=build/bin{separator}bin",
        "--distpath", "dist",
        "--workpath", "build",
        "--specpath", ".",
        "sftp_mounter/main.py"
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
    run_packaging()


