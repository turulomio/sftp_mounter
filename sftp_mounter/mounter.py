"""
SFTP mounting controller via rclone and FUSE (WinFsp/fusermount).

This module implements the `Mounter` class, which acts as the logical and integration layer with
low-level operating system tools. Its main function consists of:
1. Dynamically extracting packaged binaries (`rclone.exe` and `winfsp.msi`).
2. Checking the existence of the WinFsp driver in Windows and installing it silently/passively if necessary.
3. Obfuscating passwords to meet rclone configuration requirements at runtime.
4. Launching and supervising background processes (`rclone mount`) using temporary environment variables to avoid writing physical config files on the user's disk.
5. Cleanly controlling unmounting and termination of subprocesses.

For new developers:
- This class interacts directly with the operating system's file system and process manager.
- To avoid storing credentials in plaintext files, rclone is configured by defining dynamic environment variables structured as `RCLONE_CONFIG_<NAME>_<KEY>` instead of using an `rclone.conf` file.
- Binary extraction handles the special PyInstaller life cycle, resolving paths via `sys._MEIPASS`.
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
    Controls the life cycle of rclone processes, detection and installation
    of WinFsp, and administration of mounted local drives.
    """
    def __init__(self):
        """
        Initializes the mounter structure and extracts embedded resources.
        """
        # Configure application directory path (Windows)
        self.app_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SFTPMounter')

        # Local directory where rclone and winfsp.msi binaries will be stored
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

        # Silently ensure that the user's .ssh directory exists and create a blank file if it does not
        try:
            ssh_dir = os.path.dirname(self.known_hosts_file)
            os.makedirs(ssh_dir, exist_ok=True)
            if not os.path.exists(self.known_hosts_file):
                with open(self.known_hosts_file, 'w', encoding='utf-8') as f:
                    pass
        except Exception as e:
            logger.warning(f"Failed to create known_hosts file: {e}")

        # In-memory register of currently active mounts: {drive_letter: subprocess.Popen}
        # Allows keeping track of the rclone process associated with each drive letter to terminate it.
        self.active_mounts = {}

        # Extract embedded executables from the distributed package at startup
        self.extract_binaries()

    def get_bundled_path(self, relative_path):
        """
        Resolves the absolute path of an embedded resource/file.
        
        Supports both normal execution in a development environment and PyInstaller packaged mode.
        When PyInstaller generates a single executable, it extracts all resources
        to a temporary folder in the system at runtime and exposes this path in the `sys._MEIPASS` variable.
        
        Args:
            relative_path (str): Relative path of the file within the package.
            
        Returns:
            str | None: Absolute path of the file if it exists, otherwise None.
        """
        try:
            # PyInstaller creates a temporary folder and defines sys._MEIPASS
            base_path = sys._MEIPASS
            # If packaged, the files are located in sys._MEIPASS/bin
            local_path = os.path.join(base_path, 'bin', relative_path)
            if os.path.exists(local_path):
                return local_path
        except AttributeError:
            # Development mode: search in the 'build/bin' folder at the project root
            package_dir = os.path.abspath(os.path.dirname(__file__))
            project_root = os.path.dirname(package_dir)
            dev_path = os.path.join(project_root, 'build', 'bin', relative_path)
            if os.path.exists(dev_path):
                return dev_path
            
            # Fallback to the internal 'bin' folder of the package if copied there previously
            source_bin_path = os.path.join(package_dir, 'bin', relative_path)
            if os.path.exists(source_bin_path):
                return source_bin_path
            
        return None

    def extract_binaries(self):
        """
        Copies rclone executables (and winfsp.msi) from the program bundle
        to the user's local execution directory.
        
        Avoids copying if the files already exist and have exactly the same size,
        optimizing the application startup time.
        If rclone is not embedded, it will attempt to find one available in the system PATH.
        """
        # 1. Process rclone
        bundled_rclone = self.get_bundled_path('rclone.exe')
        
        if bundled_rclone and os.path.exists(bundled_rclone):
            try:
                # Copy if it does not exist or if it differs in size (e.g. after a version update)
                if not os.path.exists(self.rclone_exe) or os.path.getsize(bundled_rclone) != os.path.getsize(self.rclone_exe):
                    shutil.copy2(bundled_rclone, self.rclone_exe)
                    logger.info(f"Extracted rclone to {self.rclone_exe}")
            except Exception as e:
                logger.error(f"Failed to copy rclone.exe: {e}")
        else:
            # If not in embedded resources, search in system paths (PATH)
            system_rclone = shutil.which('rclone.exe') or shutil.which('rclone')
            if system_rclone:
                self.rclone_exe = system_rclone
                logger.info(f"Using system rclone found at {system_rclone}")
            else:
                logger.warning("rclone binary not found in bundle or system PATH.")

        # 2. Process WinFsp MSI installer
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
        Determines whether the WinFsp driver and system API are installed on the machine.
        
        Uses several independent verification strategies to avoid false negatives,
        accounting for custom installations without launcher service (no launcherd.exe)
        and WOW64 redirection.
        
        Returns:
            bool: True if installed, False otherwise.
        """
        # Strategy 1: Windows Registry Inspection (InstallDir)
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

        # Strategy 2: Dynamic search in uninstall keys (by product name)
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

        # Strategy 3: Check registered kernel service (Services\\winfsp / Services\\WinFsp)
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
                        # KEY_QUERY_VALUE requires fewer permissions than KEY_READ
                        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, svc, 0, winreg.KEY_QUERY_VALUE | view_flag)
                        winreg.CloseKey(key)
                        return True
                    except PermissionError:
                        # If access is denied but key exists, assume it is installed
                        return True
                    except OSError:
                        continue
        except Exception as e:
            logger.error(f"Registry check (Services) failed: {e}")

        # Strategy 4: Default directories and binary files (DLLs or EXEs)
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

        # Strategy 5: Physical presence of kernel driver (winfsp.sys)
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

        # Strategy 6: Look in the PATH environment variable
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
        Executes the WinFsp (.msi) installer passively and automatically.
        
        msiexec parameters used:
        - /i: Indicates installation.
        - /passive: Passive mode, shows only the progress bar without requiring interaction.
        - /norestart: Prevents automatic system restart during/after installation.
        
        Returns:
            bool: True if installation was successful (return codes 0 or 3010), False otherwise.
        """
        if not os.path.exists(self.winfsp_msi):
            logger.error("WinFsp MSI installer is missing in bin directory.")
            return False

        try:
            cmd = f'msiexec /i "{self.winfsp_msi}" /passive /norestart'
            logger.info(f"Running WinFsp installer: {cmd}")
            
            # Launch msiexec process and wait for completion
            process = subprocess.Popen(cmd, shell=True)
            process.wait()
            
            # Expected codes: 0 (Success), 3010 (Success, but system restart required to apply changes)
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
        Obfuscates a plaintext password using rclone's own algorithm.
        
        rclone does not accept plaintext passwords within its environment variables or direct
        config files for basic security reasons; it requires them to be obfuscated
        using its internal `obscure` command.
        
        Args:
            password (str): Plaintext password.
            
        Returns:
            str: Password encrypted/obfuscated by rclone.
        """
        if not os.path.exists(self.rclone_exe):
            return password
            
        try:
            # Execute rclone obscure <password>
            args = [self.rclone_exe, 'obscure', password]
            startupinfo = subprocess.STARTUPINFO()
            # Hide black console window flashing on Windows
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            res = subprocess.run(args, capture_output=True, text=True, check=True, startupinfo=startupinfo)
            return res.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to obscure password: {e}")
            return password

    def is_drive_letter_in_use(self, drive_letter: str) -> bool:
        """
        Validates if a drive letter in Windows (e.g. 'Z:') is already occupied.
        
        Performs a double check:
        1. Evaluate if the physical volume path ("Z:\\") exists.
        2. Run the native 'net use' network utility and search for the letter in its records.
        
        Args:
            drive_letter (str): Volume letter to verify in Windows.
            
        Returns:
            bool: True if the letter is currently reserved or occupied, False otherwise.
        """
        drive_path = f"{drive_letter.upper()}"
        if not drive_path.endswith(':'):
            drive_path += ':'
            
        # Basic existence check
        if os.path.exists(drive_path + "\\"):
            return True
            
        # Check active logical network drives
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
        Mounts a remote SFTP server as if it were a local volume.
        
        Uses the rclone binary with the `mount` command. To avoid configuration files,
        passes connection parameters dynamically via environment variables
        generated at runtime.
        """
        host = profile.get('host')
        port = profile.get('port', '22')
        user = profile.get('user')
        remote_path = profile.get('remote_path', '')
        drive_letter = profile.get('drive_letter', 'X:')
        auth_type = profile.get('auth_type', 'password')
        
        # Validate and normalize target drive format (Windows-only)
        if not drive_letter.endswith(':'):
            drive_letter += ':'
        
        if self.is_drive_letter_in_use(drive_letter):
            return False, f"The drive letter {drive_letter} is already in use."

        if not os.path.exists(self.rclone_exe):
            return False, "The rclone executable is not available."

        if not self.is_winfsp_installed():
            logger.warning("WinFsp is not detected on the system. Proceeding with mount attempt.")

        # Dynamic remote identifier
        remote_name = "sftpmount"

        # Generate rclone environment variables on the fly to avoid creating config files on disk
        env = os.environ.copy()
        env[f"RCLONE_CONFIG_{remote_name.upper()}_TYPE"] = "sftp"
        env[f"RCLONE_CONFIG_{remote_name.upper()}_HOST"] = host
        env[f"RCLONE_CONFIG_{remote_name.upper()}_PORT"] = str(port)
        env[f"RCLONE_CONFIG_{remote_name.upper()}_USER"] = user
        if not accept_host_key:
            env[f"RCLONE_CONFIG_{remote_name.upper()}_KNOWN_HOSTS_FILE"] = self.known_hosts_file
            env["RCLONE_SFTP_KNOWN_HOSTS_FILE"] = self.known_hosts_file

        # Process authentication type
        if auth_type == 'password':
            raw_password = profile.get('password', '')
            obscured = self.obscure_password(raw_password)
            env[f"RCLONE_CONFIG_{remote_name.upper()}_PASS"] = obscured
        elif auth_type == 'key':
            key_file = profile.get('key_path', '')
            if not os.path.exists(key_file):
                return False, f"Private key file does not exist: {key_file}"
            env[f"RCLONE_CONFIG_{remote_name.upper()}_KEY_FILE"] = key_file
            
            # Process passphrase associated with the private key if it exists
            key_pass = profile.get('key_password', '')
            if key_pass:
                obscured_key_pass = self.obscure_password(key_pass)
                env[f"RCLONE_CONFIG_{remote_name.upper()}_KEY_FILE_PASS"] = obscured_key_pass

        # Structure command target: remote:remote_path
        remote_target = f"{remote_name}:{remote_path}"
        
        profile_name = profile.get('profile_name', 'SFTP')
        
        from sftp_mounter.config_manager import ConfigManager
        config_mgr = ConfigManager()
        settings = config_mgr.load_settings()
        conn_in_volname = settings.get('conn_in_volname', False)
        
        if conn_in_volname:
            path_suffix = f" ({remote_path})" if remote_path else ""
            volname = f"{profile_name} {user}@{host}!{port}{path_suffix}"
        else:
            volname = profile_name
            
        # Sanitize volume name to avoid characters not allowed in Windows (such as colons, slashes, etc.)
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
                
            # Execute rclone in the background asynchronously
            process = subprocess.Popen(
                args,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                startupinfo=startupinfo
            )

            # Validate that the mounting was done effectively
            mounted = False
            error_msg = "Mount verification failed or timed out."
            
            # Perform polling for a maximum of 30 seconds (60 iterations of 0.5s)
            for _ in range(60):
                if process.poll() is not None:
                    # Process terminated with error; read stdout and stderr
                    stdout, stderr = process.communicate()
                    out_str = stdout.strip() if stdout else ""
                    err_str = stderr.strip() if stderr else ""
                    error_msg = err_str or out_str or "rclone process terminated unexpectedly."
                    break
                
                if self.is_actually_mounted(drive_letter):
                    mounted = True
                    break
                
                time.sleep(0.5)
            
            if not mounted:
                # Try to clean up/terminate process if still alive
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
                return False, f"Connection error: {error_msg}"

            # Register the active subprocess referenced by its drive letter
            self.active_mounts[drive_letter] = process
            logger.info(f"Successfully started and validated mount on {drive_letter}")
            return True, f"Drive mounted successfully on {drive_letter}"

        except Exception as e:
            logger.error(f"Failed to execute rclone mount process: {e}")
            return False, f"Failed to start process: {str(e)}"

    def _kill_rclone_for_drive(self, drive_letter: str):
        """
        Forcefully terminates any running rclone.exe processes associated with a specific drive letter.
        """
        drive = drive_letter.upper()
        if not drive.endswith(':'):
            drive += ':'
            
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # Target the specific drive letter using PowerShell
            cmd = [
                "powershell", "-NoProfile", "-Command",
                f"Get-CimInstance Win32_Process -Filter \"Name = 'rclone.exe'\" | Where-Object {{ $_.CommandLine -like '*{drive}*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"
            ]
            subprocess.run(cmd, capture_output=True, startupinfo=startupinfo, timeout=5.0)
            logger.info(f"Killed orphaned rclone processes for drive {drive} using PowerShell.")
        except Exception as e:
            logger.warning(f"PowerShell process cleanup failed: {e}")
            
            # Fallback to wmic-based query if PowerShell failed
            try:
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                cmd = ["wmic", "process", "where", "name='rclone.exe'", "get", "CommandLine,ProcessId"]
                res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo, timeout=5.0)
                for line in res.stdout.splitlines():
                    if drive in line:
                        parts = line.strip().split()
                        if parts:
                            pid = parts[-1]
                            if pid.isdigit():
                                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True, startupinfo=startupinfo)
                                logger.info(f"Killed process {pid} using taskkill.")
            except Exception as ex:
                logger.error(f"Fallback process cleanup failed: {ex}")

    def unmount_sftp(self, drive_letter: str) -> bool:
        """
        Cleanly unmounts a previously mapped SFTP drive.
        
        1. Terminates the secondary rclone process friendly (terminate) and then forced (kill) if unresponsive.
        2. Forcefully kills any orphaned/remaining rclone processes for this drive letter.
        3. Executes cleanup commands at OS level to free the assigned drive letter.
           - Windows: 'net use <letter> /delete /y'
           
        Args:
            drive_letter (str): Drive letter (Z:) to clean up.
            
        Returns:
            bool: True if unmounting completed successfully and resource is no longer active, False otherwise.
        """
        if not drive_letter.endswith(':'):
            drive_letter += ':'

        success = True
        
        # 1. Close the corresponding rclone process
        process = self.active_mounts.get(drive_letter)
        if process:
            try:
                process.terminate()
                process.wait(timeout=3.0)  # Wait a reasonable time to shutdown
                logger.info(f"Terminated rclone process for {drive_letter}")
            except subprocess.TimeoutExpired:
                process.kill()  # Force closure if unresponsive
                logger.warning(f"Killed unresponsive rclone process for {drive_letter}")
            except Exception as e:
                logger.error(f"Error terminating rclone process: {e}")
            finally:
                if drive_letter in self.active_mounts:
                    del self.active_mounts[drive_letter]

        # 2. Always kill any other/orphaned rclone processes associated with this drive letter
        self._kill_rclone_for_drive(drive_letter)

        # 3. Run native cleanup commands (Windows-only)
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # net use forces system-level disconnection in case any traces remain
            subprocess.run(['net', 'use', drive_letter, '/delete', '/y'], capture_output=True, startupinfo=startupinfo)
            logger.info(f"Forced cleanup of drive {drive_letter} using net use.")
        except Exception as e:
            logger.error(f"Failed to run net use delete: {e}")

        # Check final volume state
        is_active = self.is_drive_letter_in_use(drive_letter)
        if is_active:
            logger.warning(f"Drive {drive_letter} still appears active after unmount attempt.")
            success = False

        return success

    def get_rclone_version(self) -> str:
        """
        Executes rclone version command to detect the current installed version.
        
        Returns:
            str: Detected version (e.g. "v1.66.0") or not detected message.
        """
        if not os.path.exists(self.rclone_exe):
            return "Not detected"
            
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            res = subprocess.run([self.rclone_exe, 'version'], capture_output=True, text=True, startupinfo=startupinfo)
            lines = res.stdout.splitlines()
            if lines:
                # First line is usually something like "rclone v1.66.0"
                parts = lines[0].split()
                if len(parts) >= 2:
                    return parts[1]
                return lines[0]
        except Exception as e:
            logger.error(f"Error querying rclone version: {e}")
            
        return "Unknown"

    def get_winfsp_version(self) -> str:
        """
        Detects installed WinFsp version by querying the Windows Registry.
        
        Returns:
            str: Detected WinFsp version (e.g. "2.0.23075"), or "Not installed".
        """
        if not self.is_winfsp_installed():
            return "Not installed"
            
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
                                        return str(display_version) if display_version else "Detected (Unknown version)"
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
            
        return "Detected (Unknown version)"

    def is_actually_mounted(self, drive_letter: str) -> bool:
        """
        Verifies if the drive is effectively mounted and accessible.
        
        Args:
            drive_letter (str): Drive letter (e.g. Z:).
            
        Returns:
            bool: True if the drive is effectively mounted and accessible.
        """
        drive_path = drive_letter.upper()
        if not drive_path.endswith('\\'):
            drive_path += '\\'
        try:
            # Check if drive path exists and we can list files
            if os.path.exists(drive_path):
                os.listdir(drive_path)
                return True
        except Exception:
            pass
        return False

    def add_to_known_hosts(self, host: str, port: int) -> bool:
        """
        Attempts to retrieve and add the host key to the standard known_hosts file using ssh-keyscan.
        """
        try:
            # Ensure the existence of the parent directory
            os.makedirs(os.path.dirname(self.known_hosts_file), exist_ok=True)
            
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            cmd = ["ssh-keyscan", "-p", str(port), host]
            logger.info(f"Running command: {' '.join(cmd)}")
            
            res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=startupinfo)
            if res.returncode == 0 and res.stdout.strip():
                # Write key to known_hosts file
                with open(self.known_hosts_file, 'a', encoding='utf-8') as f:
                    f.write(res.stdout)
                logger.info(f"Added host key for {host}:{port} to known_hosts: {self.known_hosts_file}")
                return True
            else:
                logger.warning(f"ssh-keyscan failed or returned empty output: {res.stderr}")
        except Exception as e:
            logger.error(f"Failed to add to known_hosts: {e}")
        return False
