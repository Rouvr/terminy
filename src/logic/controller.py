import typing
import os
import sys
import json

from datetime import datetime

from .directory import Directory
from .record import Record
from .helpers import factory_from_dict
from .path_manager import PathManager
from .file_object import FileObject


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
        
        self.root_directory: Directory = self.load_or_create_JSON(self.JSON_file)
        self.recycle_bin: Directory = self.load_or_create_JSON(self.JSON_recycle_bin)
        
        self.clipboard: typing.List[FileObject] = []
        self.clipboard_action: str = "copy"  # or "cut"
            
    def load_or_create_JSON(self, path: str) -> Directory:
        if not os.path.exists(path):
            d = Directory.new_empty_directory()
            self.save_dir(d, path)
        return self.load(path)

    def save_dir(self,directory : Directory, path: str):
        if directory is None:
            return
        data = directory.to_dict()
        blob = json.dumps(data, indent=2)
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
        
    def get_root(self) -> typing.Optional[Directory]:
        return self.root_directory
    
    def save_state(self):
        self.save_dir(self.root_directory, self.JSON_file)
        self.save_dir(self.recycle_bin, self.JSON_recycle_bin)
    
    def exit_and_save(self):
        self.save_state()
        exit(0)
    
    def delete_file_object(self, obj: FileObject):
        if obj is None:
            return
        if obj.is_child_of(self.recycle_bin):
            print("Permanently deleting object from recycle bin.")
            if obj.parent:
                parent = typing.cast(Directory, obj.parent)
                parent.release_children(obj)
        else:
            print("Moving object to recycle bin.")
            original_path = obj.get_full_path()
            obj._restore_path = original_path 
            if obj.parent:
                parent = typing.cast(Directory, obj.parent)
                parent.release_children(obj)
            self.recycle_bin.inherit_children(obj)
    
    def find_file_by_path(self, path: str) -> typing.Optional[FileObject]:
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
        
        target_dir = self.find_file_by_path(restore_path)
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
        
    def add_to_clipboard(self, obj: FileObject, action: str) -> bool:
        if obj is None or action not in ("copy", "cut"):
            return False
        self.clipboard = [obj]
        self.clipboard_action = action
        return True
    
    def paste_from_clipboard(self, target_dir: Directory) -> bool:
        if target_dir is None or not self.clipboard:
            return False
        for obj in self.clipboard:
            if self.clipboard_action == "copy":
                new_obj = obj.copy()
                target_dir.inherit_children(new_obj)
            elif self.clipboard_action == "cut":
                target_dir.inherit_children(obj)
        return True