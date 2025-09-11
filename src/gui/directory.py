# gui_shell.py
from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QSize, Signal, QPoint, QModelIndex, QItemSelectionModel
from PySide6.QtGui import QAction, QIcon, QFontMetrics
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QToolBar, QStatusBar, QHBoxLayout,
    QVBoxLayout, QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem,
    QDockWidget, QListView, QTableView, QSplitter, QFrame, QAbstractItemView,
    QStyledItemDelegate, QHeaderView, QStyle, QStyleOption, QStyleOptionViewItem,
    QMenu, QSizePolicy, QToolTip, QStyledItemDelegate, QStyleOptionViewItem, QToolTip
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from src.gui.language import Language
from src.logic.controller import  Controller
from src.logic.directory import Directory
from src.logic.record import Record

class DirectoryItemDelegate(QStyledItemDelegate):
    """Paint icon on top, wrapped text below, and report a wider sizeHint."""
    def __init__(self, parent=None, label_columns: int = 22, label_lines: int = 2):
        super().__init__(parent)
        self.label_columns = max(8, int(label_columns))
        self.label_lines   = max(1, int(label_lines))
        
    # safe font-metrics getter (silences Pylance, works at runtime)
    def _fm(self, option: QStyleOptionViewItem) -> QFontMetrics:
        fm = getattr(option, "fontMetrics", None)
        if isinstance(fm, QFontMetrics):
            return fm
        w = getattr(option, "widget", None)
        if w is not None:
            return w.fontMetrics()
        return QFontMetrics(QApplication.font())

    def sizeHint(self, option: QStyleOptionViewItem, index) -> QSize:
        """Wider size hint to accommodate multi-line labels."""
        fm = self._fm(option)
        
        # icon size comes from the view that owns us
        w = getattr(option, "widget", None)
        icon_sz = w.iconSize() if (w is not None and hasattr(w, "iconSize")) else QSize(48, 48)

        text_h  = fm.lineSpacing() * self.label_lines + 8   # padding around text
        height  = icon_sz.height() + text_h + 8             # top/bottom pad

        min_label_w = max(120, fm.averageCharWidth() * self.label_columns)
        width   = max(icon_sz.width() + 32, min_label_w)    # width for label zone
        return QSize(width, height)

    


class DirectoryGridItem(QStandardItem):
    default_icon = QIcon.fromTheme("folder")

    def __init__(self, directory: Directory, parent=None):
        super().__init__(self.default_icon, directory.get_file_name())
        self.directory = directory
        self.setEditable(False)
        # helpful roles for painting/UX
        self.setData(directory, Qt.ItemDataRole.UserRole)
        self.setData(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                     Qt.ItemDataRole.TextAlignmentRole)
        self.setData(directory.get_file_name(), Qt.ItemDataRole.ToolTipRole)

class DirectoryGrid(QListView):
    
    directoryClicked = Signal(Directory)
    directoryDoubleClicked = Signal(Directory)
    directoryRightClicked = Signal(Directory, QPoint)  # directory + global pos for context menus
    selectionChangedSignal = Signal(list)              # list[Directory]
    spaceRightClicked = Signal(QPoint)          # global pos for context menus
    
    icon_size = 48
    spacing_size = 16
    grid_size = QSize(icon_size * 2, icon_size + icon_size)  # icon + text + padding

    """Grid of directories (icon mode)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setIconSize(QSize(DirectoryGrid.icon_size, DirectoryGrid.icon_size))
        self.setSpacing(DirectoryGrid.spacing_size)
        self.setUniformItemSizes(True)
        
        self.model_ = QStandardItemModel(self)
        self.setModel(self.model_)

        # custom delegate for better text wrapping, sizing
        self._delegate = DirectoryItemDelegate(self, label_columns=22, label_lines=2)
        self.setItemDelegate(self._delegate)
        # make the cell size match the delegate immediately
        self.setGridSize(self.cell_size_hint())
        

        self.clicked.connect(self._on_clicked)
        self.doubleClicked.connect(self._on_double_clicked)
        
        self.selectionModelChanged = False
        self.selectionModel().selectionChanged.connect(self._emit_selection)  # guarded in event below

    def _on_clicked(self, index: QModelIndex):
        item = self.model_.itemFromIndex(index)
        if isinstance(item, DirectoryGridItem):
            # show full name on click (items can’t paint outside their rect, so use tooltip)
            full = item.directory.get_file_name()
            rect = self.visualRect(index)
            global_pos = self.viewport().mapToGlobal(rect.bottomLeft())
            QToolTip.showText(global_pos, full, self, rect)
            self.directoryClicked.emit(item.directory)
            self.directoryClicked.emit(item.directory)
            
    def _on_double_clicked(self, index: QModelIndex):
        d = self.directory_from_index(index)
        if d:
            self.directoryDoubleClicked.emit(d)

    def cell_size_hint(self) -> QSize:
        fm = self.fontMetrics()
        icon = self.iconSize()
        lines = getattr(self._delegate, "label_lines", 2)
        cols  = getattr(self._delegate, "label_columns", 22)
        text_h = fm.lineSpacing() * lines + 8
        height = icon.height() + text_h + 8
        min_label_w = max(120, fm.averageCharWidth() * cols)
        width = max(icon.width() + 32, min_label_w)
        return QSize(width, height)

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

