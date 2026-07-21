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
from PySide6.QtGui import QIcon, QFont, QAction
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QFileDialog, QSystemTrayIcon,
    QMenu, QMessageBox, QFrame, QStyle, QCheckBox
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
    padding: 8px 12px;
    font-size: 13px;
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
    padding: 6px 12px;
    font-size: 13px;
    min-height: 20px;
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
    padding: 10px 16px;
    font-size: 13px;
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
"""

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
        self.current_mounted_drive = None  # Almacena la letra de unidad asignada (ej. 'Z:')
        self.is_connecting = False         # Flag para bloquear re-intentos de conexión

        self.init_ui()
        self.load_profiles_into_combo()
        self.load_global_settings()
        self.check_winfsp_status()
        
        # Iniciar el auto-montaje con un breve retraso (500 ms) para permitir que la interfaz se dibuje
        # completamente en la pantalla antes de iniciar procesos secundarios de red bloqueantes.
        QTimer.singleShot(500, self.perform_auto_mount)

    def init_ui(self):
        """
        Construye la jerarquía completa de widgets y layouts de la ventana.
        Configura los marcos de perfil, credenciales, letras de unidad y botones de acción.
        """
        self.setObjectName("mainWidget")
        self.setMinimumSize(480, 600)
        self.setStyleSheet(QSS_STYLE)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

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
        
        # Botón Acerca de / Versiones
        self.btn_about = QPushButton("ℹ")
        self.btn_about.setObjectName("btnSecondary")
        self.btn_about.setFixedSize(30, 30)
        self.btn_about.clicked.connect(self.on_about_clicked)
        title_layout.addWidget(self.btn_about)
        
        main_layout.addLayout(title_layout)

        # ----------------- SECTION: PROFILE SELECTOR -----------------
        profile_frame = QFrame()
        profile_frame.setObjectName("cardFrame")
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setContentsMargins(12, 12, 12, 12)
        
        self.lbl_profile = QLabel()
        profile_layout.addWidget(self.lbl_profile)
        
        self.cmb_profiles = QComboBox()
        self.cmb_profiles.currentIndexChanged.connect(self.on_profile_selection_changed)
        profile_layout.addWidget(self.cmb_profiles, 1)

        self.btn_delete_profile = QPushButton()
        self.btn_delete_profile.setObjectName("btnDanger")
        self.btn_delete_profile.setFixedWidth(80)
        self.btn_delete_profile.clicked.connect(self.on_delete_profile_clicked)
        profile_layout.addWidget(self.btn_delete_profile)
        main_layout.addWidget(profile_frame)

        # ----------------- SECTION: SFTP CONFIGURATION -----------------
        config_frame = QFrame()
        config_frame.setObjectName("cardFrame")
        config_layout = QGridLayout(config_frame)
        config_layout.setContentsMargins(15, 15, 15, 15)
        config_layout.setSpacing(12)

        # Host
        self.lbl_host = QLabel()
        config_layout.addWidget(self.lbl_host, 0, 0)
        self.txt_host = QLineEdit()
        config_layout.addWidget(self.txt_host, 0, 1, 1, 2)

        # Port
        self.lbl_port = QLabel()
        config_layout.addWidget(self.lbl_port, 1, 0)
        self.txt_port = QLineEdit("22")
        self.txt_port.setFixedWidth(80)
        config_layout.addWidget(self.txt_port, 1, 1, 1, 2)

        # User
        self.lbl_user = QLabel()
        config_layout.addWidget(self.lbl_user, 2, 0)
        self.txt_user = QLineEdit()
        config_layout.addWidget(self.txt_user, 2, 1, 1, 2)

        # Auth Type
        self.lbl_auth = QLabel()
        config_layout.addWidget(self.lbl_auth, 3, 0)
        self.cmb_auth_type = QComboBox()
        self.cmb_auth_type.addItems(["", "", ""])
        self.cmb_auth_type.currentIndexChanged.connect(self.on_auth_type_changed)
        config_layout.addWidget(self.cmb_auth_type, 3, 1, 1, 2)

        # Password (Row 4)
        self.lbl_password = QLabel()
        config_layout.addWidget(self.lbl_password, 4, 0)
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        config_layout.addWidget(self.txt_password, 4, 1, 1, 2)

        # Private Key Path (Row 5 - Hidden by default)
        self.lbl_key_path = QLabel()
        self.lbl_key_path.setVisible(False)
        config_layout.addWidget(self.lbl_key_path, 5, 0)
        
        self.txt_key_path = QLineEdit()
        self.txt_key_path.setVisible(False)
        config_layout.addWidget(self.txt_key_path, 5, 1)

        self.btn_browse_key = QPushButton()
        self.btn_browse_key.setObjectName("btnSecondary")
        self.btn_browse_key.setFixedWidth(80)
        self.btn_browse_key.setVisible(False)
        self.btn_browse_key.clicked.connect(self.on_browse_key_clicked)
        config_layout.addWidget(self.btn_browse_key, 5, 2)

        # Remote Path
        self.lbl_remote_path = QLabel()
        config_layout.addWidget(self.lbl_remote_path, 6, 0)
        self.txt_remote_path = QLineEdit()
        config_layout.addWidget(self.txt_remote_path, 6, 1, 1, 2)

        main_layout.addWidget(config_frame)

        # ----------------- SECTION: MOUNT CONFIGURATION -----------------
        mount_frame = QFrame()
        mount_frame.setObjectName("cardFrame")
        mount_layout = QHBoxLayout(mount_frame)
        mount_layout.setContentsMargins(12, 12, 12, 12)

        self.lbl_local_drive = QLabel()
        mount_layout.addWidget(self.lbl_local_drive)
        self.cmb_drive_letter = QComboBox()
        self.populate_drive_letters()
        mount_layout.addWidget(self.cmb_drive_letter, 1)
        
        self.btn_save_profile = QPushButton()
        self.btn_save_profile.setObjectName("btnSecondary")
        self.btn_save_profile.clicked.connect(self.on_save_profile_clicked)
        mount_layout.addWidget(self.btn_save_profile)

        main_layout.addWidget(mount_frame)

        # ----------------- SECTION: GLOBAL OPTIONS & I18N -----------------
        options_frame = QFrame()
        options_frame.setObjectName("cardFrame")
        options_layout = QVBoxLayout(options_frame)
        options_layout.setContentsMargins(12, 12, 12, 12)
        options_layout.setSpacing(10)
        
        # Checkboxes row
        checks_layout = QHBoxLayout()
        self.chk_start_with_windows = QCheckBox()
        self.chk_start_with_windows.clicked.connect(self.on_start_with_windows_changed)
        checks_layout.addWidget(self.chk_start_with_windows)
        
        self.chk_minimize_to_tray = QCheckBox()
        self.chk_minimize_to_tray.setChecked(True)
        self.chk_minimize_to_tray.clicked.connect(self.on_minimize_to_tray_changed)
        checks_layout.addWidget(self.chk_minimize_to_tray)
        
        self.chk_auto_mount = QCheckBox()
        checks_layout.addWidget(self.chk_auto_mount)
        options_layout.addLayout(checks_layout)
        
        # Language selector row
        lang_layout = QHBoxLayout()
        self.lbl_lang = QLabel()
        lang_layout.addWidget(self.lbl_lang)
        
        self.cmb_lang = QComboBox()
        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            self.cmb_lang.addItem(lang_name, lang_code)
        self.cmb_lang.currentIndexChanged.connect(self.on_language_changed)
        lang_layout.addWidget(self.cmb_lang, 1)
        options_layout.addLayout(lang_layout)
        
        main_layout.addWidget(options_frame)

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

        # ----------------- SECTION: STATUS CARD & ACTIONS -----------------
        status_card = QFrame()
        status_card.setObjectName("statusCard")
        status_card_layout = QVBoxLayout(status_card)
        status_card_layout.setContentsMargins(15, 15, 15, 15)
        status_card_layout.setSpacing(10)

        # Status Label
        status_header_layout = QHBoxLayout()
        self.lbl_status_header = QLabel()
        status_header_layout.addWidget(self.lbl_status_header)
        
        self.lbl_status = QLabel()
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setStyleSheet("color: #8b8b9c;")
        status_header_layout.addWidget(self.lbl_status, 1)
        status_card_layout.addLayout(status_header_layout)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        self.btn_connect = QPushButton()
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        btn_layout.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton()
        self.btn_disconnect.setObjectName("btnDanger")
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self.on_disconnect_clicked)
        btn_layout.addWidget(self.btn_disconnect)
        status_card_layout.addLayout(btn_layout)

        main_layout.addWidget(status_card)

        # Inicializar los textos localizados en la interfaz
        self.retranslate_ui()

        # Setup System Tray
        self.setup_system_tray()

    def retranslate_ui(self):
        """
        Actualiza dinámicamente todos los textos visibles de la UI según el idioma seleccionado.
        Esto permite cambiar el idioma en caliente sin necesidad de reiniciar la aplicación.
        """
        # Título de ventana y etiquetas fijas
        self.setWindowTitle(self.i18n.t('title'))
        self.lbl_title.setText(self.i18n.t('title'))
        self.lbl_profile.setText(self.i18n.t('profile'))
        self.btn_delete_profile.setText(self.i18n.t('delete'))
        self.lbl_host.setText(self.i18n.t('host'))
        self.txt_host.setPlaceholderText(self.i18n.t('host_placeholder'))
        self.lbl_port.setText(self.i18n.t('port'))
        self.lbl_user.setText(self.i18n.t('user'))
        self.txt_user.setPlaceholderText(self.i18n.t('user_placeholder'))
        self.lbl_auth.setText(self.i18n.t('auth'))
        self.lbl_key_path.setText(self.i18n.t('ssh_key'))
        self.txt_key_path.setPlaceholderText(self.i18n.t('ssh_key_placeholder'))
        self.btn_browse_key.setText(self.i18n.t('browse'))
        self.lbl_remote_path.setText(self.i18n.t('remote_path'))
        self.txt_remote_path.setPlaceholderText(self.i18n.t('remote_path_placeholder'))
        self.lbl_local_drive.setText(self.i18n.t('local_drive'))
        self.btn_save_profile.setText(self.i18n.t('save_profile'))
        self.chk_start_with_windows.setText(self.i18n.t('start_with_win'))
        self.chk_minimize_to_tray.setText(self.i18n.t('minimize_to_tray'))
        self.chk_auto_mount.setText(self.i18n.t('auto_mount'))
        self.lbl_winfsp_missing.setText(self.i18n.t('winfsp_missing_card'))
        self.btn_install_winfsp.setText(self.i18n.t('install_winfsp'))
        self.lbl_status_header.setText(self.i18n.t('status'))
        self.lbl_lang.setText(self.i18n.t('lang_selector'))
        self.btn_connect.setText(self.i18n.t('connect'))
        self.btn_disconnect.setText(self.i18n.t('disconnect'))
        self.btn_about.setToolTip(self.i18n.t('about'))
        
        # Combo boxes items
        self.cmb_auth_type.setItemText(0, self.i18n.t('auth_password'))
        self.cmb_auth_type.setItemText(1, self.i18n.t('auth_key_no_pass'))
        self.cmb_auth_type.setItemText(2, self.i18n.t('auth_key_pass'))
        
        # Sincronizar combobox de perfiles
        current_profile_idx = self.cmb_profiles.currentIndex()
        self.load_profiles_into_combo()
        if current_profile_idx >= 0 and current_profile_idx < self.cmb_profiles.count():
            self.cmb_profiles.blockSignals(True)
            self.cmb_profiles.setCurrentIndex(current_profile_idx)
            self.cmb_profiles.blockSignals(False)
        
        # Asegurar que el label de la contraseña/frase de paso refleje el cambio de idioma
        self.on_auth_type_changed(self.cmb_auth_type.currentIndex())
        
        # Sincronizar el label de estado
        self.update_status_label()
        
        # Sincronizar aviso de WinFsp
        self.check_winfsp_status()
        
        # Re-inicializar el menú contextual de la bandeja de sistema
        if hasattr(self, 'tray_icon'):
            self.setup_system_tray()

    def update_status_label(self):
        """
        Actualiza el texto del label de estado (lbl_status) según la conexión activa
        y aplica estilos de color correspondientes.
        """
        if self.current_mounted_drive:
            self.lbl_status.setText(self.i18n.t('status_mounted', drive=self.current_mounted_drive.upper()))
            self.lbl_status.setStyleSheet("color: #50fa7b;")
            self.btn_disconnect.setEnabled(True)
            self.btn_connect.setEnabled(False)
        elif self.is_connecting:
            self.lbl_status.setText(self.i18n.t('status_connecting'))
            self.lbl_status.setStyleSheet("color: #ffb86c;")
            self.btn_disconnect.setEnabled(False)
            self.btn_connect.setEnabled(False)
        else:
            self.lbl_status.setText(self.i18n.t('status_disconnected'))
            self.lbl_status.setStyleSheet("color: #8b8b9c;")
            self.btn_disconnect.setEnabled(False)
            self.btn_connect.setEnabled(self.mounter.is_winfsp_installed())

    def check_winfsp_status(self):
        """
        Verifica el estado del controlador WinFsp en el sistema y actualiza los componentes visuales.
        
        Si no se detecta el controlador en Windows, deshabilita el botón de conexión y
        muestra una tarjeta informativa con la opción de instalar el driver.
        """
        installed = self.mounter.is_winfsp_installed()
        if installed:
            self.lbl_winfsp_warning.setText(self.i18n.t('winfsp_ok'))
            self.lbl_winfsp_warning.setStyleSheet("color: #50fa7b; font-size: 11px;")
            self.winfsp_card.setVisible(False)
            if not self.is_connecting and not self.current_mounted_drive:
                self.btn_connect.setEnabled(True)
        else:
            self.lbl_winfsp_warning.setText(self.i18n.t('winfsp_not_installed'))
            self.lbl_winfsp_warning.setStyleSheet("color: #ff5555; font-size: 11px;")
            self.winfsp_card.setVisible(True)
            self.btn_connect.setEnabled(False)

    def populate_drive_letters(self):
        """
        Llena el selector de unidades de red (ComboBox) con las letras libres de Windows.
        
        Escanea de forma descendente (de la Z: a la D:) omitiendo las letras de volumen
        que ya se encuentren ocupadas por el sistema (ej. discos duros, lectores USB).
        En sistemas UNIX, añade rutas de montaje por defecto dentro del directorio del usuario.
        """
        self.cmb_drive_letter.clear()
        if os.name == 'nt':
            for char in range(ord('Z'), ord('C'), -1):
                letter = f"{chr(char)}:"
                if not self.mounter.is_drive_letter_in_use(letter):
                    self.cmb_drive_letter.addItem(letter)
        else:
            self.cmb_drive_letter.addItem(os.path.expanduser("~/mnt/sftp_drive"))
            self.cmb_drive_letter.addItem(os.path.expanduser("~/mnt/sftp_test"))

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
        self.lbl_status.setText(self.i18n.t('installing_winfsp'))
        self.lbl_status.setStyleSheet("color: #ffb86c;")
        self.app.processEvents()
        
        success = self.mounter.install_winfsp()
        
        self.btn_install_winfsp.setEnabled(True)
        self.check_winfsp_status()
        
        if success:
            QMessageBox.information(
                self, self.i18n.t('install_winfsp_ok_title'), self.i18n.t('install_winfsp_ok_msg')
            )
            self.update_status_label()
        else:
            QMessageBox.critical(
                self, self.i18n.t('install_winfsp_fail_title'), self.i18n.t('install_winfsp_fail_msg')
            )
            self.lbl_status.setText(self.i18n.t('status_error'))
            self.lbl_status.setStyleSheet("color: #ff5555;")

    def on_connect_clicked(self):
        """
        Inicia de forma asíncrona la conexión SFTP y monta la unidad de red.
        """
        data = self.get_current_form_data()
        
        if not data['host'] or not data['user']:
            QMessageBox.warning(self, self.i18n.t('error_incomplete_title'), self.i18n.t('error_incomplete_msg'))
            return

        self.is_connecting = True
        self.set_ui_enabled(False)
        self.lbl_status.setText(self.i18n.t('status_connecting'))
        self.lbl_status.setStyleSheet("color: #ffb86c;")
        self.app.processEvents()

        success, message = self.mounter.mount_sftp(data)

        self.is_connecting = False
        if success:
            self.current_mounted_drive = data['drive_letter']
            self.update_status_label()
            
            self.tray_icon.showMessage(
                "SFTP Drive Mounter",
                self.i18n.t('connection_ok_msg', drive=self.current_mounted_drive.upper()),
                QSystemTrayIcon.Information,
                3000
            )
        else:
            # Si el error indica que la unidad está en uso, mostramos mensaje localizado de net use
            display_msg = message
            if "already in use" in message or "ya está en uso" in message:
                display_msg = self.i18n.t('net_use_in_use', drive=data['drive_letter'].upper())
                
            QMessageBox.critical(self, self.i18n.t('connection_fail_title'), display_msg)
            self.lbl_status.setText(self.i18n.t('status_error'))
            self.lbl_status.setStyleSheet("color: #ff5555;")
            self.set_ui_enabled(True)
            self.btn_disconnect.setEnabled(False)
            self.btn_connect.setEnabled(True)

    def on_disconnect_clicked(self):
        """
        Desmonta la unidad remota activa y restaura el estado.
        """
        if not self.current_mounted_drive:
            return

        self.lbl_status.setText(self.i18n.t('status_unmounting'))
        self.lbl_status.setStyleSheet("color: #ffb86c;")
        self.btn_disconnect.setEnabled(False)
        self.app.processEvents()

        success = self.mounter.unmount_sftp(self.current_mounted_drive)

        if success:
            self.tray_icon.showMessage(
                "SFTP Drive Mounter",
                self.i18n.t('disconnection_ok_msg', drive=self.current_mounted_drive.upper()),
                QSystemTrayIcon.Information,
                2000
            )
            self.current_mounted_drive = None
            self.update_status_label()
            self.populate_drive_letters()
            self.set_ui_enabled(True)
        else:
            QMessageBox.warning(self, self.i18n.t('unmount_warning_title'), self.i18n.t('unmount_warning_msg'))
            self.lbl_status.setText(self.i18n.t('status_unmount_error'))
            self.lbl_status.setStyleSheet("color: #ff5555;")
            self.btn_disconnect.setEnabled(True)

    def set_ui_enabled(self, enabled):
        """
        Habilita o deshabilita los campos del formulario.
        """
        self.cmb_profiles.setEnabled(enabled)
        self.btn_delete_profile.setEnabled(enabled and self.cmb_profiles.currentIndex() > 0)
        self.txt_host.setEnabled(enabled)
        self.txt_port.setEnabled(enabled)
        self.txt_user.setEnabled(enabled)
        self.cmb_auth_type.setEnabled(enabled)
        self.txt_password.setEnabled(enabled)
        self.txt_key_path.setEnabled(enabled)
        self.btn_browse_key.setEnabled(enabled)
        self.txt_remote_path.setEnabled(enabled)
        self.cmb_drive_letter.setEnabled(enabled)
        self.btn_save_profile.setEnabled(enabled)
        self.cmb_lang.setEnabled(enabled)

    # ----------------- SYSTEM TRAY MANAGEMENT (BANDEJA DE SISTEMA) -----------------
    def setup_system_tray(self):
        """
        Crea e inicializa el icono de la bandeja del sistema (System Tray Icon).
        """
        if not hasattr(self, 'tray_icon'):
            self.tray_icon = QSystemTrayIcon(self)
            
            icon = self.style().standardIcon(QStyle.SP_DriveHDIcon)
            self.tray_icon.setIcon(icon)
            self.setWindowIcon(icon)
            self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # Crear o actualizar el menú contextual con textos localizados
        tray_menu = QMenu()
        
        action_show = QAction(self.i18n.t('show_window'), self)
        action_show.triggered.connect(self.show_normal)
        tray_menu.addAction(action_show)
        
        action_unmount = QAction(self.i18n.t('unmount_all'), self)
        action_unmount.triggered.connect(self.force_unmount_all)
        tray_menu.addAction(action_unmount)
        
        tray_menu.addSeparator()
        
        action_exit = QAction(self.i18n.t('exit'), self)
        action_exit.triggered.connect(self.close_app)
        tray_menu.addAction(action_exit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

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
        Forza la desconexión de la unidad SFTP mapeada activa.
        """
        if self.current_mounted_drive:
            self.on_disconnect_clicked()

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
            if self.isMinimized() and self.chk_minimize_to_tray.isChecked():
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
        if self.chk_minimize_to_tray.isChecked() and self.current_mounted_drive:
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
        self.chk_minimize_to_tray.setChecked(min_to_tray)
        
        # 2. Iniciar con Windows (leer del registro de Windows)
        start_with_win = self.get_startup_registry()
        self.chk_start_with_windows.setChecked(start_with_win)
        
        # Sincronizar el selector de idioma en la interfaz
        lang_idx = self.cmb_lang.findData(self.i18n.get_language())
        if lang_idx >= 0:
            self.cmb_lang.blockSignals(True)
            self.cmb_lang.setCurrentIndex(lang_idx)
            self.cmb_lang.blockSignals(False)
        
        # Sincronizar el archivo JSON
        if start_with_win != settings.get('start_with_windows'):
            settings['start_with_windows'] = start_with_win
            self.config_manager.save_settings(settings)

    def on_minimize_to_tray_changed(self):
        """
        Slot gatillado cuando se altera la casilla 'Minimizar al cerrar'.
        """
        settings = self.config_manager.load_settings()
        settings['minimize_to_tray'] = self.chk_minimize_to_tray.isChecked()
        self.config_manager.save_settings(settings)

    def on_start_with_windows_changed(self):
        """
        Slot gatillado cuando se activa/desactiva la casilla 'Iniciar con Windows'.
        """
        checked = self.chk_start_with_windows.isChecked()
        success = self.set_startup_registry(checked)
        if success:
            settings = self.config_manager.load_settings()
            settings['start_with_windows'] = checked
            self.config_manager.save_settings(settings)
        else:
            self.chk_start_with_windows.setChecked(not checked)
            QMessageBox.critical(
                self, self.i18n.t('config_error_title'), self.i18n.t('config_error_msg')
            )

    def on_language_changed(self, index):
        """
        Slot gatillado cuando el usuario cambia el idioma seleccionado.
        """
        lang_code = self.cmb_lang.itemData(index)
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
        self.lbl_status.setText(self.i18n.t('versions').upper() + "...")
        self.app.processEvents()
        
        # Obtener versiones dinámicamente
        app_version = self.app.applicationVersion()
        rclone_ver = self.mounter.get_rclone_version()
        winfsp_ver = self.mounter.get_winfsp_version()
        
        # Restaurar texto de estado
        self.update_status_label()
        
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
            "<i>Antigravity &copy; 2026</i>"
        )
        
        QMessageBox.about(self, self.i18n.t('about'), msg)


    def get_startup_registry(self) -> bool:
        """
        Comprueba si la entrada de inicio automático de SFTPMounter existe en el Registro de Windows.
        """
        if os.name != 'nt':
            return False
            
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
        if os.name != 'nt':
            logger.info("Not on Windows, skipping registry startup key modification.")
            return True
            
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
        Escanea la colección de perfiles almacenados e inicia el montaje del primer perfil
        que tenga marcada la casilla de 'Autoconectar' (auto_mount = True).
        """
        if not self.mounter.is_winfsp_installed():
            logger.warning("Auto-mount aborted because WinFsp is not installed.")
            return
            
        profiles = self.config_manager.load_profiles()
        for name, profile in profiles.items():
            if profile.get('auto_mount', False):
                logger.info(f"Auto-mounting profile: {name}")
                idx = self.cmb_profiles.findText(name)
                if idx >= 0:
                    self.cmb_profiles.setCurrentIndex(idx)
                    self.on_connect_clicked()
                break
