# SFTP Mounter

A simple Qt6 GUI tool to mount SFTP connections as network drives on Windows 11 using Rclone and WinFsp.

## Características

*   **Distribución Todo-en-Uno:** Compila a un único ejecutable `.exe` con todas sus dependencias incluidas.
*   **Autenticación Flexible:** Admite contraseña clásica, llave privada SSH, o llave privada SSH cifrada con frase de paso (passphrase).
*   **Historial de Conexiones:** Guarda múltiples perfiles para cargarlos rápidamente.
*   **Inicio Automático:** Opción de arrancar con Windows en segundo plano.
*   **Minimizado a la Bandeja (Tray):** Oculta la aplicación en la barra de tareas al cerrar o minimizar para mantener el SFTP montado.
*   **Autoconexión:** Opción de conectar perfiles automáticamente al abrir la aplicación.

## Requisitos de Desarrollo

*   Python >= 3.9
*   Poetry (para gestión de dependencias)

## Instalar Dependencias

```bash
poetry install
```

## Ejecutar en Desarrollo

```bash
poetry run sftp-mounter
```

## Compilar como Ejecutable Único (.exe) para Windows

### Opción A: Compilar desde Windows 11 (Recomendado)

Si estás en Windows 11, ejecuta el script de empaquetado automático mediante Poetry:

```bash
poetry run python sftp_mounter/package.py
```

El ejecutable compilado estará disponible en la carpeta raíz en `dist/SFTPMounter.exe`.

### Opción B: Compilar desde Linux (Usando Wine automatizado con PoeThePoet)

Si estás en un sistema Linux, puedes compilar la aplicación utilizando Wine y las tareas automatizadas de **PoeThePoet**:

1. **Asegúrate de tener instalado Wine** en tu sistema Linux (ej: `sudo apt install wine64` en Ubuntu/Debian).
2. **Configurar el entorno Python de Windows en Wine:**
   Ejecuta el siguiente comando para descargar e instalar silenciosamente Python para Windows y todas sus dependencias necesarias dentro de tu prefijo Wine:
   ```bash
   poetry run poe setup-wine-python
   ```
3. **Compilar el archivo ejecutable:**
   Una vez configurado Wine, ejecuta el empaquetado automático:
   ```bash
   poetry run poe build-windows-wine
   ```

El ejecutable generado se guardará directamente en la raíz en `dist/SFTPMounter.exe`.
