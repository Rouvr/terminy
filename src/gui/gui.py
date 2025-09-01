# gui_shell.py
from __future__ import annotations

import sys
from typing import List, Optional, cast

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QIcon
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

        # -- Central area: splitter for directories and records --
        central = QWidget(self)
        self.setCentralWidget(central)
        vlayout = QVBoxLayout(central)
        vlayout.setContentsMargins(8, 8, 8, 8)

        # Splitter for directory grid and record table
        splitter = QSplitter(Qt.Orientation.Vertical, self)
        vlayout.addWidget(splitter)

        # Directory section (wrap in frame for label + grid)
        dir_frame = QFrame(self)
        dir_layout = QVBoxLayout(dir_frame)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(8)
        dir_label = QLabel(Language.get("DIRECTORIES"))
        dir_layout.addWidget(dir_label)
        self.directory_grid = DirectoryGrid(self)
        self.directory_grid.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)  # Shrink vertically to content
        dir_layout.addWidget(self.directory_grid)
        splitter.addWidget(dir_frame)

        # Record section (wrap in frame for label + table)
        rec_frame = QFrame(self)
        rec_layout = QVBoxLayout(rec_frame)
        rec_layout.setContentsMargins(0, 0, 0, 0)
        rec_layout.setSpacing(8)
        rec_label = QLabel(Language.get("RECORDS"))
        rec_layout.addWidget(rec_label)
        self.record_table_model = RecordTableModel(self)  # Records populated later
        self.record_table_view = QTableView(self)
        self.record_table_view.setModel(self.record_table_model)
        self.record_table_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Expand to fill
        self.record_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.record_table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        rec_layout.addWidget(self.record_table_view)
        splitter.addWidget(rec_frame)

        # Configure splitter: small initial height for directories, records expand
        splitter.setSizes([150, 500])  # Adjust 150 based on your icon size (e.g., 48px icons + spacing)
        splitter.setCollapsible(0, False)  # Prevent collapsing directories
        splitter.setStretchFactor(0, 0)  # Directories don't stretch
        splitter.setStretchFactor(1, 1)  # Records stretch to fill

        # Simple style to keep it “slim”
        self.setStyleSheet("""
            QToolBar { padding: 4px; spacing: 6px; }
            QStatusBar { padding: 2px 6px; }
            QLabel { color: palette(mid); font-weight: 600; }
            QTreeWidget { border: 1px solid palette(midlight); }
            QListView, QTableView { border: 1px solid palette(midlight); }
            QSplitter::handle { background: palette(midlight); height: 8px; }
        """)

        # Placeholder population (empty tree)
        self._populate_mock_left_tree()

        # Hook up navigation slots
        self.actionRefresh.triggered.connect(self._refresh)
        self.actionBack.triggered.connect(self._navigate_back)
        self.actionForward.triggered.connect(self._navigate_forward)
        self.actionUp.triggered.connect(self._navigate_up)
        
        self._populate_content()

    # ------------------ Population methods ------------------

    def _populate_mock_left_tree(self):
        for name in ["Home", "Invoices", "Contracts"]:
            QTreeWidgetItem(self.favRoot, [name])
        QTreeWidgetItem(self.wsRoot, ["/"])

    def _populate_content(self):
        # Populate directory grid
        directories = self.controller.get_current_directory_list()
        self.directory_grid.populate(directories)
        self.directory_grid.viewport().update()  # Force layout refresh

        # Populate record table
        records = self.controller.get_current_record_list()  # Assuming Controller has this method
        self.record_table_model.populate(records)

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