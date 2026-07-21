"""
Punto de entrada principal de la aplicación SFTP Mounter.

Este módulo se encarga de:
1. Configurar y ajustar el `sys.path` para garantizar la resolución correcta de módulos locales.
2. Inicializar el sistema de registro de logs (`logging`) en rutas dependientes del sistema operativo.
3. Configurar variables de entorno y estilos globales para la interfaz gráfica PySide6 (High DPI, estilo Fusion).
4. Instanciar la aplicación Qt, comprobar los argumentos de línea de comandos (ej. iniciar minimizado) y lanzar el bucle de eventos.

Para desarrolladores nuevos:
- El flujo comienza en el bloque `if __name__ == '__main__':` invocando a `main()`.
- Si el ejecutable se inicia con el argumento `--minimized`, el proceso se ejecutará directamente en la bandeja del sistema (System Tray) sin mostrar la ventana principal inmediatamente.
"""

import sys
import os
import logging

# ==============================================================================
# RESOLUCIÓN DE RUTAS E IMPORTACIONES LOCALES
# ==============================================================================
# Cuando se ejecuta la aplicación como un binario empaquetado (con PyInstaller) o
# directamente desde la consola en modo de desarrollo, es fundamental ajustar
# las rutas de búsqueda de Python para evitar errores de importación de módulos.
package_dir = os.path.dirname(os.path.abspath(__file__))  # Directorio 'sftp_mounter'
parent_dir = os.path.dirname(package_dir)                 # Directorio raíz del proyecto
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

from PySide6.QtWidgets import QApplication
from sftp_mounter.gui import MainWindow

def setup_logging():
    """
    Configura el sistema de logs a nivel global en la aplicación.
    
    Genera un archivo 'app.log' en una ubicación persistente de la máquina del usuario:
    - Windows: %APPDATA%/SFTPMounter/app.log
    - Linux/macOS: ~/.config/sftpmounter/app.log
    
    El log escribe simultáneamente tanto en el archivo de texto en formato UTF-8 como
    en la salida estándar (sys.stdout) para facilitar la depuración en tiempo de desarrollo.
    """
    # Determinar el directorio de logs según la plataforma
    if os.name == 'nt':
        # Windows: busca en %APPDATA% o cae en el directorio personal
        log_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SFTPMounter')
    else:
        # Linux/macOS: estándar XDG en ~/.config
        log_dir = os.path.join(os.path.expanduser('~'), '.config', 'sftpmounter')
        
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')

    # Configuración básica de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Application started.")

def main():
    """
    Inicializa el entorno, prepara la ventana principal de PySide6 y arranca el loop de Qt.
    """
    setup_logging()
    
    # Habilitar el escalado automático de pantalla (High DPI).
    # Esto es sumamente importante en sistemas modernos (Windows 11, pantallas 4K)
    # para que la interfaz gráfica no se vea borrosa o excesivamente pequeña.
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("SFTP Drive Mounter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Antigravity")
    app.setOrganizationDomain("antigravity.ai")

    # Forzar el uso del estilo de diseño 'Fusion' de Qt, que ofrece
    # una apariencia moderna y consistente en todas las plataformas soportadas.
    app.setStyle('Fusion')

    # Inicializar la ventana principal pasándole la instancia de la aplicación
    window = MainWindow(app)
    
    # Evaluar si la aplicación debe iniciar minimizada directamente en la bandeja del sistema.
    # Útil cuando la aplicación está configurada para autoiniciar con el sistema operativo (autostart).
    start_minimized = "--minimized" in sys.argv
    if not start_minimized:
        window.show()
    else:
        logging.info("Starting minimized in system tray.")

    # Ejecutar el bucle de eventos principal de Qt
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

