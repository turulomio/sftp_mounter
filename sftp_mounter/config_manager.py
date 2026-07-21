"""
Gestor de configuración y perfiles de conexión de SFTP Mounter.

Este módulo implementa la clase `ConfigManager`, encargada de persistir y recuperar los datos 
de configuración del usuario (perfiles de conexión y ajustes globales) en un archivo JSON local.

Estructura del archivo JSON de configuración (`profiles.json`):
-------------------------------------------------------------
{
    "profiles": {
        "Nombre Del Perfil": {
            "host": "sftp.example.com",
            "port": 22,
            "user": "usuario",
            "auth_type": "password" | "key",
            "password": "...",        # Contraseña en texto plano antes de ser enviada a obscurecer por rclone
            "key_path": "/ruta/a/id_rsa",
            "key_password": "...",    # Contraseña opcional para llave privada cifrada
            "remote_path": "/var/www",
            "drive_letter": "X:",
            "auto_mount": true | false
        }
    },
    "settings": {
        "minimize_to_tray": true | false,
        "start_with_windows": true | false
    }
}

Para nuevos desarrolladores:
- Los métodos internos que inician con guion bajo (`_read_raw`, `_write_raw`) operan directamente
  con la estructura de almacenamiento raíz. No se deben invocar desde el exterior del módulo.
- La persistencia resuelve problemas de compatibilidad si el usuario tuviera un archivo antiguo
  que solo guardaba un diccionario plano de perfiles.
"""

import os
import json
import logging
from configparser_rb import string_to_rotatedbase64, rotatedbase64_to_string

logger = logging.getLogger("SFTPMounter.ConfigManager")

def _encode_pass(val):
    if not val:
        return ""
    try:
        return string_to_rotatedbase64(val)
    except Exception as e:
        logger.error(f"Error obfuscating password: {e}")
        return val

def _decode_pass(val):
    if not val:
        return ""
    try:
        return rotatedbase64_to_string(val)
    except Exception:
        # Fallback si era contraseña antigua en plano
        return val

