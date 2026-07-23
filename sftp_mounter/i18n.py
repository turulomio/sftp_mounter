"""
Módulo de Internacionalización (i18n) para SFTP Mounter.

Este módulo implementa la clase `I18N` encargada de administrar las traducciones
y textos localizados de la interfaz gráfica y los mensajes del sistema.

Idiomas soportados:
- Español ('es') - Idioma por defecto
- Inglés ('en')
- Francés ('fr')
- Portugués ('pt')
- Alemán ('de')
- Italiano ('it')
- Hindi ('hi')
- Chino ('zh')
- Ruso ('ru')
- Rumano ('ro')

Para desarrolladores nuevos:
- Si deseas añadir una nueva etiqueta de texto, agrégala en el diccionario `TRANSLATIONS`
  con sus respectivas traducciones en todos los idiomas soportados.
- Si un idioma no tiene definida la clave consultada, el método `t()` caerá automáticamente
  en el idioma por defecto o inglés para evitar que la UI falle o muestre un texto vacío.
"""

import os
import locale
import logging

logger = logging.getLogger("SFTPMounter.I18N")

# Colección global de lenguajes admitidos por la interfaz
SUPPORTED_LANGUAGES = {
    'es': 'Español',
    'en': 'English',
    'fr': 'Français',
    'pt': 'Português',
    'de': 'Deutsch',
    'it': 'Italiano',
    'hi': 'हिन्दी',
    'zh': '中文',
    'ru': 'Русский',
    'ro': 'Română'
}

