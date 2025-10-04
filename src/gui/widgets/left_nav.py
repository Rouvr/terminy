from __future__ import annotations

from PySide6.QtWidgets import QTreeWidgetItem, QDockWidget
from PySide6.QtWidgets import QDockWidget
from PySide6.QtCore import Signal, QPoint

from src.gui.language import Language
from src.gui.directory_tree import DirectoryTree

from src.logic.directory import Directory

class LeftNavDock(QDockWidget):
    directoryClicked = Signal(Directory)
    directoryDoubleClicked = Signal(Directory)
    directoryRightClicked = Signal(Directory, QPoint)
    selectionChangedSignal = Signal(list)
    spaceRightClicked = Signal(QPoint)

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.tree = DirectoryTree(self)
        self.setWidget(self.tree)

        # pass-through signals
        self.tree.directoryClicked.connect(self.directoryClicked)
        self.tree.directoryDoubleClicked.connect(self.directoryDoubleClicked)
        self.tree.directoryRightClicked.connect(self.directoryRightClicked)
        self.tree.selectionChangedSignal.connect(self.selectionChangedSignal)
        self.tree.spaceRightClicked.connect(self.spaceRightClicked)

        # Recycle bin
        self.recycle_bin_root = QTreeWidgetItem(self.tree, [Language.get("RECYCLE_BIN")])
        self.recycle_bin_root.setExpanded(False)

        # Favorites section
        self.favorites_root = QTreeWidgetItem(self.tree, [Language.get("FAVORITES")])
        self.favorites_root.setExpanded(True)
        
        # Workspace section
        self.workspace_root = QTreeWidgetItem(self.tree, [Language.get("WORKSPACE")])
        self.workspace_root.setExpanded(True)