class ConfigManager:
    """
    Administra la lectura, escritura y eliminación de perfiles de conexión y configuraciones generales.
    
    Los perfiles se almacenan de manera persistente en formato JSON en el directorio de datos de la aplicación,
    evitando la pérdida de información entre ejecuciones.
    """
    def __init__(self):
        """
        Inicializa el gestor de configuración calculando la ruta óptima según el sistema operativo.
        """
        # Determinar el directorio de configuración adecuado según el SO
        if os.name == 'nt':
            # Windows: %APPDATA%/SFTPMounter
            self.config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SFTPMounter')
        else:
            # Linux/macOS fallback estándar: ~/.config/sftpmounter
            self.config_dir = os.path.join(os.path.expanduser('~'), '.config', 'sftpmounter')
            
        self.config_file = os.path.join(self.config_dir, 'profiles.json')
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """
        Garantiza de forma segura la existencia física del directorio de configuración.
        """
        try:
            os.makedirs(self.config_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create configuration directory: {e}")

    def _read_raw(self):
        """
        Realiza la lectura física del archivo JSON y gestiona la retrocompatibilidad.
        
        Si el archivo no existe, devuelve una estructura vacía inicializada por defecto.
        Si encuentra un formato antiguo (donde el JSON contenía directamente la lista de perfiles
        en la raíz en lugar del diccionario estructurado con la clave "profiles"), migra los datos
        al vuelo para evitar roturas.
        
        Returns:
            dict: Diccionario raíz con las claves obligatorias 'profiles' y 'settings'.
        """
        if not os.path.exists(self.config_file):
            return {"profiles": {}, "settings": {}}
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Comprobar si tiene el formato estructurado moderno
                if isinstance(data, dict) and ("profiles" in data or "settings" in data):
                    if "profiles" not in data:
                        data["profiles"] = {}
                    if "settings" not in data:
                        data["settings"] = {}
                    return data
                else:
                    # MIGRACIÓN / COMPATIBILIDAD RETROACTIVA:
                    # Si el archivo contenía un diccionario plano directo, lo envolvemos
                    # en la clave "profiles" y creamos una sección de "settings" vacía.
                    logger.info("Migrando archivo de configuración antiguo a formato estructurado.")
                    return {"profiles": data if isinstance(data, dict) else {}, "settings": {}}
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return {"profiles": {}, "settings": {}}

    def _write_raw(self, data):
        """
        Escribe de forma física la estructura del diccionario completo en el archivo JSON.
        
        Args:
            data (dict): Diccionario estructurado que contiene 'profiles' y 'settings'.
            
        Returns:
            bool: True si la escritura se completó con éxito, False de lo contrario.
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                # Escribir con sangría (indent=4) para facilitar su edición/lectura manual si fuera necesario
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error writing config file: {e}")
            return False

    def load_profiles(self):
        """
        Carga y devuelve todos los perfiles de conexión SFTP, descifrando las contraseñas guardadas.
        
        Returns:
            dict: Colección de perfiles donde la clave es el nombre del perfil y el valor sus datos de configuración.
        """
        raw_profiles = self._read_raw()["profiles"]
        decoded_profiles = {}
        for name, profile in raw_profiles.items():
            p_copy = dict(profile)
            if 'password' in p_copy:
                p_copy['password'] = _decode_pass(p_copy['password'])
            if 'key_password' in p_copy:
                p_copy['key_password'] = _decode_pass(p_copy['key_password'])
            decoded_profiles[name] = p_copy
        return decoded_profiles

    def save_profiles(self, profiles):
        """
        Guarda la colección completa de perfiles en el disco cifrando las contraseñas.
        
        Args:
            profiles (dict): Diccionario completo con todos los perfiles de usuario.
            
        Returns:
            bool: True si se guardó con éxito, False en caso de error.
        """
        encoded_profiles = {}
        for name, profile in profiles.items():
            p_copy = dict(profile)
            if 'password' in p_copy:
                p_copy['password'] = _encode_pass(p_copy['password'])
            if 'key_password' in p_copy:
                p_copy['key_password'] = _encode_pass(p_copy['key_password'])
            encoded_profiles[name] = p_copy

        data = self._read_raw()
        data["profiles"] = encoded_profiles
        return self._write_raw(data)

    def load_settings(self):
        """
        Obtiene la configuración global de la aplicación (auto-inicio, minimizar en segundo plano, etc.).
        
        Returns:
            dict: Claves de configuración global y sus estados booleanos.
        """
        return self._read_raw()["settings"]

    def save_settings(self, settings):
        """
        Guarda la configuración global del sistema de forma persistente.
        
        Args:
            settings (dict): Ajustes globales a guardar.
            
        Returns:
            bool: True si se guardó con éxito, False en caso de error.
        """
        data = self._read_raw()
        data["settings"] = settings
        return self._write_raw(data)

    def get_profile(self, name):
        """
        Recupera los datos de conexión de un perfil específico dado su nombre.
        
        Args:
            name (str): Nombre del perfil que se desea consultar.
            
        Returns:
            dict | None: Diccionario con la configuración del perfil, o None si no existe.
        """
        profiles = self.load_profiles()
        return profiles.get(name)

    def save_profile(self, name, profile_data):
        """
        Crea o actualiza de forma individual un perfil por su nombre de identificación.
        
        Args:
            name (str): Nombre único del perfil.
            profile_data (dict): Diccionario con los parámetros de conexión SFTP asociados.
            
        Returns:
            bool: True si se guardaron los cambios del perfil, False en caso de error.
        """
        profiles = self.load_profiles()
        profiles[name] = profile_data
        return self.save_profiles(profiles)

    def delete_profile(self, name):
        """
        Elimina de forma permanente un perfil identificado por su nombre.
        
        Args:
            name (str): Nombre del perfil que se desea eliminar.
            
        Returns:
            bool: True si se eliminó y guardaron los cambios, False si el perfil no existía o falló el guardado.
        """
        profiles = self.load_profiles()
        if name in profiles:
            del profiles[name]
            return self.save_profiles(profiles)
        return False

