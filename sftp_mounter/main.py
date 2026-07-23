"""
Main entry point of the SFTP Mounter application.

This module is responsible for:
1. Setting up and adjusting `sys.path` to ensure correct local module resolution.
2. Initializing the logging system in OS-dependent paths.
3. Configuring global environment variables and styles for the PySide6 GUI (High DPI, Fusion style).
4. Instantiating the Qt application, checking command line arguments (e.g. starting minimized), and starting the event loop.

For new developers:
- The flow starts in the `if __name__ == '__main__':` block by calling `main()`.
- If the executable starts with the `--minimized` argument, the process runs directly in the system tray without showing the main window immediately.
"""

import sys
import os
import logging

# ==============================================================================
# RESOLUTION OF LOCAL PATHS AND IMPORTS
# ==============================================================================
# When running the application as a packaged binary (with PyInstaller) or
# directly from the console in development mode, it is essential to adjust
# Python's search paths to avoid module import errors.
package_dir = os.path.dirname(os.path.abspath(__file__))  # 'sftp_mounter' directory
parent_dir = os.path.dirname(package_dir)                 # Project root directory
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

from PySide6.QtWidgets import QApplication
from sftp_mounter.gui import MainWindow

def setup_logging():
    """
    Configures the logging system globally in the application.
    
    Generates an 'app.log' file in a persistent location of the user's machine:
    - Windows: %APPDATA%/SFTPMounter/app.log
    
    The log writes simultaneously to both the text file in UTF-8 format and
    standard output (sys.stdout) to facilitate debugging in development mode.
    """
    # Determine the log directory (Windows)
    log_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SFTPMounter')
    
    # Try to guarantee the physical existence of the directory path
    try:
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        sys.stderr.write(f"Warning: Could not create AppData log directory, falling back to temp: {e}\n")
        import tempfile
        log_dir = os.path.join(tempfile.gettempdir(), 'SFTPMounter')
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            pass
        
    # Delete old logs before initializing the logging configuration
    try:
        if os.path.exists(log_dir):
            for filename in os.listdir(log_dir):
                if filename.startswith('app.log'):
                    file_path = os.path.join(log_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
    except Exception as e:
        sys.stderr.write(f"Warning: Could not delete old log files: {e}\n")

    log_file = os.path.join(log_dir, 'app.log')

    # Basic logging configuration
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        handlers = [file_handler, logging.StreamHandler(sys.stdout)]
    except Exception as e:
        sys.stderr.write(f"Warning: Could not create log file handler (perhaps locked or read-only): {e}\n")
        handlers = [logging.StreamHandler(sys.stdout)]

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=handlers
    )
    logging.info("Application started.")

def main():
    """
    Initializes the environment, prepares the main PySide6 window, and starts the Qt event loop.
    """
    # Enable automatic screen scaling (High DPI).
    # This is extremely important on modern systems (Windows 11, 4K screens)
    # so that the user interface does not look blurry or excessively small.
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("SFTP Drive Mounter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("SFTP_Mounter")
    app.setOrganizationDomain("SFTP_Mounter")

    # Check if another instance of the application is already running using QLockFile
    from PySide6.QtCore import QLockFile, QDir
    from PySide6.QtWidgets import QMessageBox
    
    lock_file_path = os.path.join(QDir.tempPath(), "sftp_mounter_single_instance.lock")
    app.lock_file = QLockFile(lock_file_path)
    
    if not app.lock_file.tryLock(0):
        QMessageBox.warning(
            None,
            "SFTP Mounter",
            "Another instance of SFTP Mounter is already running."
        )
        sys.exit(0)

    # If the lock was acquired, proceed to configure logging and the rest of the application
    setup_logging()

    # Force the use of Qt's 'Fusion' design style, which offers
    # a modern and consistent appearance across all supported platforms.
    app.setStyle('Fusion')

    # Initialize the main window by passing the application instance
    window = MainWindow(app)
    
    # Evaluate whether the application should start minimized directly in the system tray.
    # Useful when the application is configured to autostart with the operating system.
    start_minimized = "--minimized" in sys.argv
    if not start_minimized:
        window.show()
    else:
        logging.info("Starting minimized in system tray.")

    # Run the main Qt event loop
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
