from typing import List, Optional, Tuple, Dict
import os
from pathlib import Path

class Language:

    translations: Dict[str, Dict[str, str]] = {}
    loaded_dirs = set()
    current_language = "en_en"

    @classmethod
    def load_translations(cls, lang_dir: Optional[str] = None) -> bool:
        
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
                        curr[key.strip()] = Language.process_string(val.strip())
            except Exception as e:
                continue
            res[file.removesuffix(".txt")] = curr
        cls.translations.update(res)
        cls.loaded_dirs.add(lang_dir)
        return True
    
    @classmethod
    def get_languages(cls) -> List[str]:
        return list(cls.translations.keys())

    @classmethod
    def set_language(cls, lang: str):
        if lang in cls.translations:
            cls.current_language = lang
        else:
            raise ValueError(f"Language '{lang}' not supported.")

    @classmethod
    def get_current_language(cls) -> Optional[str]:
        return cls.current_language
    
    @classmethod
    def get(cls, key: str, lang: Optional[str] = None) -> str:
        if lang is None:
            lang = cls.current_language
        return cls.translations.get(lang, {}).get(key, key)
    
    @staticmethod
    def process_string(text: str) -> str:
        #replace \? sequences with literals
        text = text.replace("\\t", "\t")
        text = text.replace("\\n", "\n")
        text = text.replace("\\r", "\r")
        text = text.replace("\\\\", "\\")
        text = text.replace("\\b", "\b")
        return text