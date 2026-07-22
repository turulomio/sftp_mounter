"""
Interfaz gráfica de usuario (GUI) para SFTP Mounter basada en PySide6.

Este módulo define la ventana principal de la aplicación (`MainWindow`), que implementa:
1. Un formulario completo para perfiles SFTP (servidor, puerto, credenciales de contraseña y clave SSH).
2. Un diseño visual premium en modo oscuro utilizando QSS (Qt Style Sheets).
3. Mecanismos de interacción asíncrona mediante señales y slots de Qt.
4. Integración con la bandeja del sistema (System Tray Icon) para minimizar y cerrar en segundo plano.
5. Persistencia de ajustes globales como el inicio automático en Windows a través del registro.

Para nuevos desarrolladores:
- PySide6 funciona mediante un sistema de hilos y bucle de eventos. Las operaciones pesadas
  se invocan a través de la clase `Mounter` que delega en subprocesos para no congelar la UI.
- La estética se maneja mediante el string `QSS_STYLE`. Modifica este string si necesitas
  personalizar fuentes, colores o márgenes.
"""

import os
import sys
import logging
from PySide6.QtCore import Qt, QSize, QTimer
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
            self.txt_log.setPlainText(f"Error al leer el archivo de logs: {e}")

    def clear_log(self):
        if not self.log_path:
            return
        try:
            with open(self.log_path, 'w', encoding='utf-8') as f:
                f.truncate(0)
            self.load_log_content()
            QMessageBox.information(self, self.i18n.t('log_viewer_title'), self.i18n.t('log_cleared_msg'))
        except Exception as e:
            QMessageBox.critical(self, self.i18n.t('log_viewer_title'), f"Error al limpiar logs: {e}")

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
            self.txt_content.setPlainText(f"Error al leer known_hosts: {e}")


class ProfileManagerDialog(QDialog):
    """
    Diálogo para crear, editar y eliminar perfiles SFTP de manera dedicada.
    Presenta una lista de perfiles a la izquierda y el formulario de edición a la derecha.
    """
    def __init__(self, parent=None, config_manager=None, i18n=None, active_mounts=None, initial_profile=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.i18n = i18n
        self.active_mounts = active_mounts or {}
        self.current_editing_profile = None
        self.initial_profile = initial_profile

        self.setWindowTitle(self.i18n.t('manage_profiles'))
        self.setMinimumSize(720, 520)
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
        config_layout.addWidget(self.txt_profile_name, 0, 1, 1, 2)

        # Host
        self.lbl_host = QLabel(self.i18n.t('host'))
        config_layout.addWidget(self.lbl_host, 1, 0)
        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText(self.i18n.t('host_placeholder'))
        config_layout.addWidget(self.txt_host, 1, 1, 1, 2)

        # Port
        self.lbl_port = QLabel(self.i18n.t('port'))
        config_layout.addWidget(self.lbl_port, 2, 0)
        self.txt_port = QLineEdit("22")
        self.txt_port.setFixedWidth(80)
        config_layout.addWidget(self.txt_port, 2, 1, 1, 2)

        # User
        self.lbl_user = QLabel(self.i18n.t('user'))
        config_layout.addWidget(self.lbl_user, 3, 0)
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText(self.i18n.t('user_placeholder'))
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
        config_layout.addWidget(self.cmb_auth_type, 4, 1, 1, 2)

        # Password / Passphrase
        self.lbl_password = QLabel(self.i18n.t('password'))
        config_layout.addWidget(self.lbl_password, 5, 0)
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        config_layout.addWidget(self.txt_password, 5, 1, 1, 2)

        # SSH Key Path
        self.lbl_key_path = QLabel(self.i18n.t('ssh_key'))
        self.lbl_key_path.setVisible(False)
        config_layout.addWidget(self.lbl_key_path, 6, 0)
        self.txt_key_path = QLineEdit()
        self.txt_key_path.setPlaceholderText(self.i18n.t('ssh_key_placeholder'))
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
        config_layout.addWidget(self.txt_remote_path, 7, 1, 1, 2)

        # Local Drive Letter
        self.lbl_local_drive = QLabel(self.i18n.t('local_drive'))
        config_layout.addWidget(self.lbl_local_drive, 8, 0)
        self.cmb_drive_letter = QComboBox()
        self.populate_drive_letters()
        config_layout.addWidget(self.cmb_drive_letter, 8, 1, 1, 2)

        # Auto-mount
        self.chk_auto_mount = QCheckBox(self.i18n.t('auto_mount'))
        config_layout.addWidget(self.chk_auto_mount, 9, 1, 1, 2)

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
            QMessageBox.warning(self, self.i18n.t('error_save_title'), f"El perfil '{name}' ya existe.")
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
            'auto_mount': self.chk_auto_mount.isChecked()
        }

        # Si se cambió el nombre de un perfil existente, eliminar el viejo
        if self.current_editing_profile and self.current_editing_profile != name:
            self.config_manager.delete_profile(self.current_editing_profile)

        if self.config_manager.save_profile(name, profile_data):
            self.current_editing_profile = name
            self.load_profile_list()
            # Seleccionar el ítem recién guardado
            items = self.lst_profiles.findItems(name, Qt.MatchExactly)
            if items:
                self.lst_profiles.setCurrentItem(items[0])
            QMessageBox.information(self, self.i18n.t('profile_saved_title'), self.i18n.t('profile_saved_msg', profile_name=name))
        else:
            QMessageBox.critical(self, self.i18n.t('error_save_title'), self.i18n.t('error_save_failed'))


