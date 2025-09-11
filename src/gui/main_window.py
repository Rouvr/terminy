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

from src.gui.widgets.topbar import TopBar
from src.gui.widgets.left_nav import LeftNavDock
from src.gui.widgets.directory_pane import DirectoryPane
from src.gui.widgets.record_pane import RecordPane
from src.gui.widgets.splitter import Splitter

from src.gui.directory import DirectoryGrid
from src.gui.language import Language
from src.gui.record import RecordTableModel
from src.gui.directory_tree import DirectoryTree, DirectoryTreeItem
from src.gui.stylesheet import stylesheet
from src.gui.widgets.center_scroll_page import CenterScrollPage

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


# ---------------------------- Main Window ----------------------------

class MainWindow(QMainWindow):
    #     #TODO 
    #     # self.directory_grid.directoryClicked.connect(self._on_directory_clicked)
    #     self.directory_grid.directoryDoubleClicked.connect(self._on_directory_double_clicked)
    #     # self.directory_grid.directoryRightClicked.connect(self._on_directory_right_clicked)
    #     # self.directory_grid.selectionChangedSignal.connect(self._on_directory_selection_changed)
    #     # self.directory_grid.spaceRightClicked.connect(self._on_directory_space_right_clicked)
        
    #     # self.tree.itemClicked.connect(self._on_tree_item_clicked)
    #     self.tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)  
    #     # self.tree.itemPressed.connect(self._on_tree_item_pressed)
    #     # self.tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
    #     # self.pathEdit.returnPressed.connect(self._on_path_entered)
    # # ----------------- Event handlers ------------------
    
    def __init__(self, controller: Controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle(Language.get("APP_TITLE"))
        self.resize(1100, 700)
        self.setStyleSheet(stylesheet)

        # Top bar
        self.topbar = TopBar(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.topbar)

        # Left nav
        self.left_dock = LeftNavDock(Language.get("LEFT_DOCK_TITLE"), self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.left_dock)

        # Center scrollable page
        central = QWidget(self); self.setCentralWidget(central)
        v = QVBoxLayout(central); v.setContentsMargins(8,8,8,8)

        self.centerPage = CenterScrollPage(self)
        v.addWidget(self.centerPage)

        self.directory_pane = self.centerPage.dirPane
        self.search_pane    = self.centerPage.searchPane
        self.record_pane    = self.centerPage.recPane

        self.directory_pane.set_page_scroll_mode(True)
        self.record_pane.set_page_scroll_mode(True, max_rows=500)
        
        self.record_pane.set_controller(self.controller)

        # Status
        status = QStatusBar(self); status.setSizeGripEnabled(False)
        self.setStatusBar(status)

        # Wiring
        self._connect_signals()
        self._populate_content()
        self._populate_workspaces()
        self._populate_favorites()

    def _connect_signals(self):
        t = self.topbar
        t.actionRefresh.triggered.connect(self._populate_content)
        t.actionBack.triggered.connect(self._navigate_back)
        t.actionForward.triggered.connect(self._navigate_forward)
        t.actionUp.triggered.connect(self._navigate_up)
        t.pathEdit.returnPressed.connect(self._navigate_path)

        self.left_dock.directoryDoubleClicked.connect(self._navigate_to_directory)
        self.directory_pane.grid.directoryDoubleClicked.connect(self._navigate_to_directory)


    # ------------------ Event handlers ------------------

    def _on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        directory = None

        if isinstance(item, DirectoryTreeItem):
            # regular tree item
            directory = item.directory
        else:
            # workspace root (or any item that stores Directory in UserRole)
            d = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(d, Directory):
                directory = d

        if directory and self.controller:
            res = self.controller.navigate_to(directory)
            logger.debug(f"[GUI] _on_tree_item_double_clicked: Navigated to {directory.get_full_path()} with result: {res}")
            self._populate_content()
            self.topbar.pathEdit.setText(directory.get_full_path())

    def _on_directory_double_clicked(self, directory: Directory):
        # Navigate to directory
        if self.controller:
            res = self.controller.navigate_to(directory)
            logger.debug(f"[GUI][{datetime.now()}] _on_directory_double_clicked: Navigated to {directory.get_full_path()} with result: {res}")
            self._populate_content()
            self.topbar.pathEdit.setText(directory.get_full_path())

    # ------------------ Population methods ------------------

    def _populate_content(self):
        self.directory_pane.populate(self.controller.get_current_directory_list())
        self.record_pane.populate(self.controller.get_current_record_list())

    def _update_workspace_tree(self):
        self.left_dock.tree.clear()
        self._populate_favorites()
        self._populate_workspaces()

    def _populate_favorites(self):
        for dir in self.controller.get_favorites():
            QTreeWidgetItem(self.left_dock.favorites_root, [dir.get_file_name()])
            
    def _populate_workspaces(self):
        self.left_dock.workspace_root.setData(0, Qt.ItemDataRole.UserRole, self.controller.get_root()) 
        DirectoryTree.attach_tree(self.controller.get_root(), self.left_dock.workspace_root)
        
    # ------------------ Navigation methods ------------------

    def _refresh(self):
        if self.controller:
            self._populate_content()
            self.statusBar().showMessage(Language.get("REFRESHED"), 1500)

    def _navigate_back(self):
        if self.controller and self.controller.navigate_back():
            self._populate_content()
            self.topbar.pathEdit.setText(self.controller.get_current_directory().get_full_path())
            self.statusBar().showMessage(Language.get("NAVIGATED_BACK"), 1500)

    def _navigate_forward(self):
        if self.controller and self.controller.navigate_forward():
            self._populate_content()
            self.topbar.pathEdit.setText(self.controller.get_current_directory().get_full_path())
            self.statusBar().showMessage(Language.get("NAVIGATED_FORWARD"), 1500)

    def _navigate_up(self):
        if self.controller and self.controller.navigate_up():
            self._populate_content()
            self.topbar.pathEdit.setText(self.controller.get_current_directory().get_full_path())
            self.statusBar().showMessage(Language.get("NAVIGATED_UP"), 1500)

    def _navigate_path(self):
        path = self.topbar.pathEdit.text().strip()
        if self.controller and path:
            directory = self.controller.path_to_object(path)
            if directory and isinstance(directory, Directory):
                self.controller.navigate_to(directory)
                self._populate_content()
                self.topbar.pathEdit.setText(directory.get_full_path())
                self.statusBar().showMessage(Language.get("NAVIGATED_TO_PATH").format(path=path), 1500)
            else:
                self.statusBar().showMessage(Language.get("ERROR_INVALID_PATH").format(path=path), 3000)
                
    def _navigate_to_directory(self, directory: Directory):
        self.controller.navigate_to(directory)
        self._populate_content()
        self.topbar.pathEdit.setText(directory.get_full_path())

    # ------------------  ------------------

    def set_controller(self, controller: "Controller"):
        self.controller = controller
        self._populate_content()
        self.topbar.pathEdit.setText(self.controller.get_current_directory().get_full_path())
    
    def save(self):
        self.controller.save_state()
        
    def exit_and_save(self):
        logger.debug(f"[Language dump] {Language.dump_requests()}")
        self.controller.exit_and_save()


def main_window():
    print(Language.get("WELCOME_MSG"))
    app = QApplication(sys.argv)
    # win = MainWindow(Co   ntroller(data_path=r"C:\Users\Filip\AppData\Local\Terminy"))
    win = MainWindow(Controller(data_path=r"D:\Code\terminy\test_data"))
    app.aboutToQuit.connect(win.exit_and_save)
    
    win.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main_window()