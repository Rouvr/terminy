from unidecode import unidecode

def normalize(text:str) -> str:
    return unidecode(text).lower().strip()

RECORD_DEFAULT_COLUMN_WIDTHS = {
    "name": 150,
    "description": 300,
    "validity_start": 100,
    "validity_end": 100,
    "created": 100,
    "modified": 100,
    "tags": 100,
    "data_folder_path": 100,
    "file_name": 100,
    "icon_path": 100,
}
