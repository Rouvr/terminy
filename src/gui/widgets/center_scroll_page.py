from __future__ import annotations
from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout

from src.gui.widgets.directory_pane import DirectoryPane
from src.gui.widgets.search_pane import SearchPane
from src.gui.widgets.record_pane import RecordPane

class CenterScrollPage(QScrollArea):
    """
    A single vertically scrolling page that stacks:
    - DirectoryPane
    - SearchPane
    - RecordPane
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)

        self._page = QWidget(self)
        self.setWidget(self._page)

        v = QVBoxLayout(self._page)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        self.dirPane = DirectoryPane(self._page)
        self.searchPane = SearchPane(self._page)
        self.recPane = RecordPane(self._page)

        v.addWidget(self.dirPane)
        v.addWidget(self.searchPane)
        v.addWidget(self.recPane)
        v.addStretch(1)  # keeps a little breathing room at bottom