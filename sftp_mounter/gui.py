"""
Graphical User Interface (GUI) for SFTP Mounter based on PySide6.

This module defines the main window of the application (`MainWindow`), which implements:
1. A complete form for SFTP profiles (host, port, credentials for password and SSH key).
2. A premium visual design in dark mode using QSS (Qt Style Sheets).
3. Asynchronous interaction mechanisms using Qt signals and slots.
4. System tray integration (System Tray Icon) to minimize and close in the background.
5. Persistence of global settings such as auto-start in Windows via the registry.

For new developers:
- PySide6 works via a system of threads and event loops. Heavy operations
  are invoked via the `Mounter` class which delegates to subprocesses so as not to freeze the UI.
- The aesthetics are handled via the `QSS_STYLE` string. Modify this string if you need
  to customize fonts, colors, or margins.
"""

import os
import sys
import logging
from PySide6.QtCore import Qt, QSize, QTimer, QThread, Signal
from PySide6.QtGui import QIcon, QFont, QAction, QActionGroup
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QFileDialog, QSystemTrayIcon,
    QMenu, QMessageBox, QFrame, QStyle, QCheckBox, QMenuBar,
    QDialog, QListWidget, QListWidgetItem, QScrollArea, QSplitter, QInputDialog,
    QPlainTextEdit
)

from sftp_mounter.config_manager import ConfigManager
from sftp_mounter.mounter import Mounter
from sftp_mounter.i18n import I18N, SUPPORTED_LANGUAGES

logger = logging.getLogger("SFTPMounter.GUI")


class MountWorker(QThread):
    finished = Signal(bool, str, dict)  # success, message, profile

    def __init__(self, mounter, profile, accept_host_key=False):
        super().__init__()
        self.mounter = mounter
        self.profile = profile
        self.accept_host_key = accept_host_key

    def run(self):
        success, message = self.mounter.mount_sftp(self.profile, accept_host_key=self.accept_host_key)
        self.finished.emit(success, message, self.profile)


class UnmountWorker(QThread):
    finished = Signal(bool)  # success

    def __init__(self, mounter, drive):
        super().__init__()
        self.mounter = mounter
        self.drive = drive

    def run(self):
        success = self.mounter.unmount_sftp(self.drive)
        self.finished.emit(success)


# Premium QSS Style Sheet (Dark Mode)
QSS_STYLE = """
QMainWindow, QWidget#mainWidget {
    background-color: #1a1a24;
    color: #e0e0ed;
    font-family: 'Segoe UI', Arial, sans-serif;
}

QLabel {
    color: #b5b5c9;
    font-size: 13px;
    font-weight: 500;
}

QLabel#titleLabel {
    color: #ffffff;
    font-size: 20px;
    font-weight: bold;
    margin-bottom: 5px;
}

QLabel#statusLabel {
    font-size: 14px;
    font-weight: bold;
}

QLineEdit {
    background-color: #242433;
    color: #ffffff;
    border: 1px solid #3c3c52;
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 14px;
    min-height: 22px;
    selection-background-color: #5d5b8f;
}

QLineEdit:focus {
    border: 1px solid #7c7aeb;
}

QComboBox {
    background-color: #242433;
    color: #ffffff;
    border: 1px solid #3c3c52;
    border-radius: 6px;
    padding: 8px 14px;
    font-size: 14px;
    min-height: 22px;
}

QComboBox:focus {
    border: 1px solid #7c7aeb;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 0px;
}

QComboBox QAbstractItemView {
    background-color: #242433;
    color: #ffffff;
    selection-background-color: #7c7aeb;
    border: 1px solid #3c3c52;
}

QPushButton {
    background-color: #7c7aeb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 11px 16px;
    font-size: 14px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #9290ff;
}

QPushButton:pressed {
    background-color: #6462c4;
}

QPushButton:disabled {
    background-color: #2c2c3d;
    color: #6a6a85;
}

QPushButton#btnDanger {
    background-color: #cf4b61;
}

QPushButton#btnDanger:hover {
    background-color: #e55c74;
}

QPushButton#btnDanger:pressed {
    background-color: #b23b50;
}

QPushButton#btnSecondary {
    background-color: #313144;
    color: #e0e0ed;
    border: 1px solid #4a4a68;
}

QPushButton#btnSecondary:hover {
    background-color: #3b3b52;
    border-color: #5a5a80;
}

QFrame#cardFrame {
    background-color: #20202e;
    border: 1px solid #2d2d40;
    border-radius: 8px;
}

QFrame#statusCard {
    background-color: #232336;
    border-radius: 8px;
}

QCheckBox {
    color: #b5b5c9;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #3c3c52;
    border-radius: 3px;
    background: #242433;
}

QCheckBox::indicator:hover {
    border-color: #7c7aeb;
}

QCheckBox::indicator:checked {
    background-color: #7c7aeb;
    border-color: #7c7aeb;
}

QMenuBar {
    background-color: #1a1a24;
    color: #e0e0ed;
    border-bottom: 1px solid #2d2d40;
    font-size: 13px;
}

QMenuBar::item {
    background-color: transparent;
    padding: 6px 10px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #2d2d40;
    color: #ffffff;
}

QMenu {
    background-color: #20202e;
    color: #e0e0ed;
    border: 1px solid #2d2d40;
    border-radius: 6px;
    padding: 4px 0px;
}

QMenu::item {
    padding: 6px 20px 6px 20px;
}

QMenu::item:selected {
    background-color: #7c7aeb;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #2d2d40;
    margin: 4px 0px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

QListWidget {
    background-color: #20202e;
    color: #e0e0ed;
    border: 1px solid #2d2d40;
    border-radius: 8px;
    padding: 5px;
    font-size: 13px;
}

QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 4px;
}

QListWidget::item:selected {
    background-color: #7c7aeb;
    color: #ffffff;
    font-weight: bold;
}

QListWidget::item:hover:!selected {
    background-color: #2a2a3d;
}

QDialog {
    background-color: #1a1a24;
    color: #e0e0ed;
    font-family: 'Segoe UI', Arial, sans-serif;
}
"""

class LogViewerDialog(QDialog):
    """
    Ventana independiente no modal para visualizar el registro de logs de montaje.
    """
    def __init__(self, parent=None, log_path=None, i18n=None):
        super().__init__(parent)
        self.log_path = log_path
        self.i18n = i18n
        
        self.setWindowTitle(self.i18n.t('log_viewer_title'))
        self.setMinimumSize(600, 400)
        self.setStyleSheet(QSS_STYLE)
        
        # Configure non-modal window flags
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.setModal(False)
        
        self.init_ui()
        
        # Auto-refresh log contents every 1.5 seconds
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_log_content)
        self.timer.start(1500)
        
        self.load_log_content()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Read-only plain text edit
        self.txt_log = QPlainTextEdit(self)
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background-color: #141419; color: #a9a9b3; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; border: 1px solid #333;")
        layout.addWidget(self.txt_log)
        
        # Button layout
        btn_layout = QHBoxLayout()
        
        self.btn_clear = QPushButton(self.i18n.t('btn_clear_log'), self)
        self.btn_clear.clicked.connect(self.clear_log)
        self.btn_clear.setStyleSheet("background-color: #55252b; min-width: 100px; padding: 8px;")
        btn_layout.addWidget(self.btn_clear)

        self.btn_copy = QPushButton(self.i18n.t('btn_copy_log'), self)
        self.btn_copy.clicked.connect(self.copy_log)
        self.btn_copy.setStyleSheet("background-color: #3b394c; min-width: 100px; padding: 8px;")
        btn_layout.addWidget(self.btn_copy)
        
        btn_layout.addStretch()
        
        self.btn_close = QPushButton(self.i18n.t('btn_close'), self)
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setStyleSheet("background-color: #444; min-width: 100px; padding: 8px;")
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)

    def load_log_content(self):
        if not self.log_path or not os.path.exists(self.log_path):
            self.txt_log.setPlainText("")
            return
            
        try:
            # Read log content
            with open(self.log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Keep scrollbar position if user hasn't scrolled up, or autoscroll to end
            scrollbar = self.txt_log.verticalScrollBar()
            was_at_bottom = scrollbar.value() == scrollbar.maximum()
            
            self.txt_log.setPlainText(content)
            
            if was_at_bottom:
                scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            self.txt_log.setPlainText(self.i18n.t('log_read_error', error=str(e)))

    def clear_log(self):
        if not self.log_path:
            return
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                f.truncate(0)
            self.load_log_content()
            QMessageBox.information(self, self.i18n.t('log_viewer_title'), self.i18n.t('log_cleared_msg'))
        except Exception as e:
            QMessageBox.critical(self, self.i18n.t('log_viewer_title'), self.i18n.t('log_clear_error', error=str(e)))

    def copy_log(self):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.txt_log.toPlainText())
        QMessageBox.information(self, self.i18n.t('log_viewer_title'), self.i18n.t('log_copied_msg'))


    def closeEvent(self, event):
        self.timer.stop()
        event.accept()


