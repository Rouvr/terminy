from __future__ import annotations

import sys
from typing import List, Optional, cast

from PySide6.QtCore import Qt, QSize, Signal, QPoint
from PySide6.QtGui import QAction, QIcon, QMouseEvent
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
from src.gui.widgets.context_menu import ContextMenuManager

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

        # Context menu manager
        self.context_menu = ContextMenuManager(self.controller, self)

        # Status
        status = QStatusBar(self); status.setSizeGripEnabled(False)
        self.setStatusBar(status)

        # Wiring
        self._connect_signals()
        self._populate_content()
        self._populate_workspaces()
        self._populate_favorites()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse navigation shortcuts"""
        if event.button() == Qt.MouseButton.XButton1:  # Mouse button back
            self._navigate_back()
            event.accept()
            return
        elif event.button() == Qt.MouseButton.XButton2:  # Mouse button forward
            self._navigate_forward()
            event.accept()
            return
        
        # Call parent implementation for other buttons
        super().mousePressEvent(event)

    def _connect_signals(self):
        t = self.topbar
        t.actionRefresh.triggered.connect(self._populate_content)
        t.actionBack.triggered.connect(self._navigate_back)
        t.actionForward.triggered.connect(self._navigate_forward)
        t.actionUp.triggered.connect(self._navigate_up)
        t.actionHome.triggered.connect(self._navigate_home)
        t.pathEdit.returnPressed.connect(self._navigate_path)

        self.left_dock.directoryDoubleClicked.connect(self._navigate_to_directory)
        self.left_dock.recycleBinClicked.connect(self._navigate_to_recycle_bin)
        self.left_dock.workspaceClicked.connect(self._navigate_home)
        
        # Context menu signals for left navbar (same as directory pane)
        self.left_dock.directoryRightClicked.connect(self._on_directory_right_clicked)
        self.left_dock.spaceRightClicked.connect(self._on_directory_space_right_clicked)
        
        self.directory_pane.grid.directoryDoubleClicked.connect(self._navigate_to_directory)

        # Context menu signals for directory pane
        self.directory_pane.grid.directoryRightClicked.connect(self._on_directory_right_clicked)
        self.directory_pane.grid.spaceRightClicked.connect(self._on_directory_space_right_clicked)
        self.directory_pane.grid.selectionChangedSignal.connect(self._on_directory_selection_changed)

        # Context menu signals for record pane
        self.record_pane.recordRightClicked.connect(self._on_record_right_clicked)
        self.record_pane.spaceRightClicked.connect(self._on_record_space_right_clicked)
        self.record_pane.recordsSelectionChanged.connect(self._on_record_selection_changed)

        # Context menu action signals
        self.context_menu.cutRequested.connect(self._on_cut_requested)
        self.context_menu.copyRequested.connect(self._on_copy_requested)
        self.context_menu.pasteRequested.connect(self._on_paste_requested)
        self.context_menu.deleteRequested.connect(self._on_delete_requested)
        self.context_menu.deletePermRequested.connect(self._on_delete_requested)
        self.context_menu.recoverRequested.connect(self._on_recover_requested)
        self.context_menu.newDirectoryRequested.connect(self._on_new_directory_requested)
        self.context_menu.newRecordRequested.connect(self._on_new_record_requested)
        self.context_menu.renameRequested.connect(self._on_rename_requested)
        self.context_menu.addToFavoritesRequested.connect(self._on_add_to_favorites_requested)
        self.context_menu.removeFromFavoritesRequested.connect(self._on_remove_from_favorites_requested)
        
        # Keyboard shortcut signals for directory pane
        self.directory_pane.grid.deleteRequested.connect(self._on_delete_requested)
        self.directory_pane.grid.renameRequested.connect(self._on_rename_requested)
        
        # Keyboard shortcut signals for left navbar (directory tree)
        self.left_dock.deleteRequested.connect(self._on_delete_requested)
        self.left_dock.renameRequested.connect(self._on_rename_requested)


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

    def _navigate_home(self):
        """Navigate to the root directory"""
        if self.controller:
            root_directory = self.controller.get_root()
            if self.controller.navigate_to(root_directory):
                self._populate_content()
                self.topbar.pathEdit.setText(root_directory.get_full_path())
                logger.debug(f"[MainWindow][{datetime.now()}] Navigated to root directory")

    def _navigate_to_recycle_bin(self):
        """Navigate to the recycle bin"""
        if self.controller:
            recycle_bin = self.controller.get_recycle_bin()
            if self.controller.navigate_to(recycle_bin):
                self._populate_content()
                self.topbar.pathEdit.setText(recycle_bin.get_full_path())
                logger.debug(f"[MainWindow][{datetime.now()}] Navigated to recycle bin")

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

    # ------------------ Context Menu Event Handlers ------------------

    def _on_directory_right_clicked(self, directory: Directory, global_pos: QPoint):
        """Handle right-click on a directory (from either directory pane or left navbar)"""
        # Get selections from both directory pane and left navbar
        main_pane_selection = self.directory_pane.grid.get_selected_directories()
        navbar_selection = self.left_dock.tree.get_selected_directories()
        
        # Use whichever has selections, preferring the one that contains the clicked directory
        if directory in navbar_selection:
            selected_directories = navbar_selection
        elif directory in main_pane_selection:
            selected_directories = main_pane_selection
        else:
            # If the clicked directory isn't in any selection, use it as single selection
            selected_directories = [directory]
            
        current_directory = self.controller.get_current_directory()
        self.context_menu.show_directory_context_menu(
            global_pos, selected_directories, current_directory, False
        )

    def _on_directory_space_right_clicked(self, global_pos: QPoint):
        """Handle right-click on empty space in directory pane"""
        current_directory = self.controller.get_current_directory()
        self.context_menu.show_directory_context_menu(
            global_pos, [], current_directory, True
        )

    def _on_directory_selection_changed(self, selected_directories: List[Directory]):
        """Handle directory selection changes"""
        logger.debug(f"[MainWindow][{datetime.now()}] Directory selection changed: {len(selected_directories)} selected")

    def _on_record_right_clicked(self, record: Record, global_pos: QPoint):
        """Handle right-click on a record"""
        selected_records = self.record_pane.get_selected_records()
        current_directory = self.controller.get_current_directory()
        self.context_menu.show_record_context_menu(
            global_pos, selected_records, current_directory, False
        )

    def _on_record_space_right_clicked(self, global_pos: QPoint):
        """Handle right-click on empty space in record pane"""
        current_directory = self.controller.get_current_directory()
        self.context_menu.show_record_context_menu(
            global_pos, [], current_directory, True
        )

    def _on_record_selection_changed(self, selected_records: List[Record]):
        """Handle record selection changes"""
        logger.debug(f"[MainWindow][{datetime.now()}] Record selection changed: {len(selected_records)} selected")

    # ------------------ Context Menu Action Handlers ------------------

    def _on_cut_requested(self, items: List):
        """Handle cut action"""
        self.controller.add_to_clipboard(items, "cut")
        logger.debug(f"[MainWindow][{datetime.now()}] Cut {len(items)} items to clipboard")

    def _on_copy_requested(self, items: List):
        """Handle copy action"""
        self.controller.add_to_clipboard(items, "copy")
        logger.debug(f"[MainWindow][{datetime.now()}] Copied {len(items)} items to clipboard")

    def _on_paste_requested(self):
        """Handle paste action"""
        current_directory = self.controller.get_current_directory()
        result = self.controller.paste_from_clipboard(current_directory)
        if result:
            self._populate_content()
            logger.debug(f"[MainWindow][{datetime.now()}] Pasted clipboard items to {current_directory._file_name}")
        else:
            logger.warning(f"[MainWindow][{datetime.now()}] Failed to paste clipboard items")

    def _on_delete_requested(self, items: List):
        """Handle delete (move to trash) action"""
        # Move items to recycle bin
        for item in items:
            self.controller.delete_file_object(item)
        self._populate_content()
        logger.debug(f"[MainWindow][{datetime.now()}] Moved {len(items)} items to trash")


    def _on_recover_requested(self, items: List):
        """Handle recover from trash action"""
        for item in items:
            self.controller.restore_file_object(item)
        self._populate_content()
        logger.debug(f"[MainWindow][{datetime.now()}] Recover requested for {len(items)} items")

    def _on_new_directory_requested(self):
        """Handle new directory creation"""
        current_directory = self.controller.get_current_directory()
        self.controller.create_directory(current_directory)    
        self._populate_content()    
        logger.debug(f"[MainWindow][{datetime.now()}] New directory requested")

    def _on_new_record_requested(self):
        """Handle new record creation"""
        current_directory = self.controller.get_current_directory()
        self.controller.create_record(current_directory)
        self._populate_content()
        logger.debug(f"[MainWindow][{datetime.now()}] New record requested")

    def _on_rename_requested(self, item):
        """Handle rename action - start inline editing"""
        from src.logic.directory import Directory
        
        if isinstance(item, Directory):
            # Try to start editing in the directory pane first
            if not self.directory_pane.grid.start_editing_directory(item):
                # If not found in directory pane, try the left navbar
                self.left_dock.tree.start_editing_directory(item)
            logger.info(f"[MainWindow][{datetime.now()}] Started inline editing for directory: {item._file_name}")
        else:
            # For records, we'll need to implement record renaming separately
            logger.info(f"[MainWindow][{datetime.now()}] Rename requested for record: {item._file_name if hasattr(item, '_file_name') else 'item'} (record renaming not yet implemented)")

    def _on_add_to_favorites_requested(self, directory: Directory):
        """Handle add to favorites action"""
        self.controller.add_favorite(directory)
        self._populate_favorites()
        logger.info(f"[MainWindow][{datetime.now()}] Added {directory._file_name} to favorites")

    def _on_remove_from_favorites_requested(self, directory: Directory):
        """Handle remove from favorites action"""
        self.controller.remove_favorite(directory)
        self._populate_favorites()
        logger.info(f"[MainWindow][{datetime.now()}] Removed {directory._file_name} from favorites")

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