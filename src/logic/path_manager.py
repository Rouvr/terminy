import os
import winreg
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.INFO)


REG_SUBKEY = r"Software\Terminy"
REG_VALNAME = "BasePath"

DEFAULT_WIN_PATH = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Terminy")
DEFAULT_UNIX_PATH = os.path.join(os.path.expanduser("~"), ".terminy")

PATH_DATA_RELATIVE_DIR = "data"
PATH_CONFIG_RELATIVE_DIR = "config"  


def _open_key(root, access):
    # Force 64-bit view on 64-bit Windows even if Python is 32-bit
    access |= winreg.KEY_WOW64_64KEY
    try:
        logger.info(f"[Path Manager][{datetime.now()}] _open_key: Opening registry key: {REG_SUBKEY}")
        return winreg.OpenKey(root, REG_SUBKEY, 0, access)
    except FileNotFoundError:
        logger.warning(f"[Path Manager][{datetime.now()}] _open_key: Registry key not found: {REG_SUBKEY}")
        if access & winreg.KEY_WRITE:
            logger.info(f"[Path Manager][{datetime.now()}] _open_key: Creating registry key: {REG_SUBKEY}")
            return winreg.CreateKeyEx(root, REG_SUBKEY, 0, access)
        logger.error(f"[Path Manager][{datetime.now()}] _open_key: Failed to open registry key: {REG_SUBKEY}")
        raise
    
def set_base_path_registry(path: str, per_user: bool = True):
    """
    Save path to the registry. Uses REG_EXPAND_SZ if it contains %VAR% so it can expand later.
    """
    root = winreg.HKEY_CURRENT_USER if per_user else winreg.HKEY_LOCAL_MACHINE
    with _open_key(root, winreg.KEY_WRITE) as k:
        valtype = winreg.REG_EXPAND_SZ if "%" in path else winreg.REG_SZ
        logger.info(f"[Path Manager][{datetime.now()}] set_base_path_registry: Setting registry value: {REG_VALNAME} = {path}")
        winreg.SetValueEx(k, REG_VALNAME, 0, valtype, path)


def get_base_path_registry(per_user: bool = True) -> str | None:
    """
    Read path from the registry. Expands env vars if the value is REG_EXPAND_SZ.
    Returns None if not set.
    """
    root = winreg.HKEY_CURRENT_USER if per_user else winreg.HKEY_LOCAL_MACHINE
    try:
        with _open_key(root, winreg.KEY_READ) as k:
            value, valtype = winreg.QueryValueEx(k, REG_VALNAME)
            return os.path.expandvars(value) if valtype == winreg.REG_EXPAND_SZ else value
    except FileNotFoundError:
        logger.warning(f"[Path Manager][{datetime.now()}] get_base_path_registry: Registry value not found: {REG_VALNAME}")
        return None
    except OSError:
        logger.error(f"[Path Manager][{datetime.now()}] get_base_path_registry: Error reading registry value: {REG_VALNAME}")
        return None

def remove_registry(per_user: bool = True):
    """
    Remove the base path from the registry.
    """
    root = winreg.HKEY_CURRENT_USER if per_user else winreg.HKEY_LOCAL_MACHINE
    try:
        with _open_key(root, winreg.KEY_WRITE) as k:
            winreg.DeleteValue(k, REG_VALNAME)
    except FileNotFoundError:
        logger.warning(f"[Path Manager][{datetime.now()}] remove_registry: Registry value not found: {REG_VALNAME}")
        pass
    except OSError:
        logger.error(f"[Path Manager][{datetime.now()}] remove_registry: Error removing registry value: {REG_VALNAME}")
        pass

class PathManager:
    
    initialized : bool = True if get_base_path_registry() else False

    
    def __init__(self):
        pass

    def __repr__(self):
        str = ""
        str += f"PathManager(initialized={self.initialized}, base_path={PathManager.base_path})"
        str += f"Registry={get_base_path_registry()}"

    def is_initialized(self) -> bool:
        return PathManager.initialized
    
    def set_path(self, path: str):
        PathManager.base_path = path
        PathManager.initialized = True
        if not os.path.exists(path):
            os.makedirs(path)
        set_base_path_registry(path)
    
    def get_base_path(self) -> str:
        if not self.is_initialized():
            logger.warning(f"[Path Manager][{datetime.now()}] get_base_path: PathManager is not initialized.")
            logger.warning(f"[Path Manager][{datetime.now()}] PathManager{repr(self)}")
            raise Exception("PathManager is not initialized. Please set the path first.")
        return os.path.expandvars(PathManager.base_path)

    def get_data_path(self) -> str:
        return os.path.join(self.get_base_path(), PATH_DATA_RELATIVE_DIR)

    def get_config_path(self) -> str:
        return os.path.join(self.get_base_path(), PATH_CONFIG_RELATIVE_DIR) 
    