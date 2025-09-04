from __future__ import annotations

import sys
from typing import List, Optional, cast

from PySide6.QtCore import Qt, QSize, Signal, QPoint, QModelIndex, QItemSelectionModel
from PySide6.QtGui import QAction, QIcon, QCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QStatusBar, QHBoxLayout,
    QVBoxLayout, QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
    QDockWidget, QListView, QTableView, QSplitter, QFrame, QAbstractItemView,
    QStyledItemDelegate, QHeaderView, QStyle, QStyleOption, QStyleOptionViewItem,
    QSizePolicy
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from src.gui.directory import DirectoryGrid
from src.gui.language import Language
from src.gui.record import RecordTableModel

from src.logic.controller import Controller
from src.logic.directory import Directory
from src.logic.record import Record

Language.load_translations()

from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.DEBUG)

class DirectoryTreeItem(QTreeWidgetItem):
    
    def __init__(self, parent: Optional[QTreeWidgetItem], directory: Directory):
        super().__init__(parent, [directory.get_file_name()]) if parent else super().__init__([directory.get_file_name()])
        self.directory = directory
        self.setIcon(0, QIcon.fromTheme("folder"))
        self.setExpanded(False)
        
class DirectoryTree(QTreeWidget):
    directoryClicked = Signal(Directory)
    directoryDoubleClicked = Signal(Directory)
    directoryRightClicked = Signal(Directory, QPoint)  # directory + global pos for context menus
    selectionChangedSignal = Signal(list)              # list[Directory]
    spaceRightClicked = Signal(QPoint)          # global pos for context menus
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(True)
        self.setExpandsOnDoubleClick(False)
        
        
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemPressed.connect(self._on_item_pressed)
        self.itemSelectionChanged.connect(self._on_selection_changed)
        
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        if isinstance(item, DirectoryTreeItem):
            self.directoryClicked.emit(item.directory)
            
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        logger.debug(f"[DirectoryTree][{datetime.now()}] _on_item_double_clicked: Item double-clicked: {item.text(0)}")
        if isinstance(item, DirectoryTreeItem):
            logger.debug(f"[DirectoryTree][{datetime.now()}] _on_item_double_clicked: Emitting directoryDoubleClicked for {item.directory.get_file_name()}")
            self.directoryDoubleClicked.emit(item.directory)
            
    def _on_item_pressed(self, item: QTreeWidgetItem, column: int):
        if QApplication.mouseButtons() == Qt.MouseButton.RightButton:
            if isinstance(item, DirectoryTreeItem):
                self.directoryRightClicked.emit(item.directory, QCursor.pos())
            else:
                self.spaceRightClicked.emit(QCursor.pos())
                
    def _on_selection_changed(self):
        dirs = []
        for item in self.selectedItems():
            if isinstance(item, DirectoryTreeItem):
                dirs.append(item.directory)
        self.selectionChangedSignal.emit(dirs)
        
    @staticmethod        
    def attach_tree(directory: Directory, parent: Optional[QTreeWidgetItem] = None, level: int = 0):
        item = parent
        if level > 0:
            item = DirectoryTreeItem(parent, directory)
        
        for subdirectory in directory.list_directories():
            DirectoryTree.attach_tree(subdirectory, item, level + 1)



    