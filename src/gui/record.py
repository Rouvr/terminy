# gui_shell.py
from __future__ import annotations

import sys
from typing import Optional, List

from PySide6.QtCore import Qt, QSize, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QStatusBar, QHBoxLayout,
    QVBoxLayout, QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
    QDockWidget, QListView, QTableView, QSplitter, QFrame, QAbstractItemView,
    QStyledItemDelegate, QHeaderView, QStyle, QStyleOption, QStyleOptionViewItem
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from datetime import datetime
from src.gui.language import Language
from src.logic.controller import  Controller
from src.logic.directory import Directory
from src.logic.record import Record


from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt  # Assuming PySide6; adjust for PyQt6 if needed
# Assume Language is imported/defined elsewhere


class RecordTableModel(QAbstractTableModel):

    

    def __init__(self, parent=None, *, records:Optional[List[Record]]=None, active_attrs: List[str]=Record.DEFAULT_VISIBLE_ATTRIBUTES, all_headers: List[str]=Record.ALL_ATTRIBUTES, read_only_attrs: List[str]=Record.READ_ONLY_ATTRIBUTES):
        super().__init__(parent)
        self.records = records or []  # List[Record]
        self.active_attrs = list(active_attrs)  # ordered list of keys
        self.all_headers = all_headers  # full list of keys
        self.read_only_attrs = set(read_only_attrs)

    # ----- shape -----
    def rowCount(self, parent=QModelIndex()):
        return len(self.records)

    def columnCount(self, parent=QModelIndex()):
        return len(self.active_attrs)

    # ----- data -----
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        record = self.records[index.row()]
        attr = self.active_attrs[index.column()]
        val = self._get(record, attr)

        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(val, datetime):
                # match your Search pane style, or localize if you prefer
                return val.strftime("%d-%m-%Y")
            if isinstance(val, (list, tuple, set)):
                return ", ".join(map(str, val))
            return val
        elif role == Qt.ItemDataRole.EditRole:
            # hand back the raw value for editors (datetime, etc.)
            return val
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        record = self.records[index.row()]
        attr = self.active_attrs[index.column()]
        if attr in self.read_only_attrs:
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
        if attr not in self.read_only_attrs:
            f |= Qt.ItemFlag.ItemIsEditable
        return f

    def _attr_label(self, attr: str) -> str:
        return Language.get(attr.upper())

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self.active_attrs):
                return self._attr_label(self.active_attrs[section])
            return ""
        return None

    # ----- API for managing records -----
    def get(self, index: int):
        """Return the Record at the given row index."""
        if 0 <= index < len(self.records):
            return self.records[index]
        raise IndexError("Index out of range")

    def add(self, record: Record):
        """Add a new Record as a row."""
        row = len(self.records)
        self.beginInsertRows(QModelIndex(), row, row)
        self.records.append(record)
        self.endInsertRows()

    def remove(self, index: int):
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

    def populate(self, records: List[Record]):
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

    def set_active_attrs(self, attrs: List[str], all_headers: List[str] = Record.ALL_ATTRIBUTES):
        self.beginResetModel()
        self.active_attrs = list(attrs)
        # keep the canonical full list if you still need it elsewhere
        self.all_headers = list(all_headers)
        self.endResetModel()

    # ----- get/set dispatch (adapted from RecordRow, now takes record as param) -----
    def _get(self, record: Record, attr: str):
        return {
            "name":             record.get_name,
            "description":      record.get_description,
            "validity_start":   lambda: record.get_validity()[0],
            "validity_end":     lambda: record.get_validity()[1],
            "tags":             record.get_tags,
            "data_folder_path": record.get_data_folder_path,
            "file_name":        record.get_file_name,
            "icon_path":        record.get_icon_path,
            "created":          getattr(record, "get_date_created", lambda: None),
            "modified":         getattr(record, "get_date_modified", lambda: None),
        }.get(attr, lambda: None)()

    def _set(self, record: Record, attr: str, value):
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
        
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if column < 0 or column >= len(self.active_attrs):
            return
        attr = self.active_attrs[column]
        desc = (order == Qt.SortOrder.DescendingOrder)

        def keyf(rec):
            v = self._get(rec, attr)
            # Normalize to sortable keys (tuple: (is_none, normalized_value))
            if v is None:
                return (1, None)  # None goes last in ascending
            if isinstance(v, datetime):
                return (0, v)
            if isinstance(v, (list, tuple, set)):
                return (0, ", ".join(map(str, v)))
            if isinstance(v, str):
                return (0, v.lower())
            return (0, v)

        self.layoutAboutToBeChanged.emit()
        self.records.sort(key=keyf, reverse=desc)
        self.layoutChanged.emit()

