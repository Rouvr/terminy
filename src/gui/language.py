from typing import List, Optional, Tuple, Dict, cast
import os
from pathlib import Path

from PySide6.QtCore import QLocale
from src.logic.registry import RegistryManager


import logging
from logging.handlers import RotatingFileHandler
logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.DEBUG)

class Language:

    translations: Dict[str, Dict[str, str]] = {}
    loaded_dirs = set()
    current_locale = QLocale.system()
    all_requests = set()

    @classmethod
    def load_translations(cls, lang_dir: Optional[str] = None) -> bool:

        cls.current_locale = cls.load_locale()

        if lang_dir is None:
            lang_dir = os.path.join(os.path.dirname(__file__), "lang")

        if lang_dir in cls.loaded_dirs:
            return False
        
        res = {}
        for file in os.listdir(lang_dir):
            curr = dict[str, str]()
            try:
                with open(os.path.join(lang_dir, file), "r", encoding="utf-8") as f:
                    for line in f.readlines():
                        if line.startswith("#"):
                            continue
                        key, val = line.split("=", 1)
                        curr[key.strip()] = cls.process_string(val.strip())
            except Exception as e:
                continue
            res[file.removesuffix(".txt")] = curr
        cls.translations.update(res)
        cls.loaded_dirs.add(lang_dir)
        return True
    
    @classmethod
    def locale_tag(cls, locale: Optional[QLocale] = None) -> str:
        if locale is None:
            locale = cls.current_locale
        tag = getattr(locale, "bcp47Name", None)
        if callable(tag):
            tag = tag()
        res = cast(str,tag if tag else locale.name())
        return res

    @classmethod
    def get_current_locale(cls) -> QLocale:
        return cls.current_locale
    
    @classmethod
    def get(cls, key: str, locale: Optional[QLocale] = None) -> str:
        if locale is None:
            locale = cls.current_locale
        tag = cls.locale_tag(locale)
        cls.all_requests.add((key, tag))
        return cls.translations.get(tag, {}).get(key, key)

    @staticmethod
    def process_string(text: str) -> str:
        #replace \? sequences with literals
        text = text.replace("\\t", "\t")
        text = text.replace("\\n", "\n")
        text = text.replace("\\r", "\r")
        text = text.replace("\\\\", "\\")
        text = text.replace("\\b", "\b")
        return text
    
    @staticmethod
    def load_locale() -> QLocale:
        tag = RegistryManager.get_reg_key(RegistryManager.REG_LOCALE_TAG)
        try:
            return QLocale(tag) if tag else QLocale.system()
        except Exception as e:
            logger.error(f"[Language] get_locale: Failed to get locale from tag '{tag}': {e}")
            return QLocale.system()
    
    @staticmethod
    def save_locale(locale: QLocale):
        tag = getattr(locale, "bcp47Name", None)
        tag = tag() if callable(tag) else None
        if not tag:
            tag = locale.name()  # e.g., "cs_CZ"

        RegistryManager.set_reg_key(RegistryManager.REG_LOCALE_TAG, cast(str, tag))

    @classmethod
    def dump_requests(cls) -> List[Tuple[str, str]]:
        return list(cls.all_requests) 