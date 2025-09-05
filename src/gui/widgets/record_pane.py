from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableView, QHeaderView
from src.gui.record import RecordTableModel
from src.gui.language import Language

class RecordPane(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(8)
        v.addWidget(QLabel(Language.get("RECORDS")))
        self.model = RecordTableModel(self)
        self.view = QTableView(self); self.view.setModel(self.model)
        self.view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        v.addWidget(self.view)

    def populate(self, records):
        self.model.populate(records)