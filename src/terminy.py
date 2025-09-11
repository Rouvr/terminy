from src.gui.main_window import main_window
from src.gui.language import Language
from PySide6.QtCore import QLocale
if __name__ == "__main__":
    Language.save_locale(QLocale("cs_CZ"))
    main_window()