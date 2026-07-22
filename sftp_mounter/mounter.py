"""
Controlador de montajes SFTP a través de rclone y FUSE (WinFsp/fusermount).

Este módulo implementa la clase `Mounter`, que actúa como la capa lógica e integradora con
herramientas de bajo nivel del sistema operativo. Su función principal consiste en:
1. Extraer dinámicamente los binarios empaquetados (`rclone` y `winfsp.msi`).
2. Comprobar la existencia del controlador WinFsp en Windows e instalarlo de forma silenciosa/pasiva si es necesario.
3. Obfuscar las contraseñas para cumplir con los requerimientos de configuración de rclone en tiempo de ejecución.
4. Lanzar y supervisar procesos secundarios (`rclone mount`) utilizando variables de entorno temporales para evitar escribir archivos de configuración físicos en el disco del usuario.
5. Controlar de forma limpia el desmontaje y la finalización de los subprocesos.

Para nuevos desarrolladores:
- Esta clase interactúa de forma directa con el sistema de archivos y el sistema de procesos del sistema operativo.
- Para evitar almacenar credenciales en archivos de texto, rclone se configura definiendo variables de entorno dinámicas estructuradas como `RCLONE_CONFIG_<NAME>_<KEY>` en lugar de usar un archivo `rclone.conf`.
- La extracción de binarios maneja el ciclo de vida especial de PyInstaller, resolviendo rutas mediante `sys._MEIPASS`.
"""

import os
import sys
import subprocess
import shutil
import logging
import time

logger = logging.getLogger("SFTPMounter.Mounter")

