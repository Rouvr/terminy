
import os
import json

from typing import Dict, List, Optional, cast
from datetime import datetime

from .directory import Directory
from .record import Record
from .helpers import normalize
from .path_manager import PathManager
from .file_object import FileObject
from .indexer import RecordIndexer

class Controller:
    def __init__(self, **kwargs) -> None:
        self.path_manager = PathManager()
        
        data_path = kwargs.get("data_path", None)
        
        if self.path_manager.is_initialized() and data_path is None:
            data_path = self.path_manager.get_data_path()
            
        if data_path is None:
            raise Exception("Controller requires a data path. Please set it via PathManager or pass 'data_path' argument.")
        
        self.JSON_file = os.path.join(data_path, "data.json")
        self.JSON_recycle_bin = os.path.join(data_path, "recycle_bin.json")
        
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

    # ------------ Expose root ------------

    def get_root(self) -> Directory:
        return self.root_directory

    # ------------ JSON + state Operations ------------

    def _load_or_create_JSON(self, path: str) -> Directory:
        if not os.path.exists(path):
            d = Directory.new_empty_directory()
            self.save_dir(d, path)
        return self.load(path)

    def save_dir(self,directory : Directory, path: str):
        if directory is None:
            return
        data = directory.to_dict()
        blob = json.dumps(data, indent=2)
        
        if os.path.exists(path):
            os.rename(path, path + ".old")

        with open(path, "w", encoding="utf-8") as f:
            f.write(blob)
            
    def load(self, path: str) -> Directory:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Data file not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            blob = f.read()
        data = json.loads(blob)
        if not data:
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
            print("Permanently deleting object from recycle bin.")
            self.id_cache.pop(obj._id, None)
            if obj.parent:
                parent = cast(Directory, obj.parent)
                parent.release_children(obj)
        else:
            print("Moving object to recycle bin.")
            original_path = obj.get_full_path()
            obj._restore_path = original_path 
            if obj.parent:
                parent = cast(Directory, obj.parent)
                parent.release_children(obj)
            self.recycle_bin.inherit_children(obj)
    
    def restore_file_object(self, obj: FileObject):
        if obj is None:
            return
        if not obj.is_child_of(self.recycle_bin):
            print("Object is not in recycle bin, cannot restore.")
            return
        if not obj._restore_path:
            print("No restore path found, cannot restore.")
            return
        
        restore_path = obj._restore_path
        obj._restore_path = None
        
        target_dir = self.path_to_file(restore_path)
        if target_dir is None:
            print(f"Restore path '{restore_path}' not found, restoring to root.")
            target_dir = self.root_directory
        
        if not isinstance(target_dir, Directory):
            print(f"Restore path '{restore_path}' is not a directory, restoring to root.")
            target_dir = self.root_directory
        
        if target_dir.can_inherit_children(obj):
            self.recycle_bin.release_children(obj)
            target_dir.inherit_children(obj)
            print(f"Restored object to '{target_dir._file_name}'.")
        else:
            print(f"Cannot restore object to '{target_dir._file_name}', name conflict.")
        
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
    