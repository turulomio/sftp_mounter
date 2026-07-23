"""
Configuration and connection profiles manager for SFTP Mounter.

This module implements the `ConfigManager` class, responsible for persisting and retrieving user
configuration data (connection profiles and global settings) in a local JSON file.

JSON configuration file structure (`profiles.json`):
-------------------------------------------------------------
{
    "profiles": {
        "Profile Name": {
            "host": "sftp.example.com",
            "port": 22,
            "user": "username",
            "auth_type": "password" | "key",
            "password": "...",        # Plaintext password before being obscured by rclone
            "key_path": "/path/to/id_rsa",
            "key_password": "...",    # Optional passphrase for encrypted private key
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

For new developers:
- Internal methods starting with an underscore (`_read_raw`, `_write_raw`) operate directly
  with the root storage structure. They should not be called from outside the module.
- Persistence resolves compatibility issues if the user had an old file
  that only saved a flat dictionary of profiles.
"""

import os
import json
import logging
import base64

logger = logging.getLogger("SFTPMounter.ConfigManager")

_OFS_KEY = 0x5A  # Simple XOR mask to obfuscate plaintext

def _encode_pass(val: str) -> str:
    if not val:
        return ""
    try:
        # Apply simple XOR transformation + native Base64
        obfuscated_bytes = bytes([b ^ _OFS_KEY for b in val.encode('utf-8')])
        return base64.b64encode(obfuscated_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"Error obfuscating password: {e}")
        return val

def _decode_pass(val: str) -> str:
    if not val:
        return ""
    try:
        # Decode Base64 + revert XOR mask
        decoded_bytes = base64.b64decode(val.encode('utf-8'))
        deobfuscated_bytes = bytes([b ^ _OFS_KEY for b in decoded_bytes])
        return deobfuscated_bytes.decode('utf-8')
    except Exception:
        # Fallback for backward compatibility if the password was in plaintext or previous format
        return val

class ConfigManager:
    """
    Manages the reading, writing, and deletion of connection profiles and general settings.
    
    Profiles are persistently stored in JSON format in the application's data directory,
    preventing information loss between executions.
    """
    def __init__(self):
        """
        Initializes the configuration manager by calculating the optimal path according to the OS.
        """
        # Windows: %APPDATA%/SFTPMounter
        self.config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SFTPMounter')
        self._ensure_config_dir()
        self.config_file = os.path.join(self.config_dir, 'profiles.json')

    def _ensure_config_dir(self):
        """
        Safely guarantees the physical existence of the configuration directory.
        """
        try:
            os.makedirs(self.config_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create configuration directory in AppData, falling back to temp: {e}")
            import tempfile
            self.config_dir = os.path.join(tempfile.gettempdir(), 'SFTPMounter')
            try:
                os.makedirs(self.config_dir, exist_ok=True)
            except Exception:
                pass

    def _read_raw(self):
        """
        Performs the physical reading of the JSON file and manages backward compatibility.
        
        If the file does not exist, returns an empty structure initialized by default.
        If it finds an old format (where the JSON directly contained the list of profiles
        in the root instead of the structured dictionary with the "profiles" key), it migrates the data
        on the fly to avoid breakage.
        
        Returns:
            dict: Root dictionary with the mandatory keys 'profiles' and 'settings'.
        """
        if not os.path.exists(self.config_file):
            return {"profiles": {}, "settings": {}}
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Check if it has the modern structured format
                if isinstance(data, dict) and ("profiles" in data or "settings" in data):
                    if "profiles" not in data:
                        data["profiles"] = {}
                    if "settings" not in data:
                        data["settings"] = {}
                    return data
                else:
                    # BACKWARD COMPATIBILITY MIGRATION:
                    # If the file contained a direct flat dictionary, we wrap it
                    # in the "profiles" key and create an empty "settings" section.
                    logger.info("Migrating old configuration file to structured format.")
                    return {"profiles": data if isinstance(data, dict) else {}, "settings": {}}
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return {"profiles": {}, "settings": {}}

    def _write_raw(self, data):
        """
        Physically writes the structure of the entire dictionary to the JSON file.
        
        Args:
            data (dict): Structured dictionary containing 'profiles' and 'settings'.
            
        Returns:
            bool: True if the write completed successfully, False otherwise.
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                # Write with indentation (indent=4) to facilitate manual editing/reading if necessary
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error writing config file: {e}")
            return False

    def load_profiles(self):
        """
        Loads and returns all SFTP connection profiles, decrypting saved passwords.
        
        Returns:
            dict: Collection of profiles where the key is the profile name and the value is its configuration data.
        """
        raw_profiles = self._read_raw()["profiles"]
        decoded_profiles = {}
        for name, profile in raw_profiles.items():
            p_copy = dict(profile)
            p_copy['profile_name'] = name
            if 'password' in p_copy:
                p_copy['password'] = _decode_pass(p_copy['password'])
            if 'key_password' in p_copy:
                p_copy['key_password'] = _decode_pass(p_copy['key_password'])
            decoded_profiles[name] = p_copy
        return decoded_profiles

    def save_profiles(self, profiles):
        """
        Saves the complete collection of profiles to disk, encrypting passwords.
        
        Args:
            profiles (dict): Complete dictionary with all user profiles.
            
        Returns:
            bool: True if saved successfully, False in case of error.
        """
        encoded_profiles = {}
        for name, profile in profiles.items():
            p_copy = dict(profile)
            if 'profile_name' in p_copy:
                p_copy.pop('profile_name')
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
        Retrieves the global configuration of the application (autostart, minimize to tray, etc.).
        
        Returns:
            dict: Global configuration keys and their boolean states.
        """
        return self._read_raw()["settings"]

    def save_settings(self, settings):
        """
        Saves the global system configuration persistently.
        
        Args:
            settings (dict): Global settings to save.
            
        Returns:
            bool: True if saved successfully, False in case of error.
        """
        data = self._read_raw()
        data["settings"] = settings
        return self._write_raw(data)

    def get_profile(self, name):
        """
        Retrieves the connection data of a specific profile by its identifier name.
        
        Args:
            name (str): Name of the profile to query.
            
        Returns:
            dict | None: Dictionary with profile configuration, or None if it does not exist.
        """
        profiles = self.load_profiles()
        return profiles.get(name)

    def save_profile(self, name, profile_data):
        """
        Creates or updates a single profile by its identification name.
        
        Args:
            name (str): Unique name of the profile.
            profile_data (dict): Dictionary with associated SFTP connection parameters.
            
        Returns:
            bool: True if profile changes were saved, False in case of error.
        """
        profiles = self.load_profiles()
        profiles[name] = profile_data
        return self.save_profiles(profiles)

    def delete_profile(self, name):
        """
        Permanently deletes a profile identified by its name.
        
        Args:
            name (str): Name of the profile to delete.
            
        Returns:
            bool: True if deleted and changes saved, False if the profile did not exist or saving failed.
        """
        profiles = self.load_profiles()
        if name in profiles:
            del profiles[name]
            return self.save_profiles(profiles)
        return False
