
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

from .directory import Directory

logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.INFO)


class Storage:
    @staticmethod
    def save_dir(directory : Directory, path: str):
        # Directory needs to exist
        if directory is None:
            logger.error(f"[Storage][{datetime.now()}] save_dir: directory is None, cannot save.")
            raise ValueError("Directory is None")
        
        data = directory.to_dict()
        blob = json.dumps(data, indent=2)

        # Remove old backup
        old_path = path + ".old"
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception as e:
                logger.error(f"[Storage][{datetime.now()}] Error removing old file: {e}")

        # Create backup
        if os.path.exists(path):
            try:
                os.rename(path, old_path)
            except Exception as e:
                logger.error(f"[Storage][{datetime.now()}] Error creating backup: {e}")

        # Write new directory
        os.makedirs(os.path.dirname(path), exist_ok=True)
        logger.info(f"[Storage][{datetime.now()}] Writing to {os.path.realpath(path)}")
        
        try:
            with open(path, "w+", encoding="utf-8") as f:
                f.write(blob)
        except Exception as e:
            logger.critical(f"[Storage][{datetime.now()}] Error writing to {os.path.realpath(path)}: {e}")

    @staticmethod
    def load_dir(path: str) -> Directory:
        if not os.path.exists(path):
            logger.error(f"[Storage][{datetime.now()}] Data file not found: {os.path.realpath(path)}")
            raise FileNotFoundError(f"Data file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            blob = f.read()
        data = json.loads(blob)
        if not data:
            logger.warning(f"[Storage][{datetime.now()}] No data found in {os.path.realpath(path)}, creating new empty directory.")
            return  Directory.new_empty_directory()
        return Directory.from_dict(data)
    
    @staticmethod
    def load_config( path: str) -> dict:
        if not os.path.exists(path):
            logger.error(f"[Storage][{datetime.now()}] Config file not found: {os.path.realpath(path)}")
            raise FileNotFoundError(f"Config file not found: {os.path.realpath(path)}")
        with open(path, "r", encoding="utf-8") as f:
            blob = f.read()
        data = json.loads(blob)
        if not data:
            logger.error(f"[Storage][{datetime.now()}] No data found in {os.path.realpath(path)}, returning empty config.")
            raise ValueError(f"No data found in {os.path.realpath(path)}")
        return data

    @staticmethod
    def save_config(path: str, config: dict):
        # Config needs to exist
        if config is None:
            logger.error(f"[Storage][{datetime.now()}] save_config: config is None, cannot save.")
            raise ValueError("Config is None")
        blob = json.dumps(config, indent=2)
        
        # Delete old backup
        old_path = path + ".old"
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception as e:
                logger.error(f"[Storage][{datetime.now()}] Error removing old file: {e}")

        # Create backup
        if os.path.exists(path):
            try:
                os.rename(path, old_path)
            except Exception as e:
                logger.error(f"[Storage][{datetime.now()}] Error creating backup: {e}")
            
        # Write new config
        os.makedirs(os.path.dirname(path), exist_ok=True)
        logger.info(f"[Storage][{datetime.now()}] Writing to {os.path.realpath(path)}")

        try:
            with open(path, "w+", encoding="utf-8") as f:
                f.write(blob)
        except Exception as e:
            logger.critical(f"[Storage][{datetime.now()}] Error writing to {os.path.realpath(path)}: {e}")