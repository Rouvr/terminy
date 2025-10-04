import os
import winreg
from datetime import datetime

import logging
from logging.handlers import RotatingFileHandler
logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.DEBUG)


class RegistryManager:
    REG_SUBKEY = r"Software\Terminy"
    REG_BASEPATH = "BasePath"
    REG_LOCALE_TAG = "LocaleTag"

    # Cache for registry values - key format: (key_name, per_user)
    _cache = {}

    DEFAULT_WIN_PATH = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Terminy")
    # DEFAULT_UNIX_PATH = os.path.join(os.path.expanduser("~"), ".terminy") #Not implemented for Unix

    @staticmethod
    def _open_key(root, access):
        # Force 64-bit view on 64-bit Windows even if Python is 32-bit
        access |= winreg.KEY_WOW64_64KEY
        try:
            logger.info(f"[Registry Manager][{datetime.now()}] _open_key: Opening registry key: {RegistryManager.REG_SUBKEY}")
            return winreg.OpenKey(root, RegistryManager.REG_SUBKEY, 0, access)
        except FileNotFoundError:
            logger.warning(f"[Registry Manager][{datetime.now()}] _open_key: Registry key not found: {RegistryManager.REG_SUBKEY}")
            if access & winreg.KEY_WRITE:
                logger.info(f"[Registry Manager][{datetime.now()}] _open_key: Creating registry key: {RegistryManager.REG_SUBKEY}")
                return winreg.CreateKeyEx(root, RegistryManager.REG_SUBKEY, 0, access)
            logger.error(f"[Registry Manager][{datetime.now()}] _open_key: Failed to open registry key: {RegistryManager.REG_SUBKEY}")
            raise
        
    @staticmethod
    def _invalidate_cache():
        """
        Clear the entire cache when registry is modified.
        """
        RegistryManager._cache.clear()
        logger.debug(f"[Registry Manager][{datetime.now()}] _invalidate_cache: Registry cache cleared")

    @staticmethod
    def clear_cache():
        """
        Public method to manually clear the registry cache.
        Useful for testing or if external registry modifications are detected.
        """
        RegistryManager._invalidate_cache()
        logger.info(f"[Registry Manager][{datetime.now()}] clear_cache: Registry cache manually cleared")

    @staticmethod
    def set_reg_key(key_name: str, data: str, per_user: bool = True):
        """
        Save path to the registry. Uses REG_EXPAND_SZ if it contains %VAR% so it can expand later.
        Invalidates cache after setting the value.
        """
        root = winreg.HKEY_CURRENT_USER if per_user else winreg.HKEY_LOCAL_MACHINE
        with RegistryManager._open_key(root, winreg.KEY_WRITE) as k:
            valtype = winreg.REG_EXPAND_SZ if "%" in data else winreg.REG_SZ
            logger.info(f"[Registry Manager][{datetime.now()}] set_reg_key: Setting registry value: {key_name} = {data}")
            winreg.SetValueEx(k, key_name, 0, valtype, data)
            # Invalidate cache after modifying registry
            RegistryManager._invalidate_cache()

    @staticmethod
    def get_reg_key(key_name: str, per_user: bool = True) -> str | None:
        """
        Read path from the registry. Expands env vars if the value is REG_EXPAND_SZ.
        Returns None if not set.
        Uses caching to avoid repeated registry access.
        """
        cache_key = (key_name, per_user)
        
        # Check cache first
        if cache_key in RegistryManager._cache:
            logger.debug(f"[Registry Manager][{datetime.now()}] get_reg_key: Cache hit for {key_name}")
            return RegistryManager._cache[cache_key]
        
        # Cache miss - read from registry
        logger.debug(f"[Registry Manager][{datetime.now()}] get_reg_key: Cache miss for {key_name}, reading from registry")
        root = winreg.HKEY_CURRENT_USER if per_user else winreg.HKEY_LOCAL_MACHINE
        try:
            with RegistryManager._open_key(root, winreg.KEY_READ) as k:
                value, valtype = winreg.QueryValueEx(k, key_name)
                result = os.path.expandvars(value) if valtype == winreg.REG_EXPAND_SZ else value
                # Cache the result
                RegistryManager._cache[cache_key] = result
                logger.debug(f"[Registry Manager][{datetime.now()}] get_reg_key: Cached value for {key_name}")
                return result
        except FileNotFoundError:
            logger.warning(f"[Registry Manager][{datetime.now()}] get_reg_key: Registry value not found: {key_name}")
            # Cache the None result to avoid repeated failed lookups
            RegistryManager._cache[cache_key] = None
            return None
        except OSError:
            logger.error(f"[Registry Manager][{datetime.now()}] get_reg_key: Error reading registry value: {key_name}")
            # Don't cache errors - allow retry on next access
            return None
    @staticmethod
    def remove_registry(key_name: str, per_user: bool = True):
        """
        Remove the specified key from the registry.
        Invalidates cache after removing the value.
        """
        root = winreg.HKEY_CURRENT_USER if per_user else winreg.HKEY_LOCAL_MACHINE
        try:
            with RegistryManager._open_key(root, winreg.KEY_WRITE) as k:
                winreg.DeleteValue(k, key_name)
                logger.info(f"[Registry Manager][{datetime.now()}] remove_registry: Removed registry value: {key_name}")
                # Invalidate cache after modifying registry
                RegistryManager._invalidate_cache()
        except FileNotFoundError:
            logger.warning(f"[Registry Manager][{datetime.now()}] remove_registry: Registry value not found: {key_name}")
            pass
        except OSError:
            logger.error(f"[Registry Manager][{datetime.now()}] remove_registry: Error removing registry value: {key_name}")
            pass