from uuid import uuid4
from typing import Optional, cast
from datetime import datetime
from .helpers import normalize

class FileObject:
    def __init__(self, **kwargs):
        self._id: str = str(uuid4())
        self._file_name: str = ""
        self._date_created: datetime = datetime.now()
        self._date_modified: datetime = datetime.now()
        self._icon_path: str = ""
        self._restore_path: Optional[str] = None
        self._parent: Optional[FileObject] = None
        self.__dict__.update(kwargs)
        self._normal_file_name: str = normalize(self._file_name)

    @classmethod
    def from_dict(cls, data: dict) -> 'FileObject':
        obj = cls()
        obj._file_name = data.get("_file_name", "")
        obj._normal_file_name = normalize(obj._file_name)
        obj._id = str(uuid4())
        date_created_str = data.get("_date_created")
        obj._date_created = datetime.fromisoformat(date_created_str) if isinstance(date_created_str, str) and date_created_str else datetime.now()
        date_modified_str = data.get("_date_modified")
        obj._date_modified = datetime.fromisoformat(date_modified_str) if isinstance(date_modified_str, str) and date_modified_str else datetime.now()
        
        obj._icon_path = data.get("_icon_path", "")
        return obj
    
    def to_dict(self) -> dict:
        return {
            "type": "FileObject",
            "_file_name": self._file_name,
            "_date_created": self._date_created.isoformat(),
            "_date_modified": self._date_modified.isoformat(),
            "_icon_path": self._icon_path,
        }

    def _update_modified(self):
        self._date_modified = datetime.now()

    def __repr__(self) -> str:
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"FileObject({attrs})"
    
    def is_child_of(self, other: 'FileObject') -> bool:
        parent = self._parent
        while parent:
            if parent == other:
                return True
            parent = parent._parent
        return False
    
    def copy(self) -> 'FileObject':
        return FileObject(
            _file_name=self._file_name,
            _date_created=self._date_created,
            _date_modified=self._date_modified,
            _icon_path=self._icon_path,
        )
    
    def get_created_at(self) -> datetime:
        return self._date_created

    def get_modified_at(self) -> datetime:
        return self._date_modified

    def get_icon_path(self) -> str:
        return self._icon_path
    
    def set_icon_path(self, path: str):
        self._icon_path = path
        self._update_modified()
        
    def get_file_name(self) -> str:
        return self._file_name if self._file_name else "/"
    
    def set_file_name(self, name: str):
        self._file_name = name
        self._update_modified() 
        
    def get_full_path(self) -> str:
        parts = []
        current = self
        while current:
            parts.append(current._file_name)
            current = current._parent
        return '/' + '/'.join(reversed(parts)).strip('/')
    
    def get_id(self) -> str:
        return self._id