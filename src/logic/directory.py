import typing
from .record import Record
from .file_object import FileObject
from datetime import datetime

class Directory(FileObject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._children: typing.List[FileObject] = []
        self.__dict__.update(kwargs)
        
    def __repr__(self) -> str:
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"Directory({attrs})"

    def to_dict(self) -> dict:
        return super().to_dict() | {
            "type": "Directory",
            "_children": [child.to_dict() for child in self._children],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Directory':
        super_obj = FileObject.from_dict(data)
        
        obj = cls()
        obj._id =  super_obj._id
        obj._date_created = super_obj._date_created
        obj._date_modified = super_obj._date_modified
        obj._icon_path = super_obj._icon_path
        obj._file_name = super_obj._file_name
        obj._normal_file_name = super_obj._normal_file_name

        children = data.get("_children", [])
        obj._children = [
                typing.cast(FileObject, Directory.from_dict(child_data)) 
                for child_data in children if isinstance(child_data, dict) and child_data.get("type") == "Directory"
            ] + [
                 typing.cast(FileObject, Record.from_dict(child_data)) 
                for child_data in children if isinstance(child_data, dict) and child_data.get("type") == "Record"
            ]
        return obj
    
    def list_directories(self) -> typing.List['Directory']:
        return [child for child in self._children if isinstance(child, Directory)]

    def list_records(self) -> typing.List[Record]:
        return [child for child in self._children if isinstance(child, Record)]

    def list_files(self) -> typing.List[FileObject]:
        return self._children
    
    def can_release_children(self, children: typing.List[FileObject] | FileObject) -> bool:
        if isinstance(children, FileObject):
            children = [children]
            
        for child in children:
            if child not in self._children:
                return False
        return True
    
    def can_release_children_by_filename(self, filenames: typing.List[str] | str) -> bool:
        if isinstance(filenames, str):
            filenames = [filenames]
        to_release = [child for child in self._children if child._file_name in filenames]
        return self.can_release_children(to_release)
    
    def release_children(self, children: typing.List[FileObject] | FileObject) -> typing.List[FileObject]:
        if isinstance(children, FileObject):
            children = [children]
        released = []
        for child in children:
            # O(n) :/
            if child in self._children:
                self._children.remove(child)
                child.parent = None
                released.append(child)
        return released

    def release_children_by_filename(self, filenames: typing.List[str] | str) -> typing.List[FileObject]:
        if isinstance(filenames, str):
            filenames = [filenames]
        to_release = [child for child in self._children if child._file_name in filenames]
        return self.release_children(to_release)

    @staticmethod
    def new_empty_directory() -> 'Directory':
        return Directory(date_created=datetime.now(), date_modified=datetime.now())

    def can_inherit_children(self, child_candidates: typing.List[FileObject] | FileObject) -> bool:
        if isinstance(child_candidates, FileObject):
            child_candidates = [child_candidates]
            
        for child_candidate in child_candidates:
            if not self._can_inherit_child(child_candidate):
                return False
        return True
    
    def _can_inherit_child(self, child_candidate: FileObject) -> bool:
        if child_candidate == self:
            return False
        
        if not child_candidate:
            return False   
                
        # parent can inherit its own children, parent cannot inherit any of its ancestors
        if self.is_child_of(child_candidate):
            return False
        
        return True
    
    def inherit_children(self, child_candidates: typing.List[FileObject] | FileObject, check: bool = True) -> typing.List[FileObject]:
        """Returns the list of actually inherited children (a subset of candidates)."""
        if isinstance(child_candidates, FileObject):
            child_candidates = [child_candidates]
        
        if check:
            if not self.can_inherit_children(child_candidates):
                return []
        
        inherited = []
        for child in child_candidates:
            if child not in self._children:
                if child.parent:
                    parent = typing.cast(Directory, child.parent)
                    parent.release_children(child)
                self._children.append(child)
                child.parent = self
                inherited.append(child)
        
        return inherited
    
    def copy(self) -> 'Directory':
        new_dir = Directory(
            _file_name=self._file_name,
            _date_created=self._date_created,
            _date_modified=self._date_modified,
            _icon_path=self._icon_path,
        )
        new_dir._children = [child.copy() for child in self._children]
        for child in new_dir._children:
            child.parent = new_dir
        return new_dir

    def print_children(self, depth: int = 0):
        print(f"{'  ' * depth}☐ {self.get_file_name()}")
        for child in self.list_records():
            print(f"{'  ' * (depth + 1)}– {child.get_file_name()}")
        for child in self.list_directories():
            child.print_children(depth + 1)
            
    @classmethod
    def _walk_records(cls, d: 'Directory'):
        for r in d.list_records():
            yield r
        for sub in d.list_directories():
            yield from cls._walk_records(sub)