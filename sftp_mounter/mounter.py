import os
import sys
import subprocess
import shutil
import logging
import time

logger = logging.getLogger("SFTPMounter.Mounter")

class Mounter:
    """
    Handles checking dependencies (WinFsp), extracting bundled binaries,
    installing WinFsp silently, and managing rclone mount processes.
    """
    def __init__(self):
        # Configuration paths
        if os.name == 'nt':
            self.app_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SFTPMounter')
        else:
            self.app_dir = os.path.join(os.path.expanduser('~'), '.config', 'sftpmounter')

        self.bin_dir = os.path.join(self.app_dir, 'bin')
        os.makedirs(self.bin_dir, exist_ok=True)

        # Paths to binaries
        self.rclone_exe = os.path.join(self.bin_dir, 'rclone.exe' if os.name == 'nt' else 'rclone')
        self.winfsp_msi = os.path.join(self.bin_dir, 'winfsp.msi')

        # Keep track of active mounts: {drive_letter: subprocess.Popen}
        self.active_mounts = {}

        # Extract binaries on initialization
        self.extract_binaries()

    def get_bundled_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except AttributeError:
            base_path = os.path.abspath(os.path.dirname(__file__))
        
        # Look in resources or bin directory
        # Try local bin folder first
        local_path = os.path.join(base_path, 'bin', relative_path)
        if os.path.exists(local_path):
            return local_path
        
        # Fallback to base path directly
        fallback_path = os.path.join(base_path, relative_path)
        if os.path.exists(fallback_path):
            return fallback_path
            
        return None

    def extract_binaries(self):
        """Extracts bundled rclone and WinFsp installer from resource folder to local app bin folder."""
        # 1. Handle rclone
        rclone_name = 'rclone.exe' if os.name == 'nt' else 'rclone'
        bundled_rclone = self.get_bundled_path(rclone_name)
        
        if bundled_rclone and os.path.exists(bundled_rclone):
            try:
                # Copy only if it doesn't exist or size is different
                if not os.path.exists(self.rclone_exe) or os.path.getsize(bundled_rclone) != os.path.getsize(self.rclone_exe):
                    shutil.copy2(bundled_rclone, self.rclone_exe)
                    if os.name != 'nt':
                        os.chmod(self.rclone_exe, 0o755)
                    logger.info(f"Extracted rclone to {self.rclone_exe}")
            except Exception as e:
                logger.error(f"Failed to copy rclone.exe: {e}")
        else:
            # If not bundled, check if it's already in PATH (system-wide rclone)
            system_rclone = shutil.which('rclone')
            if system_rclone:
                self.rclone_exe = system_rclone
                logger.info(f"Using system rclone found at {system_rclone}")
            else:
                logger.warning("rclone binary not found in bundle or system PATH.")

        # 2. Handle WinFsp MSI (only on Windows)
        if os.name == 'nt':
            bundled_msi = self.get_bundled_path('winfsp.msi')
            if bundled_msi and os.path.exists(bundled_msi):
                try:
                    if not os.path.exists(self.winfsp_msi) or os.path.getsize(bundled_msi) != os.path.getsize(self.winfsp_msi):
                        shutil.copy2(bundled_msi, self.winfsp_msi)
                        logger.info(f"Extracted WinFsp MSI to {self.winfsp_msi}")
                except Exception as e:
                    logger.error(f"Failed to copy winfsp.msi: {e}")

    def is_winfsp_installed(self) -> bool:
        """Checks if WinFsp is installed on the system."""
        if os.name != 'nt':
            # On non-Windows, we assume FUSE is installed or mock it
            return True

        # Check typical install directories
        possible_paths = [
            r"C:\Program Files (x86)\WinFsp\bin\launcherd.exe",
            r"C:\Program Files\WinFsp\bin\launcherd.exe"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return True

        # Check Registry
        try:
            import winreg
            # HKEY_LOCAL_MACHINE\SOFTWARE\WinFsp or HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\WinFsp
            keys = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WinFsp"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\WinFsp")
            ]
            for root, key_path in keys:
                try:
                    key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ)
                    val, _ = winreg.QueryValueEx(key, "InstallDir")
                    winreg.CloseKey(key)
                    if val and os.path.exists(os.path.join(val, "bin", "launcherd.exe")):
                        return True
                except OSError:
                    continue
        except Exception as e:
            logger.error(f"Registry check failed: {e}")

        return False

    def install_winfsp(self) -> bool:
        """Runs the WinFsp installer silently."""
        if os.name != 'nt':
            logger.info("Not on Windows, skipping WinFsp installation.")
            return True

        if not os.path.exists(self.winfsp_msi):
            logger.error("WinFsp MSI installer is missing in bin directory.")
            return False

        try:
            # Run msiexec in passive mode (shows progress bar, requests UAC silently)
            cmd = f'msiexec /i "{self.winfsp_msi}" /passive /norestart'
            logger.info(f"Running WinFsp installer: {cmd}")
            
            # Start process and wait
            process = subprocess.Popen(cmd, shell=True)
            process.wait()
            
            if process.returncode in (0, 3010): # 3010 is success but reboot required
                logger.info("WinFsp installed successfully.")
                return True
            else:
                logger.error(f"WinFsp installation failed with code: {process.returncode}")
                return False
        except Exception as e:
            logger.error(f"Error during WinFsp installation: {e}")
            return False

    def obscure_password(self, password: str) -> str:
        """Obscures the password using rclone's built-in obscure function."""
        if not os.path.exists(self.rclone_exe):
            return password
            
        try:
            # Run rclone obscure <password>
            args = [self.rclone_exe, 'obscure', password]
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            res = subprocess.run(args, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            return res.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to obscure password: {e}")
            return password

    def is_drive_letter_in_use(self, drive_letter: str) -> bool:
        """Checks if a Windows drive letter (e.g. 'X:') is already in use."""
        if os.name != 'nt':
            return os.path.exists(drive_letter)
            
        drive_path = f"{drive_letter.upper()}"
        if not drive_path.endswith(':'):
            drive_path += ':'
            
        # 1. Simple path existence check
        if os.path.exists(drive_path + "\\"):
            return True
            
        # 2. Run 'net use'
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run(['net', 'use'], capture_output=True, text=True, startupinfo=startupinfo)
            if drive_path in res.stdout:
                return True
        except Exception:
            pass
            
        return False

    def mount_sftp(self, profile: dict) -> (bool, str):
        """
        Mounts the SFTP server as a network drive using rclone.
        Returns (success, message).
        """
        host = profile.get('host')
        port = profile.get('port', '22')
        user = profile.get('user')
        remote_path = profile.get('remote_path', '')
        drive_letter = profile.get('drive_letter', 'X:')
        auth_type = profile.get('auth_type', 'password')
        
        # Standardize drive letter format (e.g., 'X:')
        if os.name == 'nt':
            if not drive_letter.endswith(':'):
                drive_letter += ':'
            
            if self.is_drive_letter_in_use(drive_letter):
                return False, f"La letra de unidad {drive_letter} ya está en uso."
        else:
            # On Linux, drive_letter acts as a mounting directory path
            os.makedirs(drive_letter, exist_ok=True)

        if not os.path.exists(self.rclone_exe):
            return False, "El ejecutable rclone no está disponible."

        if not self.is_winfsp_installed():
            return False, "WinFsp no está instalado en el sistema."

        # Define remote configuration name
        remote_name = "sftpmount"

        # Prepare Environment variables for Rclone configuration
        env = os.environ.copy()
        env[f"RCLONE_CONFIG_{remote_name.upper()}_TYPE"] = "sftp"
        env[f"RCLONE_CONFIG_{remote_name.upper()}_HOST"] = host
        env[f"RCLONE_CONFIG_{remote_name.upper()}_PORT"] = str(port)
        env[f"RCLONE_CONFIG_{remote_name.upper()}_USER"] = user
        
        # Configure SSH authentication
        if auth_type == 'password':
            raw_password = profile.get('password', '')
            obscured = self.obscure_password(raw_password)
            env[f"RCLONE_CONFIG_{remote_name.upper()}_PASS"] = obscured
        elif auth_type == 'key':
            key_file = profile.get('key_path', '')
            if not os.path.exists(key_file):
                return False, f"El archivo de clave privada no existe: {key_file}"
            env[f"RCLONE_CONFIG_{remote_name.upper()}_KEY_FILE"] = key_file
            
            key_pass = profile.get('key_password', '')
            if key_pass:
                obscured_key_pass = self.obscure_password(key_pass)
                env[f"RCLONE_CONFIG_{remote_name.upper()}_KEY_FILE_PASS"] = obscured_key_pass

        # Prepare Rclone command arguments
        remote_target = f"{remote_name}:{remote_path}"
        
        args = [
            self.rclone_exe, "mount", remote_target, drive_letter,
            "--vfs-cache-mode", "writes",        # Crucial for file editing in Windows Explorer
            "--vfs-cache-max-age", "10s",
            "--volname", f"SFTP {user}@{host}",   # Label in Windows Explorer
            "--network-mode",                    # Displays it as a network drive
        ]

        logger.info(f"Launching rclone mount with command: {' '.join(args)}")

        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            # Run rclone in background
            process = subprocess.Popen(
                args,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )
            
            # Wait briefly to see if it exits immediately
            time.sleep(2.0)
            
            if process.poll() is not None:
                _, stderr = process.communicate()
                error_msg = stderr.strip() if stderr else "Error desconocido al conectar."
                logger.error(f"Rclone mount process failed immediately: {error_msg}")
                return False, f"Error al conectar: {error_msg}"

            # Keep track of the running process
            self.active_mounts[drive_letter] = process
            logger.info(f"Successfully started mount on {drive_letter}")
            return True, f"Unidad montada correctamente en {drive_letter}"

        except Exception as e:
            logger.error(f"Failed to execute rclone mount process: {e}")
            return False, f"Error al iniciar el proceso: {str(e)}"

    def unmount_sftp(self, drive_letter: str) -> bool:
        """
        Unmounts a mapped drive letter and terminates the rclone process.
        """
        if os.name == 'nt' and not drive_letter.endswith(':'):
            drive_letter += ':'

        success = True
        
        # 1. Kill the rclone process if we tracked it
        process = self.active_mounts.get(drive_letter)
        if process:
            try:
                process.terminate()
                process.wait(timeout=3.0)
                logger.info(f"Terminated rclone process for {drive_letter}")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning(f"Killed unresponsive rclone process for {drive_letter}")
            except Exception as e:
                logger.error(f"Error terminating rclone process: {e}")
            finally:
                if drive_letter in self.active_mounts:
                    del self.active_mounts[drive_letter]

        # 2. Run system-level unmount commands
        if os.name == 'nt':
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(['net', 'use', drive_letter, '/delete', '/y'], capture_output=True, startupinfo=startupinfo)
                logger.info(f"Forced cleanup of drive {drive_letter} using net use.")
            except Exception as e:
                logger.error(f"Failed to run net use delete: {e}")
        else:
            try:
                subprocess.run(['fusermount', '-u', drive_letter], capture_output=True)
                if os.path.exists(drive_letter):
                    os.rmdir(drive_letter)
            except Exception as e:
                logger.error(f"Failed to run fusermount: {e}")

        # Check if drive is still active
        if os.name == 'nt':
            is_active = self.is_drive_letter_in_use(drive_letter)
            if is_active:
                logger.warning(f"Drive {drive_letter} still appears active after unmount attempt.")
                success = False
        else:
            success = not os.path.exists(drive_letter)

        return success
