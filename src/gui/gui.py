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
    QStyledItemDelegate, QHeaderView, QStyle, QStyleOption, QStyleOptionViewItem,
    QScrollArea
)
from PySide6.QtGui import QStandardItemModel, QStandardItem

from src.gui.directory import DirectoryGridModel
from src.gui.language import Language
from src.gui.record import RecordTableModel

from src.logic.controller import Controller
from src.logic.directory import Directory
from src.logic.record import Record

Language.load_translations()

# ---------------------------- Views & Models ----------------------------

class SearchGrid(QListView):
    """Search results grid (icon mode)."""
    def __init__(self, parent=None):
        super().__init__(parent)

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
            self.model_.appendRow(DirectoryGridModel(directory))

class RecordTable(QTableView):
    """Table of records."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().hide()

    def set_record(self, record: Record):
        model = RecordTableModel(
            record=record,
            active_attrs=RecordTableModel.DEFAULT_ATTRIBUTES,
            all_headers=RecordTableModel.ALL_ATTRIBUTES,
            write_attrs=RecordTableModel.WRITE_ATTRIBUTES
        )
        self.setModel(model)

# ---------------------------- Main Window ----------------------------

class MainWindow(QMainWindow):
    def __init__(self, controller: Controller):
        super().__init__()
        self.setWindowTitle(Language.get("APP_TITLE"))
        self.resize(1100, 700)

        self.controller = controller

        # -- Top toolbar (slim) with path box (like Windows Explorer) --
        self.toolbar = QToolBar("Main", self)
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)

        self.actionBack = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack), Language.get(" "), self)
        self.actionForward = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward), Language.get("   "), self)
        self.actionUp = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp), Language.get(" "), self)
        self.toolbar.addActions([self.actionBack, self.actionForward, self.actionUp])
        self.toolbar.addSeparator()

        self.pathEdit = QLineEdit(self)
        self.pathEdit.setPlaceholderText(Language.get("/"))
        self.pathEdit.setFixedHeight(28)
        pathWrap = QWidget(self)
        h = QHBoxLayout(pathWrap)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(QLabel(Language.get("   "), self))
        h.addWidget(self.pathEdit)
        self.toolbar.addWidget(pathWrap)

        self.toolbar.addSeparator()
        self.actionRefresh = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), Language.get("  "), self)
        self.toolbar.addAction(self.actionRefresh)

        # -- Footer (slim status bar) --
        self.status = QStatusBar(self)
        self.status.setSizeGripEnabled(False)
        self.setStatusBar(self.status)
        self.status.showMessage(Language.get("  "))

        # -- Left dock: directory tree + favorites (like VS Code) --
        self.leftDock = QDockWidget(Language.get("  "), self)
        self.leftDock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.tree = QTreeWidget(self.leftDock)
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)
        self.leftDock.setWidget(self.tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.leftDock)
        self.leftDock.setMinimumWidth(240)

        # Favorites section
        self.favRoot = QTreeWidgetItem(self.tree, [Language.get("   ")])
        self.favRoot.setExpanded(True)
        # Workspace section
        self.wsRoot = QTreeWidgetItem(self.tree, [Language.get("    ")])
        self.wsRoot.setExpanded(True)

        # -- Central area: scrollable content --
        central = QWidget(self)
        self.setCentralWidget(central)
        vlayout = QVBoxLayout(central)
        vlayout.setContentsMargins(8, 8, 8, 8)

        # Scrollable area
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        vlayout.addWidget(scroll_area)

        # Content widget inside scroll area
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Search grid
        self.search_grid = SearchGrid(self)
        content_layout.addWidget(QLabel(Language.get("SEARCH_RESULTS")))
        content_layout.addWidget(self.search_grid)

        # Directory grid
        self.directory_grid = DirectoryGrid(self)
        content_layout.addWidget(QLabel(Language.get("DIRECTORIES")))
        content_layout.addWidget(self.directory_grid)

        # Records table
        content_layout.addWidget(QLabel(Language.get("RECORDS")))
        self.record_tables = []
        if self.controller:
            self._populate_content()

        # Simple style to keep it “slim”
        self.setStyleSheet("""
            QToolBar { padding: 4px; spacing: 6px; }
            QStatusBar { padding: 2px 6px; }
            QLabel { color: palette(mid); font-weight: 600; }
            QTreeWidget { border: 1px solid palette(midlight); }
            QListView, QTableView { border: 1px solid palette(midlight); }
            QScrollArea { border: none; }
        """)

        # Placeholder population (empty tree)
        self._populate_mock_left_tree()

        # Hook up trivial no-op slots (future wiring to Controller)
        self.actionRefresh.triggered.connect(self._refresh)
        self.actionBack.triggered.connect(self._navigate_back)
        self.actionForward.triggered.connect(self._navigate_forward)
        self.actionUp.triggered.connect(self._navigate_up)

    # ------------------ Population methods ------------------

    def _populate_mock_left_tree(self):
        for name in ["Home", "Invoices", "Contracts"]:
            QTreeWidgetItem(self.favRoot, [name])
        QTreeWidgetItem(self.wsRoot, ["/"])

    def _populate_content(self):
        # Populate directory grid
        directories = self.controller.get_current_directory_list()
        self.directory_grid.populate(directories)

        # Populate record tables
        for table in self.record_tables:
            table.setParent(None)
        self.record_tables.clear()

        records = self.controller.get_current_record_list()
        content_widget = self.centralWidget().layout().itemAt(0).widget().widget()
        content_layout = content_widget.layout()
        for record in records:
            table = RecordTable(self)
            table.set_record(record)
            content_layout.addWidget(table)
            self.record_tables.append(table)

    # ------------------ Navigation methods ------------------

    def _refresh(self):
        if self.controller:
            self._populate_content()
            self.status.showMessage(Language.get("REFRESHED"), 1500)

    def _navigate_back(self):
        if self.controller and self.controller.navigate_back():
            self._populate_content()
            self.pathEdit.setText(self.controller.get_current_directory().get_full_path())
            self.status.showMessage(Language.get("NAVIGATED_BACK"), 1500)

    def _navigate_forward(self):
        if self.controller and self.controller.navigate_forward():
            self._populate_content()
            self.pathEdit.setText(self.controller.get_current_directory().get_full_path())
            self.status.showMessage(Language.get("NAVIGATED_FORWARD"), 1500)

    def _navigate_up(self):
        if self.controller and self.controller.navigate_up():
            self._populate_content()
            self.pathEdit.setText(self.controller.get_current_directory().get_full_path())
            self.status.showMessage(Language.get("NAVIGATED_UP"), 1500)

    # ------------------ Future wiring points ------------------

    def set_controller(self, controller: "Controller"):
        self.controller = controller
        self._populate_content()
        self.pathEdit.setText(self.controller.get_current_directory().get_full_path())

    def _reload_from_directory(self, directory: "Directory"):
        if self.controller:
            self.controller.navigate_to(directory)
            self._populate_content()
            self.pathEdit.setText(directory.get_full_path())

# ---------------------------- utils ----------------------------

def _fmt_dt(dt) -> str:
    try:
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""

# ---------------------------- entry point ----------------------------

def gui_main():
    print(Language.get("TEST_MSG"))
    app = QApplication(sys.argv)
    win = MainWindow(Controller(data_path=r"C:\Users\Filip\AppData\Local\Terminy"))
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    gui_main()