TRANSLATIONS = {
    'title': {
        'es': 'SFTP Mounter', 'en': 'SFTP Mounter', 'fr': 'Montador SFTP',
        'pt': 'SFTP Mounter', 'de': 'SFTP Mounter', 'it': 'Montatore SFTP',
        'hi': 'SFTP Mounter', 'zh': 'SFTP Mounter', 'ru': 'SFTP Mounter',
        'ro': 'SFTP Mounter'
    },
    'menu_options': {
        'es': 'Opciones', 'en': 'Options', 'fr': 'Options',
        'pt': 'Opções', 'de': 'Optionen', 'it': 'Opzioni',
        'hi': 'विकल्प', 'zh': '选项', 'ru': 'Опции',
        'ro': 'Opțiuni'
    },
    'menu_settings': {
        'es': 'Configuración', 'en': 'Settings', 'fr': 'Paramètres',
        'pt': 'Configurações', 'de': 'Einstellungen', 'it': 'Impostazioni',
        'hi': 'सेटिंग्स', 'zh': '设置', 'ru': 'Настройки',
        'ro': 'Setări'
    },
    'conn_in_volname': {
        'es': 'Cadena de conexión en nombre de unidad', 'en': 'Connection string in drive name', 'fr': 'Chaîne de connexion dans le nom du lecteur',
        'pt': 'String de conexão no nome da unidade', 'de': 'Verbindungszeichenfolge im Laufwerksnamen', 'it': 'Stringa di connessione nel nome dell\'unità',
        'hi': 'ड्राइव नाम में कनेक्शन स्ट्रing', 'zh': '驱动器名称中的连接字符串', 'ru': 'Строка подключения в имени диска',
        'ro': 'Șirul de conexiune în numele unității'
    },
    'menu_view_log': {
        'es': 'Ver log', 'en': 'View log', 'fr': 'Voir le journal',
        'pt': 'Ver log', 'de': 'Log anzeigen', 'it': 'Visualizza log',
        'hi': 'लॉग देखें', 'zh': '查看日志', 'ru': 'Просмотр лога',
        'ro': 'Vezi logul'
    },
    'menu_view_known_hosts': {
        'es': 'Ver known_hosts', 'en': 'View known_hosts', 'fr': 'Voir known_hosts',
        'pt': 'Ver known_hosts', 'de': 'known_hosts anzeigen', 'it': 'Visualizza known_hosts',
        'hi': 'known_hosts देखें', 'zh': '查看 known_hosts', 'ru': 'Просмотр known_hosts',
        'ro': 'Vezi known_hosts'
    },
    'known_hosts_title': {
        'es': 'Visor de known_hosts', 'en': 'known_hosts Viewer', 'fr': 'Visionneuse de known_hosts',
        'pt': 'Visualizador de known_hosts', 'de': 'known_hosts-Viewer', 'it': 'Visualizzatore di known_hosts',
        'hi': 'known_hosts दर्शक', 'zh': 'known_hosts 查看器', 'ru': 'Просмотрщик known_hosts',
        'ro': 'Vizualizator known_hosts'
    },
    'known_hosts_not_found': {
        'es': 'El archivo known_hosts no existe o no contiene entradas.', 'en': 'The known_hosts file does not exist or has no entries.', 'fr': 'Le fichier known_hosts n\'existe pas ou ne contient pas d\'entrées.',
        'pt': 'O arquivo known_hosts não existe ou não contém entradas.', 'de': 'Die known_hosts-Datei existiert nicht oder enthält keine Einträge.', 'it': 'Il file known_hosts non esiste o non contiene voci.',
        'hi': 'known_hosts फ़ाइल मौजूद नहीं है या इसमें कोई प्रविष्टि नहीं है।', 'zh': 'known_hosts 文件不存在或没有条目。', 'ru': 'Файл known_hosts не existe или не содержит записей.',
        'ro': 'Fișierul known_hosts nu există sau nu conține intrări.'
    },
    'log_viewer_title': {
        'es': 'Registro de Logs', 'en': 'Log Viewer', 'fr': 'Visionneuse de journaux',
        'pt': 'Visualizador de Logs', 'de': 'Log-Viewer', 'it': 'Visualizzatore di log',
        'hi': 'लॉग दर्शक', 'zh': '日志查看器', 'ru': 'Просмотрщик логов',
        'ro': 'Vizualizator loguri'
    },
    'btn_clear_log': {
        'es': 'Limpiar log', 'en': 'Clear log', 'fr': 'Effacer le journal',
        'pt': 'Limpar log', 'de': 'Log löschen', 'it': 'Cancella log',
        'hi': 'लॉग साफ़ करें', 'zh': '清除日志', 'ru': 'Очистить лог',
        'ro': 'Curăță logul'
    },
    'btn_copy_log': {
        'es': 'Copiar log', 'en': 'Copy log', 'fr': 'Copier le journal',
        'pt': 'Copiar log', 'de': 'Log kopieren', 'it': 'Copia log',
        'hi': 'लॉग कॉपी करें', 'zh': '复制日志', 'ru': 'Копировать лог',
        'ro': 'Copiază logul'
    },
    'log_copied_msg': {
        'es': 'El contenido del log ha sido copiado al portapapeles.', 'en': 'The log content has been copied to the clipboard.', 'fr': 'Le contenu du journal a été copié dans le presse-papiers.',
        'pt': 'O conteúdo del log foi copiado para a área de transferência.', 'de': 'Der Log-Inhalt wurde in die Zwischenablage kopiert.', 'it': 'Il contenuto del log è stato copiato negli appunti.',
        'hi': 'लॉग सामग्री क्लिपबोर्ड पर कॉपी कर दी गई है।', 'zh': '日志内容已复制到剪贴板。', 'ru': 'Содержимое лога скопировано в буфер обмена.',
        'ro': 'Conținutul logului a fost copiat în clipboard.'
    },
    'btn_close': {
        'es': 'Cerrar', 'en': 'Close', 'fr': 'Fermer',
        'pt': 'Fechar', 'de': 'Schließen', 'it': 'Chiudi',
        'hi': 'बंद करें', 'zh': '关闭', 'ru': 'Закрыть',
        'ro': 'Închide'
    },
    'log_cleared_msg': {
        'es': 'El archivo de logs ha sido limpiado.', 'en': 'The log file has been cleared.', 'fr': 'Le fichier de journal a été effacé.',
        'pt': 'O arquivo de log foi limpo.', 'de': 'Die Logdatei wurde gelöscht.', 'it': 'Il file di log è stato cancellato.',
        'hi': 'लॉग फ़ाइल साफ़ कर दी गई है।', 'zh': '日志文件已清除。', 'ru': 'Файл лога очищен.',
        'ro': 'Fișierul de log a fost curățat.'
    },
    'menu_help': {
        'es': 'Ayuda', 'en': 'Help', 'fr': 'Aide',
        'pt': 'Ajuda', 'de': 'Hilfe', 'it': 'Aiuto',
        'hi': 'सहायता', 'zh': '帮助', 'ru': 'Помощь',
        'ro': 'Ajutor'
    },
    'menu_language': {
        'es': 'Idioma', 'en': 'Language', 'fr': 'Langue',
        'pt': 'Idioma', 'de': 'Sprache', 'it': 'Lingua',
        'hi': 'भाषा', 'zh': '语言', 'ru': 'Язык',
        'ro': 'Limbă'
    },
    'mounted_drives': {
        'es': 'Unidades montadas', 'en': 'Mounted drives', 'fr': 'Lecteurs montés',
        'pt': 'Unidades montadas', 'de': 'Gemountete Laufwerke', 'it': 'Unità montate',
        'hi': 'माउंट किए गए ड्राइव', 'zh': '已挂载的驱动器', 'ru': 'Подключенные диски',
        'ro': 'Unități montate'
    },
    'winfsp_ok': {
        'es': 'WinFsp: OK', 'en': 'WinFsp: OK', 'fr': 'WinFsp: OK',
        'pt': 'WinFsp: OK', 'de': 'WinFsp: OK', 'it': 'WinFsp: OK',
        'hi': 'WinFsp: OK', 'zh': 'WinFsp: OK', 'ru': 'WinFsp: OK',
        'ro': 'WinFsp: OK'
    },
    'winfsp_not_installed': {
        'es': 'WinFsp: No instalado', 'en': 'WinFsp: Not installed', 'fr': 'WinFsp: Non installé',
        'pt': 'WinFsp: Não instalado', 'de': 'WinFsp: Nicht installiert', 'it': 'WinFsp: Non installato',
        'hi': 'WinFsp: स्थापित नहीं है', 'zh': 'WinFsp: 未安装', 'ru': 'WinFsp: Не установлен',
        'ro': 'WinFsp: Neinstalat'
    },
    'profile': {
        'es': 'Perfil:', 'en': 'Profile:', 'fr': 'Profil:',
        'pt': 'Perfil:', 'de': 'Profil:', 'it': 'Profilo:',
        'hi': 'प्रोफ़ाइल:', 'zh': '配置文件:', 'ru': 'Профиль:',
        'ro': 'Profil:'
    },
    'new_profile': {
        'es': '<Nuevo Perfil>', 'en': '<New Profile>', 'fr': '<Nouveau profil>',
        'pt': '<Novo Perfil>', 'de': '<Neues Profil>', 'it': '<Nuovo Profilo>',
        'hi': '<नया प्रोफ़ाइल>', 'zh': '<新建配置文件>', 'ru': '<Новый профиль>',
        'ro': '<Profil nou>'
    },
    'delete': {
        'es': 'Eliminar', 'en': 'Delete', 'fr': 'Supprimer',
        'pt': 'Excluir', 'de': 'Löschen', 'it': 'Elimina',
        'hi': 'हटाएं', 'zh': '删除', 'ru': 'Удалить',
        'ro': 'Șterge'
    },
    'host': {
        'es': 'Servidor (Host):', 'en': 'Server (Host):', 'fr': 'Serveur (Hôte):',
        'pt': 'Servidor (Host):', 'de': 'Server (Host):', 'it': 'Server (Host):',
        'hi': 'सर्वर (होस्ट):', 'zh': '服务器 (主机):', 'ru': 'Сервер (Хост):',
        'ro': 'Server (Host):'
    },
    'host_placeholder': {
        'es': 'sftp.example.com o IP', 'en': 'sftp.example.com or IP', 'fr': 'sftp.example.com ou IP',
        'pt': 'sftp.example.com ou IP', 'de': 'sftp.example.com oder IP', 'it': 'sftp.example.com o IP',
        'hi': 'sftp.example.com या IP', 'zh': 'sftp.example.com 或 IP', 'ru': 'sftp.example.com или IP',
        'ro': 'sftp.example.com sau IP'
    },
    'port': {
        'es': 'Puerto:', 'en': 'Port:', 'fr': 'Port:',
        'pt': 'Porta:', 'de': 'Port:', 'it': 'Porta:',
        'hi': 'पोर्ट:', 'zh': '端口:', 'ru': 'Порт:',
        'ro': 'Port:'
    },
    'user': {
        'es': 'Usuario:', 'en': 'Username:', 'fr': 'Utilisateur:',
        'pt': 'Usuário:', 'de': 'Benutzername:', 'it': 'Utente:',
        'hi': 'उपयोगकर्ता:', 'zh': '用户名:', 'ru': 'Пользователь:',
        'ro': 'Utilizator:'
    },
    'user_placeholder': {
        'es': 'username', 'en': 'username', 'fr': 'nom d\'utilisateur',
        'pt': 'nome de usuário', 'de': 'Benutzername', 'it': 'nome utente',
        'hi': 'username', 'zh': '用户名', 'ru': 'имя пользователя',
        'ro': 'nume utilizator'
    },
    'auth': {
        'es': 'Autenticación:', 'en': 'Authentication:', 'fr': 'Authentification:',
        'pt': 'Autenticação:', 'de': 'Authentifizierung:', 'it': 'Autenticazione:',
        'hi': 'प्रमाणीकरण:', 'zh': '身份验证:', 'ru': 'Аутентификация:',
        'ro': 'Autentificare:'
    },
    'auth_password': {
        'es': 'Contraseña', 'en': 'Password', 'fr': 'Mot de passe',
        'pt': 'Senha', 'de': 'Passwort', 'it': 'Password',
        'hi': 'पासवर्ड', 'zh': '密码', 'ru': 'Пароль',
        'ro': 'Parolă'
    },
    'auth_key_no_pass': {
        'es': 'Llave Privada SSH (sin contraseña)', 'en': 'SSH Private Key (no passphrase)',
        'fr': 'Clé privée SSH (sans mot de passe)', 'pt': 'Chave Privada SSH (sem senha)',
        'de': 'SSH-Privatschlüssel (ohne Passphrase)', 'it': 'Chiave privata SSH (senza passphrase)',
        'hi': 'SSH निजी कुंजी (बिना पासफ़्रेज़)', 'zh': 'SSH 私钥 (无密码)', 'ru': 'Закрытый ключ SSH (без пароля)',
        'ro': 'Cheie privată SSH (fără frază de acces)'
    },
    'auth_key_pass': {
        'es': 'Llave Privada SSH + Frase de paso', 'en': 'SSH Private Key + Passphrase',
        'fr': 'Clé privée SSH + Phrase de passe', 'pt': 'Chave Privada SSH + Frase secreta',
        'de': 'SSH-Privatschlüssel + Passphrase', 'it': 'Chiave privata SSH + Passphrase',
        'hi': 'SSH निजी कुंजी + पासफ़्रेज़', 'zh': 'SSH 私钥 + 密码', 'ru': 'Закрытый ключ SSH + Пароль',
        'ro': 'Cheie privată SSH + Frază de acces'
    },
    'password': {
        'es': 'Contraseña:', 'en': 'Password:', 'fr': 'Mot de passe:',
        'pt': 'Senha:', 'de': 'Passwort:', 'it': 'Password:',
        'hi': 'पासवर्ड:', 'zh': '密码:', 'ru': 'Пароль:',
        'ro': 'Parolă:'
    },
    'passphrase': {
        'es': 'Frase de paso:', 'en': 'Passphrase:', 'fr': 'Phrase de passe:',
        'pt': 'Frase secreta:', 'de': 'Passphrase:', 'it': 'Passphrase:',
        'hi': 'पासफ़्रेज़:', 'zh': '密码:', 'ru': 'Парольная фраза:',
        'ro': 'Frază de acces:'
    },
    'ssh_key': {
        'es': 'Llave SSH:', 'en': 'SSH Key:', 'fr': 'Clé SSH:',
        'pt': 'Chave SSH:', 'de': 'SSH-Schlüssel:', 'it': 'Chiave SSH:',
        'hi': 'SSH कुंजी:', 'zh': 'SSH 私钥:', 'ru': 'SSH Ключ:',
        'ro': 'Cheie SSH:'
    },
    'ssh_key_placeholder': {
        'es': 'Ruta al archivo .key / .pem', 'en': 'Path to .key / .pem file', 'fr': 'Chemin vers le fichier .key / .pem',
        'pt': 'Caminho para o arquivo .key / .pem', 'de': 'Pfad zur .key / .pem Datei', 'it': 'Percorso del file .key / .pem',
        'hi': '.key / .pem फ़ाइल का पथ', 'zh': '.key / .pem 文件路径', 'ru': 'Путь к файлу .key / .pem',
        'ro': 'Cale către fișierul .key / .pem'
    },
    'browse': {
        'es': 'Buscar...', 'en': 'Browse...', 'fr': 'Parcourir...',
        'pt': 'Buscar...', 'de': 'Durchsuchen...', 'it': 'Sfoglia...',
        'hi': 'ब्राउज़ करें...', 'zh': '浏览...', 'ru': 'Обзор...',
        'ro': 'Răsfoiește...'
    },
    'remote_path': {
        'es': 'Ruta Remota:', 'en': 'Remote Path:', 'fr': 'Chemin distant:',
        'pt': 'Caminho Remoto:', 'de': 'Remoter Pfad:', 'it': 'Percorso Remoto:',
        'hi': 'रिमोट पथ:', 'zh': '远程路径:', 'ru': 'Удаленный путь:',
        'ro': 'Cale la distanță:'
    },
    'remote_path_placeholder': {
        'es': 'Ej: /var/www o dejar vacío para Home', 'en': 'e.g., /var/www or leave empty for Home', 'fr': 'ex: /var/www ou laisser vide pour Home',
        'pt': 'Ex: /var/www ou deixar vazio para Home', 'de': 'z.B. /var/www o. leer lassen f. Home', 'it': 'Es: /var/www o lascia vuoto per Home',
        'hi': 'जैसे: /var/www या होम के लिए खाली छोड़ें', 'zh': '例如: /var/www 或留空以使用家目录', 'ru': 'Например: /var/www или оставьте пустым для Home',
        'ro': 'De ex: /var/www sau lăsați gol pentru Home'
    },
    'local_drive': {
        'es': 'Unidad Local:', 'en': 'Local Drive:', 'fr': 'Lecteur local:',
        'pt': 'Unidade Local:', 'de': 'Lokales Laufwerk:', 'it': 'Unità Locale:',
        'hi': 'स्थानीय ड्राइव:', 'zh': '本地驱动器:', 'ru': 'Локальный диск:',
        'ro': 'Unitate locală:'
    },
    'save_profile': {
        'es': 'Guardar Perfil', 'en': 'Save Profile', 'fr': 'Enregistrer le profil',
        'pt': 'Salvar Perfil', 'de': 'Profil speichern', 'it': 'Salva Profilo',
        'hi': 'प्रोफ़ाइल सहेजें', 'zh': '保存配置文件', 'ru': 'Сохранить профиль',
        'ro': 'Salvează profilul'
    },
    'start_with_win': {
        'es': 'Iniciar con Windows', 'en': 'Start with Windows', 'fr': 'Démarrer avec Windows',
        'pt': 'Iniciar com o Windows', 'de': 'Mit Windows starten', 'it': 'Avvia con Windows',
        'hi': 'विंडोज के साथ शुरू करें', 'zh': '开机自启 (Windows)', 'ru': 'Запускать с Windows',
        'ro': 'Pornește cu Windows'
    },
    'minimize_to_tray': {
        'es': 'Minimizar al cerrar', 'en': 'Minimize to tray', 'fr': 'Minimiser dans la barre',
        'pt': 'Minimizar para bandeja', 'de': 'Im Tray minimieren', 'it': 'Minimizza nel tray',
        'hi': 'बंद करने पर ट्रे में छोटा करें', 'zh': '最小化到系统托盘', 'ru': 'Сворачивать в трей',
        'ro': 'Minimizează în tray'
    },
    'auto_mount': {
        'es': 'Autoconectar', 'en': 'Auto-mount', 'fr': 'Connexion auto',
        'pt': 'Autoconectar', 'de': 'Auto-Verbindung', 'it': 'Auto-connessione',
        'hi': 'ऑटो-माउंट', 'zh': '自动挂载', 'ru': 'Автоподключение',
        'ro': 'Auto-conectare'
    },
    'auto_mount_status': {
        'es': 'Autoconectar: {status}', 'en': 'Auto-mount: {status}', 'fr': 'Connexion auto: {status}',
        'pt': 'Autoconectar: {status}', 'de': 'Auto-Verbindung: {status}', 'it': 'Auto-connessione: {status}',
        'hi': 'ऑटो-माउंट: {status}', 'zh': '自动挂载: {status}', 'ru': 'Автоподключение: {status}',
        'ro': 'Auto-conectare: {status}'
    },
    'yes': {
        'es': 'Sí', 'en': 'Yes', 'fr': 'Oui', 'pt': 'Sim', 'de': 'Ja', 'it': 'Sì', 'hi': 'हाँ', 'zh': '是', 'ru': 'Да', 'ro': 'Da'
    },
    'no': {
        'es': 'No', 'en': 'No', 'fr': 'Non', 'pt': 'Não', 'de': 'Nein', 'it': 'No', 'hi': 'नहीं', 'zh': '否', 'ru': 'Нет', 'ro': 'Nu'
    },
    'winfsp_missing_card': {
        'es': 'Falta el driver WinFsp necesario para montar unidades.', 'en': 'Missing WinFsp driver required to mount drives.',
        'fr': 'Pilote WinFsp manquant requis pour monter des lecteurs.', 'pt': 'Falta o driver WinFsp necesario para montar unidades.',
        'de': 'WinFsp-Treiber fehlt, der zum Mounten benötigt wird.', 'it': 'Driver WinFsp mancante necessario per montare le unità.',
        'hi': 'माउंट करने के लिए WinFsp ड्राइवर आवश्यक है।', 'zh': '缺少挂载驱动器所需的 WinFsp 驱动程序。', 'ru': 'Отсутствует драйвер WinFsp, необходимый для подключения дисков.',
        'ro': 'Lipsește driverul WinFsp necesar pentru a monta unități.'
    },
    'install_winfsp': {
        'es': 'Instalar WinFsp', 'en': 'Install WinFsp', 'fr': 'Installer WinFsp',
        'pt': 'Instalar WinFsp', 'de': 'WinFsp installieren', 'it': 'Installa WinFsp',
        'hi': 'WinFsp स्थापित करें', 'zh': '安装 WinFsp', 'ru': 'Установить WinFsp',
        'ro': 'Instalează WinFsp'
    },
    'status': {
        'es': 'Estado:', 'en': 'Status:', 'fr': 'État:',
        'pt': 'Status:', 'de': 'Status:', 'it': 'Stato:',
        'hi': 'स्थिति:', 'zh': '状态:', 'ru': 'Статус:',
        'ro': 'Stare:'
    },
    'status_disconnected': {
        'es': 'DESCONECTADO', 'en': 'DISCONNECTED', 'fr': 'DÉCONNECTÉ',
        'pt': 'DESCONECTADO', 'de': 'GETRENNT', 'it': 'DISCONNESSO',
        'hi': 'डिस्कनेक्टेड', 'zh': '已断开连接', 'ru': 'ОТКЛЮЧЕНО',
        'ro': 'DECONECTAT'
    },
    'status_connecting': {
        'es': 'CONECTANDO Y MONTANDO...', 'en': 'CONNECTING & MOUNTING...', 'fr': 'CONNEXION & MONTAGE...',
        'pt': 'CONECTANDO E MONTANDO...', 'de': 'VERBINDEN & MOUNTEN...', 'it': 'CONNESSIONE & MONTAGGIO...',
        'hi': 'कनेक्ट और माउंट किया जा रहा है...', 'zh': '正在连接并挂载...', 'ru': 'ПОДКЛЮЧЕНИЕ...',
        'ro': 'CONECTARE ȘI MONTARE...'
    },
    'status_mounted': {
        'es': 'MONTADO EN {drive}', 'en': 'MOUNTED ON {drive}', 'fr': 'MONTÉ SUR {drive}',
        'pt': 'MONTADO EM {drive}', 'de': 'GEMOUNTET AUF {drive}', 'it': 'MONTATO SU {drive}',
        'hi': '{drive} पर माउंट किया गया', 'zh': '已挂载到 {drive}', 'ru': 'ПОДКЛЮЧЕНО К {drive}',
        'ro': 'MONTAT PE {drive}'
    },
    'status_unmounting': {
        'es': 'DESMONTANDO...', 'en': 'UNMOUNTING...', 'fr': 'DÉMONTAGE...',
        'pt': 'DESMONTANDO...', 'de': 'UNMOUNTEN...', 'it': 'SMONTAGGIO...',
        'hi': 'अनमाउंट किया जा रहा है...', 'zh': '正在卸载...', 'ru': 'ОТКЛЮЧЕНИЕ...',
        'ro': 'DEMONTARE...'
    },
    'status_error': {
        'es': 'ERROR', 'en': 'ERROR', 'fr': 'ERREUR',
        'pt': 'ERRO', 'de': 'FEHLER', 'it': 'ERRORE',
        'hi': 'त्रुटि', 'zh': '错误', 'ru': 'ОШИБКА',
        'ro': 'EROARE'
    },
    'status_unmount_error': {
        'es': 'ERROR AL DESMONTAR', 'en': 'UNMOUNT ERROR', 'fr': 'ERREUR DE DÉMONTAGE',
        'pt': 'ERRO AO DESMONTAR', 'de': 'DEINSTALLATIONSFEHLER', 'it': 'ERRORE DI SMONTAGGIO',
        'hi': 'अनमाउंट त्रुटि', 'zh': '卸载错误', 'ru': 'ОШИБКА РАЗМОНТИРОВАНИЯ',
        'ro': 'EROARE LA DEMONTARE'
    },
    'connect': {
        'es': 'Conectar y Montar', 'en': 'Connect & Mount', 'fr': 'Connecter & Monter',
        'pt': 'Conectar e Montar', 'de': 'Verbinden & Mounten', 'it': 'Connetti e Monta',
        'hi': 'कनेक्ट और माउंट करें', 'zh': '连接并挂载', 'ru': 'Подключить',
        'ro': 'Conectează și Montează'
    },
    'disconnect': {
        'es': 'Desmontar', 'en': 'Unmount', 'fr': 'Démonter',
        'pt': 'Desmontar', 'de': 'Unmounten', 'it': 'Smonta',
        'hi': 'अनमाउंट करें', 'zh': '卸载', 'ru': 'Отключить',
        'ro': 'Demontează'
    },
    'about': {
        'es': 'Acerca de', 'en': 'About', 'fr': 'À propos',
        'pt': 'Sobre', 'de': 'Über', 'it': 'Informazioni',
        'hi': 'के बारे में', 'zh': '关于', 'ru': 'О программе',
        'ro': 'Despre'
    },
    'versions': {
        'es': 'Versiones del Sistema', 'en': 'System Versions', 'fr': 'Versions du système',
        'pt': 'Versões do Sistema', 'de': 'Systemversionen', 'it': 'Versioni del Sistema',
        'hi': 'सिस्टम संस्करण', 'zh': '系统版本', 'ru': 'Версии системы',
        'ro': 'Versiuni sistem'
    },
    'app_version': {
        'es': 'Versión del programa: {version}', 'en': 'Program version: {version}', 'fr': 'Version du programme: {version}',
        'pt': 'Versão do programa: {version}', 'de': 'Programmversion: {version}', 'it': 'Versione del programma: {version}',
        'hi': 'कार्यक्रम संस्करण: {version}', 'zh': '程序版本: {version}', 'ru': 'Версия программы: {version}',
        'ro': 'Versiune program: {version}'
    },
    'rclone_version': {
        'es': 'Versión de Rclone: {version}', 'en': 'Rclone version: {version}', 'fr': 'Version Rclone: {version}',
        'pt': 'Versão do Rclone: {version}', 'de': 'Rclone-Version: {version}', 'it': 'Versione Rclone: {version}',
        'hi': 'Rclone संस्करण: {version}', 'zh': 'Rclone 版本: {version}', 'ru': 'Версия Rclone: {version}',
        'ro': 'Versiune Rclone: {version}'
    },
    'winfsp_version': {
        'es': 'Versión de WinFsp: {version}', 'en': 'WinFsp version: {version}', 'fr': 'Version WinFsp: {version}',
        'pt': 'Versão do WinFsp: {version}', 'de': 'WinFsp-Version: {version}', 'it': 'Versione WinFsp: {version}',
        'hi': 'WinFsp संस्करण: {version}', 'zh': 'WinFsp 版本: {version}', 'ru': 'Версия WinFsp: {version}',
        'ro': 'Versiune WinFsp: {version}'
    },
    'close': {
        'es': 'Cerrar', 'en': 'Close', 'fr': 'Fermer',
        'pt': 'Fechar', 'de': 'Schließen', 'it': 'Chiudi',
        'hi': 'बंद करें', 'zh': '关闭', 'ru': 'Закрыть',
        'ro': 'Închide'
    },
    'error_save_title': {
        'es': 'Error al guardar', 'en': 'Save Error', 'fr': 'Erreur d\'enregistrement',
        'pt': 'Erro ao salvar', 'de': 'Speicherfehler', 'it': 'Errore di salvataggio',
        'hi': 'सहेजने में त्रुटि', 'zh': '保存错误', 'ru': 'Ошибка сохранения',
        'ro': 'Eroare la salvare'
    },
    'error_save_required': {
        'es': 'Los campos Servidor y Usuario son obligatorios.', 'en': 'Server and Username fields are required.', 'fr': 'Les champs Serveur et Utilisateur sont obligatoires.',
        'pt': 'Os campos Servidor e Usuário son obligatórios.', 'de': 'Die Felder Server und Benutzername sind erforderlich.', 'it': 'I campi Server e Utente sono obbligatori.',
        'hi': 'सर्वर और उपयोगकर्ता फ़ील्ड आवश्यक हैं।', 'zh': '服务器和用户名是必填项。', 'ru': 'Поля Сервер и Пользователь обязательны.',
        'ro': 'Câmpurile Server și Utilizator sunt obligatorii.'
    },
    'profile_saved_title': {
        'es': 'Perfil Guardado', 'en': 'Profile Saved', 'fr': 'Profil enregistré',
        'pt': 'Perfil Salvo', 'de': 'Profil gespeichert', 'it': 'Perfilo Salvato',
        'hi': 'प्रोफ़ाइल सहेजी गई', 'zh': '配置文件已保存', 'ru': 'Профиль сохранен',
        'ro': 'Profil salvat'
    },
    'profile_saved_msg': {
        'es': 'El perfil \'{profile_name}\' ha sido guardado.', 'en': 'Profile \'{profile_name}\' has been saved.', 'fr': 'Le profil \'{profile_name}\' a été enregistré.',
        'pt': 'O perfil \'{profile_name}\' foi salvo.', 'de': 'Das Profil \'{profile_name}\' wurde gespeichert.', 'it': 'Il perfil \'{profile_name}\' è stato salvato.',
        'hi': 'प्रोफ़ाइल \'{profile_name}\' सहेज ली गई है।', 'zh': '配置文件 \'{profile_name}\' 已保存。', 'ru': 'Профиль \'{profile_name}\' сохранен.',
        'ro': 'Profilul \'{profile_name}\' a fost salvat.'
    },
    'error_save_failed': {
        'es': 'No se pudo guardar el perfil.', 'en': 'Failed to save profile.', 'fr': 'Impossible d\'enregistrer le profil.',
        'pt': 'Não foi posible salvar o perfil.', 'de': 'Fehler beim Speichern des Profils.', 'it': 'Impossibile salvare il profilo.',
        'hi': 'प्रोफ़ाइल सहेजने में विफल।', 'zh': '无法保存配置文件。', 'ru': 'Не удалось сохранить профиль.',
        'ro': 'Nu s-a putut salva profilul.'
    },
    'confirm_delete_title': {
        'es': 'Confirmar eliminación', 'en': 'Confirm Deletion', 'fr': 'Confirmer la suppression',
        'pt': 'Confirmar exclusão', 'de': 'Löschen confirmar', 'it': 'Conferma eliminazione',
        'hi': 'हटाने की पुष्टि करें', 'zh': '确认删除', 'ru': 'Подтверждение удаления',
        'ro': 'Confirmare ștergere'
    },
    'confirm_delete_msg': {
        'es': '¿Estás seguro de que deseas eliminar el perfil \'{profile_name}\'?', 'en': 'Are you sure you want to delete profile \'{profile_name}\'?', 'fr': 'Êtes-vous sûr de vouloir supprimer le profil \'{profile_name}\'?',
        'pt': 'Tem certeza que deseja excluir o perfil \'{profile_name}\'?', 'de': 'Sind Sie sicher, dass Sie das Profil \'{profile_name}\' löschen möchten?', 'it': 'Sei sicuro di voler eliminare el profilo \'{profile_name}\'?',
        'hi': 'क्या आप वाकई प्रोफ़ाइल \'{profile_name}\' को हटाना चाहते हैं?', 'zh': '您确定要删除配置文件 \'{profile_name}\' 吗？', 'ru': 'Вы уверены, что хотите удалить профиль \'{profile_name}\'?',
        'ro': 'Sigur doriți să ștergeți profilul \'{profile_name}\'?'
    },
    'profile_deleted_title': {
        'es': 'Perfil Eliminado', 'en': 'Profile Deleted', 'fr': 'Profil supprimé',
        'pt': 'Perfil Excluído', 'de': 'Profil gelöscht', 'it': 'Profilo Eliminato',
        'hi': 'प्रोफ़ाइल हटाई गई', 'zh': '配置文件已删除', 'ru': 'Профиль удален',
        'ro': 'Profil șters'
    },
    'profile_deleted_msg': {
        'es': 'El perfil \'{profile_name}\' ha sido eliminado.', 'en': 'Profile \'{profile_name}\' has been deleted.', 'fr': 'Le profil \'{profile_name}\' a été supprimé.',
        'pt': 'O perfil \'{profile_name}\' foi excluído.', 'de': 'Das Profil \'{profile_name}\' wurde gelöscht.', 'it': 'Il profilo \'{profile_name}\' è stato eliminato.',
        'hi': 'प्रोफ़ाइल \'{profile_name}\' हटा दी गई है।', 'zh': '配置文件 \'{profile_name}\' 已删除。', 'ru': 'Профиль \'{profile_name}\' удален.',
        'ro': 'Profilul \'{profile_name}\' a fost șters.'
    },
    'error_delete_failed': {
        'es': 'No se pudo eliminar el perfil.', 'en': 'Failed to delete profile.', 'fr': 'Impossible de supprimer le profil.',
        'pt': 'Não foi posible excluir o perfil.', 'de': 'Fehler beim Löschen des Profils.', 'it': 'Impossibile eliminare il profilo.',
        'hi': 'प्रोफ़ाइल हटाने में विफल।', 'zh': '无法删除配置文件。', 'ru': 'Не удалось удалить профиль.',
        'ro': 'Nu s-a putut șterge profilul.'
    },
    'installing_winfsp': {
        'es': 'INSTALANDO WINFSP...', 'en': 'INSTALLING WINFSP...', 'fr': 'INSTALLATION DE WINFSP...',
        'pt': 'INSTALANDO WINFSP...', 'de': 'WINFSP WIRD INSTALLIERT...', 'it': 'INSTALLAZIONE DI WINFSP...',
        'hi': 'WinFsp स्थापित किया जा रहा है...', 'zh': '正在安装 WinFsp...', 'ru': 'УСТАНОВКА WINFSP...',
        'ro': 'SE INSTALEAZĂ WINFSP...'
    },
    'install_winfsp_ok_title': {
        'es': 'Instalación Completada', 'en': 'Installation Completed', 'fr': 'Installation terminée',
        'pt': 'Instalação Concluída', 'de': 'Installation abgeschlossen', 'it': 'Installazione Completata',
        'hi': 'स्थापना पूर्ण', 'zh': '安装完成', 'ru': 'Установка завершена',
        'ro': 'Instalare completă'
    },
    'install_winfsp_ok_msg': {
        'es': 'WinFsp se ha instalado correctamente. Ahora puedes montar unidades.', 'en': 'WinFsp installed successfully. You can now mount drives.', 'fr': 'WinFsp a été installé avec succès. Vous pouvez maintenant monter des lecteurs.',
        'pt': 'WinFsp foi instalado com sucesso. Agora você pode montar unidades.', 'de': 'WinFsp wurde erfolgreich installiert. Sie können jetzt Laufwerke mounten.', 'it': 'WinFsp è stato installato correttamente. Ora puoi montare le unità.',
        'hi': 'WinFsp सफलतापूर्वक स्थापित हो गया है। अब आप ड्राइव माउंट कर सकते हैं।', 'zh': 'WinFsp 安装成功。您现在可以挂载驱动器了。', 'ru': 'WinFsp успешно установлен. Теперь вы можете подключать диски.',
        'ro': 'WinFsp a fost instalat cu succes. Acum puteți monta unități.'
    },
    'install_winfsp_fail_title': {
        'es': 'Instalación Fallida', 'en': 'Installation Failed', 'fr': 'Échec de l\'installation',
        'pt': 'Falha na Instalação', 'de': 'Installation fehlgeschlagen', 'it': 'Installazione Fallita',
        'hi': 'स्थापना विफल', 'zh': '安装失败', 'ru': 'Ошибка установки',
        'ro': 'Instalare eșuată'
    },
    'install_winfsp_fail_msg': {
        'es': 'No se pudo instalar WinFsp. Por favor, asegúrate de otorgar permisos de administrador.', 'en': 'Failed to install WinFsp. Please ensure you grant administrator permissions.', 'fr': 'Impossible d\'installer WinFsp. Veuillez vous assurer d\'accorder les autorisations d\'administrateur.',
        'pt': 'Falha ao instalar o WinFsp. Certifique-se de conceder permissões de administrador.', 'de': 'WinFsp konnte nicht installiert werden. Bitte stellen Sie sicher, dass Sie Administratorrechte erteilen.', 'it': 'Impossibile installare WinFsp. Assicurati di concedere le autorizzazioni di amministratore.',
        'hi': 'WinFsp स्थापित करने में विफल। कृपया सुनिश्चित करें कि आप व्यवस्थापक अनुमतियां प्रदान करते हैं।', 'zh': '无法安装 WinFsp。请确保授予管理员权限。', 'ru': 'Не удалось установить WinFsp. Убедитесь, что у вас есть права администратора.',
        'ro': 'Nu s-a putut instala WinFsp. Asigurați-vă că acordați permisiuni de administrator.'
    },
    'error_incomplete_title': {
        'es': 'Datos incompletos', 'en': 'Incomplete Data', 'fr': 'Données incomplètes',
        'pt': 'Dados incompletos', 'de': 'Unvollständige Daten', 'it': 'Dati incompleti',
        'hi': 'अधूरा डेटा', 'zh': '数据不完整', 'ru': 'Неполные данные',
        'ro': 'Date incomplete'
    },
    'error_incomplete_msg': {
        'es': 'Por favor rellena el Servidor y Usuario.', 'en': 'Please fill in both Server and Username.', 'fr': 'Veuillez remplir à la fois le serveur et le nom d\'utilisateur.',
        'pt': 'Por favor preencha o Servidor e o Usuário.', 'de': 'Bitte füllen Sie sowohl Server als auch Benutzername aus.', 'it': 'Si prega di compilare sia il Server che l\'Utente.',
        'hi': 'कृपया सर्वर और उपयोगकर्ता दोनों भरें।', 'zh': '请填写服务器和用户名。', 'ru': 'Пожалуйста, заполните поля Сервер и Пользователь.',
        'ro': 'Vă rugăm să completați atât Serverul, cât și Utilizatorul.'
    },
    'connection_ok_msg': {
        'es': 'Servidor montado correctamente en {drive}', 'en': 'Server mounted successfully on {drive}', 'fr': 'Serveur monté avec succès sur {drive}',
        'pt': 'Servidor montado com sucesso em {drive}', 'de': 'Server erfolgreich auf {drive} gemountet', 'it': 'Server montato correttamente su {drive}',
        'hi': 'सर्वर सफलतापूर्वक {drive} पर माउंट हो गया', 'zh': '服务器已成功挂载到 {drive}', 'ru': 'Сервер успешно подключен к {drive}',
        'ro': 'Server montat cu succes pe {drive}'
    },
    'connection_fail_title': {
        'es': 'Error de Conexión', 'en': 'Connection Error', 'fr': 'Erreur de connexion',
        'pt': 'Erro de Conexão', 'de': 'Verbindungsfehler', 'it': 'Errore di Connessione',
        'hi': 'कनेक्शन त्रुटi', 'zh': '连接错误', 'ru': 'Ошибка подключения',
        'ro': 'Eroare de conexiune'
    },
    'disconnection_ok_msg': {
        'es': 'Unidad {drive} desmontada correctamente.', 'en': 'Drive {drive} unmounted successfully.', 'fr': 'Lecteur {drive} démonté avec succès.',
        'pt': 'Unidade {drive} desmontada com sucesso.', 'de': 'Laufwerk {drive} deinstalliert.', 'it': 'Unità {drive} smontata correttamente.',
        'hi': 'ड्राइव {drive} सफलतापूर्वक अनमाउंट हो गई।', 'zh': '驱动器 {drive} 已成功卸载。', 'ru': 'Диск {drive} успешно отключен.',
        'ro': 'Unitatea {drive} a fost demontată cu succes.'
    },
    'unmount_warning_title': {
        'es': 'Advertencia', 'en': 'Warning', 'fr': 'Avertissement',
        'pt': 'Aviso', 'de': 'Warnung', 'it': 'Avviso',
        'hi': 'चेतावनी', 'zh': '警告', 'ru': 'Предупреждение',
        'ro': 'Avertisment'
    },
    'unmount_warning_msg': {
        'es': 'No se pudo desmontar la unidad por completo (puede que esté siendo utilizada por algún programa).', 'en': 'Failed to unmount the drive completely (it might be in use by another program).', 'fr': 'Impossible de démonter complètement le lecteur (il se peut qu\'il soit utilisé par un autre programme).',
        'pt': 'Não foi possível desmontar a unidade completamente (pode estar sendo usada por outro programa).', 'de': 'Das Laufwerk konnte nicht unmountet werden.', 'it': 'Impossibile smontare completamente l\'unità.',
        'hi': 'ड्राइव को पूरी तरह से अनमाउंट करने में विफल (हो सकता है कि यह किसी अन्य प्रोग्राम द्वारा उपयोग में हो)।', 'zh': '未能完全卸载驱动器 (它可能正被其他程序使用)。', 'ru': 'Не удалось полностью отключить диск (возможно, он занят другой программой).',
        'ro': 'Nu s-a putut demonta unitatea complet (poate fi utilizată de un alt program).'
    },
    'config_error_title': {
        'es': 'Error de Configuración', 'en': 'Configuration Error', 'fr': 'Erreur de configuration',
        'pt': 'Erro de Configuração', 'de': 'Konfigurationsfehler', 'it': 'Errore di Configurazione',
        'hi': 'कॉन्फ़िगरेशन त्रुटि', 'zh': '配置错误', 'ru': 'Ошибка конфигурации',
        'ro': 'Eroare de configurare'
    },
    'config_error_msg': {
        'es': 'No se pudo modificar el registro de inicio. Asegúrate de tener los permisos necesarios.', 'en': 'Could not modify startup registry. Please ensure you have necessary permissions.', 'fr': 'Impossible de modifier le registre de démarrage. Veuillez vous assurer que vous disposez des autorisations nécessaires.',
        'pt': 'Não fue posible modificar o registro de inicialização.', 'de': 'Autostart-Registrierung konnte nicht geändert werden.', 'it': 'Impossibile modificare il registro di avvio.',
        'hi': 'स्टार्टअप रजिस्ट्री को संशोधित नहीं किया जा सका। कृपया सुनिश्चित करें कि आपके पास आवश्यक अनुमतियां हैं।', 'zh': '无法修改开机启动注册表。请确保您具有必要的权限。', 'ru': 'Не удалось изменить автозагрузку в реестре. Убедитесь, что у вас есть необходимые права.',
        'ro': 'Nu s-a putut modifica registrul de pornire. Asigurați-vă că aveți permisiunile necesare.'
    },
    'input_profile_name_title': {
        'es': 'Guardar Perfil', 'en': 'Save Profile', 'fr': 'Enregistrer le profil',
        'pt': 'Salvar Perfil', 'de': 'Profil speichern', 'it': 'Salva Profilo',
        'hi': 'प्रोफ़ाइल सहेजें', 'zh': '保存配置文件', 'ru': 'Сохранить профиль',
        'ro': 'Salvează profilul'
    },
    'input_profile_name_msg': {
        'es': 'Introduce el nombre del perfil:', 'en': 'Enter profile name:', 'fr': 'Entrez le nom du profil :',
        'pt': 'Digite o nome do perfil:', 'de': 'Profilnamen eingeben:', 'it': 'Inserisci il nome del profilo:',
        'hi': 'प्रोफ़ाइल नाम दर्ज करें:', 'zh': '输入配置文件名称:', 'ru': 'Введите имя профиля:',
        'ro': 'Introduceți numele profilului:'
    },
    'lang_selector': {
        'es': 'Idioma:', 'en': 'Language:', 'fr': 'Langue:',
        'pt': 'Idioma:', 'de': 'Sprache:', 'it': 'Lingua:',
        'hi': 'भाषा:', 'zh': '语言:', 'ru': 'Язык:',
        'ro': 'Limbă:'
    },
    'tray_msg_minimized': {
        'es': 'La aplicación se ha minimizado a la bandeja del sistema.', 'en': 'The application has been minimized to the system tray.', 'fr': 'L\'application a été minimisée dans la barre d\'état.',
        'pt': 'O aplicativo foi minimizado para a bandeja del sistema.', 'de': 'Die Anwendung wurde minimiert.', 'it': 'L\'applicazione è stata minimizzata.',
        'hi': 'एप्लिकेशन सिस्टम ट्रे में छोटा कर दिया गया है।', 'zh': '应用程序已最小化到系统托盘。', 'ru': 'Приложение свернуто в системный трей.',
        'ro': 'Aplicația a fost minimizată în tray-ul de sistem.'
    },
    'tray_msg_background': {
        'es': 'El montaje sigue activo en segundo plano. Usa el icono de la barra de tareas para salir.', 'en': 'Mount is still active in the background. Use taskbar icon to exit.', 'fr': 'Le montage est toujours actif en arrière-plan. Utilisez l\'icône de la barre des tâches pour quitter.',
        'pt': 'O volume continua ativo em segundo plano.', 'de': 'Laufwerk ist im Hintergrund aktiv.', 'it': 'Il montaggio è ancora attivo in background.',
        'hi': 'माउंट पृष्ठभूमि में सक्रिय है। बाहर निकलने के लिए टास्कबार आइकन का उपयोग करें।', 'zh': '挂载在后台仍然有效。使用任务栏图标退出。', 'ru': 'Подключение остается активным в фоновом режиме. Используйте иконку в трее для выхода.',
        'ro': 'Montarea este încă activă în fundal. Utilizați pictograma din bara de activități pentru a ieși.'
    },
    'net_use_in_use': {
        'es': 'La letra de unidad {drive} ya está en uso.', 'en': 'Drive letter {drive} is already in use.', 'fr': 'La lettre de lecteur {drive} est déjà utilisée.',
        'pt': 'A letra da unidade {drive} já está em uso.', 'de': 'Laufwerksbuchstabe {drive} wird bereits verwendet.', 'it': 'La letra dell\'unità {drive} è già in uso.',
        'hi': 'ड्राइव अक्षर {drive} पहले से ही उपयोग में है।', 'zh': '盘符 {drive} 已在使用中。', 'ru': 'Буква диска {drive} уже используется.',
        'ro': 'Litera unității {drive} este deja folosită.'
    },
    'show_window': {
        'es': 'Mostrar Ventana', 'en': 'Show Window', 'fr': 'Afficher la fenêtre',
        'pt': 'Mostrar Janela', 'de': 'Fenster anzeigen', 'it': 'Mostra Finestra',
        'hi': 'विंडो दिखाएं', 'zh': '显示窗口', 'ru': 'Показать окно',
        'ro': 'Afișează fereastra'
    },
    'unmount_all': {
        'es': 'Desmontar Todo', 'en': 'Unmount All', 'fr': 'Tout démonter',
        'pt': 'Desmontar Tudo', 'de': 'Alles unmounten', 'it': 'Smonta Tutto',
        'hi': 'सभी अनमाउंट करें', 'zh': '全部卸载', 'ru': 'Размонтировать всё',
        'ro': 'Demontează tot'
    },
    'exit': {
        'es': 'Salir', 'en': 'Exit', 'fr': 'Quitter',
        'pt': 'Sair', 'de': 'Beenden', 'it': 'Esci',
        'hi': 'बाहर निकलें', 'zh': '退出', 'ru': 'Выход',
        'ro': 'Ieșire'
    },
    'license': {
        'es': 'Licencia: GPLv3', 'en': 'License: GPLv3', 'fr': 'Licence: GPLv3',
        'pt': 'Licença: GPLv3', 'de': 'Lizenz: GPLv3', 'it': 'Licenza: GPLv3',
        'hi': 'लाइसेंस: GPLv3', 'zh': '授权许可: GPLv3', 'ru': 'Лицензия: GPLv3',
        'ro': 'Licență: GPLv3'
    },
    'author': {
        'es': 'Autor: turulomio', 'en': 'Author: turulomio', 'fr': 'Auteur: turulomio',
        'pt': 'Autor: turulomio', 'de': 'Autor: turulomio', 'it': 'Autore: turulomio',
        'hi': 'लेखक: turulomio', 'zh': '作者: turulomio', 'ru': 'Автор: turulomio',
        'ro': 'Autor: turulomio'
    },
    'project_url': {
        'es': 'Proyecto: {url}', 'en': 'Project: {url}', 'fr': 'Projet: {url}',
        'pt': 'Projeto: {url}', 'de': 'Projekt: {url}', 'it': 'Progetto: {url}',
        'hi': 'परियोजना: {url}', 'zh': '项目: {url}', 'ru': 'Проект: {url}',
        'ro': 'Proiect: {url}'
    },
    'manage_profiles': {
        'es': 'Gestionar perfiles...', 'en': 'Manage profiles...', 'fr': 'Gérer les profils...',
        'pt': 'Gerenciar perfis...', 'de': 'Profile verwalten...', 'it': 'Gestisci profili...',
        'hi': 'प्रोफ़ाइल प्रबंधित करें...', 'zh': '管理配置文件...', 'ru': 'Управление профилями...',
        'ro': 'Gestionare profiluri...'
    },
    'add_profile': {
        'es': 'Añadir perfil', 'en': 'Add profile', 'fr': 'Ajouter un profil',
        'pt': 'Adicionar perfil', 'de': 'Profil hinzufügen', 'it': 'Aggiungi profilo',
        'hi': 'प्रोफ़ाइल जोड़ें', 'zh': '添加配置文件', 'ru': 'Добавить профиль',
        'ro': 'Adaugă profil'
    },
    'edit_profile': {
        'es': 'Editar perfil', 'en': 'Edit profile', 'fr': 'Modifier le profil',
        'pt': 'Editar perfil', 'de': 'Profil bearbeiten', 'it': 'Modifica profilo',
        'hi': 'प्रोफ़ाइल संपादित करें', 'zh': '编辑配置文件', 'ru': 'Редактировать профиль',
        'ro': 'Editează profilul'
    },
    'save': {
        'es': 'Guardar', 'en': 'Save', 'fr': 'Enregistrer',
        'pt': 'Salvar', 'de': 'Speichern', 'it': 'Salva',
        'hi': 'सहेजें', 'zh': '保存', 'ru': 'Сохранить',
        'ro': 'Salvează'
    },
    'no_profiles': {
        'es': 'No hay perfiles configurados.\nCrea uno en Opciones -> Gestionar perfiles...',
        'en': 'No profiles configured.\nCreate one in Options -> Manage profiles...',
        'fr': 'Aucun profil configuré.\nCréez-en un dans Options -> Gérer les profils...',
        'pt': 'Nenhum perfil configurado.\nCrie um em Opções -> Gerenciar perfis...',
        'de': 'Keine Profile konfiguriert.\nErstellen Sie eines unter Optionen -> Profile verwalten...',
        'it': 'Nessun profilo configurato.\nCreane uno in Opzioni -> Gestisci profili...',
        'hi': 'कोई प्रोफ़ाइल कॉन्फ़िगर नहीं की गई है।\nविकल्प -> प्रोफ़ाइल प्रबंधित करें में एक बनाएं...',
        'zh': '未配置配置文件。\n请在 选项 -> 管理配置文件 中创建一个...',
        'ru': 'Профили не настроены.\nСоздайте в Опции -> Управление профилями...',
        'ro': 'Niciun profil configurat.\nCreați unul în Opțiuni -> Gestionare profiluri...'
    },
    'profile_active_warning': {
        'es': 'No se puede editar o eliminar un perfil mientras esté montado o conectando.',
        'en': 'Cannot edit or delete a profile while it is mounted or connecting.',
        'fr': 'Impossible de modifier ou supprimer un profil lorsqu\'il est monté.',
        'pt': 'Não é possível editar ou excluir um perfil enquanto estiver montado.',
        'de': 'Ein Profil kann nicht bearbeitet oder gelöscht werden, während es gemountet ist.',
        'it': 'Impossibile modificare o eliminare un profilo mentre è montato.',
        'hi': 'माउंट या कनेक्ट होने के दौरान प्रोफ़ाइल को संपादित या हटाया नहीं जा सकता।',
        'zh': '挂载或连接时无法编辑或删除配置文件。',
        'ru': 'Нельзя редактировать или удалять подключенный профиль.',
        'ro': 'Nu se poate edita sau șterge un profil în timp ce este montat.'
    },
    'host_key_unknown_title': {
        'es': 'Verificación de clave de host SSH',
        'en': 'SSH Host Key Verification',
        'fr': 'Vérification de la clé d\'hôte SSH',
        'pt': 'Verificação da chave de host SSH',
        'de': 'SSH-Hostschlüssel-Überprüfung',
        'it': 'Verifica della chiave host SSH',
        'hi': 'SSH होस्ट कुंजी सत्यापन',
        'zh': 'SSH 主机密钥验证',
        'ru': 'Проверка ключа узла SSH',
        'ro': 'Verificarea cheii de host SSH'
    },
    'host_key_unknown_msg': {
        'es': 'La autenticidad del servidor SSH \'{host}\' no ha sido verificada o ha cambiado la clave de host.\n\n¿Deseas confiar en este servidor y aceptar su clave para guardarla en known_hosts?',
        'en': 'The authenticity of SSH host \'{host}\' can\'t be established or the host key has changed.\n\nDo you want to trust this server and accept its host key?',
        'fr': 'L\'authenticité de l\'hôte SSH \'{host}\' ne peut pas être établie.\n\nVoulez-vous faire confiance à ce serveur et accepter sa clé d\'hôte ?',
        'pt': 'A autenticidade do host SSH \'{host}\' não pôde ser verificada.\n\nDeseja confiar neste servidor e aceitar sua chave?',
        'de': 'Die Authentizität des SSH-Hosts \'{host}\' kann nicht bestätigt werden.\n\nMöchten Sie diesem Server vertrauen und seinen Schlüssel akzeptieren?',
        'it': 'L\'autenticità dell\'host SSH \'{host}\' non può essere verificata.\n\nVuoi fidarti di questo server e accettare la sua chiave?',
        'hi': 'SSH होस्ट \'{host}\' की प्रामाणिकता स्थापित नहीं की जा सकती।\n\nक्या आप इस सर्वर पर भरोसा करना चाहते हैं?',
        'zh': '无法确认 SSH 主机 \'{host}\' 的真实性。\n\n您要信任此服务器并接受其主机密钥吗？',
        'ru': 'Не удалось подтвердить подлинность узла SSH \'{host}\'.\n\nВы хотите доверять этому серверу и принять его ключ?',
        'ro': 'Autenticitatea host-ului SSH \'{host}\' nu poate fi stabilită.\n\nDoriți să aveți încredere în acest server și să-i acceptați cheia?'
    }
}

