import os
import json
import logging

logger = logging.getLogger("SFTPMounter.ConfigManager")

class ConfigManager:
    """
    Manages loading, saving, and deleting SFTP connection profiles.
    Profiles are stored in a JSON file in the user's application data directory.
    """
    def __init__(self):
        # Determine appropriate configuration directory
        if os.name == 'nt':
            # Windows: %APPDATA%/SFTPMounter
            self.config_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'SFTPMounter')
        else:
            # Linux/macOS fallback: ~/.config/sftpmounter
            self.config_dir = os.path.join(os.path.expanduser('~'), '.config', 'sftpmounter')
            
        self.config_file = os.path.join(self.config_dir, 'profiles.json')
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create configuration directory: {e}")

    def _read_raw(self):
        """Reads raw data from the configuration file, converting old formats if necessary."""
        if not os.path.exists(self.config_file):
            return {"profiles": {}, "settings": {}}
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and ("profiles" in data or "settings" in data):
                    if "profiles" not in data:
                        data["profiles"] = {}
                    if "settings" not in data:
                        data["settings"] = {}
                    return data
                else:
                    # Backward compatibility for direct dict structure
                    return {"profiles": data if isinstance(data, dict) else {}, "settings": {}}
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            return {"profiles": {}, "settings": {}}

    def _write_raw(self, data):
        """Writes raw configuration data to the file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error writing config file: {e}")
            return False

    def load_profiles(self):
        """Loads all profiles from the JSON configuration file."""
        return self._read_raw()["profiles"]

    def save_profiles(self, profiles):
        """Saves the given profiles dictionary to the JSON configuration file."""
        data = self._read_raw()
        data["profiles"] = profiles
        return self._write_raw(data)

    def load_settings(self):
        """Loads global application settings."""
        return self._read_raw()["settings"]

    def save_settings(self, settings):
        """Saves global application settings."""
        data = self._read_raw()
        data["settings"] = settings
        return self._write_raw(data)

    def get_profile(self, name):
        """Retrieves a profile by name."""
        profiles = self.load_profiles()
        return profiles.get(name)

    def save_profile(self, name, profile_data):
        """Saves or updates a single profile by name."""
        profiles = self.load_profiles()
        profiles[name] = profile_data
        return self.save_profiles(profiles)

    def delete_profile(self, name):
        """Deletes a profile by name."""
        profiles = self.load_profiles()
        if name in profiles:
            del profiles[name]
            return self.save_profiles(profiles)
        return False

