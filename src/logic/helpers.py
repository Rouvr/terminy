import json
from datetime import datetime
from typing import Any, Dict, List, Tuple, cast

from .file_object import FileObject
from .directory import Directory
from .record import Record

from unidecode import unidecode

def normalize(text:str) -> str:
    return unidecode(text).lower().strip()

def factory_from_dict(data: Dict[str, Any]) -> FileObject:
    """Pick the right class based on the 'type' field."""
    t = data.get("type")
    if t == "Directory":
        return Directory.from_dict(data)
    if t == "Record":
        return Record.from_dict(data)
    return FileObject.from_dict(data)