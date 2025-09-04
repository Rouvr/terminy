
import os
import json
import logging
from logging.handlers import RotatingFileHandler

from typing import Dict, List, Optional, cast
from datetime import datetime

from .directory import Directory
from .record import Record
from .helpers import normalize
from .path_manager import PathManager
from .file_object import FileObject
from .indexer import RecordIndexer
from .storage import Storage

logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.DEBUG)



class Controller:
    def __init__(self, **kwargs) -> None:
        
        # Initialize PathManager and determine data/config paths
        logger.debug(f"[Controller][{datetime.now()}] Initializing Controller...")
        self.path_manager = PathManager()
        
        data_path = kwargs.get("data_path", "")
        config_path = kwargs.get("config_path", "")

        if self.path_manager.is_initialized() and not data_path:
            data_path = self.path_manager.get_data_path()
        if self.path_manager.is_initialized() and not config_path:
            config_path = self.path_manager.get_config_path()

        logger.info(f"[Controller][{datetime.now()}] Final data path: {data_path}")
        logger.info(f"[Controller][{datetime.now()}] Resolved data_path: {os.path.realpath(data_path)}")

        if not data_path:
            logger.error(f"[Controller][{datetime.now()}] Controller requires a data path. Please set it via PathManager or pass 'data_path' argument.")
            raise Exception("Controller requires a data path. Please set it via PathManager or pass 'data_path' argument.")

        self.JSON_config = os.path.join(data_path, "config.json")
        self.JSON_data = os.path.join(data_path, "data.json")
        self.JSON_recycle_bin = os.path.join(data_path, "recycle_bin.json")
        logger.debug(f"[Controller][{datetime.now()}] Json files: {self.JSON_data}, {self.JSON_recycle_bin}")

        # Load root directory
        try:
            self.root_directory: Directory = Storage.load_dir(self.JSON_data)
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"[Controller][{datetime.now()}] Error loading root directory: {e}")
            self.root_directory = Directory.new_empty_directory()

        # Load recycle bin
        try:
            self.recycle_bin: Directory = Storage.load_dir(self.JSON_recycle_bin)
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"[Controller][{datetime.now()}] Error loading recycle bin: {e}")
            self.recycle_bin = Directory.new_empty_directory()

        # Load config
        try:
            self.config: dict = Storage.load_config(self.JSON_config)
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"[Controller][{datetime.now()}] Error loading config: {e}")
            self.config = {}

        # Build index
        self.record_indexer = RecordIndexer(self.root_directory)

        self.id_cache: Dict[str, FileObject] = {}
        for obj in Directory._walk_records(self.root_directory):
            self.id_cache[obj._id] = obj
        self.search = self.record_indexer.search


        # Working variables 
        self.clipboard: List[FileObject] = []
        self.clipboard_action: str = "copy"  # or "cut"
        
        self.current_dir: Directory = self.root_directory
        self.dir_history = [self.current_dir]
        self.dir_history_index = 0
        
        self._favorites = []
        self._load_favorites()

    # ------------ Directories ------------

    def get_root(self) -> Directory:
        return self.root_directory
    
    def get_recycle_bin(self) -> Directory:
        return self.recycle_bin
    
    def get_current_directory(self) -> Directory:
        return self.current_dir
    
    def navigate_up(self) -> bool:
        parent = cast(Directory, self.current_dir._parent if self.current_dir._parent else self.root_directory) 
        self.current_dir = parent
        self.dir_history.append(self.current_dir)
        self.dir_history_index = len(self.dir_history) - 1
        return True
    
    def navigate_to(self, directory: Directory) -> bool:
        if directory is None:
            logger.warning(f"[Controller][{datetime.now()}] navigate_to called with None directory.")
            return False 
        if not directory.is_child_of(self.root_directory) and directory != self.root_directory:
            logger.warning(f"[Controller][{datetime.now()}] navigate_to called with invalid directory: {directory}")
            return False
        self.current_dir = directory
        self.dir_history.append(self.current_dir)
        self.dir_history_index = len(self.dir_history) - 1
        return True

    def navigate_back(self) -> bool:
        if self.dir_history_index > 0:
            self.dir_history_index -= 1
            self.current_dir = self.dir_history[self.dir_history_index]
            return True
        return False
    
    def navigate_forward(self) -> bool:
        if self.dir_history_index < len(self.dir_history) - 1:
            self.dir_history_index += 1
            self.current_dir = self.dir_history[self.dir_history_index]
            return True
        return False
    
    def history_can_go_back(self) -> bool:
        return self.dir_history_index > 0

    def history_can_go_forward(self) -> bool:
        return self.dir_history_index < len(self.dir_history) - 1

    def get_current_directory_list(self) -> list[Directory]:
        return self.current_dir.list_directories() if self.current_dir else []

    def get_current_record_list(self) -> list[Record]:
        if self.current_dir == self.root_directory:
            logging.debug(f"[Controller][{datetime.now()}] Fetching all records in root directory.")
            return self.record_indexer.all_records()
        logging.debug(f"[Controller][{datetime.now()}] Fetching records in directory: {self.current_dir._file_name}")
        return self.current_dir.list_records() if self.current_dir else []

    # ------------ Favorites ------------

    def _load_favorites(self):
        self._favorites: List[Directory] = []

        for path in self.config.get("favorites", []):
            file = self.path_to_object(path)
            if file and isinstance(file, Directory):
                self._favorites.append(file)

    def add_favorite(self, file: Directory):
        if file and file not in self._favorites:
            self._favorites.append(file)
        self.config["favorites"] = [self.object_to_path(fav) for fav in self._favorites]

    def remove_favorite(self, file: Directory):
        if file in self._favorites:
            self._favorites.remove(file)
            self.config["favorites"] = [self.object_to_path(fav) for fav in self._favorites]

    def get_favorites(self) -> List[Directory]:
        return self._favorites
    

    # ------------ state Operations ------------

    def save_state(self):
        Storage.save_dir(self.root_directory, self.JSON_data)
        Storage.save_dir(self.recycle_bin, self.JSON_recycle_bin)
        Storage.save_config(self.JSON_config, self.config)
        logger.info(f"[Controller][{datetime.now()}] State saved successfully.")

    def exit_and_save(self):
        self.save_state()
        exit(0)

   # ------------ File Operations ------------

    def delete_file_object(self, obj: FileObject):
        if obj is None:
            return
        if obj.is_child_of(self.recycle_bin):
            logger.debug(f"[Controller][{datetime.now()}] Permanently deleting object from recycle bin: {obj._file_name}")
            self.id_cache.pop(obj._id, None)
            if obj._parent:
                parent = cast(Directory, obj._parent)
                parent.release_children(obj)
        else:
            original_path = obj.get_full_path()
            obj._restore_path = original_path 
            if obj._parent:
                parent = cast(Directory, obj._parent)
                parent.release_children(obj)
            self.recycle_bin.inherit_children(obj)
    
    def restore_file_object(self, obj: FileObject):
        if obj is None:
            return
        if not obj.is_child_of(self.recycle_bin):
            logger.warning(f"[Controller][{datetime.now()}] Object is not in recycle bin, cannot restore: {obj._file_name}")
            return
        if not obj._restore_path:
            logger.warning(f"[Controller][{datetime.now()}] No restore path found, cannot restore: {obj._file_name}")
            return
        
        restore_path = obj._restore_path
        obj._restore_path = None
        
        target_dir = self.path_to_object(restore_path)
        if target_dir is None:
            logger.warning(f"[Controller][{datetime.now()}] Restore path '{restore_path}' not found, restoring to root.")
            target_dir = self.root_directory
        
        if not isinstance(target_dir, Directory):
            logger.warning(f"[Controller][{datetime.now()}] Restore path '{restore_path}' is not a directory, restoring to root.")
            target_dir = self.root_directory
        
        if target_dir.can_inherit_children(obj):
            self.recycle_bin.release_children(obj)
            target_dir.inherit_children(obj)
            logger.debug(f"[Controller][{datetime.now()}] Restored object to '{target_dir._file_name}'.")
        else:
            logger.warning(f"[Controller][{datetime.now()}] Cannot restore object to '{target_dir._file_name}', name conflict.")

    def add_to_clipboard(self, objs: List[FileObject] | FileObject, action: str = "copy") -> bool:
        if objs is None or action not in ("copy", "cut"):
            return False

        if isinstance(objs, list):
            self.clipboard.extend(objs)
        else:
            self.clipboard.append(objs)

        self.clipboard_action = action
        return True
    
    def paste_from_clipboard(self, target_dir: Directory) -> bool:
        if target_dir is None or not self.clipboard:
            return False
        for obj in self.clipboard:
            if self.clipboard_action == "copy":
                new_obj = obj.copy()
                
                # sanity check TODO remove
                if new_obj._id in self.id_cache:
                    logger.fatal(f"[Controller][{datetime.now()}] ID conflict detected??? {new_obj._id}, {self.id_cache[new_obj._id]}, {self.id_cache}")
                    raise ValueError(f"ID conflict detected??? {new_obj._id}, {self.id_cache[new_obj._id]}, {self.id_cache}")
                
                self.id_cache[new_obj._id] = new_obj
                target_dir.inherit_children(new_obj)
            elif self.clipboard_action == "cut":
                target_dir.inherit_children(obj)
        return True

    def create_record(self, target_dir : Directory, **kwargs):
        if target_dir is None:
            return None
        record = Record(**kwargs)
        self.id_cache[record._id] = record
        self.record_indexer.update(record)
        target_dir.inherit_children(record)
        return record

    def create_directory(self, target_dir, **kwargs):
        if target_dir is None:
            return None
        directory = Directory(**kwargs)
        self.id_cache[directory._id] = directory
        target_dir.inherit_children(directory)
        return directory
    
    def edit_record(self, record: Record, **kwargs):
        if record is None:
            return None
        for key, value in kwargs.items():
            if key in ("_id"):
                continue
            setattr(record, key, value)
        self.record_indexer.update(record)
        return record
    
    def edit_directory(self, directory: Directory, **kwargs):
        if directory is None:
            return None
        for key, value in kwargs.items():
            if key in ("_id"):
                continue
            setattr(directory, key, value)
        return directory
    
    def move_file_objects(self, objects: List[FileObject] | FileObject, target_dir: Directory) -> bool:
        if not objects or target_dir is None:
            return False

        if not isinstance(target_dir, Directory):
            return False

        if isinstance(objects, FileObject):
            objects = [objects]
            
        if not target_dir.can_inherit_children(objects):
            return False
        
        target_dir.inherit_children(objects, check=False)


        return True

    # ---------------- File id conversions ---------------
    # Path
    # Object
    # ID
    # -- All -> All --
        
    def path_to_object(self, path: str) -> Optional[FileObject]:
        if not path or path == "/":
            return self.root_directory
        parts = [part for part in path.strip("/").split("/") if part]
        current = self.root_directory
        for part in parts:
            found = False
            for child in current.list_directories():
                if child._file_name == part:
                    current = child
                    found = True
                    break
            if not found:
                return None
        return current

    def path_to_id(self, path: str) -> Optional[str]:
        file_object = self.path_to_object(path)
        return file_object._id if file_object else None

    def object_to_id(self, obj: FileObject) -> Optional[str]:
        if not obj:
            return None
        return obj._id

    def object_to_path(self, obj: FileObject) -> Optional[str]:
        if not obj:
            return None
        return obj.get_full_path()
    
    def id_to_object(self, id: str) -> Optional[FileObject]:
        if not id:
            return None
        return self.id_cache.get(id, None)

    def id_to_path(self, id: str) -> Optional[str]:
        obj = self.id_to_object(id)
        return obj.get_full_path() if obj else None