class Mounter:
    """
    Controla el ciclo de vida de los procesos de rclone, la detección e instalación
    de WinFsp y la administración de unidades locales montadas.
    """
    def __init__(self):
        """
        Inicializa la estructura del mounter y extrae los recursos embebidos.
        """
        # Configurar ruta del directorio de la aplicación (Windows)
        self.app_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SFTPMounter')

        # Directorio local donde se guardarán los binarios rclone y winfsp.msi
        self.bin_dir = os.path.join(self.app_dir, 'bin')
        
        try:
            os.makedirs(self.bin_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create bin dir in AppData, falling back to temp: {e}")
            import tempfile
            self.app_dir = os.path.join(tempfile.gettempdir(), 'SFTPMounter')
            self.bin_dir = os.path.join(self.app_dir, 'bin')
            os.makedirs(self.bin_dir, exist_ok=True)

        self.rclone_exe = os.path.join(self.bin_dir, 'rclone.exe')
        self.winfsp_msi = os.path.join(self.bin_dir, 'winfsp.msi')
        self.known_hosts_file = os.path.expanduser('~/.ssh/known_hosts')

        # Asegurar de manera silenciosa que el directorio .ssh del usuario existe y crear el fichero en blanco
        try:
            ssh_dir = os.path.dirname(self.known_hosts_file)
            os.makedirs(ssh_dir, exist_ok=True)
            if not os.path.exists(self.known_hosts_file):
                with open(self.known_hosts_file, 'w', encoding='utf-8') as f:
                    pass
        except Exception as e:
            logger.warning(f"Failed to create known_hosts file: {e}")






        # Registro en memoria de montajes actualmente activos: {drive_letter: subprocess.Popen}
        # Permite llevar el control del proceso de rclone asociado a cada letra de unidad para poder terminarlo.
        self.active_mounts = {}

        # Extraer los ejecutables embebidos desde el paquete distribuido en el arranque
        self.extract_binaries()

    def get_bundled_path(self, relative_path):
        """
        Resuelve la ruta absoluta de un recurso/archivo embebido.
        
        Soporta tanto la ejecución normal en entorno de desarrollo como el modo empaquetado de PyInstaller.
        Cuando PyInstaller genera un ejecutable único, en tiempo de ejecución extrae todos sus
        recursos en una carpeta temporal del sistema y expone dicha ruta en la variable `sys._MEIPASS`.
        
        Args:
            relative_path (str): Ruta relativa del archivo dentro del paquete.
            
        Returns:
            str | None: Ruta absoluta del archivo si existe, de lo contrario None.
        """
        try:
            # PyInstaller crea una carpeta temporal y define sys._MEIPASS
            base_path = sys._MEIPASS
            # Si está empaquetado, los archivos se encuentran en sys._MEIPASS/bin
            local_path = os.path.join(base_path, 'bin', relative_path)
            if os.path.exists(local_path):
                return local_path
        except AttributeError:
            # Modo desarrollo: buscar en la carpeta 'build/bin' en la raíz del proyecto
            package_dir = os.path.abspath(os.path.dirname(__file__))
            project_root = os.path.dirname(package_dir)
            dev_path = os.path.join(project_root, 'build', 'bin', relative_path)
            if os.path.exists(dev_path):
                return dev_path
            
            # Caer en la carpeta 'bin' interna del paquete si se hubiera copiado ahí previamente
            source_bin_path = os.path.join(package_dir, 'bin', relative_path)
            if os.path.exists(source_bin_path):
                return source_bin_path
            
        return None

    def extract_binaries(self):
        """
        Copia los ejecutables rclone (y winfsp.msi en Windows) desde el bundle
        del programa al directorio de ejecución local del usuario.
        
        Evita copiar si los archivos ya existen y tienen exactamente el mismo tamaño,
        optimizando el tiempo de inicio de la aplicación.
        Si rclone no viene embebido, intentará buscar uno disponible en el PATH del sistema.
        """
        # 1. Procesar rclone
        bundled_rclone = self.get_bundled_path('rclone.exe')
        
        if bundled_rclone and os.path.exists(bundled_rclone):
            try:
                # Copiar si no existe o si difiere en tamaño (ej. tras una actualización de versión)
                if not os.path.exists(self.rclone_exe) or os.path.getsize(bundled_rclone) != os.path.getsize(self.rclone_exe):
                    shutil.copy2(bundled_rclone, self.rclone_exe)
                    logger.info(f"Extracted rclone to {self.rclone_exe}")
            except Exception as e:
                logger.error(f"Failed to copy rclone.exe: {e}")
        else:
            # Si no está en los recursos embebidos, buscar en las rutas del sistema (PATH)
            system_rclone = shutil.which('rclone.exe') or shutil.which('rclone')
            if system_rclone:
                self.rclone_exe = system_rclone
                logger.info(f"Using system rclone found at {system_rclone}")
            else:
                logger.warning("rclone binary not found in bundle or system PATH.")

        # 2. Procesar instalador MSI de WinFsp
        bundled_msi = self.get_bundled_path('winfsp.msi')
        if bundled_msi and os.path.exists(bundled_msi):
            try:
                if not os.path.exists(self.winfsp_msi) or os.path.getsize(bundled_msi) != os.path.getsize(self.winfsp_msi):
                    shutil.copy2(bundled_msi, self.winfsp_msi)
                    logger.info(f"Extracted WinFsp MSI to {self.winfsp_msi}")
            except Exception as e:
                logger.error(f"Failed to copy winfsp.msi: {e}")

    def is_winfsp_installed(self) -> bool:
        """
        Determina si el controlador y API del sistema de archivos WinFsp están instalados en la máquina.
        
        Utiliza varias estrategias independientes de verificación para evitar falsos negativos,
        contemplando instalaciones personalizadas sin servicio launcher (sin launcherd.exe)
        y la redirección WOW64.
        
        Returns:
            bool: True si está instalado, False de lo contrario.
        """

        # Estrategia 1: Inspección del Registro de Windows (InstallDir)
        try:
            import winreg
            keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WinFsp"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\WinFsp")
            ]
            for root, key_path in keys:
                for view_flag in [0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]:
                    try:
                        key = winreg.OpenKey(root, key_path, 0, winreg.KEY_QUERY_VALUE | view_flag)
                        val, _ = winreg.QueryValueEx(key, "InstallDir")
                        winreg.CloseKey(key)
                        if val and os.path.isdir(val):
                            return True
                    except OSError:
                        continue
        except Exception as e:
            logger.error(f"Registry check (InstallDir) failed: {e}")

        # Estrategia 2: Búsqueda dinámica en las claves de desinstalación (por nombre de producto)
        try:
            import winreg
            uninstall_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            for path in uninstall_paths:
                for view_flag in [0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]:
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ | view_flag)
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                i += 1
                                try:
                                    subkey = winreg.OpenKey(key, subkey_name, 0, winreg.KEY_QUERY_VALUE)
                                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                    winreg.CloseKey(subkey)
                                    if display_name and "winfsp" in str(display_name).lower():
                                        winreg.CloseKey(key)
                                        return True
                                except OSError:
                                    continue
                            except OSError:
                                break
                        winreg.CloseKey(key)
                    except OSError:
                        continue
        except Exception as e:
            logger.error(f"Registry check (Uninstall search) failed: {e}")

        # Estrategia 3: Comprobar el servicio de kernel registrado (Services\\winfsp / Services\\WinFsp)
        try:
            import winreg
            services = [
                r"SYSTEM\CurrentControlSet\Services\winfsp",
                r"SYSTEM\CurrentControlSet\Services\WinFsp",
                r"SYSTEM\CurrentControlSet\Services\WinFsp.Launcher"
            ]
            for svc in services:
                for view_flag in [0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]:
                    try:
                        # KEY_QUERY_VALUE requiere menos permisos que KEY_READ
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, svc, 0, winreg.KEY_QUERY_VALUE | view_flag)
                        winreg.CloseKey(key)
                        return True
                    except PermissionError:
                        # Si el acceso es denegado pero la clave existe, asumimos que está instalado
                        return True
                    except OSError:
                        continue
        except Exception as e:
            logger.error(f"Registry check (Services) failed: {e}")

        # Estrategia 4: Directorios por defecto y archivos binarios (DLLs o EXE)
        possible_dirs = [
            r"C:\Program Files (x86)\WinFsp",
            r"C:\Program Files\WinFsp"
        ]
        prog_w6432 = os.environ.get('ProgramW6432')
        if prog_w6432:
            possible_dirs.append(os.path.join(prog_w6432, "WinFsp"))
            
        for d in possible_dirs:
            bin_dir = os.path.join(d, "bin")
            if os.path.isdir(bin_dir):
                files = ["launcherd.exe", "winfsp-x64.dll", "winfsp-x86.dll", "winfsp-a64.dll"]
                if any(os.path.exists(os.path.join(bin_dir, f)) for f in files) or len(os.listdir(bin_dir)) > 0:
                    return True

        # Estrategia 5: Presencia física del driver del kernel (winfsp.sys)
        try:
            sys_root = os.environ.get('SystemRoot', 'C:\\Windows')
            possible_driver_paths = [
                os.path.join(sys_root, 'System32', 'drivers', 'winfsp.sys'),
                os.path.join(sys_root, 'Sysnative', 'drivers', 'winfsp.sys'),
                os.path.join(sys_root, 'System32', 'drivers', 'winfsp-x64.sys'),
                os.path.join(sys_root, 'System32', 'drivers', 'winfsp-x86.sys')
            ]
            for dp in possible_driver_paths:
                if os.path.exists(dp):
                    return True
        except Exception as e:
            logger.error(f"Physical driver file check failed: {e}")

        # Estrategia 6: Buscar en la variable de entorno PATH
        try:
            path_env = os.environ.get('PATH', '')
            for folder in path_env.split(os.path.pathsep):
                if folder and 'winfsp' in folder.lower():
                    files = ["launcherd.exe", "winfsp-x64.dll", "winfsp-x86.dll"]
                    if any(os.path.exists(os.path.join(folder, f)) for f in files):
                        return True
                    parent_dir = os.path.dirname(folder)
                    if any(os.path.exists(os.path.join(parent_dir, 'bin', f)) for f in files):
                        return True
        except Exception as e:
            logger.error(f"PATH environment search failed: {e}")

        return False



    def install_winfsp(self) -> bool:
        """
        Ejecuta el instalador WinFsp (.msi) de forma pasiva y automatizada.
        
        Parámetros msiexec utilizados:
        - /i: Indica instalación.
        - /passive: Modo pasivo, muestra únicamente la barra de progreso sin requerir interacciones.
        - /norestart: Impide el reinicio automático del sistema durante/después de la instalación.
        
        Returns:
            bool: True si la instalación fue exitosa (códigos de retorno 0 o 3010), False en caso contrario.
        """

        if not os.path.exists(self.winfsp_msi):
            logger.error("WinFsp MSI installer is missing in bin directory.")
            return False

        try:
            cmd = f'msiexec /i "{self.winfsp_msi}" /passive /norestart'
            logger.info(f"Running WinFsp installer: {cmd}")
            
            # Lanzar el proceso msiexec y esperar su finalización
            process = subprocess.Popen(cmd, shell=True)
            process.wait()
            
            # Códigos esperados: 0 (Éxito completo), 3010 (Éxito, pero se requiere reiniciar el sistema para aplicar cambios)
            if process.returncode in (0, 3010):
                logger.info("WinFsp installed successfully.")
                return True
            else:
                logger.error(f"WinFsp installation failed with code: {process.returncode}")
                return False
        except Exception as e:
            logger.error(f"Error during WinFsp installation: {e}")
            return False

    def obscure_password(self, password: str) -> str:
        """
        Ofusca una contraseña en texto plano utilizando el algoritmo propio de rclone.
        
        rclone no acepta contraseñas en texto claro dentro de sus variables de entorno o archivos
        de configuración directos por razones de seguridad básica; requiere que estén ofuscadas
        usando su comando interno `obscure`.
        
        Args:
            password (str): Contraseña en texto claro.
            
        Returns:
            str: Contraseña cifrada/ofuscada por rclone.
        """
        if not os.path.exists(self.rclone_exe):
            return password
            
        try:
            # Ejecutar rclone obscure <password>
            args = [self.rclone_exe, 'obscure', password]
            startupinfo = subprocess.STARTUPINFO()
            # Ocultar ventana de consola negra parpadeante en Windows
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            res = subprocess.run(args, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            return res.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to obscure password: {e}")
            return password

    def is_drive_letter_in_use(self, drive_letter: str) -> bool:
        """
        Valida si una letra de unidad en Windows (ej. 'Z:') ya está ocupada.
        
        Realiza una doble comprobación:
        1. Evaluar si la ruta física del volumen ("Z:\\") existe.
        2. Ejecutar la utilidad de red nativa 'net use' y buscar la letra en sus registros.
        
        Args:
            drive_letter (str): Letra de volumen a verificar en Windows.
            
        Returns:
            bool: True si la letra está actualmente reservada u ocupada, False en caso contrario.
        """
        drive_path = f"{drive_letter.upper()}"
        if not drive_path.endswith(':'):
            drive_path += ':'
            
        # Comprobación básica de existencia
        if os.path.exists(drive_path + "\\"):
            return True
            
        # Comprobación de unidades de red lógicas activas
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run(['net', 'use'], capture_output=True, text=True, startupinfo=startupinfo)
            if drive_path in res.stdout:
                return True
        except Exception:
            pass
            
        return False

    def mount_sftp(self, profile: dict, accept_host_key: bool = False) -> (bool, str):
        """
        Monta un servidor SFTP remoto como si fuese un volumen local.
        
        Utiliza el binario de rclone con el comando `mount`. Para evitar archivos de configuración,
        pasa los parámetros de conexión dinámicamente mediante variables de entorno
        generadas en tiempo de ejecución.
        """
        host = profile.get('host')
        port = profile.get('port', '22')
        user = profile.get('user')
        remote_path = profile.get('remote_path', '')
        drive_letter = profile.get('drive_letter', 'X:')
        auth_type = profile.get('auth_type', 'password')
        
        # Validar y normalizar formato de unidad de destino (Windows-only)
        if not drive_letter.endswith(':'):
            drive_letter += ':'
        
        if self.is_drive_letter_in_use(drive_letter):
            return False, f"La letra de unidad {drive_letter} ya está en uso."

        if not os.path.exists(self.rclone_exe):
            return False, "El ejecutable rclone no está disponible."

        if not self.is_winfsp_installed():
            logger.warning("WinFsp no se detecta en el sistema. Se continuará con el intento de montaje.")

        # Identificador del remoto dinámico
        remote_name = "sftpmount"

        # Generar las variables de entorno de rclone al vuelo para evitar crear el archivo config en disco
        env = os.environ.copy()
        env[f"RCLONE_CONFIG_{remote_name.upper()}_TYPE"] = "sftp"
        env[f"RCLONE_CONFIG_{remote_name.upper()}_HOST"] = host
        env[f"RCLONE_CONFIG_{remote_name.upper()}_PORT"] = str(port)
        env[f"RCLONE_CONFIG_{remote_name.upper()}_USER"] = user
        if not accept_host_key:
            env[f"RCLONE_CONFIG_{remote_name.upper()}_KNOWN_HOSTS_FILE"] = self.known_hosts_file
            env["RCLONE_SFTP_KNOWN_HOSTS_FILE"] = self.known_hosts_file



        
        # Procesar tipo de autenticación
        if auth_type == 'password':
            raw_password = profile.get('password', '')
            obscured = self.obscure_password(raw_password)
            env[f"RCLONE_CONFIG_{remote_name.upper()}_PASS"] = obscured
        elif auth_type == 'key':
            key_file = profile.get('key_path', '')
            if not os.path.exists(key_file):
                return False, f"El archivo de clave privada no existe: {key_file}"
            env[f"RCLONE_CONFIG_{remote_name.upper()}_KEY_FILE"] = key_file
            
            # Procesar frase de paso asociada a la clave privada si existe
            key_pass = profile.get('key_password', '')
            if key_pass:
                obscured_key_pass = self.obscure_password(key_pass)
                env[f"RCLONE_CONFIG_{remote_name.upper()}_KEY_FILE_PASS"] = obscured_key_pass

        # Estructurar destino del comando: remoto:ruta_remota
        remote_target = f"{remote_name}:{remote_path}"
        
        profile_name = profile.get('profile_name', 'SFTP')
        path_suffix = f" ({remote_path})" if remote_path else ""
        volname = f"{profile_name} {user}@{host} {port}{path_suffix}"
        # Sanear el nombre de volumen para evitar caracteres no permitidos en Windows (como dos puntos, barras, etc.)
        for char in [':', '\\', '/', '*', '?', '"', '<', '>', '|']:
            volname = volname.replace(char, '_')

        args = [
            self.rclone_exe, "mount", remote_target, drive_letter,
            "--vfs-cache-mode", "writes",
            "--vfs-cache-max-age", "10s",
            "--volname", volname,
            "--network-mode",
        ]


        logger.info(f"Launching rclone mount with command: {' '.join(args)}")

        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            # Ejecutar rclone en segundo plano de manera asíncrona
            process = subprocess.Popen(
                args,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )

            
            # Validar que el montaje se ha realizado de manera efectiva
            mounted = False
            error_msg = "El montaje no pudo ser verificado o expiró el tiempo de espera."
            
            # Realizamos polling por un máximo de 30 segundos (60 iteraciones de 0.5s)
            for _ in range(60):

                if process.poll() is not None:
                    # El proceso ha terminado con error; leemos la salida de error y stdout
                    stdout, stderr = process.communicate()
                    out_str = stdout.strip() if stdout else ""
                    err_str = stderr.strip() if stderr else ""
                    error_msg = err_str or out_str or "El proceso de rclone finalizó inesperadamente."
                    break
                
                if self.is_actually_mounted(drive_letter):
                    mounted = True
                    break
                
                time.sleep(0.5)
            
            if not mounted:
                # Intentar limpiar/terminar el proceso si sigue vivo
                if process.poll() is None:
                    process.terminate()
                    try:
                        stdout, stderr = process.communicate(timeout=2.0)
                        out_str = stdout.strip() if stdout else ""
                        err_str = stderr.strip() if stderr else ""
                        if err_str or out_str:
                            error_msg = err_str or out_str
                    except Exception:
                        process.kill()
                        try:
                            stdout, stderr = process.communicate(timeout=1.0)
                            out_str = stdout.strip() if stdout else ""
                            err_str = stderr.strip() if stderr else ""
                            if err_str or out_str:
                                error_msg = err_str or out_str
                        except Exception:
                            pass
                else:
                    stdout, stderr = process.communicate()
                    out_str = stdout.strip() if stdout else ""
                    err_str = stderr.strip() if stderr else ""
                    if err_str or out_str:
                        error_msg = err_str or out_str
                logger.error(f"Rclone mount validation failed for {drive_letter}: {error_msg}")
                return False, f"Error al conectar: {error_msg}"

            # Registrar el subproceso activo referenciado por su letra de unidad
            self.active_mounts[drive_letter] = process
            logger.info(f"Successfully started and validated mount on {drive_letter}")
            return True, f"Unidad montada correctamente en {drive_letter}"

        except Exception as e:
            logger.error(f"Failed to execute rclone mount process: {e}")
            return False, f"Error al iniciar el proceso: {str(e)}"

    def unmount_sftp(self, drive_letter: str) -> bool:
        """
        Desmonta de forma limpia una unidad SFTP previamente mapeada.
        
        1. Termina el proceso secundario rclone de forma amigable (terminate) y luego forzada (kill) si no responde.
        2. Ejecuta comandos de limpieza a nivel del OS para limpiar la letra de unidad asignada.
           - Windows: 'net use <letra> /delete /y'
           - Linux: 'fusermount -u <ruta>'
           
        Args:
            drive_letter (str): Letra de unidad (Z:) o ruta de montaje a limpiar.
            
        Returns:
            bool: True si el desmontaje se completó con éxito y el recurso ya no está activo, False de lo contrario.
        """
        if not drive_letter.endswith(':'):
            drive_letter += ':'

        success = True
        
        # 1. Cerrar el proceso rclone correspondiente
        process = self.active_mounts.get(drive_letter)
        if process:
            try:
                process.terminate()
                process.wait(timeout=3.0)  # Esperar un tiempo razonable para que se apague
                logger.info(f"Terminated rclone process for {drive_letter}")
            except subprocess.TimeoutExpired:
                process.kill()  # Forzar cierre si no responde
                logger.warning(f"Killed unresponsive rclone process for {drive_letter}")
            except Exception as e:
                logger.error(f"Error terminating rclone process: {e}")
            finally:
                if drive_letter in self.active_mounts:
                    del self.active_mounts[drive_letter]

        # 2. Ejecutar comandos de limpieza nativos (Windows-only)
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # net use fuerza la desconexión a nivel de sistema por si queda algún rastro
            subprocess.run(['net', 'use', drive_letter, '/delete', '/y'], capture_output=True, startupinfo=startupinfo)
            logger.info(f"Forced cleanup of drive {drive_letter} using net use.")
        except Exception as e:
            logger.error(f"Failed to run net use delete: {e}")

        # Comprobar el estado final del volumen
        is_active = self.is_drive_letter_in_use(drive_letter)
        if is_active:
            logger.warning(f"Drive {drive_letter} still appears active after unmount attempt.")
            success = False

        return success

    def get_rclone_version(self) -> str:
        """
        Ejecuta el comando version de rclone para detectar la versión actual instalada.
        
        Returns:
            str: Versión detectada (ej. "v1.66.0") o mensaje de no detectado.
        """
        if not os.path.exists(self.rclone_exe):
            return "No detectado"
            
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            res = subprocess.run([self.rclone_exe, 'version'], capture_output=True, text=True, startupinfo=startupinfo)
            lines = res.stdout.splitlines()
            if lines:
                # La primera línea suele ser algo como "rclone v1.66.0"
                parts = lines[0].split()
                if len(parts) >= 2:
                    return parts[1]
                return lines[0]
        except Exception as e:
            logger.error(f"Error querying rclone version: {e}")
            
        return "Desconocido"

    def get_winfsp_version(self) -> str:
        """
        Detecta la versión de WinFsp instalada consultando el Registro de Windows.
        
        Returns:
            str: Versión de WinFsp detectada (ej. "2.0.23075"), o "No instalado".
        """
        if not self.is_winfsp_installed():
            return "No instalado"
            
        try:
            import winreg
            uninstall_paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
            ]
            for path in uninstall_paths:
                for view_flag in [0, winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY]:
                    try:
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ | view_flag)
                        i = 0
                        while True:
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                i += 1
                                try:
                                    subkey = winreg.OpenKey(key, subkey_name, 0, winreg.KEY_QUERY_VALUE)
                                    display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                    if display_name and "winfsp" in str(display_name).lower():
                                        display_version, _ = winreg.QueryValueEx(subkey, "DisplayVersion")
                                        winreg.CloseKey(subkey)
                                        winreg.CloseKey(key)
                                        return str(display_version) if display_version else "Detectado (Versión desconocida)"
                                    winreg.CloseKey(subkey)
                                except OSError:
                                    continue
                            except OSError:
                                break
                        winreg.CloseKey(key)
                    except OSError:
                        continue
        except Exception as e:
            logger.error(f"Error querying WinFsp version: {e}")
            
        return "Detectado (Versión desconocida)"

    def is_actually_mounted(self, drive_letter: str) -> bool:
        """
        Verifica si la unidad está montada de forma efectiva y accesible.
        
        Args:
            drive_letter (str): Letra de unidad (ej: Z:).
            
        Returns:
            bool: True si la unidad está efectivamente montada y es accesible.
        """
        drive_path = drive_letter.upper()
        if not drive_path.endswith('\\'):
            drive_path += '\\'
        try:
            # Comprobar si existe la unidad y si podemos listar/leer
            if os.path.exists(drive_path):
                os.listdir(drive_path)
                return True
        except Exception:
            pass
        return False

    def add_to_known_hosts(self, host: str, port: int) -> bool:
        """
        Intenta recuperar y añadir la clave de host al archivo known_hosts estándar utilizando ssh-keyscan.
        """
        try:
            # Asegurar la existencia del directorio padre
            os.makedirs(os.path.dirname(self.known_hosts_file), exist_ok=True)
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            cmd = ["ssh-keyscan", "-p", str(port), host]
            logger.info(f"Running command: {' '.join(cmd)}")
            
            res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            if res.returncode == 0 and res.stdout.strip():
                # Escribir la clave al archivo known_hosts
                with open(self.known_hosts_file, 'a', encoding='utf-8') as f:
                    f.write(res.stdout)
                logger.info(f"Added host key for {host}:{port} to known_hosts: {self.known_hosts_file}")
                return True
            else:
                logger.warning(f"ssh-keyscan failed or returned empty output: {res.stderr}")
        except Exception as e:
            logger.error(f"Failed to add to known_hosts: {e}")
        return False





