import sys
import os
import logging

# Ensure local imports inside the package directory work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from gui import MainWindow

def setup_logging():
    """Sets up logging configuration."""
    if os.name == 'nt':
        log_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SFTPMounter')
    else:
        log_dir = os.path.join(os.path.expanduser('~'), '.config', 'sftpmounter')
        
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')

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
    setup_logging()
    
    # Enable high DPI scaling for Windows 11 compatibility
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("SFTP Drive Mounter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Antigravity")
    app.setOrganizationDomain("antigravity.ai")

    # Handle system-wide styles
    app.setStyle('Fusion')

    window = MainWindow(app)
    
    # Check if we should start minimized
    start_minimized = "--minimized" in sys.argv
    if not start_minimized:
        window.show()
    else:
        logging.info("Starting minimized in system tray.")

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
