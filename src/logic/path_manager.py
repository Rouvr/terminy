import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

from src.logic.registry import RegistryManager

logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.INFO)


class PathManager:
    PATH_DATA_RELATIVE_DIR = "data"
    PATH_CONFIG_RELATIVE_DIR = "config"  
    

    def __init__(self):
        self.base_path: str | None = RegistryManager.get_reg_key(RegistryManager.REG_BASEPATH)
        self.initialized : bool = bool(self.base_path)

    def __repr__(self):
        str = ""
        str += f"PathManager(initialized={self.initialized}, base_path={self.base_path})"
        str += f"Registry={RegistryManager.get_reg_key(RegistryManager.REG_BASEPATH)}"

    def is_initialized(self) -> bool:
        return self.initialized

    def set_path(self, path: str):
        PathManager.base_path = path
        PathManager.initialized = True
        if not os.path.exists(path):
            os.makedirs(path)
        RegistryManager.set_reg_key(RegistryManager.REG_BASEPATH, path)

    def get_base_path(self) -> str:
        if not self.is_initialized() or not self.base_path: # second half only for python type checker
            logger.warning(f"[Path Manager][{datetime.now()}] get_base_path: PathManager is not initialized.")
            logger.warning(f"[Path Manager][{datetime.now()}] PathManager{repr(self)}")
            raise Exception("PathManager is not initialized. Please set the path first.")

        return os.path.expandvars(self.base_path)

    def get_data_path(self) -> str:
        return os.path.join(self.get_base_path(), self.PATH_DATA_RELATIVE_DIR)

    def get_config_path(self) -> str:
        return os.path.join(self.get_base_path(), self.PATH_CONFIG_RELATIVE_DIR)
