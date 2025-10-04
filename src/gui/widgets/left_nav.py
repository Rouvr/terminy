from __future__ import annotations

from PySide6.QtWidgets import QTreeWidgetItem, QDockWidget
from PySide6.QtWidgets import QDockWidget
from PySide6.QtCore import Signal, QPoint, Qt

from src.gui.language import Language
from src.gui.directory_tree import DirectoryTree

from src.logic.directory import Directory

class LeftNavDock(QDockWidget):
    directoryClicked = Signal(Directory)
    directoryDoubleClicked = Signal(Directory)
    directoryRightClicked = Signal(Directory, QPoint)
    selectionChangedSignal = Signal(list)
    spaceRightClicked = Signal(QPoint)
    
    # Special navigation signals
    recycleBinClicked = Signal()
    workspaceClicked = Signal()
    
    # Keyboard shortcut signals (pass-through from DirectoryTree)
    deleteRequested = Signal(list)  # List[Directory] to delete
    renameRequested = Signal(Directory)  # Directory to rename

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
        
        # Keyboard shortcut pass-through signals
        self.tree.deleteRequested.connect(self.deleteRequested)
        self.tree.renameRequested.connect(self.renameRequested)

        # Special navigation signals
        self.tree.recycleBinClicked.connect(self._on_recycle_bin_clicked)
        self.tree.workspaceClicked.connect(self._on_workspace_clicked)

        # Recycle bin
        self.recycle_bin_root = QTreeWidgetItem(self.tree, [Language.get("RECYCLE_BIN")])
        self.recycle_bin_root.setExpanded(False)
        self.recycle_bin_root.setData(0, Qt.ItemDataRole.UserRole, "RECYCLE_BIN")

        # Favorites section
        self.favorites_root = QTreeWidgetItem(self.tree, [Language.get("FAVORITES")])
        self.favorites_root.setExpanded(True)
        self.favorites_root.setData(0, Qt.ItemDataRole.UserRole, "FAVORITES")
        
        # Workspace section
        self.workspace_root = QTreeWidgetItem(self.tree, [Language.get("WORKSPACE")])
        self.workspace_root.setExpanded(True)
        self.workspace_root.setData(0, Qt.ItemDataRole.UserRole, "WORKSPACE")

    def _on_recycle_bin_clicked(self):
        """Handle recycle bin click - emit signal for main window"""
        self.recycleBinClicked.emit()

    def _on_workspace_clicked(self):
        """Handle workspace click - emit signal for main window"""
        self.workspaceClicked.emit()