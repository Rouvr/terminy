from PySide6.QtWidgets import QToolBar, QWidget, QHBoxLayout, QLabel, QLineEdit
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QStyle
from src.gui.language import Language

class TopBar(QToolBar):
    def __init__(self, parent=None):
        super().__init__("Main", parent)
        self.setMovable(False)
        self.setIconSize(QSize(16, 16))

        self.actionBack = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft), Language.get("ACTION_BACK"), self)
        self.actionForward = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight), Language.get("ACTION_FORWARD"), self)
        self.actionUp = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp), Language.get("ACTION_UP"), self)
        self.actionRefresh = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload), Language.get("ACTION_REFRESH"), self)

        self.addActions([self.actionBack, self.actionForward, self.actionUp])
        self.addSeparator()

        self.pathEdit = QLineEdit(self)
        self.pathEdit.setPlaceholderText(Language.get("TOP_TOOLBAR_PATH_PLACEHOLDER"))
        self.pathEdit.setFixedHeight(28)

        wrap = QWidget(self)
        h = QHBoxLayout(wrap); h.setContentsMargins(0,0,0,0)
        h.addWidget(QLabel(Language.get("TOP_TOOLBAR_INFO"), self))
        h.addWidget(self.pathEdit)
        self.addWidget(wrap)

        self.addSeparator()
        self.addAction(self.actionRefresh)