from __future__ import annotations

from datetime import datetime
from typing import Dict, Tuple

from PySide6.QtCore import Qt, Signal, QDate, QLocale
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QToolButton, QPushButton, QDateEdit, QSizePolicy, QCalendarWidget
)

from src.gui.language import Language
from src.logic.registry import RegistryManager

