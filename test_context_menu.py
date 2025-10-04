#!/usr/bin/env python3
"""
Test script for context menu functionality in Terminy.
This script demonstrates how to use the context menu system.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.logic.controller import Controller

def test_context_menu():
    """Test the context menu functionality"""
    app = QApplication(sys.argv)
    
    # Use test data
    controller = Controller(data_path=r"test_data")
    main_window = MainWindow(controller)
    
    print("Context Menu Test")
    print("================")
    print()
    print("Instructions:")
    print("1. Right-click on a directory in the directory pane")
    print("2. Right-click on empty space in the directory pane")
    print("3. Right-click on a record in the record pane")
    print("4. Right-click on empty space in the record pane")
    print()
    print("Expected context menu options:")
    print("- Cut (if items selected)")
    print("- Copy (if items selected)")
    print("- Paste (if clipboard has content)")
    print("- Delete/Delete Permanently (depending on location)")
    print("- Rename (if single item selected)")
    print("- Add/Remove from Favorites (for directories)")
    print("- New Directory/Record options")
    print()
    print("Note: Some actions are not fully implemented yet (logged to console)")
    print()
    
    main_window.show()
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    test_context_menu()