# Notas de Configuración y Compilación

Este archivo contiene anotaciones importantes sobre el repositorio y el flujo de empaquetado:

*   **Binarios y Dependencias externas:** Los binarios de terceros (como `rclone.exe` y `winfsp.msi`) **no deben ser incluidos en el repositorio Git**.
*   **Descarga Dinámica:** El script de empaquetado `sftp_mounter/package.py` se encarga de descargar estos binarios de internet en caliente durante el proceso de compilación.
*   **Ignorar en Git:** Las carpetas `sftp_mounter/bin/`, `dist/`, `build/`, `.venv/` y los archivos temporales generados por PyInstaller están excluidos en el archivo `.gitignore` para mantener limpio el repositorio.