class KnownHostsViewerDialog(QDialog):
    """
    Ventana independiente no modal para visualizar el archivo SSH known_hosts.
    """
    def __init__(self, parent=None, i18n=None):
        super().__init__(parent)
        self.i18n = i18n
        self.known_hosts_path = parent.mounter.known_hosts_file
        
        self.setWindowTitle(self.i18n.t('known_hosts_title'))
        self.setMinimumSize(600, 400)
        self.setStyleSheet(QSS_STYLE)
        
        # Configure non-modal window flags
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        self.setModal(False)
        
        self.init_ui()
        self.load_content()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Path label
        self.lbl_path = QLabel(f"Path: {self.known_hosts_path}", self)
        self.lbl_path.setStyleSheet("color: #8b8b9c; font-size: 11px;")
        layout.addWidget(self.lbl_path)
        
        # Read-only plain text edit
        self.txt_content = QPlainTextEdit(self)
        self.txt_content.setReadOnly(True)
        self.txt_content.setStyleSheet("background-color: #141419; color: #a9a9b3; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; border: 1px solid #333;")
        layout.addWidget(self.txt_content)
        
        # Button layout
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_close = QPushButton(self.i18n.t('btn_close'), self)
        self.btn_close.clicked.connect(self.close)
        self.btn_close.setStyleSheet("background-color: #444; min-width: 100px; padding: 8px;")
        btn_layout.addWidget(self.btn_close)
        
        layout.addLayout(btn_layout)

    def load_content(self):
        if not os.path.exists(self.known_hosts_path):
            self.txt_content.setPlainText(self.i18n.t('known_hosts_not_found'))
            return
            
        try:
            with open(self.known_hosts_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.txt_content.setPlainText(content if content.strip() else self.i18n.t('known_hosts_not_found'))
        except Exception as e:
            self.txt_content.setPlainText(f"Error reading known_hosts: {e}")


class ProfileManagerDialog(QDialog):
    """
    Dialog to create, edit, and delete SFTP profiles in a dedicated way.
    Presents a list of profiles on the left and the edit form on the right.
    """
    def __init__(self, parent=None, config_manager=None, i18n=None, active_mounts=None, initial_profile=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.i18n = i18n
        self.active_mounts = active_mounts or {}
        self.current_editing_profile = None
        self.initial_profile = initial_profile

        self.setWindowTitle(self.i18n.t('manage_profiles'))
        self.setMinimumSize(720, 680)
        self.setStyleSheet(QSS_STYLE)

        self.init_ui()
        self.load_profile_list()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Content Splitter (Left: Profile List, Right: Edit Form)
        splitter = QSplitter(Qt.Horizontal)
        
        # --- LEFT PANEL ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.lbl_list_title = QLabel(self.i18n.t('profile'))
        self.lbl_list_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(self.lbl_list_title)

        self.lst_profiles = QListWidget()
        self.lst_profiles.currentItemChanged.connect(self.on_profile_selected)
        left_layout.addWidget(self.lst_profiles)

        left_btn_layout = QHBoxLayout()
        self.btn_add_profile = QPushButton(self.i18n.t('add_profile'))
        self.btn_add_profile.setObjectName("btnSecondary")
        self.btn_add_profile.clicked.connect(self.on_add_profile_clicked)
        left_btn_layout.addWidget(self.btn_add_profile)

        self.btn_delete_profile = QPushButton(self.i18n.t('delete'))
        self.btn_delete_profile.setObjectName("btnDanger")
        self.btn_delete_profile.clicked.connect(self.on_delete_profile_clicked)
        left_btn_layout.addWidget(self.btn_delete_profile)
        left_layout.addLayout(left_btn_layout)

        splitter.addWidget(left_widget)

        # --- RIGHT PANEL (Form) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)

        form_frame = QFrame()
        form_frame.setObjectName("cardFrame")
        config_layout = QGridLayout(form_frame)
        config_layout.setContentsMargins(15, 15, 15, 15)
        config_layout.setSpacing(10)

        # Profile Name
        self.lbl_profile_name = QLabel(self.i18n.t('profile'))
        config_layout.addWidget(self.lbl_profile_name, 0, 0)
        self.txt_profile_name = QLineEdit()
        self.txt_profile_name.setToolTip(self.i18n.t('tooltip_profile_name'))
        config_layout.addWidget(self.txt_profile_name, 0, 1, 1, 2)

        # Host
        self.lbl_host = QLabel(self.i18n.t('host'))
        config_layout.addWidget(self.lbl_host, 1, 0)
        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText(self.i18n.t('host_placeholder'))
        self.txt_host.setToolTip(self.i18n.t('tooltip_host'))
        config_layout.addWidget(self.txt_host, 1, 1, 1, 2)

        # Port
        self.lbl_port = QLabel(self.i18n.t('port'))
        config_layout.addWidget(self.lbl_port, 2, 0)
        self.txt_port = QLineEdit("22")
        self.txt_port.setFixedWidth(80)
        self.txt_port.setToolTip(self.i18n.t('tooltip_port'))
        config_layout.addWidget(self.txt_port, 2, 1, 1, 2)

        # User
        self.lbl_user = QLabel(self.i18n.t('user'))
        config_layout.addWidget(self.lbl_user, 3, 0)
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText(self.i18n.t('user_placeholder'))
        self.txt_user.setToolTip(self.i18n.t('tooltip_user'))
        config_layout.addWidget(self.txt_user, 3, 1, 1, 2)

        # Auth Type
        self.lbl_auth = QLabel(self.i18n.t('auth'))
        config_layout.addWidget(self.lbl_auth, 4, 0)
        self.cmb_auth_type = QComboBox()
        self.cmb_auth_type.addItems([
            self.i18n.t('auth_password'),
            self.i18n.t('auth_key_no_pass'),
            self.i18n.t('auth_key_pass')
        ])
        self.cmb_auth_type.currentIndexChanged.connect(self.on_auth_type_changed)
        self.cmb_auth_type.setToolTip(self.i18n.t('tooltip_auth_type'))
        config_layout.addWidget(self.cmb_auth_type, 4, 1, 1, 2)

        # Password / Passphrase
        self.lbl_password = QLabel(self.i18n.t('password'))
        config_layout.addWidget(self.lbl_password, 5, 0)
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        self.txt_password.setToolTip(self.i18n.t('tooltip_password'))
        config_layout.addWidget(self.txt_password, 5, 1, 1, 2)

        # SSH Key Path
        self.lbl_key_path = QLabel(self.i18n.t('ssh_key'))
        self.lbl_key_path.setVisible(False)
        config_layout.addWidget(self.lbl_key_path, 6, 0)
        self.txt_key_path = QLineEdit()
        self.txt_key_path.setPlaceholderText(self.i18n.t('ssh_key_placeholder'))
        self.txt_key_path.setToolTip(self.i18n.t('tooltip_key_path'))
        self.txt_key_path.setVisible(False)
        config_layout.addWidget(self.txt_key_path, 6, 1)

        self.btn_browse_key = QPushButton(self.i18n.t('browse'))
        self.btn_browse_key.setObjectName("btnSecondary")
        self.btn_browse_key.setFixedWidth(85)
        self.btn_browse_key.setVisible(False)
        self.btn_browse_key.clicked.connect(self.on_browse_key_clicked)
        config_layout.addWidget(self.btn_browse_key, 6, 2)

        # Remote Path
        self.lbl_remote_path = QLabel(self.i18n.t('remote_path'))
        config_layout.addWidget(self.lbl_remote_path, 7, 0)
        self.txt_remote_path = QLineEdit()
        self.txt_remote_path.setPlaceholderText(self.i18n.t('remote_path_placeholder'))
        self.txt_remote_path.setToolTip(self.i18n.t('tooltip_remote_path'))
        config_layout.addWidget(self.txt_remote_path, 7, 1, 1, 2)

        # Local Drive Letter
        self.lbl_local_drive = QLabel(self.i18n.t('local_drive'))
        config_layout.addWidget(self.lbl_local_drive, 8, 0)
        self.cmb_drive_letter = QComboBox()
        self.populate_drive_letters()
        self.cmb_drive_letter.setToolTip(self.i18n.t('tooltip_drive_letter'))
        config_layout.addWidget(self.cmb_drive_letter, 8, 1, 1, 2)

        # Auto-mount & Hide Dotfiles
        self.chk_auto_mount = QCheckBox(self.i18n.t('auto_mount'))
        self.chk_auto_mount.setToolTip(self.i18n.t('tooltip_auto_mount'))
        config_layout.addWidget(self.chk_auto_mount, 9, 1)

        self.chk_hide_dotfiles = QCheckBox(self.i18n.t('hide_dotfiles'))
        self.chk_hide_dotfiles.setToolTip(self.i18n.t('tooltip_hide_dotfiles'))
        config_layout.addWidget(self.chk_hide_dotfiles, 9, 2)

        # File Mode
        self.lbl_filemode = QLabel(self.i18n.t('filemode'))
        config_layout.addWidget(self.lbl_filemode, 10, 0)
        
        filemode_layout = QHBoxLayout()
        self.txt_filemode = QLineEdit()
        self.txt_filemode.setPlaceholderText("e.g. 0640")
        self.txt_filemode.setToolTip(self.i18n.t('tooltip_filemode'))
        filemode_layout.addWidget(self.txt_filemode)
        
        self.btn_help_permissions = QPushButton("?")
        self.btn_help_permissions.setFixedSize(22, 22)
        self.btn_help_permissions.setObjectName("btnSecondary")
        self.btn_help_permissions.setStyleSheet("padding: 0px; font-size: 14px; font-weight: bold; border-radius: 11px;")
        self.btn_help_permissions.setToolTip("Click to view detailed help on permissions.")
        self.btn_help_permissions.clicked.connect(self.show_permissions_help)
        filemode_layout.addWidget(self.btn_help_permissions)
        
        config_layout.addLayout(filemode_layout, 10, 1, 1, 2)

        # Directory Mode
        self.lbl_dirmode = QLabel(self.i18n.t('dirmode'))
        config_layout.addWidget(self.lbl_dirmode, 11, 0)
        self.txt_dirmode = QLineEdit()
        self.txt_dirmode.setPlaceholderText("e.g. 0750")
        self.txt_dirmode.setToolTip(self.i18n.t('tooltip_dirmode'))
        config_layout.addWidget(self.txt_dirmode, 11, 1, 1, 2)

        # UID
        self.lbl_uid = QLabel(self.i18n.t('uid'))
        config_layout.addWidget(self.lbl_uid, 12, 0)
        self.txt_uid = QLineEdit()
        self.txt_uid.setPlaceholderText("e.g. 1000")
        self.txt_uid.setToolTip(self.i18n.t('tooltip_uid'))
        config_layout.addWidget(self.txt_uid, 12, 1, 1, 2)

        # GID
        self.lbl_gid = QLabel(self.i18n.t('gid'))
        config_layout.addWidget(self.lbl_gid, 13, 0)
        self.txt_gid = QLineEdit()
        self.txt_gid.setPlaceholderText("e.g. 1000")
        self.txt_gid.setToolTip(self.i18n.t('tooltip_gid'))
        config_layout.addWidget(self.txt_gid, 13, 1, 1, 2)

        right_layout.addWidget(form_frame)

        splitter.addWidget(right_widget)
        splitter.setSizes([220, 480])

        main_layout.addWidget(splitter, 1)

        # Bottom Buttons
        bottom_btn_layout = QHBoxLayout()
        bottom_btn_layout.addStretch()

        self.btn_save = QPushButton(self.i18n.t('save'))
        self.btn_save.clicked.connect(self.on_save_clicked)
        bottom_btn_layout.addWidget(self.btn_save)

        self.btn_close = QPushButton(self.i18n.t('close'))
        self.btn_close.setObjectName("btnSecondary")
        self.btn_close.clicked.connect(self.accept)
        bottom_btn_layout.addWidget(self.btn_close)

        main_layout.addLayout(bottom_btn_layout)

    def populate_drive_letters(self):
        self.cmb_drive_letter.clear()
        for char in range(ord('Z'), ord('C'), -1):
            letter = f"{chr(char)}:"
            self.cmb_drive_letter.addItem(letter)

    def load_profile_list(self):
        self.lst_profiles.blockSignals(True)
        self.lst_profiles.clear()
        profiles = self.config_manager.load_profiles()
        for name in profiles.keys():
            item = QListWidgetItem(name)
            self.lst_profiles.addItem(item)
        self.lst_profiles.blockSignals(False)

        if self.lst_profiles.count() > 0:
            if self.initial_profile:
                items = self.lst_profiles.findItems(self.initial_profile, Qt.MatchExactly)
                if items:
                    self.lst_profiles.setCurrentItem(items[0])
                else:
                    self.lst_profiles.setCurrentRow(0)
            else:
                self.lst_profiles.setCurrentRow(0)
        else:
            self.clear_form()

    def clear_form(self):
        self.current_editing_profile = None
        self.txt_profile_name.clear()
        self.txt_host.clear()
        self.txt_port.setText("22")
        self.txt_user.clear()
        self.cmb_auth_type.setCurrentIndex(0)
        self.txt_password.clear()
        self.txt_key_path.clear()
        self.txt_remote_path.clear()
        self.chk_auto_mount.setChecked(False)
        self.chk_hide_dotfiles.setChecked(False)
        self.txt_filemode.clear()
        self.txt_dirmode.clear()
        self.txt_uid.clear()
        self.txt_gid.clear()
        self.btn_delete_profile.setEnabled(False)

    def on_profile_selected(self, current, previous):
        if not current:
            self.clear_form()
            return

        profile_name = current.text()
        self.current_editing_profile = profile_name
        profile = self.config_manager.get_profile(profile_name)
        if not profile:
            return

        self.txt_profile_name.setText(profile_name)
        self.txt_host.setText(profile.get('host', ''))
        self.txt_port.setText(str(profile.get('port', '22')))
        self.txt_user.setText(profile.get('user', ''))

        auth = profile.get('auth_type', 'password')
        if auth == 'key':
            auth_idx = 2 if profile.get('key_password') else 1
        else:
            auth_idx = 0
        self.cmb_auth_type.setCurrentIndex(auth_idx)

        if auth_idx == 2:
            self.txt_password.setText(profile.get('key_password', ''))
        else:
            self.txt_password.setText(profile.get('password', ''))

        self.txt_key_path.setText(profile.get('key_path', ''))
        self.txt_remote_path.setText(profile.get('remote_path', ''))
        self.chk_auto_mount.setChecked(profile.get('auto_mount', False))
        self.chk_hide_dotfiles.setChecked(profile.get('hide_dotfiles', False))

        self.txt_filemode.setText(profile.get('filemode', ''))
        self.txt_dirmode.setText(profile.get('dirmode', ''))
        self.txt_uid.setText(profile.get('uid', ''))
        self.txt_gid.setText(profile.get('gid', ''))

        drive = profile.get('drive_letter', '')
        idx = self.cmb_drive_letter.findText(drive)
        if idx >= 0:
            self.cmb_drive_letter.setCurrentIndex(idx)

        is_mounted = drive in self.active_mounts
        self.btn_delete_profile.setEnabled(not is_mounted)
        self.btn_save.setEnabled(not is_mounted)

    def on_auth_type_changed(self, index):
        if index == 0:  # Password
            self.lbl_password.setText(self.i18n.t('password'))
            self.lbl_password.setVisible(True)
            self.txt_password.setVisible(True)
            self.lbl_key_path.setVisible(False)
            self.txt_key_path.setVisible(False)
            self.btn_browse_key.setVisible(False)
        elif index == 1:  # Key only
            self.lbl_password.setVisible(False)
            self.txt_password.setVisible(False)
            self.lbl_key_path.setVisible(True)
            self.txt_key_path.setVisible(True)
            self.btn_browse_key.setVisible(True)
        elif index == 2:  # Key + Passphrase
            self.lbl_password.setText(self.i18n.t('passphrase'))
            self.lbl_password.setVisible(True)
            self.txt_password.setVisible(True)
            self.lbl_key_path.setVisible(True)
            self.txt_key_path.setVisible(True)
            self.btn_browse_key.setVisible(True)

    def on_browse_key_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.i18n.t('ssh_key'), "", "All Files (*);;Key Files (*.pem *.key id_rsa)"
        )
        if file_path:
            self.txt_key_path.setText(file_path)

    def on_add_profile_clicked(self):
        name, ok = QInputDialog.getText(
            self, self.i18n.t('add_profile'), self.i18n.t('input_profile_name_msg')
        )
        if not ok or not name.strip():
            return

        name = name.strip()
        profiles = self.config_manager.load_profiles()
        if name in profiles:
            QMessageBox.warning(self, self.i18n.t('error_save_title'), self.i18n.t('profile_exists', profile_name=name))
            return

        self.clear_form()
        self.current_editing_profile = None
        self.txt_profile_name.setText(name)
        item = QListWidgetItem(name)
        self.lst_profiles.addItem(item)
        self.lst_profiles.setCurrentItem(item)

    def on_delete_profile_clicked(self):
        if not self.current_editing_profile:
            return

        profile_name = self.current_editing_profile
        profile = self.config_manager.get_profile(profile_name)
        if profile and profile.get('drive_letter', '') in self.active_mounts:
            QMessageBox.warning(self, self.i18n.t('error_save_title'), self.i18n.t('profile_active_warning'))
            return

        reply = QMessageBox.question(
            self,
            self.i18n.t('confirm_delete_title'),
            self.i18n.t('confirm_delete_msg', profile_name=profile_name),
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.config_manager.delete_profile(profile_name):
                self.load_profile_list()
            else:
                QMessageBox.critical(self, self.i18n.t('error_save_title'), self.i18n.t('error_delete_failed'))

    def on_save_clicked(self):
        name = self.txt_profile_name.text().strip()
        host = self.txt_host.text().strip()
        user = self.txt_user.text().strip()

        if not name or not host or not user:
            QMessageBox.warning(self, self.i18n.t('error_save_title'), self.i18n.t('error_save_required'))
            return

        drive = self.cmb_drive_letter.currentText()
        if drive in self.active_mounts:
            QMessageBox.warning(self, self.i18n.t('error_save_title'), self.i18n.t('profile_active_warning'))
            return

        idx = self.cmb_auth_type.currentIndex()
        auth_type = 'password'
        password = ''
        key_path = ''
        key_password = ''

        if idx == 0:
            auth_type = 'password'
            password = self.txt_password.text()
        elif idx == 1:
            auth_type = 'key'
            key_path = self.txt_key_path.text().strip()
        elif idx == 2:
            auth_type = 'key'
            key_path = self.txt_key_path.text().strip()
            key_password = self.txt_password.text()

        profile_data = {
            'host': host,
            'port': int(self.txt_port.text().strip() or "22"),
            'user': user,
            'auth_type': auth_type,
            'password': password,
            'key_path': key_path,
            'key_password': key_password,
            'remote_path': self.txt_remote_path.text().strip(),
            'drive_letter': drive,
            'auto_mount': self.chk_auto_mount.isChecked(),
            'hide_dotfiles': self.chk_hide_dotfiles.isChecked(),
            'filemode': self.txt_filemode.text().strip(),
            'dirmode': self.txt_dirmode.text().strip(),
            'uid': self.txt_uid.text().strip(),
            'gid': self.txt_gid.text().strip()
        }

        # If the name of an existing profile was changed, delete the old one
        if self.current_editing_profile and self.current_editing_profile != name:
            self.config_manager.delete_profile(self.current_editing_profile)

        if self.config_manager.save_profile(name, profile_data):
            self.current_editing_profile = name
            self.load_profile_list()
            # Select the newly saved item
            items = self.lst_profiles.findItems(name, Qt.MatchExactly)
            if items:
                self.lst_profiles.setCurrentItem(items[0])
            QMessageBox.information(self, self.i18n.t('profile_saved_title'), self.i18n.t('profile_saved_msg', profile_name=name))
        else:
            QMessageBox.critical(self, self.i18n.t('error_save_title'), self.i18n.t('error_save_failed'))

    def show_permissions_help(self):
        """
        Shows a detailed explanation of File Mode, Directory Mode, UID, and GID.
        """
        msg = (
            f"<h3><b>{self.i18n.t('permissions_help_title')}</b></h3><br>"
            f"<b>{self.i18n.t('filemode')} (Optional - e.g. 0640):</b><br>"
            f"{self.i18n.t('filemode_help_desc')}<br><br>"
            f"<b>{self.i18n.t('dirmode')} (Optional - e.g. 0750):</b><br>"
            f"{self.i18n.t('dirmode_help_desc')}<br><br>"
            f"<b>{self.i18n.t('uid')} / {self.i18n.t('gid')} (Optional):</b><br>"
            f"{self.i18n.t('uid_gid_help_desc')}<br><br>"
            f"<i>{self.i18n.t('already_created_note')}</i>"
        )
        QMessageBox.information(self, self.i18n.t('permissions_help_title'), msg)


class SettingsDialog(QDialog):
    """
    Dialog to configure global application settings:
    language, auto-start with Windows, minimize on close, and showing connection string in drive name.
    """
    def __init__(self, parent=None, config_manager=None, i18n=None, main_window=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.i18n = i18n
        self.main_window = main_window

        self.setWindowTitle(self.i18n.t('menu_settings') or "Settings")
        self.setMinimumSize(420, 320)
        self.setStyleSheet(QSS_STYLE)

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        form_frame = QFrame()
        form_frame.setObjectName("cardFrame")
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(15, 15, 15, 15)
        form_layout.setSpacing(12)

        # Language
        self.lbl_lang = QLabel(self.i18n.t('menu_language') or "Language")
        self.cmb_lang = QComboBox()
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            self.cmb_lang.addItem(lang_name, lang_code)
        form_layout.addWidget(self.lbl_lang, 0, 0)
        form_layout.addWidget(self.cmb_lang, 0, 1)

        # Start with Windows
        self.chk_start_with_win = QCheckBox(self.i18n.t('start_with_win') or "Start with Windows")
        form_layout.addWidget(self.chk_start_with_win, 1, 0, 1, 2)

        # Minimize on close
        self.chk_minimize_to_tray = QCheckBox(self.i18n.t('minimize_to_tray') or "Minimize on close")
        form_layout.addWidget(self.chk_minimize_to_tray, 2, 0, 1, 2)

        # Connection string in drive name
        self.chk_conn_in_volname = QCheckBox(self.i18n.t('conn_in_volname') or "Connection string in drive name")
        form_layout.addWidget(self.chk_conn_in_volname, 3, 0, 1, 2)

        main_layout.addWidget(form_frame)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_save = QPushButton(self.i18n.t('save') or "Save")
        self.btn_save.setObjectName("btnPrimary")
        self.btn_save.clicked.connect(self.on_save_clicked)
        btn_layout.addWidget(self.btn_save)

        self.btn_cancel = QPushButton(self.i18n.t('cancel') or "Cancel")
        self.btn_cancel.setObjectName("btnSecondary")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

    def load_settings(self):
        settings = self.config_manager.load_settings()
        
        # 1. Language
        current_lang = self.i18n.get_language()
        idx = self.cmb_lang.findData(current_lang)
        if idx >= 0:
            self.cmb_lang.setCurrentIndex(idx)

        # 2. Start with Windows
        start_with_win = self.main_window.get_startup_registry()
        self.chk_start_with_win.setChecked(start_with_win)

        # 3. Minimize on close
        min_to_tray = settings.get('minimize_to_tray', True)
        self.chk_minimize_to_tray.setChecked(min_to_tray)

        # 4. Connection string in drive name
        conn_in_volname = settings.get('conn_in_volname', False)
        self.chk_conn_in_volname.setChecked(conn_in_volname)

    def on_save_clicked(self):
        settings = self.config_manager.load_settings()
        
        # Save language
        new_lang = self.cmb_lang.currentData()
        if new_lang != self.i18n.get_language():
            self.i18n.set_language(new_lang)
            settings['language'] = new_lang
            self.main_window.retranslate_ui()

        # Save Start with Windows
        chk_win = self.chk_start_with_win.isChecked()
        if chk_win != self.main_window.get_startup_registry():
            success = self.main_window.set_startup_registry(chk_win)
            if success:
                settings['start_with_windows'] = chk_win
            else:
                QMessageBox.critical(
                    self, self.main_window.i18n.t('config_error_title'), self.main_window.i18n.t('config_error_msg')
                )

        # Save Minimize on close
        settings['minimize_to_tray'] = self.chk_minimize_to_tray.isChecked()

        # Save Connection string in drive name
        settings['conn_in_volname'] = self.chk_conn_in_volname.isChecked()

        self.config_manager.save_settings(settings)
        
        # Synchronize and force UI reload on MainWindow
        self.main_window.load_profiles_dashboard()
        self.main_window.load_global_settings()
        
        self.accept()


class MainWindow(QWidget):
    """
    Main window of the application. Manages visual controls,
    connection form validation, and system events (tray, startup, etc.).
    """
    def __init__(self, app):
        """
        Initializes the graphical interface, binds config and mount managers,
        and schedules the initial auto-mount if applicable.
        
        Args:
            app (QApplication): Running Qt application instance.
        """
        super().__init__()
        self.app = app
        self.config_manager = ConfigManager()
        self.mounter = Mounter()
        
        # Cargar idioma preferido de la configuración o detectar automáticamente
        settings = self.config_manager.load_settings()
        saved_lang = settings.get('language', '')
        self.i18n = I18N(default_lang=saved_lang if saved_lang else 'en')
        
        # Variables de estado interno
        self.is_connecting = False         # Flag para bloquear re-intentos de conexión
        self.log_viewer = None
        self.log_path = os.path.join(self.mounter.app_dir, 'mounts.log')
        self.known_hosts_viewer = None
        self.active_workers = {}


        self.init_ui()
        self.load_global_settings()
        self.check_winfsp_status()
        self.load_profiles_dashboard()
        
        QTimer.singleShot(500, self.perform_auto_mount)

    def init_ui(self):
        self.setObjectName("mainWidget")
        self.setMinimumSize(870, 680)
        self.resize(870, 680)
        self.setStyleSheet(QSS_STYLE)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ----------------- SECTION: MENU BAR -----------------
        self.menu_bar = QMenuBar(self)
        main_layout.setMenuBar(self.menu_bar)
        
        # Opciones Menu
        self.menu_options = QMenu(self)
        self.menu_bar.addMenu(self.menu_options)
        
        # Gestionar perfiles
        self.act_manage_profiles = QAction(self)
        self.act_manage_profiles.triggered.connect(self.on_open_profile_manager)
        self.menu_options.addAction(self.act_manage_profiles)

        # Ver log
        self.act_view_log = QAction(self)
        self.act_view_log.triggered.connect(self.on_open_log_viewer)
        self.menu_options.addAction(self.act_view_log)

        # Ver known_hosts
        self.act_view_known_hosts = QAction(self)
        self.act_view_known_hosts.triggered.connect(self.on_open_known_hosts_viewer)
        self.menu_options.addAction(self.act_view_known_hosts)

        self.menu_options.addSeparator()

        # Configuración / Settings
        self.act_settings = QAction(self)
        self.act_settings.triggered.connect(self.on_open_settings)
        self.menu_options.addAction(self.act_settings)
            
        self.menu_options.addSeparator()

        # Salir / Exit
        self.act_exit = QAction(self)
        self.act_exit.triggered.connect(self.on_menu_exit_clicked)
        self.menu_options.addAction(self.act_exit)
            
        # Ayuda Menu
        self.menu_help = QMenu(self)
        self.menu_bar.addMenu(self.menu_help)
        
        # Acerca de
        self.act_about = QAction(self)
        self.act_about.triggered.connect(self.on_about_clicked)
        self.menu_help.addAction(self.act_about)

        # Header Title Layout
        title_layout = QHBoxLayout()
        self.lbl_title = QLabel("SFTP Mounter")
        self.lbl_title.setObjectName("titleLabel")
        title_layout.addWidget(self.lbl_title)
        
        # WinFsp status header warning
        self.lbl_winfsp_warning = QLabel("")
        self.lbl_winfsp_warning.setStyleSheet("color: #ffb86c; font-size: 11px;")
        self.lbl_winfsp_warning.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_layout.addWidget(self.lbl_winfsp_warning)
        
        main_layout.addLayout(title_layout)

        # ----------------- WinFsp INSTALL CARD (Conditional) -----------------
        self.winfsp_card = QFrame()
        self.winfsp_card.setObjectName("statusCard")
        self.winfsp_card.setStyleSheet("background-color: #2b2123; border: 1px solid #54252b;")
        winfsp_card_layout = QHBoxLayout(self.winfsp_card)
        winfsp_card_layout.setContentsMargins(12, 10, 12, 10)
        
        self.lbl_winfsp_missing = QLabel()
        self.lbl_winfsp_missing.setStyleSheet("color: #ff79c6; font-size: 12px;")
        winfsp_card_layout.addWidget(self.lbl_winfsp_missing, 1)
        
        self.btn_install_winfsp = QPushButton()
        self.btn_install_winfsp.setObjectName("btnDanger")
        self.btn_install_winfsp.clicked.connect(self.on_install_winfsp_clicked)
        winfsp_card_layout.addWidget(self.btn_install_winfsp)
        
        self.winfsp_card.setVisible(False)
        main_layout.addWidget(self.winfsp_card)

        # ----------------- DASHBOARD: SCROLL AREA DE PERFILES -----------------
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.scroll_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_widget)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        self.scroll_area.setWidget(self.scroll_widget)
        main_layout.addWidget(self.scroll_area, 1)

        # Retranslate y System Tray
        self.retranslate_ui()
        self.setup_system_tray()

    def load_profiles_dashboard(self):
        """
        Limpia y reconstruye dinámicamente las tarjetas de perfiles en el Dashboard.
        """
        # Limpiar widgets anteriores en cards_layout
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        profiles = self.config_manager.load_profiles()
        self.profile_cards = {}  # {name: {'frame': frame, 'btn_action': btn, 'lbl_status': lbl, 'profile': profile}}

        if not profiles:
            no_profiles_lbl = QLabel(self.i18n.t('no_profiles'))
            no_profiles_lbl.setAlignment(Qt.AlignCenter)
            no_profiles_lbl.setStyleSheet("color: #6a6a85; font-size: 14px; margin-top: 50px;")
            self.cards_layout.addWidget(no_profiles_lbl)
            self.cards_layout.addStretch()
            return

        for name, profile in profiles.items():
            card_frame = QFrame()
            card_frame.setObjectName("cardFrame")
            card_layout = QHBoxLayout(card_frame)
            card_layout.setContentsMargins(15, 12, 15, 12)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(4)

            # Nombre y Unidad
            header_layout = QHBoxLayout()
            lbl_name = QLabel(name)
            lbl_name.setStyleSheet("font-weight: bold; font-size: 15px; color: #ffffff;")
            header_layout.addWidget(lbl_name)

            drive = profile.get('drive_letter', '')
            if drive:
                lbl_drive = QLabel(f"[{drive.upper()}]")
                lbl_drive.setStyleSheet("color: #7c7aeb; font-weight: bold; font-size: 13px;")
                header_layout.addWidget(lbl_drive)
            header_layout.addStretch()

            info_layout.addLayout(header_layout)

            # Detalle conexión (user@host:port)
            host = profile.get('host', '')
            port = profile.get('port', 22)
            user = profile.get('user', '')
            remote_path = profile.get('remote_path', '')
            auto_mount = profile.get('auto_mount', False)
            auto_mount_str = self.i18n.t('yes') if auto_mount else self.i18n.t('no')
            
            detail_str = f"{user}@{host}:{port}"
            if remote_path:
                detail_str += f" ({remote_path})"
            detail_str += f" • {self.i18n.t('auto_mount_status', status=auto_mount_str)}"

            lbl_detail = QLabel(detail_str)
            lbl_detail.setStyleSheet("color: #8b8b9c; font-size: 12px;")
            info_layout.addWidget(lbl_detail)

            # Estado
            lbl_status = QLabel(self.i18n.t('status_disconnected'))
            lbl_status.setStyleSheet("color: #8b8b9c; font-size: 12px; font-weight: bold;")
            info_layout.addWidget(lbl_status)

            card_layout.addLayout(info_layout, 1)

            # Botón único de acción (más ancho para evitar entrecortar texto)
            btn_action = QPushButton(self.i18n.t('connect'))
            btn_action.setMinimumWidth(180)
            btn_action.setStyleSheet("padding: 11px 20px; font-size: 13px;")
            btn_action.clicked.connect(lambda checked=False, p_name=name: self.on_card_action_clicked(p_name))
            card_layout.addWidget(btn_action)

            # Botón para editar el perfil
            btn_edit = QPushButton()
            btn_edit.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
            btn_edit.setToolTip(self.i18n.t('manage_profiles'))
            btn_edit.setFixedSize(40, 40)
            btn_edit.setStyleSheet("background-color: #3b394c; border: 1px solid #54527c; padding: 5px;")
            btn_edit.clicked.connect(lambda checked=False, p_name=name: self.on_edit_profile_clicked(p_name))
            card_layout.addWidget(btn_edit)

            self.cards_layout.addWidget(card_frame)

            self.profile_cards[name] = {
                'frame': card_frame,
                'btn_action': btn_action,
                'lbl_status': lbl_status,
                'profile': profile
            }

            self.update_card_status(name)

        self.cards_layout.addStretch()

    def update_card_status(self, profile_name):
        """
        Updates the appearance of a profile card based on whether the corresponding drive is mounted.
        """
        card = self.profile_cards.get(profile_name)
        if not card:
            return

        profile = card['profile']
        drive = profile.get('drive_letter', '')
        is_mounted = drive in self.mounter.active_mounts

        if is_mounted:
            card['lbl_status'].setText(self.i18n.t('status_mounted', drive=drive.upper()))
            card['lbl_status'].setStyleSheet("color: #50fa7b; font-size: 12px; font-weight: bold;")
            card['btn_action'].setText(self.i18n.t('disconnect'))
            card['btn_action'].setObjectName("btnDanger")
            card['btn_action'].setStyleSheet("background-color: #cf4b61; min-width: 180px; padding: 11px 20px; font-size: 13px;")
            card['btn_action'].setEnabled(True)
        else:
            card['lbl_status'].setText(self.i18n.t('status_disconnected'))
            card['lbl_status'].setStyleSheet("color: #8b8b9c; font-size: 12px; font-weight: bold;")
            card['btn_action'].setText(self.i18n.t('connect'))
            card['btn_action'].setObjectName("")
            card['btn_action'].setStyleSheet("background-color: #7c7aeb; min-width: 180px; padding: 11px 20px; font-size: 13px;")
            card['btn_action'].setEnabled(True)

    def on_card_action_clicked(self, profile_name):
        """
        Triggered when clicking the action button on a profile card.
        If the drive is mounted, it disconnects it. Otherwise, it connects it.
        """
        card = self.profile_cards.get(profile_name)
        if not card:
            return

        profile = card['profile']
        drive = profile.get('drive_letter', '')

        # Avoid clicking if there is already an active process for this profile
        if profile_name in self.active_workers:
            return

        if drive in self.mounter.active_mounts:
            # Desconectar
            card['lbl_status'].setText(self.i18n.t('status_unmounting'))
            card['lbl_status'].setStyleSheet("color: #ffb86c; font-size: 12px; font-weight: bold;")
            card['btn_action'].setEnabled(False)
            self.app.processEvents()

            self.log_action(profile_name, f"Iniciando desmontaje de la unidad {drive.upper()}")
            
            worker = UnmountWorker(self.mounter, drive)
            self.active_workers[profile_name] = worker
            worker.finished.connect(lambda success, d=drive, pn=profile_name: self.on_unmount_finished(success, d, pn))
            worker.start()
        else:
            # Conectar
            card['lbl_status'].setText(self.i18n.t('status_connecting'))
            card['lbl_status'].setStyleSheet("color: #ffb86c; font-size: 12px; font-weight: bold;")
            card['btn_action'].setEnabled(False)
            self.app.processEvents()

            self.log_action(profile_name, f"Starting connection/mount on {drive.upper()}")
            
            worker = MountWorker(self.mounter, profile)
            self.active_workers[profile_name] = worker
            worker.finished.connect(lambda success, msg, prof=profile, pn=profile_name: self.on_mount_finished(success, msg, prof, pn))
            worker.start()

    def on_unmount_finished(self, success, drive, profile_name):
        self.active_workers.pop(profile_name, None)
        card = self.profile_cards.get(profile_name)
        if not card:
            return

        if success:
            self.log_action(profile_name, f"Drive {drive.upper()} unmounted successfully")
            self.tray_icon.showMessage(
                "SFTP Drive Mounter",
                self.i18n.t('disconnection_ok_msg', drive=drive.upper()),
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.log_action(profile_name, f"Error unmounting drive {drive.upper()}")
            QMessageBox.warning(self, self.i18n.t('unmount_warning_title'), self.i18n.t('unmount_warning_msg'))

        self.update_card_status(profile_name)
        self.setup_system_tray()

    def on_mount_finished(self, success, message, profile, profile_name):
        self.active_workers.pop(profile_name, None)
        card = self.profile_cards.get(profile_name)
        if not card:
            return

        drive = profile.get('drive_letter', '')

        # If it fails due to SSH host key verification (host key verification/unknown host)
        is_host_key_error = any(term in message.lower() for term in [
            "host key", "key verification", "hostkey", "host key fingerprint", "strictly host key checking", "knownhosts", "key is unknown"
        ]) and "no host key validation is being performed" not in message.lower()

        if not success and is_host_key_error:
            self.log_action(profile_name, f"Failed due to unknown host key. Requesting user confirmation.")
            reply = QMessageBox.question(
                self,
                self.i18n.t('host_key_unknown_title'),
                self.i18n.t('host_key_unknown_msg', host=profile.get('host', '')),
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.log_action(profile_name, f"User accepted host key. Attempting to add key to known_hosts...")
                added = self.mounter.add_to_known_hosts(profile.get('host'), profile.get('port', 22))
                
                card['lbl_status'].setText(self.i18n.t('status_connecting'))
                self.app.processEvents()
                
                # Launch a second MountWorker with accept_host_key=True
                worker = MountWorker(self.mounter, profile, accept_host_key=True)
                self.active_workers[profile_name] = worker
                worker.finished.connect(lambda s, m, p=profile, pn=profile_name: self.on_mount_finished(s, m, p, pn))
                worker.start()
                return

        if success:
            self.log_action(profile_name, f"Mount on {drive.upper()} completed and verified successfully")
            self.tray_icon.showMessage(
                "SFTP Drive Mounter",
                self.i18n.t('connection_ok_msg', drive=drive.upper()),
                QSystemTrayIcon.Information,
                3000
            )
        else:
            self.log_action(profile_name, f"Error performing mount on {drive.upper()}: {message}")
            display_msg = message
            if "already in use" in message or "ya está en uso" in message:
                display_msg = self.i18n.t('net_use_in_use', drive=drive.upper())
            QMessageBox.critical(self, self.i18n.t('connection_fail_title'), display_msg)

        self.update_card_status(profile_name)
        self.setup_system_tray()


    def on_open_profile_manager(self):
        """
        Abre el diálogo de gestión de perfiles ProfileManagerDialog.
        Al cerrar, recarga dinámicamente las tarjetas del Dashboard.
        """
        dialog = ProfileManagerDialog(
            parent=self,
            config_manager=self.config_manager,
            i18n=self.i18n,
            active_mounts=self.mounter.active_mounts
        )
        dialog.exec_()
        self.load_profiles_dashboard()

    def on_edit_profile_clicked(self, profile_name):
        """
        Opens the profile management dialog with a specific profile selected by default.
        """
        dialog = ProfileManagerDialog(
            parent=self,
            config_manager=self.config_manager,
            i18n=self.i18n,
            active_mounts=self.mounter.active_mounts,
            initial_profile=profile_name
        )
        dialog.exec_()
        self.load_profiles_dashboard()

    def on_open_log_viewer(self):
        """
        Opens the independent non-modal log viewer window.
        """
        if self.log_viewer is None or not self.log_viewer.isVisible():
            self.log_viewer = LogViewerDialog(parent=self, log_path=self.log_path, i18n=self.i18n)
            self.log_viewer.show()
        else:
            self.log_viewer.activateWindow()
            self.log_viewer.raise_()

    def on_open_known_hosts_viewer(self):
        """
        Opens the independent non-modal known_hosts viewer window.
        """
        if self.known_hosts_viewer is None or not self.known_hosts_viewer.isVisible():
            self.known_hosts_viewer = KnownHostsViewerDialog(parent=self, i18n=self.i18n)
            self.known_hosts_viewer.show()
        else:
            self.known_hosts_viewer.activateWindow()
            self.known_hosts_viewer.raise_()



    def log_action(self, profile_name: str, message: str):
        """
        Registers a mount event in the log file with ISO datetime format, mount name, and log message.
        """
        import datetime
        try:
            iso_time = datetime.datetime.now().isoformat()
            log_line = f"{iso_time} [{profile_name}] {message}\n"
            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(log_line)
        except Exception as e:
            logger.error(f"Failed to write to mounts.log: {e}")

    def retranslate_ui(self):
        self.setWindowTitle(self.i18n.t('title'))
        self.lbl_title.setText(self.i18n.t('title'))
        self.lbl_winfsp_missing.setText(self.i18n.t('winfsp_missing_card'))
        self.btn_install_winfsp.setText(self.i18n.t('install_winfsp'))

        # Menús y acciones
        self.menu_options.setTitle(self.i18n.t('menu_options'))
        self.act_manage_profiles.setText(self.i18n.t('manage_profiles'))
        self.act_view_log.setText(self.i18n.t('menu_view_log'))
        self.act_view_known_hosts.setText(self.i18n.t('menu_view_known_hosts'))
        self.act_settings.setText(self.i18n.t('menu_settings'))
        self.act_exit.setText(self.i18n.t('menu_exit'))
        self.menu_help.setTitle(self.i18n.t('menu_help'))
        self.act_about.setText(self.i18n.t('about'))

        self.check_winfsp_status()
        if hasattr(self, 'profile_cards'):
            self.load_profiles_dashboard()

        if hasattr(self, 'tray_icon'):
            self.setup_system_tray()

    def check_winfsp_status(self):
        installed = self.mounter.is_winfsp_installed()
        if installed:
            self.lbl_winfsp_warning.setText(self.i18n.t('winfsp_ok'))
            self.lbl_winfsp_warning.setStyleSheet("color: #50fa7b; font-size: 11px;")
            self.winfsp_card.setVisible(False)
        else:
            self.lbl_winfsp_warning.setText(self.i18n.t('winfsp_not_installed'))
            self.lbl_winfsp_warning.setStyleSheet("color: #ff5555; font-size: 11px;")
            self.winfsp_card.setVisible(True)

    def populate_drive_letters(self):
        """
        Fills the network drive selector (ComboBox) with available Windows drive letters.
        
        Scans downwards (from Z: to D:) omitting drive letters
        already occupied by the system (e.g. hard drives, USB readers).
        In UNIX systems, adds default mount paths inside the user's home directory.
        """
        self.cmb_drive_letter.clear()
        for char in range(ord('Z'), ord('C'), -1):
            letter = f"{chr(char)}:"
            if not self.mounter.is_drive_letter_in_use(letter):
                self.cmb_drive_letter.addItem(letter)

    def load_profiles_into_combo(self):
        """
        Queries the config manager to retrieve profiles and load them into the interface.
        Always adds the '<New Profile>' option (translated) at the first index.
        """
        self.cmb_profiles.blockSignals(True)
        self.cmb_profiles.clear()
        self.cmb_profiles.addItem(self.i18n.t('new_profile'))
        
        profiles = self.config_manager.load_profiles()
        for name in profiles.keys():
            self.cmb_profiles.addItem(name)
        self.cmb_profiles.blockSignals(False)

    def on_profile_selection_changed(self, index):
        """
        Slot triggered when the user selects a different profile from the list.
        
        If the first item is selected (index <= 0), form fields are cleared.
        Otherwise, connection data for the selected profile is loaded.
        
        Args:
            index (int): Selected index in the profiles ComboBox.
        """
        if index <= 0:
            # Clear inputs for a new profile
            self.txt_host.clear()
            self.txt_port.setText("22")
            self.txt_user.clear()
            self.cmb_auth_type.setCurrentIndex(0)
            self.txt_password.clear()
            self.txt_key_path.clear()
            self.txt_remote_path.clear()
            self.chk_auto_mount.setChecked(False)
            self.btn_delete_profile.setEnabled(False)
        else:
            profile_name = self.cmb_profiles.itemText(index)
            profile = self.config_manager.get_profile(profile_name)
            if profile:
                self.txt_host.setText(profile.get('host', ''))
                self.txt_port.setText(str(profile.get('port', '22')))
                self.txt_user.setText(profile.get('user', ''))
                
                auth = profile.get('auth_type', 'password')
                if auth == 'key':
                    if profile.get('key_password'):
                        auth_idx = 2
                    else:
                        auth_idx = 1
                else:
                    auth_idx = 0
                self.cmb_auth_type.setCurrentIndex(auth_idx)
                
                if auth_idx == 2:
                    self.txt_password.setText(profile.get('key_password', ''))
                else:
                    self.txt_password.setText(profile.get('password', ''))
                    
                self.txt_key_path.setText(profile.get('key_path', ''))
                self.txt_remote_path.setText(profile.get('remote_path', ''))
                self.chk_auto_mount.setChecked(profile.get('auto_mount', False))
                
                drive = profile.get('drive_letter', '')
                drive_idx = self.cmb_drive_letter.findText(drive)
                if drive_idx >= 0:
                    self.cmb_drive_letter.setCurrentIndex(drive_idx)
                elif drive:
                    self.cmb_drive_letter.addItem(drive)
                    self.cmb_drive_letter.setCurrentIndex(self.cmb_drive_letter.count() - 1)
                
                self.btn_delete_profile.setEnabled(True)
        
        self.update_status_label()

    def on_auth_type_changed(self, index):
        """
        Muestra u oculta controles dinámicamente según la opción de autenticación seleccionada.
        
        Args:
            index (int): Índice de la selección del ComboBox de autenticación.
        """
        if index == 0:  # Contraseña
            self.lbl_password.setText(self.i18n.t('password'))
            self.lbl_password.setVisible(True)
            self.txt_password.setVisible(True)
            self.lbl_key_path.setVisible(False)
            self.txt_key_path.setVisible(False)
            self.btn_browse_key.setVisible(False)
        elif index == 1:  # Llave sola
            self.lbl_password.setVisible(False)
            self.txt_password.setVisible(False)
            self.lbl_key_path.setVisible(True)
            self.txt_key_path.setVisible(True)
            self.btn_browse_key.setVisible(True)
        elif index == 2:  # Key + Passphrase
            self.lbl_password.setText(self.i18n.t('passphrase'))
            self.lbl_password.setVisible(True)
            self.txt_password.setVisible(True)
            self.lbl_key_path.setVisible(True)
            self.txt_key_path.setVisible(True)
            self.btn_browse_key.setVisible(True)

    def on_browse_key_clicked(self):
        """
        Opens a native Qt file dialog to let the user select their private SSH key path.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.i18n.t('ssh_key'), "", "All Files (*);;Key Files (*.pem *.key id_rsa)"
        )
        if file_path:
            self.txt_key_path.setText(file_path)

    def get_current_form_data(self):
        """
        Collects all data entered in the UI form.
        
        Returns:
            dict: Parameters ready for persistence or processing.
        """
        idx = self.cmb_auth_type.currentIndex()
        
        auth_type = 'password'
        password = ''
        key_path = ''
        key_password = ''
        
        if idx == 0:
            auth_type = 'password'
            password = self.txt_password.text()
        elif idx == 1:
            auth_type = 'key'
            key_path = self.txt_key_path.text().strip()
        elif idx == 2:
            auth_type = 'key'
            key_path = self.txt_key_path.text().strip()
            key_password = self.txt_password.text()

        return {
            'host': self.txt_host.text().strip(),
            'port': int(self.txt_port.text().strip() or "22"),
            'user': self.txt_user.text().strip(),
            'auth_type': auth_type,
            'password': password,
            'key_path': key_path,
            'key_password': key_password,
            'remote_path': self.txt_remote_path.text().strip(),
            'drive_letter': self.cmb_drive_letter.currentText(),
            'auto_mount': self.chk_auto_mount.isChecked()
        }

    def on_save_profile_clicked(self):
        """
        Validates and saves current form data as a connection profile.
        If it is a new profile, requests a name from the user via QInputDialog.
        """
        profile_name = self.cmb_profiles.currentText()
        if profile_name == self.i18n.t('new_profile') or not profile_name.strip():
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(
                self, self.i18n.t('input_profile_name_title'), self.i18n.t('input_profile_name_msg')
            )
            if not ok or not name.strip():
                return
            profile_name = name.strip()

        data = self.get_current_form_data()
        
        if not data['host'] or not data['user']:
            QMessageBox.warning(self, self.i18n.t('error_save_title'), self.i18n.t('error_save_required'))
            return

        if self.config_manager.save_profile(profile_name, data):
            QMessageBox.information(
                self, self.i18n.t('profile_saved_title'), self.i18n.t('profile_saved_msg', profile_name=profile_name)
            )
            self.load_profiles_into_combo()
            idx = self.cmb_profiles.findText(profile_name)
            if idx >= 0:
                self.cmb_profiles.setCurrentIndex(idx)
        else:
            QMessageBox.critical(self, self.i18n.t('status_error'), self.i18n.t('error_save_failed'))

    def on_delete_profile_clicked(self):
        """
        Permanently deletes the selected connection profile.
        """
        profile_name = self.cmb_profiles.currentText()
        if profile_name == self.i18n.t('new_profile'):
            return
            
        confirm = QMessageBox.question(
            self, self.i18n.t('confirm_delete_title'),
            self.i18n.t('confirm_delete_msg', profile_name=profile_name),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            if self.config_manager.delete_profile(profile_name):
                QMessageBox.information(
                    self, self.i18n.t('profile_deleted_title'),
                    self.i18n.t('profile_deleted_msg', profile_name=profile_name)
                )
                self.load_profiles_into_combo()
                self.cmb_profiles.setCurrentIndex(0)
            else:
                QMessageBox.critical(self, self.i18n.t('status_error'), self.i18n.t('error_delete_failed'))

    def on_install_winfsp_clicked(self):
        """
        Lanza el proceso de instalación pasiva de WinFsp.
        """
        self.btn_install_winfsp.setEnabled(False)
        self.app.processEvents()
        
        success = self.mounter.install_winfsp()
        
        self.btn_install_winfsp.setEnabled(True)
        self.check_winfsp_status()
        
        if success:
            QMessageBox.information(
                self, self.i18n.t('install_winfsp_ok_title'), self.i18n.t('install_winfsp_ok_msg')
            )
        else:
            QMessageBox.critical(
                self, self.i18n.t('install_winfsp_fail_title'), self.i18n.t('install_winfsp_fail_msg')
            )

    # ----------------- SYSTEM TRAY MANAGEMENT (BANDEJA DE SISTEMA) -----------------
    def setup_system_tray(self):
        """
        Crea e inicializa el icono de la bandeja del sistema (System Tray Icon).
        """
        if not hasattr(self, 'tray_icon'):
            self.tray_icon = QSystemTrayIcon(self)
            
            # Intentar cargar el logotipo personalizado
            icon = None
            try:
                import sys
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                if getattr(sys, 'frozen', False):
                    logo_path = os.path.join(sys._MEIPASS, 'bin', 'logo.svg')
                else:
                    logo_path = os.path.join(project_root, 'build', 'bin', 'logo.svg')
                
                if os.path.exists(logo_path):
                    icon = QIcon(logo_path)
            except Exception as e:
                logger.error(f"Error loading custom logo icon: {e}")
                
            if not icon or icon.isNull():
                icon = self.style().standardIcon(QStyle.SP_DriveHDIcon)
                
            self.tray_icon.setIcon(icon)
            self.setWindowIcon(icon)
            self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # Crear o actualizar el menú contextual con textos localizados
        tray_menu = QMenu()
        
        action_show = QAction(self.i18n.t('show_window'), self)
        action_show.triggered.connect(self.show_normal)
        tray_menu.addAction(action_show)
        
        # Mostrar listado de unidades montadas activas
        active_drives = list(self.mounter.active_mounts.keys())
        if active_drives:
            tray_menu.addSeparator()
            header_action = QAction(self.i18n.t('mounted_drives') + ":", self)
            header_action.setEnabled(False)
            tray_menu.addAction(header_action)
            
            for drive in sorted(active_drives):
                drive_action = QAction(f"  • {drive.upper()}", self)
                drive_action.triggered.connect(lambda checked=False, d=drive: self.open_drive_folder(d))
                tray_menu.addAction(drive_action)

        action_unmount = QAction(self.i18n.t('unmount_all'), self)
        action_unmount.triggered.connect(self.force_unmount_all)
        tray_menu.addAction(action_unmount)
        
        tray_menu.addSeparator()
        
        action_exit = QAction(self.i18n.t('exit'), self)
        action_exit.triggered.connect(self.close_app)
        tray_menu.addAction(action_exit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def open_drive_folder(self, drive):
        """
        Abre el explorador de archivos en la ruta del montaje seleccionado.
        """
        import os
        import subprocess
        
        path = os.path.abspath(drive)
        os.startfile(path)

    def show_normal(self):
        """
        Restaura la visibilidad normal de la ventana en pantalla.
        """
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_tray_icon_activated(self, reason):
        """
        Slot gatillado ante la interacción con el icono de la bandeja del sistema.
        """
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()
                self.activateWindow()

    def force_unmount_all(self):
        """
        Forza la desconexión de todas las unidades SFTP activas.
        """
        drives = list(self.mounter.active_mounts.keys())
        for drive in drives:
            self.mounter.unmount_sftp(drive)
        if hasattr(self, 'profile_cards'):
            for p_name in self.profile_cards.keys():
                self.update_card_status(p_name)
        self.setup_system_tray()

    def close_app(self):
        """
        Cierra limpiamente la aplicación.
        """
        self.force_unmount_all()
        self.tray_icon.hide()
        self.app.quit()

    def on_menu_exit_clicked(self):
        """
        Confirms with the user, unmounts all active drives, and exits the application.
        """
        confirm = QMessageBox.question(
            self,
            self.i18n.t('confirm_exit_title'),
            self.i18n.t('confirm_exit_msg'),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            QMessageBox.information(
                self,
                self.i18n.t('exiting_title'),
                self.i18n.t('exiting_msg')
            )
            self.close_app()

    def changeEvent(self, event):
        """
        Intercepta los eventos de cambio de estado de la ventana en PySide6.
        """
        if event.type() == event.type().WindowStateChange:
            if self.isMinimized() and getattr(self, 'minimize_to_tray', True):
                self.hide()
                event.ignore()
                self.tray_icon.showMessage(
                    "SFTP Drive Mounter",
                    self.i18n.t('tray_msg_minimized'),
                    QSystemTrayIcon.Information,
                    1500
                )
        super().changeEvent(event)

    def closeEvent(self, event):
        """
        Intercepta el evento de cierre de ventana.
        """
        if getattr(self, 'minimize_to_tray', True) and len(self.mounter.active_mounts) > 0:
            self.hide()
            event.ignore()
            self.tray_icon.showMessage(
                "SFTP Drive Mounter",
                self.i18n.t('tray_msg_background'),
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.close_app()

    # ----------------- GLOBAL SETTINGS & AUTOSTART (REGISTRO DE WINDOWS) -----------------
    def load_global_settings(self):
        """
        Carga la configuración global desde el config_manager.
        """
        settings = self.config_manager.load_settings()
        
        # 1. Minimizar a la bandeja (por defecto True)
        self.minimize_to_tray = settings.get('minimize_to_tray', True)
        
        # 2. Iniciar con Windows (leer del registro de Windows)
        start_with_win = self.get_startup_registry()
        
        # Sincronizar el archivo JSON
        if start_with_win != settings.get('start_with_windows'):
            settings['start_with_windows'] = start_with_win
            self.config_manager.save_settings(settings)

    def on_open_settings(self):
        """
        Abre el diálogo de configuración global de la aplicación (Settings).
        """
        dialog = SettingsDialog(self, self.config_manager, self.i18n, self)
        dialog.exec()

    def on_about_clicked(self):
        """
        Muestra un cuadro de diálogo informativo (Acerca de) con las versiones del software,
        autor, licencia y enlace al proyecto en GitHub.
        """
        # Obtener versiones dinámicamente
        app_version = self.app.applicationVersion()
        rclone_ver = self.mounter.get_rclone_version()
        winfsp_ver = self.mounter.get_winfsp_version()
        
        github_url = "https://github.com/turulomio/sftp_mounter"
        github_link = f"<a href='{github_url}' style='color: #7c7aeb;'>{github_url}</a>"
        
        # Construir mensaje de versiones
        msg = (
            f"<b>{self.i18n.t('title')}</b><br><br>"
            f"• {self.i18n.t('app_version', version=app_version)}<br>"
            f"• {self.i18n.t('rclone_version', version=rclone_ver)}<br>"
            f"• {self.i18n.t('winfsp_version', version=winfsp_ver)}<br><br>"
            f"• {self.i18n.t('author')}<br>"
            f"• {self.i18n.t('license')}<br>"
            f"• {self.i18n.t('project_url', url=github_link)}<br><br>"
            "<i>Mariano Muñoz &copy; 2026</i>"
        )
        
        QMessageBox.about(self, self.i18n.t('about'), msg)


    def get_startup_registry(self) -> bool:
        """
        Determina si el inicio automático está habilitado consultando el registro de Windows.
        """
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, "SFTPMounter")
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            logger.error(f"Failed to read startup registry key: {e}")
            return False

    def set_startup_registry(self, enabled: bool) -> bool:
        """
        Agrega o remueve la clave del registro de Windows para controlar el inicio automático.
        """
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                if getattr(sys, 'frozen', False):
                    exe_path = f'"{sys.executable}" --minimized'
                else:
                    exe_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}" --minimized'
                
                winreg.SetValueEx(key, "SFTPMounter", 0, winreg.REG_SZ, exe_path)
                logger.info(f"Registry run key set: {exe_path}")
            else:
                try:
                    winreg.DeleteValue(key, "SFTPMounter")
                    logger.info("Registry run key deleted.")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return True
        except Exception as e:
            logger.error(f"Failed to write startup registry key: {e}")
            return False

    def perform_auto_mount(self):
        """
        Scans the connection profiles and starts mounting all profiles
        with auto-mount enabled sequentially.
        """
        if not self.mounter.is_winfsp_installed():
            logger.warning("Auto-mount aborted because WinFsp is not installed.")
            return
            
        profiles = self.config_manager.load_profiles()
        self.auto_mount_queue = [p for p in profiles.values() if p.get('auto_mount', False)]
        self.process_auto_mount_queue()

    def process_auto_mount_queue(self):
        """
        Processes the auto-mount queue sequentially in a non-blocking way.
        """
        if not hasattr(self, 'auto_mount_queue') or not self.auto_mount_queue:
            return
            
        profile = self.auto_mount_queue.pop(0)
        logger.info(f"Auto-mounting profile for host: {profile.get('host')}")
        
        # Find the profile name
        profiles = self.config_manager.load_profiles()
        target_name = None
        for name, p in profiles.items():
            if p.get('host') == profile.get('host') and p.get('drive_letter') == profile.get('drive_letter'):
                target_name = name
                break
        
        if target_name:
            self.on_card_action_clicked(target_name)
        
        if self.auto_mount_queue:
            QTimer.singleShot(500, self.process_auto_mount_queue)
