import os
import sys
import winreg

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
        return winreg.OpenKey(root, REG_SUBKEY, 0, access)
    except FileNotFoundError:
        if access & winreg.KEY_WRITE:
            return winreg.CreateKeyEx(root, REG_SUBKEY, 0, access)
        raise
    
def set_base_path_registry(path: str, per_user: bool = True):
    """
    Save path to the registry. Uses REG_EXPAND_SZ if it contains %VAR% so it can expand later.
    """
    root = winreg.HKEY_CURRENT_USER if per_user else winreg.HKEY_LOCAL_MACHINE
    with _open_key(root, winreg.KEY_WRITE) as k:
        valtype = winreg.REG_EXPAND_SZ if "%" in path else winreg.REG_SZ
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
        return None
    except OSError:
        return None

class PathManager:
    
    initialized : bool = True if get_base_path_registry() else False

    
    def __init__(self):
        pass

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
            raise Exception("PathManager is not initialized. Please set the path first.")
        return os.path.expandvars(PathManager.base_path)

    def get_data_path(self) -> str:
        return os.path.join(self.get_base_path(), PATH_DATA_RELATIVE_DIR)

    def get_config_path(self) -> str:
        return os.path.join(self.get_base_path(), PATH_CONFIG_RELATIVE_DIR) 
    