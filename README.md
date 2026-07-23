# SFTP Mounter

A simple Qt6 GUI tool to mount SFTP connections as network drives on Windows 11 using Rclone and WinFsp.

## Características

*   **Distribución Todo-en-Uno:** Compila a un único ejecutable `.exe` con todas sus dependencias incluidas (como el binario portable de `rclone`).
*   **Múltiples Montajes Simultáneos:** Permite mapear y conectar varias unidades SFTP concurrentemente de forma independiente, asociando distintas letras de unidad a cada perfil de conexión.
*   **Detección Robusta de WinFsp:** Comprobación dinámica a través de la API del Registro de Windows (incluyendo las claves `Uninstall` por GUID, servicios del kernel con control de permisos y carpetas del sistema sin depender de `launcherd.exe`), garantizando la detección del driver del sistema de archivos en cualquier configuración de Windows.
*   **Diseño Limpio con Barra de Menús:** Interfaz despejada mediante una barra de menús superior (`QMenuBar`) que agrupa opciones globales:
    - *Opciones:* Activar inicio automático, minimizar a la bandeja, y submenú para cambiar el idioma al vuelo.
    - *Ayuda:* Acceso al diálogo "Acerca de".
*   **Auto-montaje en Cola:** Soporte para auto-conectar múltiples unidades al arranque usando un temporizador asíncrono no bloqueante para mantener la respuesta de la UI.
*   **Acceso Rápido desde la Bandeja:** El menú contextual del icono de la bandeja de sistema lista las unidades montadas activas en tiempo real y permite abrir su ruta en el Explorador de Archivos nativo con un solo clic.
*   **Autenticación Flexible:** Admite contraseña clásica, llave privada SSH, o llave privada SSH cifrada con frase de paso (passphrase).
*   **Historial de Conexiones:** Guarda múltiples perfiles para cargarlos rápidamente.
*   **Inicio Automático:** Opción de arrancar con Windows en segundo plano.
*   **Minimizado a la Bandeja (Tray):** Oculta la aplicación en la barra de tareas al cerrar o minimizar para mantener el SFTP montado.
*   **Instancia Única Protegida:** Implementa un mecanismo de prevención mediante `QLockFile` para evitar la ejecución simultánea de múltiples instancias y sus consecuentes conflictos de bloqueo en archivos de log.
*   **Conexiones No Persistentes (Temporales):** Los montajes son transitorios y no se registran permanentemente en Windows. Si una unidad queda en estado "desconectado" o no es eliminada debido a configuraciones específicas del usuario, desaparecerá automáticamente al reiniciar el sistema.

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

Ejecuta el script de empaquetado automático mediante Poetry en tu sistema Windows:

```bash
poetry run python sftp_mounter/package.py
```

El ejecutable compilado estará disponible en la carpeta raíz en `dist/SFTPMounter-v<version>.exe`.

---

> [!IMPORTANT]
> **Compatibilidad de Sistema**: Esta aplicación ha sido rediseñada para ser **exclusivamente compatible con sistemas operativos Windows** (Windows 10/11). Se ha eliminado el soporte y el código relativo a sistemas Linux/macOS, puesto que las dependencias de montaje (`WinFsp`) y el control del sistema de archivos están orientados al entorno de red de Windows.



# RUTA DE ARCHIVOS EN WINDOWS 11

## Logs
C:\Users\mariano\AppData\Roaming\SFTPMounter\app.log

## Configuración
C:\Users\mariano\AppData\Roaming\SFTPMounter\config.json

## Binarios
C:\Users\mariano\AppData\Roaming\SFTPMounter\bin\rclone.exe
C:\Users\mariano\AppData\Roaming\SFTPMounter\bin\winfsp.msi

## SSH known_hosts
C:\Users\mariano\.ssh\known_hosts

Actualmente no se almacena nada en known_hosts, Rclone no lo hace. Se emula haciendo una conexión a la ip y al puerto con herramientas como putty, ssh ... (PENDIENTE DE DESARROLLO)