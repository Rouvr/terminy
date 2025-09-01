# gui_shell.py
from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QStatusBar, QHBoxLayout,
    QVBoxLayout, QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
    QDockWidget, QListView, QTableView, QSplitter, QFrame, QAbstractItemView,
    QStyledItemDelegate, QHeaderView, QStyle, QStyleOption, QStyleOptionViewItem
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
    """Grid of directories (icon mode)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setIconSize(QSize(48, 48))
        self.setSpacing(16)
        self.setUniformItemSizes(True)
        self.model_ = QStandardItemModel(self)
        self.setModel(self.model_)

    def clear(self):
        self.model_.clear()

    def populate(self, directories: list[Directory]):
        self.model_.clear()
        for directory in directories:
            self.model_.appendRow(DirectoryGridItem(directory))
