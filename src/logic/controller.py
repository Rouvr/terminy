
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

logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.INFO)



class Controller:
    def __init__(self, **kwargs) -> None:
        logger.info(f"[Controller][{datetime.now()}] Initializing Controller...")
        self.path_manager = PathManager()
        
        data_path = kwargs.get("data_path", "")

        if self.path_manager.is_initialized() and not data_path:
            data_path = self.path_manager.get_data_path()

        logger.info(f"[Controller][{datetime.now()}] Final data path: {data_path}")
        logger.info(f"[Controller][{datetime.now()}] Resolved data_path: {os.path.realpath(data_path)}")

        if not data_path:
            logger.error(f"[Controller][{datetime.now()}] Controller requires a data path. Please set it via PathManager or pass 'data_path' argument.")
            raise Exception("Controller requires a data path. Please set it via PathManager or pass 'data_path' argument.")
        
        self.JSON_file = os.path.join(data_path, "data.json")
        self.JSON_recycle_bin = os.path.join(data_path, "recycle_bin.json")
        logger.info(f"[Controller][{datetime.now()}] Json files: {self.JSON_file}, {self.JSON_recycle_bin}")

        self.root_directory: Directory = self._load_or_create_JSON(self.JSON_file)
        self.recycle_bin: Directory = self._load_or_create_JSON(self.JSON_recycle_bin)


        self.clipboard: List[FileObject] = []
        self.clipboard_action: str = "copy"  # or "cut"
        
        # Build index
        self.record_indexer = RecordIndexer(self.root_directory)

        self.id_cache: Dict[str, FileObject] = {}
        for obj in Directory._walk_records(self.root_directory):
            self.id_cache[obj._id] = obj
            
        self.search = self.record_indexer.search

        self.current_dir: Directory = self.root_directory
        self.dir_history = [self.current_dir]
        self.dir_history_index = 0


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
        if directory is None or not directory.is_child_of(self.root_directory):
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
            logging.info(f"[Controller][{datetime.now()}] Fetching all records in root directory.")
            return self.record_indexer.all_records()
        logging.info(f"[Controller][{datetime.now()}] Fetching records in directory: {self.current_dir._file_name}")
        return self.current_dir.list_records() if self.current_dir else []

    # ------------ JSON + state Operations ------------

    def _load_or_create_JSON(self, path: str) -> Directory:
        logger.info(f"[Controller][{datetime.now()}] Loading or creating JSON at {path}")
        # Ensure the parent directory exists
        parent_dir = os.path.dirname(path)
        logger.info(f"[Controller][{datetime.now()}] Checking parent directory: {parent_dir}")
        if not os.path.exists(parent_dir) or not os.path.isdir(parent_dir):
            logger.info(f"[Controller][{datetime.now()}] Parent directory {parent_dir} does not exist or is not a directory, creating it.")
            os.makedirs(parent_dir, exist_ok=True)
        
        # Double-check if the file exists
        if not os.path.exists(path) or not os.path.isfile(path):
            logger.info(f"[Controller][{datetime.now()}] File {path} does not exist or is not a file, creating new empty directory.")
            d = Directory.new_empty_directory()
            try:
                self.save_dir(d, path)
                logger.info(f"[Controller][{datetime.now()}] Saved new directory to {path}")
            except Exception as e:
                logger.error(f"[Controller][{datetime.now()}] Error saving directory to {path}: {e}")
                raise
        else:
            logger.info(f"[Controller][{datetime.now()}] File {path} exists, loading directory.")

        logger.info(f"[Controller][{datetime.now()}] Real path = {os.path.realpath(path)}")

        try:
            return self.load(path)
        except Exception as e:
            logger.error(f"[Controller][{datetime.now()}] Error loading directory from {path}: {e}")
            raise

    def save_dir(self,directory : Directory, path: str):
        if directory is None:
            logger.error(f"[Controller][{datetime.now()}] save_dir: directory is None, cannot save.")
            return
        data = directory.to_dict()
        blob = json.dumps(data, indent=2)
        
        
        if os.path.exists(path):
            os.rename(path, path + ".old")

        os.makedirs(os.path.dirname(path), exist_ok=True)
        logger.info(f"Writing to {path}")
        with open(path, "w+", encoding="utf-8") as f:
            f.write(blob)
            
    def load(self, path: str) -> Directory:
        if not os.path.exists(path):
            logger.error(f"Data file not found: {path}")
            raise FileNotFoundError(f"Data file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            blob = f.read()
        data = json.loads(blob)
        if not data:
            logger.warning(f"No data found in {path}, creating new empty directory.")
            return  Directory.new_empty_directory()
        return Directory.from_dict(data)
        
    def save_state(self):
        self.save_dir(self.root_directory, self.JSON_file)
        self.save_dir(self.recycle_bin, self.JSON_recycle_bin)
    
    def exit_and_save(self):
        self.save_state()
        exit(0)

   # ------------ File Operations ------------

    def delete_file_object(self, obj: FileObject):
        if obj is None:
            return
        if obj.is_child_of(self.recycle_bin):
            logger.info(f"[Controller][{datetime.now()}] Permanently deleting object from recycle bin: {obj._file_name}")
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
        
        target_dir = self.path_to_file(restore_path)
        if target_dir is None:
            logger.warning(f"[Controller][{datetime.now()}] Restore path '{restore_path}' not found, restoring to root.")
            target_dir = self.root_directory
        
        if not isinstance(target_dir, Directory):
            logger.warning(f"[Controller][{datetime.now()}] Restore path '{restore_path}' is not a directory, restoring to root.")
            target_dir = self.root_directory
        
        if target_dir.can_inherit_children(obj):
            self.recycle_bin.release_children(obj)
            target_dir.inherit_children(obj)
            logger.info(f"[Controller][{datetime.now()}] Restored object to '{target_dir._file_name}'.")
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
        
    def path_to_file(self, path: str) -> Optional[FileObject]:
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
        file_object = self.path_to_file(path)
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

    def get_favorite_dirs(self) -> List[Directory]:
        return [obj for obj in self.id_cache.values() if isinstance(obj, Directory) and obj.is_favorite()]