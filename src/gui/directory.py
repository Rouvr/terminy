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

class DirectoryGridModel(QStandardItem):
    default_icon = QIcon.fromTheme("folder")

    def __init__(self, directory: Directory, parent=None):
        super().__init__(self.default_icon, directory.get_file_name())
        self.directory = directory
        self.setEditable(False)

