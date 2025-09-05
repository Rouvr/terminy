
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter

from src.gui.widgets.directory_pane import DirectoryPane
from src.gui.widgets.record_pane import RecordPane
from src.gui.language import Language

Language.load_translations()

class Splitter(QSplitter):
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Vertical, parent)
        self.dirPane = DirectoryPane(self)
        self.recPane = RecordPane(self)
        self.addWidget(self.dirPane)
        self.addWidget(self.recPane)
        self.setSizes([150, 500])