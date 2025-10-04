from __future__ import annotations

from typing import List, Optional, Union
from datetime import datetime

from PySide6.QtCore import Qt, QPoint, Signal, QObject
from PySide6.QtWidgets import QMenu, QWidget
from PySide6.QtGui import QIcon, QAction

from src.gui.language import Language
from src.logic.controller import Controller
from src.logic.directory import Directory
from src.logic.record import Record
from src.logic.file_object import FileObject

import logging
from logging.handlers import RotatingFileHandler
logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.DEBUG)


class ContextMenuManager(QObject):
    """
    Manages context menus for directory and record panes.
    Provides different menu options based on the context and selected items.
    """
    
    # Signals for actions
    cutRequested = Signal(list)  # list[FileObject]
    copyRequested = Signal(list)  # list[FileObject]
    pasteRequested = Signal()
    deleteRequested = Signal(list)  # list[FileObject]
    deletePermRequested = Signal(list)  # list[FileObject] - permanent delete
    recoverRequested = Signal(list)  # list[FileObject] - recover from trash
    newDirectoryRequested = Signal()
    newRecordRequested = Signal()
    renameRequested = Signal(object)  # FileObject
    addToFavoritesRequested = Signal(object)  # Directory
    removeFromFavoritesRequested = Signal(object)  # Directory

    def __init__(self, controller: Controller, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.controller = controller
        self.parent_widget = parent

    def show_directory_context_menu(self, 
                                   global_pos: QPoint, 
                                   selected_directories: List[Directory], 
                                   current_directory: Optional[Directory] = None,
                                   clicked_on_empty_space: bool = False):
        """
        Show context menu for directory pane.
        
        Args:
            global_pos: Global position where to show the menu
            selected_directories: List of currently selected directories
            current_directory: The current directory we're in
            clicked_on_empty_space: True if clicked on empty space in the pane
        """
        menu = QMenu(self.parent_widget)
        
        # Determine if we're in trash
        is_in_trash = current_directory == self.controller.get_recycle_bin() if current_directory else False
        
        # Check if clipboard has content
        has_clipboard = len(self.controller.clipboard) > 0
        
        # Check if any selected directories are in favorites
        favorites = self.controller.get_favorites()
        selected_in_favorites = [d for d in selected_directories if d in favorites]
        selected_not_in_favorites = [d for d in selected_directories if d not in favorites]

        if not clicked_on_empty_space and selected_directories:
            # Actions for selected directories
            
            # Cut
            cut_action = menu.addAction(QIcon.fromTheme("edit-cut"), Language.get("CUT") or "Cut")
            cut_action.triggered.connect(lambda: self._cut_items(selected_directories))
            
            # Copy
            copy_action = menu.addAction(QIcon.fromTheme("edit-copy"), Language.get("COPY") or "Copy")
            copy_action.triggered.connect(lambda: self._copy_items(selected_directories))
            
            menu.addSeparator()
            
            if is_in_trash:
                # Recover from trash
                recover_action = menu.addAction(QIcon.fromTheme("edit-undo"), Language.get("RECOVER") or "Recover")
                recover_action.triggered.connect(lambda: self.recoverRequested.emit(selected_directories))
                
                # Delete permanently
                delete_perm_action = menu.addAction(QIcon.fromTheme("edit-delete"), Language.get("DELETE_PERMANENTLY") or "Delete Permanently")
                delete_perm_action.triggered.connect(lambda: self.deletePermRequested.emit(selected_directories))
            else:
                # Delete (move to trash)
                delete_action = menu.addAction(QIcon.fromTheme("user-trash"), Language.get("DELETE") or "Delete")
                delete_action.triggered.connect(lambda: self.deleteRequested.emit(selected_directories))
            
            # Only show rename if single item selected
            if len(selected_directories) == 1:
                menu.addSeparator()
                rename_action = menu.addAction(QIcon.fromTheme("edit-rename"), Language.get("RENAME") or "Rename")
                rename_action.triggered.connect(lambda: self.renameRequested.emit(selected_directories[0]))
            
            # Favorites actions (only for directories not in trash)
            if not is_in_trash:
                menu.addSeparator()
                
                # Add to favorites (for directories not already in favorites)
                if selected_not_in_favorites:
                    add_fav_action = menu.addAction(QIcon.fromTheme("bookmark-new"), Language.get("ADD_TO_FAVORITES") or "Add to Favorites")
                    add_fav_action.triggered.connect(lambda: self._add_to_favorites(selected_not_in_favorites))
                
                # Remove from favorites (for directories already in favorites)
                if selected_in_favorites:
                    remove_fav_action = menu.addAction(QIcon.fromTheme("bookmark-remove"), Language.get("REMOVE_FROM_FAVORITES") or "Remove from Favorites")
                    remove_fav_action.triggered.connect(lambda: self._remove_from_favorites(selected_in_favorites))

        # Actions always available
        if not is_in_trash:  # Don't allow pasting in trash
            menu.addSeparator()
            
            # Paste
            paste_action = menu.addAction(QIcon.fromTheme("edit-paste"), Language.get("PASTE") or "Paste")
            paste_action.setEnabled(has_clipboard)
            paste_action.triggered.connect(lambda: self.pasteRequested.emit())
            
            menu.addSeparator()
            
            # New submenu
            new_menu = menu.addMenu(QIcon.fromTheme("document-new"), Language.get("NEW") or "New")
            
            new_dir_action = new_menu.addAction(QIcon.fromTheme("folder-new"), Language.get("NEW_DIRECTORY") or "Directory")
            new_dir_action.triggered.connect(lambda: self.newDirectoryRequested.emit())
            
            new_rec_action = new_menu.addAction(QIcon.fromTheme("document-new"), Language.get("NEW_RECORD") or "Record")
            new_rec_action.triggered.connect(lambda: self.newRecordRequested.emit())

        if menu.actions():  # Only show menu if it has actions
            menu.exec(global_pos)

    def show_record_context_menu(self, 
                                global_pos: QPoint, 
                                selected_records: List[Record],
                                current_directory: Optional[Directory] = None,
                                clicked_on_empty_space: bool = False):
        """
        Show context menu for record pane.
        
        Args:
            global_pos: Global position where to show the menu
            selected_records: List of currently selected records
            current_directory: The current directory we're in
            clicked_on_empty_space: True if clicked on empty space in the pane
        """
        menu = QMenu(self.parent_widget)
        
        # Determine if we're in trash
        is_in_trash = current_directory == self.controller.get_recycle_bin() if current_directory else False
        
        # Check if clipboard has content
        has_clipboard = len(self.controller.clipboard) > 0

        if not clicked_on_empty_space and selected_records:
            # Actions for selected records
            
            # Cut
            cut_action = menu.addAction(QIcon.fromTheme("edit-cut"), Language.get("CUT") or "Cut")
            cut_action.triggered.connect(lambda: self._cut_items(selected_records))
            
            # Copy
            copy_action = menu.addAction(QIcon.fromTheme("edit-copy"), Language.get("COPY") or "Copy")
            copy_action.triggered.connect(lambda: self._copy_items(selected_records))
            
            menu.addSeparator()
            
            if is_in_trash:
                # Recover from trash
                recover_action = menu.addAction(QIcon.fromTheme("edit-undo"), Language.get("RECOVER") or "Recover")
                recover_action.triggered.connect(lambda: self.recoverRequested.emit(selected_records))
                
                # Delete permanently
                delete_perm_action = menu.addAction(QIcon.fromTheme("edit-delete"), Language.get("DELETE_PERMANENTLY") or "Delete Permanently")
                delete_perm_action.triggered.connect(lambda: self.deletePermRequested.emit(selected_records))
            else:
                # Delete (move to trash)
                delete_action = menu.addAction(QIcon.fromTheme("user-trash"), Language.get("DELETE") or "Delete")
                delete_action.triggered.connect(lambda: self.deleteRequested.emit(selected_records))
            
            # Only show rename if single item selected
            if len(selected_records) == 1:
                menu.addSeparator()
                rename_action = menu.addAction(QIcon.fromTheme("edit-rename"), Language.get("RENAME") or "Rename")
                rename_action.triggered.connect(lambda: self.renameRequested.emit(selected_records[0]))

        # Actions always available
        if not is_in_trash:  # Don't allow pasting in trash
            menu.addSeparator()
            
            # Paste
            paste_action = menu.addAction(QIcon.fromTheme("edit-paste"), Language.get("PASTE") or "Paste")
            paste_action.setEnabled(has_clipboard)
            paste_action.triggered.connect(lambda: self.pasteRequested.emit())
            
            menu.addSeparator()
            
            # New record
            new_rec_action = menu.addAction(QIcon.fromTheme("document-new"), Language.get("NEW_RECORD") or "New Record")
            new_rec_action.triggered.connect(lambda: self.newRecordRequested.emit())

        if menu.actions():  # Only show menu if it has actions
            menu.exec(global_pos)

    def _cut_items(self, items: Union[List[Directory], List[Record]]):
        """Handle cut operation"""
        logger.debug(f"[ContextMenu][{datetime.now()}] Cut requested for {len(items)} items")
        self.cutRequested.emit(items)

    def _copy_items(self, items: Union[List[Directory], List[Record]]):
        """Handle copy operation"""
        logger.debug(f"[ContextMenu][{datetime.now()}] Copy requested for {len(items)} items")
        self.copyRequested.emit(items)

    def _add_to_favorites(self, directories: List[Directory]):
        """Add directories to favorites"""
        for directory in directories:
            self.addToFavoritesRequested.emit(directory)

    def _remove_from_favorites(self, directories: List[Directory]):
        """Remove directories from favorites"""
        for directory in directories:
            self.removeFromFavoritesRequested.emit(directory)