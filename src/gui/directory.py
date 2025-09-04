# gui_shell.py
from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QSize, Signal, QPoint, QModelIndex, QItemSelectionModel
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QStatusBar, QHBoxLayout,
    QVBoxLayout, QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
    QDockWidget, QListView, QTableView, QSplitter, QFrame, QAbstractItemView,
    QStyledItemDelegate, QHeaderView, QStyle, QStyleOption, QStyleOptionViewItem,
    QMenu, QSizePolicy
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

# ---- Keep GUI aware only of these classes/methods (import lazily, optional) ----

from src.gui.language import Language
from src.logic.controller import  Controller
from src.logic.directory import Directory
from src.logic.record import Record

class DirectoryGridItem(QStandardItem):
    default_icon = QIcon.fromTheme("folder")

    def __init__(self, directory: Directory, parent=None):
        super().__init__(self.default_icon, directory.get_file_name())
        self.directory = directory
        self.setEditable(False)

class DirectoryGrid(QListView):
    
    directoryClicked = Signal(Directory)
    directoryDoubleClicked = Signal(Directory)
    directoryRightClicked = Signal(Directory, QPoint)  # directory + global pos for context menus
    selectionChangedSignal = Signal(list)              # list[Directory]
    spaceRightClicked = Signal(QPoint)          # global pos for context menus
    
    """Grid of directories (icon mode)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setIconSize(QSize(48, 48))
        self.setSpacing(16)
        self.setUniformItemSizes(True)
        self.model_ = QStandardItemModel(self)
        self.setModel(self.model_)


        self.clicked.connect(self._on_clicked)
        self.doubleClicked.connect(self._on_double_clicked)
        
        self.selectionModelChanged = False
        self.selectionModel().selectionChanged.connect(self._emit_selection)  # guarded in event below

    def _on_clicked(self, index):
        item = self.model_.itemFromIndex(index)
        if isinstance(item, DirectoryGridItem):
            self.directoryClicked.emit(item.directory)
            
    def _on_double_clicked(self, index: QModelIndex):
        d = self.directory_from_index(index)
        if d:
            self.directoryDoubleClicked.emit(d)

    def directory_from_index(self, index: QModelIndex) -> Optional[Directory]:
        if not index.isValid():
            return None

        # Primary: our model uses DirectoryGridItem with .directory
        item = self.model_.itemFromIndex(index)
        if isinstance(item, DirectoryGridItem):
            return item.directory

        # Fallback: if a future model stores the object in UserRole
        d = index.data(Qt.ItemDataRole.UserRole)
        if isinstance(d, Directory):
            return d

        return None

    def showEvent(self, e):
        super().showEvent(e)
        if not self.selectionModelChanged and self.selectionModel():
            self.selectionModel().selectionChanged.connect(self._emit_selection)
            self.selectionModelChanged = True
            
    def _emit_selection(self, *_):
        dirs = []
        for idx in self.selectionModel().selectedIndexes():
            d = self.directory_from_index(idx)
            if d:
                dirs.append(d)
        self.selectionChangedSignal.emit(dirs)
            
    # --- Right click support ---
    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        d = self.directory_from_index(index) if index.isValid() else None
        global_pos = self.viewport().mapToGlobal(event.pos())

        if d:
            # Let MainWindow decide what to do (open menu, actions, etc.)
            self.directoryRightClicked.emit(d, global_pos)
        else:
            self.spaceRightClicked.emit(global_pos)
            
    def clear(self):
        self.model_.clear()

    def populate(self, directories: list[Directory]):
        self.model_.clear()
        for directory in directories:
            self.model_.appendRow(DirectoryGridItem(directory))

    def select_directories(self, dirs: list[Directory]):
        sm = self.selectionModel()
        if not sm:
            return
        sm.clearSelection()
        model = self.model()
        if not model:
            return
        for row in range(model.rowCount()):
            idx = model.index(row, 0)
            d = self.directory_from_index(idx)
            if d in dirs:
                sm.select(idx, QItemSelectionModel.SelectionFlag.Select)

