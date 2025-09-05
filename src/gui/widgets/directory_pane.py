from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from src.gui.directory import DirectoryGrid
from src.gui.language import Language
from src.logic.directory import Directory

class DirectoryPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(8)
        v.addWidget(QLabel(Language.get("DIRECTORIES")))
        self.grid = DirectoryGrid(self)
        v.addWidget(self.grid)

    def populate(self, directories: list[Directory]):
        self.grid.populate(directories)