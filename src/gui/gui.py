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

Language.load_translations()

# ---------------------------- Views & Models ----------------------------


class DirectoryGrid(QListView):
    """Top pane: grid of directories (icon mode)."""
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

    def populate(self, dir_names: list[str]):
        self.model_.clear()
        folder_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        for name in dir_names:
            it = QStandardItem(folder_icon, name)
            it.setEditable(False)
            self.model_.appendRow(it)


class RecordTable(QTableView):
    """Bottom pane: table of records (one row = one record)."""
    COLS = ["Name", "Validity Start", "Validity End", "Created", "Modified", "Tags"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.verticalHeader().setVisible(False)
        self.model_ = QStandardItemModel(self)
        self.model_.setHorizontalHeaderLabels(self.COLS)
        self.setModel(self.model_)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

    def clear(self):
        self.model_.removeRows(0, self.model_.rowCount())

    def populate(self, rows: list[tuple[str, str, str, str, str, str]]):
        self.clear()
        for r in rows:
            self.model_.appendRow([QStandardItem(x) for x in r])


# ---------------------------- Main Window ----------------------------

class MainWindow(QMainWindow):
    def __init__(self, controller: Optional["Controller"] = None):
        super().__init__()
        self.setWindowTitle(Language.get("APP_TITLE"))
        self.resize(1100, 700)

        self.controller = controller  # Keep GUI surface area small (Controller/Directory/Record/search)

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
        self.pathEdit.setPlaceholderText(Language.get(" "))
        self.pathEdit.setFixedHeight(28)
        pathWrap = QWidget(self)
        h = QHBoxLayout(pathWrap)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(QLabel(Language.get("   "), self))
        h.addWidget(self.pathEdit)
        self.toolbar.addWidget(pathWrap)

        # Optional quick actions (placeholders)
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

        # -- Central area: vertical split (top grid of directories, bottom table of records) --
        central = QWidget(self)
        self.setCentralWidget(central)

        vlayout = QVBoxLayout(central)
        vlayout.setContentsMargins(8, 8, 8, 8)

        self.split = QSplitter(Qt.Orientation.Vertical, central)
        vlayout.addWidget(self.split)

        # Top: directories grid
        topFrame = QFrame(self.split)
        topFrame.setFrameShape(QFrame.Shape.NoFrame)
        topLayout = QVBoxLayout(topFrame)
        topLayout.setContentsMargins(0, 0, 0, 4)
        topLayout.addWidget(QLabel(Language.get("   "), topFrame))
        self.dirGrid = DirectoryGrid(topFrame)
        topLayout.addWidget(self.dirGrid)

        # Bottom: records table
        bottomFrame = QFrame(self.split)
        bottomFrame.setFrameShape(QFrame.Shape.NoFrame)
        bottomLayout = QVBoxLayout(bottomFrame)
        bottomLayout.setContentsMargins(0, 4, 0, 0)
        bottomLayout.addWidget(QLabel(Language.get("    "), bottomFrame))
        self.recTable = RecordTable(bottomFrame)
        bottomLayout.addWidget(self.recTable)

        self.split.addWidget(topFrame)
        self.split.addWidget(bottomFrame)
        self.split.setSizes([380, 320])

        # Simple style to keep it “slim”
        self.setStyleSheet("""
            QToolBar { padding: 4px; spacing: 6px; }
            QStatusBar { padding: 2px 6px; }
            QLabel { color: palette(mid); font-weight: 600; }
            QTreeWidget { border: 1px solid palette(midlight); }
            QListView, QTableView { border: 1px solid palette(midlight); }
        """)

        # Placeholder population (empty tree + empty views)
        self._populate_mock_left_tree()
        self._populate_mock_center()

        # Hook up trivial no-op slots (future wiring to Controller)
        self.actionRefresh.triggered.connect(self._noop)
        self.actionBack.triggered.connect(self._noop)
        self.actionForward.triggered.connect(self._noop)
        self.actionUp.triggered.connect(self._noop)

    # ------------------ Placeholder population ------------------

    def _populate_mock_left_tree(self):
        # Favorites (placeholder items)
        for name in ["Home", "Invoices", "Contracts"]:
            QTreeWidgetItem(self.favRoot, [name])
        # Workspace (placeholder root)
        QTreeWidgetItem(self.wsRoot, ["/"])

    def _populate_mock_center(self):
        # Directories grid (placeholder names)
        self.dirGrid.populate(["Invoices", "Contracts", "Archive", "Suppliers"])

        # Records table (placeholder rows)
        rows = [
            ("Faktura 2025-08-001", "2025-07-25", "2025-09-01", "2025-07-20", "2025-08-24", "invoice, construction"),
            ("Faktura 2025-08-002", "2025-08-01", "2025-09-05", "2025-08-01", "2025-08-24", "invoice, machinery"),
            ("Smlouva s ACME",      "2025-06-01", "",           "2025-06-01", "2025-08-12", "contract, service"),
        ]
        self.recTable.populate(rows)

    # ------------------ Future wiring points ------------------

    def set_controller(self, controller: "Controller"):
        """Optional: inject your controller later (GUI stays narrow)."""
        self.controller = controller
        # Example future hookups (not implemented now):
        # - self._reload_from_directory(controller.get_root())
        # - connect search box to controller.search

    def _reload_from_directory(self, directory: "Directory"):
        """Populate dir grid & record table from a real Directory (future)."""
        # Top grid: names of child directories
        dir_names = [d._file_name for d in directory.list_directories()]
        self.dirGrid.populate(dir_names)
        # Bottom table: records with key fields
        rows = []
        for r in directory.list_records():
            rows.append((
                getattr(r, "_name", r._file_name),
                _fmt_dt(getattr(r, "_validity_start", None)),
                _fmt_dt(getattr(r, "_validity_end", None)),
                _fmt_dt(getattr(r, "_date_created", None)),
                _fmt_dt(getattr(r, "_date_modified", None)),
                ", ".join(getattr(r, "_tags", [])),
            ))
        self.recTable.populate(rows)

    def _noop(self):
        self.status.showMessage("Not implemented yet", 1500)


# ---------------------------- utils ----------------------------

def _fmt_dt(dt) -> str:
    try:
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return ""


# ---------------------------- entry point ----------------------------

def gui_main():
    print(Language.get("TEST_MSG"))  # Example of using Language class
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    gui_main()
