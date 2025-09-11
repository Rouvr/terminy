from __future__ import annotations

import math
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QStyledItemDelegate, QStyleOptionViewItem, QToolTip
from PySide6.QtGui import QFontMetrics

from src.gui.directory import DirectoryGrid
from src.logic.directory import Directory


class DirectoryPane(QWidget):
    """
    Headerless pane that hosts DirectoryGrid.

    When page-scroll mode is ON:
      - The inner grid's vertical scrollbar is disabled.
      - The pane computes a fixed height that fits all items.
      - The OUTER container (e.g., a QScrollArea page) scrolls everything together.

    When page-scroll mode is OFF (default):
      - The grid behaves normally (shows its own vertical scrollbar as needed).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.grid = DirectoryGrid(self)
        v.addWidget(self.grid)

        self._page_scroll_enabled = False
        self._page_scroll_max_rows = 1000

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.grid.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # update height when the model content changes
        if self.grid.model():
            self._connect_model_signals()


    def populate(self, directories: list[Directory]):
        """Populate the grid and recompute auto-height if needed."""
        self.grid.populate(directories)
        self.update_auto_height_deferred()

    def set_page_scroll_mode(self, enabled: bool, max_rows: int = 1000):
        """
        When enabled, the pane refuses to shrink below content height
        and disables the grid's own vertical scrollbar.
        """
        self._page_scroll_enabled = bool(enabled)
        self._page_scroll_max_rows = max(1, int(max_rows))

        self.grid.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff if self._page_scroll_enabled
            else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.update_auto_height_deferred()

    # ---------------- Internals ----------------

    def _connect_model_signals(self):
        m = self.grid.model()
        if not m:
            return
        # Update auto height on any content/layout change
        m.rowsInserted.connect(self.update_auto_height_deferred)
        m.rowsRemoved.connect(self.update_auto_height_deferred)
        m.modelReset.connect(self.update_auto_height_deferred)
        m.layoutChanged.connect(self.update_auto_height_deferred)
        m.dataChanged.connect(lambda *_: self.update_auto_height_deferred())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.update_auto_height_deferred()

    def update_auto_height_deferred(self):
        QTimer.singleShot(0, self.update_auto_height)

    def update_auto_height(self):
        if not self._page_scroll_enabled:
            # normal behavior: no forced height, let the view scroll itself
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.grid.setMinimumHeight(0)
            self.grid.setMaximumHeight(16777215)
            return

        model = self.grid.model()
        if not model:
            # nothing to show - collapse
            self.grid.setFixedHeight(0)
            self.setMinimumHeight(0)
            self.setMaximumHeight(0)
            return

        count = model.rowCount()
        if count <= 0:
            # nothing to show - collapse 
            self.grid.setFixedHeight(0)
            self.setMinimumHeight(0)
            self.setMaximumHeight(0)
            return

        # we have items - restore ability to grow
        self.setMaximumHeight(16777215)

        # use the grid’s own icon/text-based cell size
        cell = self.grid.cell_size_hint() 
        cell_w, cell_h = cell.width(), cell.height()

        spacing = getattr(self.grid, "spacing", lambda: 0)()
        vp_w = max(1, self.grid.viewport().width() - 2 * self.grid.frameWidth())

        cols = max(1, (vp_w + spacing) // (cell_w + spacing))
        rows = min((count + cols - 1) // cols, self._page_scroll_max_rows)

        total_h = rows * cell_h + max(0, rows - 1) * spacing
        total_h += 2 * self.grid.frameWidth()

        self.grid.setFixedHeight(total_h)
        # keep pane itself from being squeezed smaller than the grid
        self.setMinimumHeight(total_h)