#!/usr/bin/env python3
"""
Test script for navigation functionality in Terminy.
Tests the new home button and left nav panel navigation.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from src.gui.main_window import MainWindow
from src.logic.controller import Controller

def test_navigation():
    """Test the navigation functionality"""
    app = QApplication(sys.argv)
    
    # Use test data
    controller = Controller(data_path=r"test_data")
    main_window = MainWindow(controller)
    
    print("Navigation Test")
    print("===============")
    print()
    print("New Features to Test:")
    print("1. HOME BUTTON - Click the home icon in the top toolbar")
    print("   - Should navigate to the root directory")
    print()
    print("2. LEFT NAVIGATION PANEL:")
    print("   - Click 'Workspace' item - should navigate to root directory")
    print("   - Click 'Recycle Bin' item - should navigate to recycle bin")
    print()
    print("3. EXISTING FEATURES:")
    print("   - Back/Forward buttons work as before")
    print("   - Up button moves to parent directory")
    print("   - Path bar allows direct navigation")
    print()
    print("Expected behavior:")
    print("- Home button and Workspace click go to root directory")
    print("- Recycle bin click opens the recycle bin view")
    print("- Path bar updates to show current location")
    print("- Status bar shows navigation messages")
    print()
    
    main_window.show()
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)

if __name__ == "__main__":
    test_navigation()