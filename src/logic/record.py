from typing import List, Optional, Tuple
from datetime import datetime
from src.logic.file_object import FileObject
from src.logic.helpers import normalize

class Record(FileObject):
    
    ALL_ATTRIBUTES = [
        "name",
        "description",
        "validity_start",
        "validity_end",
        "created",
        "modified",
        "tags",
        "data_folder_path",
        "file_name",
        "icon_path",
    ]
    READ_ONLY_ATTRIBUTES = [
        "created",
        "modified"
    ]
    DEFAULT_VISIBLE_ATTRIBUTES = [
        "name",
        "description",
        "validity_start",
        "validity_end",
        "tags",
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self._name: str = ""
        self._description: str = ""
        self._validity_start: Optional[datetime] = None
        self._validity_end: Optional[datetime] = None
        self._data_folder_path: str = ""
        self._tags: List[str] = []
        self.__dict__.update(kwargs)
        
        self._normal_name : str = normalize(self._name)
        self._normal_description : str = normalize(self._description)

    def to_dict(self) -> dict:
        return super().to_dict() | {
            "type": "Record",
            "_name": self._name,
            "_description": self._description,
            "_validity_start": self._validity_start.isoformat() if self._validity_start else None,
            "_validity_end": self._validity_end.isoformat() if self._validity_end else None,
            "_data_folder_path": self._data_folder_path,
            "_tags": self._tags,
        }

    @classmethod
    def from_dict(cls, data: dict, parent: Optional[FileObject] = None) -> 'Record':
        super_obj = FileObject.from_dict(data)

        obj = cls()
        obj._date_created = super_obj._date_created 
        obj._date_modified = super_obj._date_modified
        obj._icon_path = super_obj._icon_path
        obj._file_name = super_obj._file_name
        obj._id =  super_obj._id
        obj._normal_file_name = super_obj._normal_file_name
        obj._parent = parent
        
        obj._name = data.get("_name", "")
        obj._normal_name = normalize(obj._name)
        obj._description = data.get("_description", "")
        
        validity_start_str = data.get("_validity_start")
        obj._validity_start = datetime.fromisoformat(validity_start_str) if isinstance(validity_start_str, str) and validity_start_str else None
        validity_end_str = data.get("_validity_end")
        obj._validity_end = datetime.fromisoformat(validity_end_str) if isinstance(validity_end_str, str) and validity_end_str else None
        
        obj._data_folder_path = data.get("_data_folder_path", "")
        obj._tags = data.get("_tags", [])
        return obj

    def __repr__(self) -> str:
        attrs = ', '.join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"Record({attrs})"

    def __str__(self) -> str:
        out = "Record("
        out += f"{self._name} " if self._name else ""
        out += f"[{self._validity_start} - {self._validity_end}] " if self._validity_start or self._validity_end else ""
        out += f"C-{self._date_created} " if self._date_created else ""
        out += f"M-{self._date_modified} " if self._date_modified else ""
        out += f"\"{self._description}\" " if self._description else ""
        out += f"{self._tags}, " if self._tags else ""
        out += f"\"{self._file_name}\" " if self._file_name else ""
        out += ")"
        return out

    def is_valid(self) -> bool:
        now = datetime.now()
        if self._validity_start and now < self._validity_start:
            return False
        if self._validity_end and now > self._validity_end:
            return False
        return True

    def get_tags(self) -> List[str]:
        return self._tags
    
    def add_tag(self, tag: str):
        if tag not in self._tags:
            self._tags.append(tag)
            self._update_modified()

    def remove_tag(self, tag: str):
        if tag in self._tags:
            self._tags.remove(tag)
            self._update_modified() 
            
    def set_tags(self, tags: List[str]):
        self._tags = tags
        self._update_modified()

    def set_name(self, name: str):
        self._name = name
        self._update_modified()
        
    def get_name(self) -> str:
        return self._name   
    
    def set_description(self, description: str):
        self._description = description
        self._update_modified() 
        
    def get_description(self) -> str:
        return self._description
    
    def set_validity(self, start: Optional[datetime], end: Optional[datetime]):
        self._validity_start = start
        self._validity_end = end
        self._update_modified()
        
    def get_validity(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        return self._validity_start, self._validity_end
    
    def set_data_folder_path(self, path: str):
        self._data_folder_path = path
        self._update_modified()
        
    def get_data_folder_path(self) -> str:
        return self._data_folder_path
    
    def get_date_created(self) -> datetime:
        return self._date_created
    
    def get_date_modified(self) -> datetime:
        return self._date_modified

    def set_icon_path(self, path: str):
        self._icon_path = path
        self._update_modified()

    def get_icon_path(self) -> str:
        return self._icon_path

    def copy(self) -> 'Record':
        return Record(
            _file_name=self._file_name,
            _date_created=self._date_created,
            _date_modified=self._date_modified,
            _icon_path=self._icon_path,
            _name=self._name,
            _description=self._description,
            _validity_start=self._validity_start,
            _validity_end=self._validity_end,
            _data_folder_path=self._data_folder_path,
            _tags=self._tags.copy(),
        )