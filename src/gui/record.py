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


from src.gui.language import Language
from src.logic.controller import  Controller
from src.logic.directory import Directory
from src.logic.record import Record


from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt  # Assuming PySide6; adjust for PyQt6 if needed
# Assume Language is imported/defined elsewhere

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

    def __init__(self, parent=None, *, records=None, active_attrs=DEFAULT_ATTRIBUTES, all_headers=ALL_ATTRIBUTES, write_attrs=WRITE_ATTRIBUTES):
        super().__init__(parent)
        self.records = records or []  # List[Record]
        self.active_attrs = list(active_attrs)  # ordered list of keys
        self.headers = [all_headers[a] for a in self.active_attrs]
        self.write_attrs = set(write_attrs)

    # ----- shape -----
    def rowCount(self, parent=QModelIndex()):
        return len(self.records)

    def columnCount(self, parent=QModelIndex()):
        return len(self.active_attrs)

    # ----- data -----
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return None
        record = self.records[index.row()]
        attr = self.active_attrs[index.column()]
        return self._get(record, attr)

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        record = self.records[index.row()]
        attr = self.active_attrs[index.column()]
        if attr not in self.write_attrs:
            return False
        self._set(record, attr, value)
        # re-read canonical value
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        attr = self.active_attrs[index.column()]
        f = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled
        if attr in self.write_attrs:
            f |= Qt.ItemFlag.ItemIsEditable
        return f

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None

    # ----- API for managing records -----
    def get(self, index):
        """Return the Record at the given row index."""
        if 0 <= index < len(self.records):
            return self.records[index]
        raise IndexError("Index out of range")

    def add(self, record):
        """Add a new Record as a row."""
        row = len(self.records)
        self.beginInsertRows(QModelIndex(), row, row)
        self.records.append(record)
        self.endInsertRows()

    def remove(self, index):
        """Remove the row at the given index."""
        if 0 <= index < len(self.records):
            self.beginRemoveRows(QModelIndex(), index, index)
            del self.records[index]
            self.endRemoveRows()
        else:
            raise IndexError("Index out of range")

    def clear(self):
        """Clear all rows."""
        if self.records:
            self.beginRemoveRows(QModelIndex(), 0, len(self.records) - 1)
            self.records.clear()
            self.endRemoveRows()

    def populate(self, records):
        """Replace all rows with the given list of Records."""
        self.clear()
        if records:
            self.beginInsertRows(QModelIndex(), 0, len(records) - 1)
            self.records.extend(records)
            self.endInsertRows()

    def reload(self):
        """Notify views that all data has changed (e.g., after external modifications)."""
        if not self.records or not self.active_attrs:
            return
        top_left = self.index(0, 0)
        bottom_right = self.index(len(self.records) - 1, len(self.active_attrs) - 1)
        self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])

    def set_active_attrs(self, attrs, all_headers):
        """Update the active attributes (columns)."""
        self.beginResetModel()
        self.active_attrs = list(attrs)
        self.headers = [all_headers[a] for a in self.active_attrs]
        self.endResetModel()

    # ----- get/set dispatch (adapted from RecordRow, now takes record as param) -----
    def _get(self, record, attr):
        return {
            "name":             record.get_name,
            "description":      record.get_description,
            "validity_start":   lambda: record.get_validity()[0],
            "validity_end":     lambda: record.get_validity()[1],
            "tags":             record.get_tags,
            "data_folder_path": record.get_data_folder_path,
            "file_name":        record.get_file_name,
            "icon_path":        record.get_icon_path,
            "created":          getattr(record, "get_created", lambda: None),
            "modified":         getattr(record, "get_modified", lambda: None),
        }.get(attr, lambda: None)()

    def _set(self, record, attr, value):
        {
            "name":             record.set_name,
            "description":      record.set_description,
            "validity_start":   lambda v: record.set_validity(start=v, end=record.get_validity()[1]),
            "validity_end":     lambda v: record.set_validity(start=record.get_validity()[0], end=v),
            "tags":             record.set_tags,
            "data_folder_path": record.set_data_folder_path,
            "file_name":        record.set_file_name,
            "icon_path":        record.set_icon_path,
        }.get(attr, lambda *_: None)(value)