import json
from datetime import datetime
from typing import Any, Dict, List, Tuple, cast

from unidecode import unidecode

def normalize(text:str) -> str:
    return unidecode(text).lower().strip()

