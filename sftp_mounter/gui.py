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
        
        # Variables de estado interno
        self.current_mounted_drive = None  # Almacena la letra de unidad asignada (ej. 'Z:')
        self.is_connecting = False         # Flag para bloquear re-intentos concurrentes de conexión

        self.init_ui()
        self.load_profiles_into_combo()
        self.check_winfsp_status()
        self.load_global_settings()
        
        # Iniciar el auto-montaje con un breve retraso (500 ms) para permitir que la interfaz se dibuje
        # completamente en la pantalla antes de iniciar procesos secundarios de red bloqueantes.
        QTimer.singleShot(500, self.perform_auto_mount)

    def init_ui(self):
        """
        Construye la jerarquía completa de widgets y layouts de la ventana.
        Configura los marcos de perfil, credenciales, letras de unidad y botones de acción.
        """
        self.setObjectName("mainWidget")
        self.setWindowTitle("SFTP Drive Mounter")
        self.setMinimumSize(480, 560)
        self.setStyleSheet(QSS_STYLE)

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header Title
        title_layout = QHBoxLayout()
        title_label = QLabel("SFTP Mounter")
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)
        
        # WinFsp status header warning
        self.lbl_winfsp_warning = QLabel("")
        self.lbl_winfsp_warning.setStyleSheet("color: #ffb86c; font-size: 11px;")
        self.lbl_winfsp_warning.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_layout.addWidget(self.lbl_winfsp_warning)
        main_layout.addLayout(title_layout)

        # ----------------- SECTION: PROFILE SELECTOR -----------------
        profile_frame = QFrame()
        profile_frame.setObjectName("cardFrame")
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setContentsMargins(12, 12, 12, 12)
        
        profile_layout.addWidget(QLabel("Perfil:"))
        self.cmb_profiles = QComboBox()
        self.cmb_profiles.currentIndexChanged.connect(self.on_profile_selection_changed)
        profile_layout.addWidget(self.cmb_profiles, 1)

        self.btn_delete_profile = QPushButton("Eliminar")
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
        config_layout.addWidget(QLabel("Servidor (Host):"), 0, 0)
        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText("sftp.example.com o IP")
        config_layout.addWidget(self.txt_host, 0, 1, 1, 2)

        # Port
        config_layout.addWidget(QLabel("Puerto:"), 1, 0)
        self.txt_port = QLineEdit("22")
        self.txt_port.setFixedWidth(80)
        config_layout.addWidget(self.txt_port, 1, 1, 1, 2)

        # User
        config_layout.addWidget(QLabel("Usuario:"), 2, 0)
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("username")
        config_layout.addWidget(self.txt_user, 2, 1, 1, 2)

        # Auth Type
        config_layout.addWidget(QLabel("Autenticación:"), 3, 0)
        self.cmb_auth_type = QComboBox()
        self.cmb_auth_type.addItems([
            "Contraseña", 
            "Llave Privada SSH (sin contraseña)", 
            "Llave Privada SSH + Frase de paso"
        ])
        self.cmb_auth_type.currentIndexChanged.connect(self.on_auth_type_changed)
        config_layout.addWidget(self.cmb_auth_type, 3, 1, 1, 2)

        # Password (Row 4)
        self.lbl_password = QLabel("Contraseña:")
        config_layout.addWidget(self.lbl_password, 4, 0)
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.Password)
        config_layout.addWidget(self.txt_password, 4, 1, 1, 2)

        # Private Key Path (Row 5 - Hidden by default)
        self.lbl_key_path = QLabel("Llave SSH:")
        self.lbl_key_path.setVisible(False)
        config_layout.addWidget(self.lbl_key_path, 5, 0)
        
        self.txt_key_path = QLineEdit()
        self.txt_key_path.setPlaceholderText("Ruta al archivo .key / .pem")
        self.txt_key_path.setVisible(False)
        config_layout.addWidget(self.txt_key_path, 5, 1)

        self.btn_browse_key = QPushButton("Buscar...")
        self.btn_browse_key.setObjectName("btnSecondary")
        self.btn_browse_key.setFixedWidth(80)
        self.btn_browse_key.setVisible(False)
        self.btn_browse_key.clicked.connect(self.on_browse_key_clicked)
        config_layout.addWidget(self.btn_browse_key, 5, 2)

        # Remote Path
        config_layout.addWidget(QLabel("Ruta Remota:"), 6, 0)
        self.txt_remote_path = QLineEdit()
        self.txt_remote_path.setPlaceholderText("Ej: /var/www o dejar vacío para Home")
        config_layout.addWidget(self.txt_remote_path, 6, 1, 1, 2)

        main_layout.addWidget(config_frame)

        # ----------------- SECTION: MOUNT CONFIGURATION -----------------
        mount_frame = QFrame()
        mount_frame.setObjectName("cardFrame")
        mount_layout = QHBoxLayout(mount_frame)
        mount_layout.setContentsMargins(12, 12, 12, 12)

        mount_layout.addWidget(QLabel("Unidad Local:"))
        self.cmb_drive_letter = QComboBox()
        self.populate_drive_letters()
        mount_layout.addWidget(self.cmb_drive_letter, 1)
        
        self.btn_save_profile = QPushButton("Guardar Perfil")
        self.btn_save_profile.setObjectName("btnSecondary")
        self.btn_save_profile.clicked.connect(self.on_save_profile_clicked)
        mount_layout.addWidget(self.btn_save_profile)

        main_layout.addWidget(mount_frame)

        # ----------------- SECTION: GLOBAL OPTIONS -----------------
        options_frame = QFrame()
        options_frame.setObjectName("cardFrame")
        options_layout = QHBoxLayout(options_frame)
        options_layout.setContentsMargins(12, 12, 12, 12)
        
        self.chk_start_with_windows = QCheckBox("Iniciar con Windows")
        self.chk_start_with_windows.clicked.connect(self.on_start_with_windows_changed)
        options_layout.addWidget(self.chk_start_with_windows)
        
        self.chk_minimize_to_tray = QCheckBox("Minimizar al cerrar")
        self.chk_minimize_to_tray.setChecked(True)
        self.chk_minimize_to_tray.clicked.connect(self.on_minimize_to_tray_changed)
        options_layout.addWidget(self.chk_minimize_to_tray)
        
        self.chk_auto_mount = QCheckBox("Autoconectar")
        self.chk_auto_mount.setToolTip("Conectar este perfil automáticamente al iniciar la aplicación.")
        options_layout.addWidget(self.chk_auto_mount)
        
        main_layout.addWidget(options_frame)

        # ----------------- WinFsp INSTALL CARD (Conditional) -----------------
        self.winfsp_card = QFrame()
        self.winfsp_card.setObjectName("statusCard")
        self.winfsp_card.setStyleSheet("background-color: #2b2123; border: 1px solid #54252b;")
        winfsp_card_layout = QHBoxLayout(self.winfsp_card)
        winfsp_card_layout.setContentsMargins(12, 10, 12, 10)
        
        lbl_winfsp_text = QLabel("Falta el driver WinFsp necesario para montar unidades.")
        lbl_winfsp_text.setStyleSheet("color: #ff79c6; font-size: 12px;")
        winfsp_card_layout.addWidget(lbl_winfsp_text, 1)
        
        self.btn_install_winfsp = QPushButton("Instalar WinFsp")
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
        status_header_layout.addWidget(QLabel("Estado:"))
        self.lbl_status = QLabel("DESCONECTADO")
        self.lbl_status.setObjectName("statusLabel")
        self.lbl_status.setStyleSheet("color: #8b8b9c;")
        status_header_layout.addWidget(self.lbl_status, 1)
        status_card_layout.addLayout(status_header_layout)

        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        self.btn_connect = QPushButton("Conectar y Montar")
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        btn_layout.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Desmontar")
        self.btn_disconnect.setObjectName("btnDanger")
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self.on_disconnect_clicked)
        btn_layout.addWidget(self.btn_disconnect)
        status_card_layout.addLayout(btn_layout)

        main_layout.addWidget(status_card)

        # Setup System Tray
        self.setup_system_tray()

    def check_winfsp_status(self):
        """
        Verifica el estado del controlador WinFsp en el sistema y actualiza los componentes visuales.
        
        Si no se detecta el controlador en Windows, deshabilita el botón de conexión y
        muestra una tarjeta informativa con la opción de instalar el driver.
        """
        installed = self.mounter.is_winfsp_installed()
        if installed:
            self.lbl_winfsp_warning.setText("WinFsp: OK")
            self.lbl_winfsp_warning.setStyleSheet("color: #50fa7b; font-size: 11px;")
            self.winfsp_card.setVisible(False)
            self.btn_connect.setEnabled(True)
        else:
            self.lbl_winfsp_warning.setText("WinFsp: No instalado")
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
        Siempre añade la opción '<Nuevo Perfil>' en el primer índice.
        """
        self.cmb_profiles.clear()
        self.cmb_profiles.addItem("<Nuevo Perfil>")
        
        profiles = self.config_manager.load_profiles()
        for name in profiles.keys():
            self.cmb_profiles.addItem(name)

    def on_profile_selection_changed(self, index):
        """
        Slot gatillado cuando el usuario selecciona un perfil diferente de la lista.
        
        Si se selecciona '<Nuevo Perfil>', se limpian todos los campos del formulario.
        En caso contrario, se leen los parámetros del perfil seleccionado y se rellenan
        los inputs correspondientes de la interfaz.
        
        Args:
            index (int): Índice seleccionado en el ComboBox de perfiles.
        """
        if index <= 0:
            # Clear inputs for new profile
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
        
        - Contraseña (index 0): Oculta los campos de ruta de llave privada.
        - Llave privada (sin contraseña) (index 1): Oculta el campo de contraseña.
        - Llave privada + Frase de paso (index 2): Muestra todos los campos (ruta llave y contraseña de frase de paso).
        
        Args:
            index (int): Índice de la selección del ComboBox de autenticación.
        """
        if index == 0:  # Contraseña
            self.lbl_password.setText("Contraseña:")
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
            self.lbl_password.setText("Frase de paso:")
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
            self, "Seleccionar Llave Privada SSH", "", "All Files (*);;Key Files (*.pem *.key id_rsa)"
        )
        if file_path:
            self.txt_key_path.setText(file_path)

    def get_current_form_data(self):
        """
        Recopila todos los datos ingresados en el formulario de la UI
        y los consolida en un diccionario estructurado de datos.
        
        Returns:
            dict: Parámetros listos para su persistencia o procesamiento por el montador.
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
        if profile_name == "<Nuevo Perfil>" or not profile_name.strip():
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "Guardar Perfil", "Introduce el nombre del perfil:")
            if not ok or not name.strip():
                return
            profile_name = name.strip()

        data = self.get_current_form_data()
        
        # Validaciones elementales
        if not data['host'] or not data['user']:
            QMessageBox.warning(self, "Error al guardar", "Los campos Servidor y Usuario son obligatorios.")
            return

        if self.config_manager.save_profile(profile_name, data):
            QMessageBox.information(self, "Perfil Guardado", f"El perfil '{profile_name}' ha sido guardado.")
            self.load_profiles_into_combo()
            idx = self.cmb_profiles.findText(profile_name)
            if idx >= 0:
                self.cmb_profiles.setCurrentIndex(idx)
        else:
            QMessageBox.critical(self, "Error", "No se pudo guardar el perfil.")

    def on_delete_profile_clicked(self):
        """
        Elimina de forma permanente el perfil de conexión que está seleccionado.
        Requiere confirmación expresa del usuario mediante un QMessageBox.
        """
        profile_name = self.cmb_profiles.currentText()
        if profile_name == "<Nuevo Perfil>":
            return
            
        confirm = QMessageBox.question(
            self, "Confirmar eliminación",
            f"¿Estás seguro de que deseas eliminar el perfil '{profile_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            if self.config_manager.delete_profile(profile_name):
                QMessageBox.information(self, "Perfil Eliminado", f"El perfil '{profile_name}' ha sido eliminado.")
                self.load_profiles_into_combo()
                self.cmb_profiles.setCurrentIndex(0)
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el perfil.")

    def on_install_winfsp_clicked(self):
        """
        Lanza el proceso de instalación pasiva de WinFsp.
        Bloquea temporalmente el botón de instalación y actualiza los logs visuales.
        """
        self.btn_install_winfsp.setEnabled(False)
        self.lbl_status.setText("INSTALANDO WINFSP...")
        self.lbl_status.setStyleSheet("color: #ffb86c;")
        # Forzar a Qt a procesar eventos pendientes para actualizar visualmente la interfaz de inmediato
        self.app.processEvents()
        
        success = self.mounter.install_winfsp()
        
        self.btn_install_winfsp.setEnabled(True)
        self.check_winfsp_status()
        
        if success:
            QMessageBox.information(self, "Instalación Completada", "WinFsp se ha instalado correctamente. Ahora puedes montar unidades.")
            self.lbl_status.setText("DESCONECTADO")
            self.lbl_status.setStyleSheet("color: #8b8b9c;")
        else:
            QMessageBox.critical(self, "Instalación Fallida", "No se pudo instalar WinFsp. Por favor, asegúrate de otorgar permisos de administrador.")
            self.lbl_status.setText("ERROR")
            self.lbl_status.setStyleSheet("color: #ff5555;")

    def on_connect_clicked(self):
        """
        Inicia de forma asíncrona la conexión SFTP y monta la unidad de red.
        Bloquea los controles de formulario durante el intento para prevenir estados corruptos.
        Muestra notificaciones nativas del sistema si se conecta exitosamente.
        """
        data = self.get_current_form_data()
        
        if not data['host'] or not data['user']:
            QMessageBox.warning(self, "Datos incompletos", "Por favor rellena el Servidor y Usuario.")
            return

        self.is_connecting = True
        self.set_ui_enabled(False)
        self.lbl_status.setText("CONECTANDO Y MONTANDO...")
        self.lbl_status.setStyleSheet("color: #ffb86c;")
        self.app.processEvents()

        # Invocar la llamada lógica pesada
        success, message = self.mounter.mount_sftp(data)

        self.is_connecting = False
        if success:
            self.current_mounted_drive = data['drive_letter']
            self.lbl_status.setText(f"MONTADO EN {self.current_mounted_drive.upper()}")
            self.lbl_status.setStyleSheet("color: #50fa7b;")
            self.btn_disconnect.setEnabled(True)
            self.btn_connect.setEnabled(False)
            
            # Notificación nativa en la bandeja de tareas
            self.tray_icon.showMessage(
                "SFTP Drive Mounter",
                f"Servidor montado correctamente en {self.current_mounted_drive.upper()}",
                QSystemTrayIcon.Information,
                3000
            )
        else:
            QMessageBox.critical(self, "Error de Conexión", message)
            self.lbl_status.setText("ERROR")
            self.lbl_status.setStyleSheet("color: #ff5555;")
            self.set_ui_enabled(True)
            self.btn_disconnect.setEnabled(False)
            self.btn_connect.setEnabled(True)

    def on_disconnect_clicked(self):
        """
        Desmonta la unidad remota activa y restaura el estado y los controles de la interfaz.
        """
        if not self.current_mounted_drive:
            return

        self.lbl_status.setText("DESMONTANDO...")
        self.lbl_status.setStyleSheet("color: #ffb86c;")
        self.btn_disconnect.setEnabled(False)
        self.app.processEvents()

        success = self.mounter.unmount_sftp(self.current_mounted_drive)

        if success:
            self.tray_icon.showMessage(
                "SFTP Drive Mounter",
                f"Unidad {self.current_mounted_drive.upper()} desmontada correctamente.",
                QSystemTrayIcon.Information,
                2000
            )
            self.current_mounted_drive = None
            self.lbl_status.setText("DESCONECTADO")
            self.lbl_status.setStyleSheet("color: #8b8b9c;")
            
            # Actualizar de nuevo la disponibilidad de las letras de unidad libres en el ComboBox
            self.populate_drive_letters()
            
            self.set_ui_enabled(True)
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
        else:
            QMessageBox.warning(self, "Advertencia", "No se pudo desmontar la unidad por completo (puede que esté siendo utilizada por algún programa).")
            self.lbl_status.setText("ERROR AL DESMONTAR")
            self.lbl_status.setStyleSheet("color: #ff5555;")
            self.btn_disconnect.setEnabled(True)

    def set_ui_enabled(self, enabled):
        """
        Habilita o deshabilita recursivamente los campos del formulario para impedir
        que el usuario modifique las propiedades de la conexión activa mientras está montada.
        
        Args:
            enabled (bool): True para desbloquear controles, False para bloquearlos.
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

    # ----------------- SYSTEM TRAY MANAGEMENT (BANDEJA DE SISTEMA) -----------------
    def setup_system_tray(self):
        """
        Crea e inicializa el icono de la bandeja del sistema (System Tray Icon).
        Asigna el menú contextual con opciones para mostrar la ventana, forzar el desmontaje o salir.
        """
        self.tray_icon = QSystemTrayIcon(self)
        
        # Usar un icono de unidad estándar de Qt para mejorar la integración visual
        icon = self.style().standardIcon(QStyle.SP_DriveHDIcon)
        self.tray_icon.setIcon(icon)
        self.setWindowIcon(icon)

        # Crear el menú contextual de la bandeja
        tray_menu = QMenu()
        
        action_show = QAction("Mostrar Ventana", self)
        action_show.triggered.connect(self.show_normal)
        tray_menu.addAction(action_show)
        
        action_unmount = QAction("Desmontar Todo", self)
        action_unmount.triggered.connect(self.force_unmount_all)
        tray_menu.addAction(action_unmount)
        
        tray_menu.addSeparator()
        
        action_exit = QAction("Salir", self)
        action_exit.triggered.connect(self.close_app)
        tray_menu.addAction(action_exit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def show_normal(self):
        """
        Restaura la visibilidad normal de la ventana en pantalla y la enfoca en primer plano.
        """
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def on_tray_icon_activated(self, reason):
        """
        Slot gatillado ante la interacción con el icono de la bandeja del sistema.
        Al hacer doble clic, alterna entre mostrar la ventana o esconderla en segundo plano.
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
        Garantiza que cualquier unidad de red activa se desmonte antes de destruir el proceso de Qt.
        """
        self.force_unmount_all()
        self.tray_icon.hide()
        self.app.quit()

    def changeEvent(self, event):
        """
        Intercepta los eventos de cambio de estado de la ventana en PySide6.
        Si la ventana se minimiza y el ajuste 'Minimizar al cerrar' está habilitado,
        oculta la ventana de la barra de tareas y la esconde en el system tray.
        """
        if event.type() == event.type().WindowStateChange:
            if self.isMinimized() and self.chk_minimize_to_tray.isChecked():
                self.hide()
                event.ignore()
                self.tray_icon.showMessage(
                    "SFTP Drive Mounter",
                    "La aplicación se ha minimizado a la bandeja del sistema.",
                    QSystemTrayIcon.Information,
                    1500
                )
        super().changeEvent(event)

    def closeEvent(self, event):
        """
        Intercepta el evento de cierre de ventana (ej. al pulsar la cruz 'X' de Windows).
        Si la unidad está montada y está habilitado el ajuste de tray, se cancela el cierre
        del proceso y únicamente se esconde la UI, permitiendo que la unidad permanezca accesible.
        """
        if self.chk_minimize_to_tray.isChecked() and self.current_mounted_drive:
            self.hide()
            event.ignore()
            self.tray_icon.showMessage(
                "SFTP Drive Mounter",
                "El montaje sigue activo en segundo plano. Usa el icono de la barra de tareas para salir.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.close_app()

    # ----------------- GLOBAL SETTINGS & AUTOSTART (REGISTRO DE WINDOWS) -----------------
    def load_global_settings(self):
        """
        Carga la configuración global desde el config_manager y la aplica a los controles de la UI.
        Sincroniza el estado del checkbox de inicio automático con la clave correspondiente en el registro.
        """
        settings = self.config_manager.load_settings()
        
        # 1. Minimizar a la bandeja (por defecto True)
        min_to_tray = settings.get('minimize_to_tray', True)
        self.chk_minimize_to_tray.setChecked(min_to_tray)
        
        # 2. Iniciar con Windows (leer directamente el registro de Windows para mayor fiabilidad)
        start_with_win = self.get_startup_registry()
        self.chk_start_with_windows.setChecked(start_with_win)
        
        # Sincronizar el archivo JSON si difiere del registro del SO
        if start_with_win != settings.get('start_with_windows'):
            settings['start_with_windows'] = start_with_win
            self.config_manager.save_settings(settings)

    def on_minimize_to_tray_changed(self):
        """
        Slot gatillado cuando se altera la casilla 'Minimizar al cerrar'.
        Guarda la preferencia en los ajustes del JSON.
        """
        settings = self.config_manager.load_settings()
        settings['minimize_to_tray'] = self.chk_minimize_to_tray.isChecked()
        self.config_manager.save_settings(settings)

    def on_start_with_windows_changed(self):
        """
        Slot gatillado cuando se activa/desactiva la casilla 'Iniciar con Windows'.
        Modifica el registro del sistema operativo y guarda la configuración.
        """
        checked = self.chk_start_with_windows.isChecked()
        success = self.set_startup_registry(checked)
        if success:
            settings = self.config_manager.load_settings()
            settings['start_with_windows'] = checked
            self.config_manager.save_settings(settings)
        else:
            # Revertir estado del check en caso de fallo
            self.chk_start_with_windows.setChecked(not checked)
            QMessageBox.critical(
                self, "Error de Configuración", 
                "No se pudo modificar el registro de inicio. Asegúrate de tener los permisos necesarios."
            )

    def get_startup_registry(self) -> bool:
        """
        Comprueba si la entrada de inicio automático de SFTPMounter existe en el Registro de Windows.
        Ruta del registro analizada: HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
        
        Returns:
            bool: True si la entrada existe, False en caso contrario o si no está en Windows.
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
        
        Si el programa se ejecuta compilado (frozen), apunta directamente al ejecutable,
        de lo contrario apunta al intérprete de python pasando el script main como argumento.
        En ambos casos se anexa el argumento '--minimized' para iniciar en segundo plano.
        
        Args:
            enabled (bool): True para registrar inicio automático, False para removerlo.
            
        Returns:
            bool: True si el registro fue exitoso o no aplica, False en caso de error de permisos.
        """
        if os.name != 'nt':
            logger.info("Not on Windows, skipping registry startup key modification.")
            return True
            
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            if enabled:
                # Comprobar si se ejecuta desde el empaquetado de PyInstaller (sys.frozen)
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
