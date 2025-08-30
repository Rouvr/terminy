# gui_shell.py
from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QSize, QAbstractTableModel, QModelIndex
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


    

class RecordTableModel(QAbstractTableModel):
    ALL_ATTRIBUTES = {
        "name":            Language.get("NAME"),
        "description":     Language.get("DESCRIPTION"),
        "validity_start":  Language.get("VALIDITY_START"),
        "validity_end":    Language.get("VALIDITY_END"),
        "created":         Language.get("CREATED"),
        "modified":        Language.get("MODIFIED"),
        "tags":            Language.get("TAGS"),
        "data_folder_path":Language.get("DATA_FOLDER_PATH"),
        "file_name":       Language.get("FILE_NAME"),
        "icon_path":       Language.get("ICON_PATH")
    }
    WRITE_ATTRIBUTES = {
        "name",
        "description",
        "validity_start",
        "validity_end",
        "tags",
        "data_folder_path",
        "file_name",
        "icon_path"
    }
    READ_ATTRIBUTES = {
        "name",
        "description",
        "validity_start",
        "validity_end",
        "tags",
        "data_folder_path",
        "file_name",
        "icon_path",
        "created",
        "modified"
    }
    DEFAULT_ATTRIBUTES = [
        "name",
        "description",
        "validity_start",
        "validity_end",
        "tags",
    ]
    
    def __init__(self, record, active_attrs, all_headers, write_attrs, parent=None):
        super().__init__(parent)
        self.record = record
        self.active_attrs = list(active_attrs)          # ordered list of keys
        self.headers = [all_headers[a] for a in self.active_attrs]
        self.write_attrs = set(write_attrs)

    # ----- shape -----
    def rowCount(self, parent=QModelIndex()): return 1
    def columnCount(self, parent=QModelIndex()): return len(self.active_attrs)

    # ----- data -----
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        # Ensure Qt.DisplayRole and Qt.EditRole are accessible
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return None
        attr = self.active_attrs[index.column()]
        return self._get(attr)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        attr = self.active_attrs[index.column()]
        if attr not in self.write_attrs:
            return False
        self._set(attr, value)
        # re-read canonical value
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

    def flags(self, index):
        if not index.isValid(): return Qt.ItemFlag.NoItemFlags
        attr = self.active_attrs[index.column()]
        f = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if attr in self.write_attrs:
            f |= Qt.ItemFlag.ItemIsEditable
        return f

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole: return None
        if orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    # ----- API -----
    def reload(self, attrs=None):
        # notify the view that data changed; efficient batching
        if not self.active_attrs: return
        left = self.index(0, 0)
        right = self.index(0, len(self.active_attrs)-1)
        self.dataChanged.emit(left, right, [Qt.ItemDataRole.DisplayRole])

    def set_active_attrs(self, attrs, all_headers):
        self.beginResetModel()
        self.active_attrs = list(attrs)
        self.headers = [all_headers[a] for a in self.active_attrs]
        self.endResetModel()

    # ----- your existing get/set dispatch -----
    def _get(self, attr):
        return {
            "name":             self.record.get_name,
            "description":      self.record.get_description,
            "validity_start":   lambda: self.record.get_validity()[0],
            "validity_end":     lambda: self.record.get_validity()[1],
            "tags":             self.record.get_tags,
            "data_folder_path": self.record.get_data_folder_path,
            "file_name":        self.record.get_file_name,
            "icon_path":        self.record.get_icon_path,
            "created":          getattr(self.record, "get_created", lambda: None),
            "modified":         getattr(self.record, "get_modified", lambda: None),
        }.get(attr, lambda: None)()

    def _set(self, attr, value):
        {
            "name":             self.record.set_name,
            "description":      self.record.set_description,
            "validity_start":   lambda v: self.record.set_validity(start=v, end=self.record.get_validity()[1]),
            "validity_end":     lambda v: self.record.set_validity(start=self.record.get_validity()[0], end=v),
            "tags":             self.record.set_tags,
            "data_folder_path": self.record.set_data_folder_path,
            "file_name":        self.record.set_file_name,
            "icon_path":        self.record.set_icon_path,
        }.get(attr, lambda *_: None)(value)