class MainWindow(QWidget):
    """
    Ventana principal de la aplicación. Administra los controles visuales,
    la validación de los formularios de conexión y los eventos del sistema (bandeja, inicio, etc.).
    """
    def __init__(self, app):
        """
        Inicializa la interfaz gráfica, enlaza los gestores de configuración y montaje,
        y programa el auto-montaje inicial si corresponde.
        
        Args:
            app (QApplication): Instancia de la aplicación Qt en ejecución.
        """
        super().__init__()
        self.app = app
        self.config_manager = ConfigManager()
        self.mounter = Mounter()
        
        # Cargar idioma preferido de la configuración o detectar automáticamente
        settings = self.config_manager.load_settings()
        saved_lang = settings.get('language', '')
        self.i18n = I18N(default_lang=saved_lang if saved_lang else 'es')
        
        # Variables de estado interno
        self.is_connecting = False         # Flag para bloquear re-intentos de conexión
        self.log_viewer = None
        self.log_path = os.path.join(self.mounter.app_dir, 'mounts.log')
        self.known_hosts_viewer = None

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

        # Iniciar con Windows
        self.act_start_with_win = QAction(self)
        self.act_start_with_win.setCheckable(True)
        self.act_start_with_win.triggered.connect(self.on_start_with_windows_changed)
        self.menu_options.addAction(self.act_start_with_win)
        
        # Minimizar al cerrar
        self.act_minimize_to_tray = QAction(self)
        self.act_minimize_to_tray.setCheckable(True)
        self.act_minimize_to_tray.triggered.connect(self.on_minimize_to_tray_changed)
        self.menu_options.addAction(self.act_minimize_to_tray)
        
        self.menu_options.addSeparator()
        
        # Idioma Submenu
        self.menu_language = QMenu(self)
        self.menu_options.addMenu(self.menu_language)
        
        self.lang_action_group = QActionGroup(self)
        self.lang_action_group.setExclusive(True)
        self.lang_action_group.triggered.connect(self.on_menu_language_triggered)
        self.lang_actions = {}
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            action = QAction(lang_name, self)
            action.setCheckable(True)
            action.setActionGroup(self.lang_action_group)
            action.setData(lang_code)
            self.menu_language.addAction(action)
            self.lang_actions[lang_code] = action
            
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
        Actualiza el aspecto de una tarjeta de perfil según si la unidad correspondiente está montada.
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
        Gatillado al pulsar el botón de acción en la tarjeta de un perfil.
        Si la unidad está montada, la desconecta. De lo contrario, la conecta.
        """
        card = self.profile_cards.get(profile_name)
        if not card:
            return

        profile = card['profile']
        drive = profile.get('drive_letter', '')

        if drive in self.mounter.active_mounts:
            # Desconectar
            card['lbl_status'].setText(self.i18n.t('status_unmounting'))
            card['lbl_status'].setStyleSheet("color: #ffb86c; font-size: 12px; font-weight: bold;")
            card['btn_action'].setEnabled(False)
            self.app.processEvents()

            self.log_action(profile_name, f"Iniciando desmontaje de la unidad {drive.upper()}")
            success = self.mounter.unmount_sftp(drive)
            if success:
                self.log_action(profile_name, f"Unidad {drive.upper()} desmontada con éxito")
                self.tray_icon.showMessage(
                    "SFTP Drive Mounter",
                    self.i18n.t('disconnection_ok_msg', drive=drive.upper()),
                    QSystemTrayIcon.Information,
                    2000
                )
            else:
                self.log_action(profile_name, f"Error al desmontar la unidad {drive.upper()}")
                QMessageBox.warning(self, self.i18n.t('unmount_warning_title'), self.i18n.t('unmount_warning_msg'))

            self.update_card_status(profile_name)
            self.setup_system_tray()
        else:
            # Conectar
            card['lbl_status'].setText(self.i18n.t('status_connecting'))
            card['lbl_status'].setStyleSheet("color: #ffb86c; font-size: 12px; font-weight: bold;")
            card['btn_action'].setEnabled(False)
            self.app.processEvents()

            self.log_action(profile_name, f"Iniciando conexión/montaje en {drive.upper()}")
            success, message = self.mounter.mount_sftp(profile)

            # Si falla debido a verificación de clave de host SSH (host key verification/unknown host)
            is_host_key_error = any(term in message.lower() for term in [
                "host key", "key verification", "hostkey", "host key fingerprint", "strictly host key checking", "knownhosts", "key is unknown"
            ]) and "no host key validation is being performed" not in message.lower()


            if not success and is_host_key_error:
                self.log_action(profile_name, f"Fallo por clave de host desconocida. Solicitando confirmación al usuario.")
                reply = QMessageBox.question(
                    self,
                    self.i18n.t('host_key_unknown_title'),
                    self.i18n.t('host_key_unknown_msg', host=profile.get('host', '')),
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.log_action(profile_name, f"Usuario aceptó la clave de host. Reintentando montaje en {drive.upper()}")
                    card['lbl_status'].setText(self.i18n.t('status_connecting'))
                    self.app.processEvents()
                    success, message = self.mounter.mount_sftp(profile, accept_host_key=True)

            if success:
                self.log_action(profile_name, f"Montaje en {drive.upper()} completado y verificado con éxito")
                self.tray_icon.showMessage(
                    "SFTP Drive Mounter",
                    self.i18n.t('connection_ok_msg', drive=drive.upper()),
                    QSystemTrayIcon.Information,
                    3000
                )
            else:
                self.log_action(profile_name, f"Error al realizar montaje en {drive.upper()}: {message}")
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
        Abre el diálogo de gestión de perfiles con un perfil específico seleccionado por defecto.
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
        Abre la ventana independiente no modal del visor de logs.
        """
        if self.log_viewer is None or not self.log_viewer.isVisible():
            self.log_viewer = LogViewerDialog(parent=self, log_path=self.log_path, i18n=self.i18n)
            self.log_viewer.show()
        else:
            self.log_viewer.activateWindow()
            self.log_viewer.raise_()

    def on_open_known_hosts_viewer(self):
        """
        Abre la ventana independiente no modal del visor de known_hosts.
        """
        if self.known_hosts_viewer is None or not self.known_hosts_viewer.isVisible():
            self.known_hosts_viewer = KnownHostsViewerDialog(parent=self, i18n=self.i18n)
            self.known_hosts_viewer.show()
        else:
            self.known_hosts_viewer.activateWindow()
            self.known_hosts_viewer.raise_()

    def log_action(self, profile_name: str, message: str):
        """
        Registra un evento de montaje en el archivo de logs con formato datetime(formato iso) Nombre del montaje y log.
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
        self.menu_help.setTitle(self.i18n.t('menu_help'))
        self.act_start_with_win.setText(self.i18n.t('start_with_win'))
        self.act_minimize_to_tray.setText(self.i18n.t('minimize_to_tray'))
        self.menu_language.setTitle(self.i18n.t('menu_language'))
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
        Llena el selector de unidades de red (ComboBox) con las letras libres de Windows.
        
        Escanea de forma descendente (de la Z: a la D:) omitiendo las letras de volumen
        que ya se encuentren ocupadas por el sistema (ej. discos duros, lectores USB).
        En sistemas UNIX, añade rutas de montaje por defecto dentro del directorio del usuario.
        """
        self.cmb_drive_letter.clear()
        for char in range(ord('Z'), ord('C'), -1):
            letter = f"{chr(char)}:"
            if not self.mounter.is_drive_letter_in_use(letter):
                self.cmb_drive_letter.addItem(letter)

    def load_profiles_into_combo(self):
        """
        Consulta el gestor de configuración para recuperar los perfiles y cargarlos en la interfaz.
        Siempre añade la opción '<Nuevo Perfil>' (traducida) en el primer índice.
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
        Slot gatillado cuando el usuario selecciona un perfil diferente de la lista.
        
        Si se selecciona el primer elemento (índice <= 0), se limpian los campos del formulario.
        En caso contrario, se cargan y completan los datos del perfil seleccionado.
        
        Args:
            index (int): Índice seleccionado en el ComboBox de perfiles.
        """
        if index <= 0:
            # Limpiar entradas para un perfil nuevo
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
        elif index == 2:  # Llave + Frase de paso
            self.lbl_password.setText(self.i18n.t('passphrase'))
            self.lbl_password.setVisible(True)
            self.txt_password.setVisible(True)
            self.lbl_key_path.setVisible(True)
            self.txt_key_path.setVisible(True)
            self.btn_browse_key.setVisible(True)

    def on_browse_key_clicked(self):
        """
        Abre un cuadro de diálogo del explorador de archivos nativo de Qt 
        para que el usuario seleccione la ruta de su llave privada SSH.
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.i18n.t('ssh_key'), "", "All Files (*);;Key Files (*.pem *.key id_rsa)"
        )
        if file_path:
            self.txt_key_path.setText(file_path)

    def get_current_form_data(self):
        """
        Recopila todos los datos ingresados en el formulario de la UI.
        
        Returns:
            dict: Parámetros listos para su persistencia o procesamiento.
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
        Valida y almacena los datos actuales del formulario como un perfil guardado.
        Si es un perfil nuevo, solicita un nombre descriptivo al usuario mediante un QInputDialog.
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
        Elimina de forma permanente el perfil de conexión que está seleccionado.
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

    def changeEvent(self, event):
        """
        Intercepta los eventos de cambio de estado de la ventana en PySide6.
        """
        if event.type() == event.type().WindowStateChange:
            if self.isMinimized() and self.act_minimize_to_tray.isChecked():
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
        if self.act_minimize_to_tray.isChecked() and len(self.mounter.active_mounts) > 0:
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
        Carga la configuración global desde el config_manager y la aplica a los controles de la UI.
        """
        settings = self.config_manager.load_settings()
        
        # 1. Minimizar a la bandeja (por defecto True)
        min_to_tray = settings.get('minimize_to_tray', True)
        self.act_minimize_to_tray.setChecked(min_to_tray)
        
        # 2. Iniciar con Windows (leer del registro de Windows)
        start_with_win = self.get_startup_registry()
        self.act_start_with_win.setChecked(start_with_win)
        
        # Sincronizar el selector de idioma en el menú
        current_lang = self.i18n.get_language()
        if current_lang in self.lang_actions:
            self.lang_actions[current_lang].setChecked(True)
        
        # Sincronizar el archivo JSON
        if start_with_win != settings.get('start_with_windows'):
            settings['start_with_windows'] = start_with_win
            self.config_manager.save_settings(settings)

    def on_minimize_to_tray_changed(self):
        """
        Slot gatillado cuando se altera la casilla 'Minimizar al cerrar'.
        """
        settings = self.config_manager.load_settings()
        settings['minimize_to_tray'] = self.act_minimize_to_tray.isChecked()
        self.config_manager.save_settings(settings)

    def on_start_with_windows_changed(self):
        """
        Slot gatillado cuando se activa/desactiva la casilla 'Iniciar con Windows'.
        """
        checked = self.act_start_with_win.isChecked()
        success = self.set_startup_registry(checked)
        if success:
            settings = self.config_manager.load_settings()
            settings['start_with_windows'] = checked
            self.config_manager.save_settings(settings)
        else:
            self.act_start_with_win.setChecked(not checked)
            QMessageBox.critical(
                self, self.i18n.t('config_error_title'), self.i18n.t('config_error_msg')
            )

    def on_menu_language_triggered(self, action):
        """
        Slot gatillado cuando el usuario cambia el idioma seleccionado en el menú.
        """
        lang_code = action.data()
        if lang_code:
            self.i18n.set_language(lang_code)
            
            # Guardar ajuste persistente
            settings = self.config_manager.load_settings()
            settings['language'] = lang_code
            self.config_manager.save_settings(settings)
            
            # Forzar re-traducción de la UI
            self.retranslate_ui()

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
            "<i>Turulomio &copy; 2026</i>"
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
        Escanea la colección de perfiles almacenados e inicia el montaje de todos los perfiles
        que tengan marcada la casilla de 'Autoconectar' (auto_mount = True) de forma secuencial.
        """
        if not self.mounter.is_winfsp_installed():
            logger.warning("Auto-mount aborted because WinFsp is not installed.")
            return
            
        profiles = self.config_manager.load_profiles()
        self.auto_mount_queue = [p for p in profiles.values() if p.get('auto_mount', False)]
        self.process_auto_mount_queue()

    def process_auto_mount_queue(self):
        """
        Procesa de forma secuencial y no bloqueante la cola de perfiles a auto-conectar.
        """
        if not hasattr(self, 'auto_mount_queue') or not self.auto_mount_queue:
            return
            
        profile = self.auto_mount_queue.pop(0)
        logger.info(f"Auto-mounting profile for host: {profile.get('host')}")
        
        # Buscar el nombre del perfil
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