class I18N:
    """
    Controla el idioma actual seleccionado en la aplicación y proporciona
    la traducción correspondiente a cada una de las etiquetas del sistema.
    """
    def __init__(self, default_lang='es'):
        self.current_language = default_lang
        self.detect_system_language()

    def detect_system_language(self):
        """
        Intenta identificar de forma automática el idioma del sistema operativo.
        Si está dentro de los admitidos, lo configura como el idioma activo por defecto.
        """
        try:
            # Obtener localización por defecto del SO
            loc = locale.getdefaultlocale()[0]
            if loc:
                lang = loc.split('_')[0].lower()
                if lang in SUPPORTED_LANGUAGES:
                    self.current_language = lang
                    return
        except Exception:
            pass
            
        # Alternativa para sistemas POSIX/Linux inspeccionando variables de entorno comunes
        for env in ('LANG', 'LC_ALL', 'LC_MESSAGES'):
            val = os.environ.get(env)
            if val:
                lang = val.split('_')[0].lower()
                if lang in SUPPORTED_LANGUAGES:
                    self.current_language = lang
                    return
                    
        # Caer en la opción por defecto en caso de no poder detectar
        self.current_language = 'en'

    def set_language(self, lang):
        """
        Modifica el idioma actual de la aplicación.
        
        Args:
            lang (str): Código ISO de 2 letras (es, en, fr, pt, de, it, hi, zh, ru, ro).
        """
        if lang in SUPPORTED_LANGUAGES:
            self.current_language = lang
            logger.info(f"Language changed to: {lang} ({SUPPORTED_LANGUAGES[lang]})")

    def get_language(self):
        """
        Devuelve el código del idioma activo actual.
        """
        return self.current_language

    def t(self, key, **kwargs):
        """
        Traduce una etiqueta al idioma seleccionado.
        
        Si la clave no existe, devuelve la propia clave para alertar del error de traducción.
        Si la clave existe pero no tiene traducción en el idioma actual, cae en español o inglés.
        
        Args:
            key (str): Nombre de la clave a consultar.
            **kwargs: Parámetros opcionales para formatear en la cadena del mensaje.
            
        Returns:
            str: Texto localizado y formateado.
        """
        if key not in TRANSLATIONS:
            logger.warning(f"Translation key not found: '{key}'")
            return key
            
        translations_dict = TRANSLATIONS[key]
        
        # Intentar el idioma actual, caer en español, inglés o en la primera disponible
        text = translations_dict.get(self.current_language)
        if not text:
            text = translations_dict.get('es')
        if not text:
            text = translations_dict.get('en')
        if not text:
            # Primera opción disponible en el diccionario
            text = next(iter(translations_dict.values()))
            
        # Formatear si se pasaron argumentos adicionales de reemplazo (ej. {drive})
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError as e:
                logger.error(f"Formatting error in translation key '{key}': missing placeholder {e}")
                
        return text
