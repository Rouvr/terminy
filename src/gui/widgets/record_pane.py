from __future__ import annotations

from functools import partial
from typing import Optional

from PySide6.QtCore import Qt, QDate,QLocale, QTimer, Signal, QPoint
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView, QHeaderView,
    QMenu, QToolButton, QStyledItemDelegate, QDateEdit, QWidget, QWidgetAction, QCheckBox, QStyle
)
from src.gui.record import RecordTableModel
from src.gui.language import Language
from src.logic.controller import Controller
from src.logic.record import Record


import logging
from logging.handlers import RotatingFileHandler
logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.DEBUG)

class RecordPane(QWidget):
    # Signals for context menu events
    recordRightClicked = Signal(Record, QPoint)  # record + global pos for context menus
    recordsSelectionChanged = Signal(list)       # list[Record] 
    spaceRightClicked = Signal(QPoint)           # global pos for context menus on empty space
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self._controller: Optional[Controller] = None


        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)

        # --- Header row: "Records" label + right-aligned 3-lines button ---
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        self.titleLabel = QLabel(Language.get("RECORDS"))
        header.addWidget(self.titleLabel)
        header.addStretch(1)

        self.columnsBtn = QToolButton(self)
        self.columnsBtn.setText("≡")  # rectangle with 3 lines vibe
        self.columnsBtn.setToolTip(Language.get("COLUMNS") or "Columns")
        self.columnsBtn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.columnsBtn.setStyleSheet("QToolButton{border:1px solid palette(mid); padding:0 6px;}")
        self.columnsMenu = QMenu(self)
        self.columnsBtn.setMenu(self.columnsMenu)
        header.addWidget(self.columnsBtn)

        v.addLayout(header)

        # --- Table ---
        self.model = RecordTableModel(self)
        self.view = QTableView(self)
        self.view.setModel(self.model)

        # allow click-to-sort on header
        self.view.setSortingEnabled(True)
        self.view.horizontalHeader().setSectionsClickable(True)
        self.view.horizontalHeader().setSortIndicatorShown(True)
        # rows auto-height
        self.view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Enable selection and context menu
        self.view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._show_context_menu)
        
        # Track selection changes
        self.view.selectionModel().selectionChanged.connect(self._on_selection_changed)

        v.addWidget(self.view)
        self._defaultDelegate = QStyledItemDelegate(self.view) 

        # page-scroll mode flags
        self._page_scroll_enabled = False
        self._page_scroll_max_rows = 500
        
        # header column resize persistence
        self._suppress_header_resize = False
        self._header = self.view.horizontalHeader()
        self._header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._header.setStretchLastSection(False)
        self._header.sectionResized.connect(self._on_section_resized)

    # --------- public API ---------
    def set_controller(self, controller: Controller):
        self._controller = controller
        self._rebuild_columns_menu()
        self._apply_visible_attrs_from_controller()  # builds columns + applies widths
        QTimer.singleShot(0, self._apply_record_column_widths)  # ensure applied after first layout

    def populate(self, records):
        self.model.populate(records)
        self._apply_record_column_widths()  # <- use persisted widths here
        self.update_auto_height()

    # turn on/off "page-scroll" mode for the table
    def set_page_scroll_mode(self, enabled: bool, max_rows: int = 500):
        self._page_scroll_enabled = bool(enabled)
        self._page_scroll_max_rows = max(1, int(max_rows))
        self.view.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff if self._page_scroll_enabled
            else Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.update_auto_height()

    # calculate a fixed height that fits rows so the outer page scrolls
    def update_auto_height(self):
        if not self._page_scroll_enabled:
            self.view.setMaximumHeight(16777215)
            return

        # Make sure rows have their content-sized heights
        self.view.resizeRowsToContents()

        rows = self.model.rowCount()
        rows = min(rows, self._page_scroll_max_rows)

        h = 0
        hdr = self.view.horizontalHeader()
        if hdr.isVisible():
            h += hdr.height()

        for r in range(rows):
            h += self.view.rowHeight(r)

        # frame + a small buffer so last row isn't clipped
        h += 2 * self.view.frameWidth() + 2

        # --- NEW: if a horizontal scrollbar will be needed, add its thickness ---
        header_total_w = hdr.length()  # sum of all section widths
        vp_w = self.view.viewport().width()
        needs_hsb = header_total_w > vp_w

        if needs_hsb:
            sb_h = self.view.horizontalScrollBar().sizeHint().height()
            if sb_h <= 0:
                sb_h = self.view.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent, None, self.view)
            h += sb_h

        self.view.setFixedHeight(h)

    # --------- internals ---------
    
    def _label_for_attr(self, attr: str) -> str:
        return Language.get(attr.upper())
    
    def _on_section_resized(self, logical: int, old: int, new: int):
        if self._suppress_header_resize or not self._controller:
            return
        # map current column index -> attribute
        if logical < 0 or logical >= len(self.model.active_attrs):
            return
        attr = self.model.active_attrs[logical]

        # persist just this one
        self._controller.set_record_column_width([(attr, int(new))])
        
        QTimer.singleShot(0, self.update_auto_height)


    def _rebuild_columns_menu(self):
        if not self._controller:
            return
        self.columnsMenu.clear()

        all_attrs = self._controller.get_record_attrs()
        visible   = set(self._controller.get_visible_record_attrs())

        for attr in all_attrs:
            cb = QCheckBox(self._label_for_attr(attr), self.columnsMenu)  # ← translated
            cb.setChecked(attr in visible)
            cb.toggled.connect(partial(self._on_attr_toggled, attr))      # ← keep key!
            wa = QWidgetAction(self.columnsMenu)
            wa.setDefaultWidget(cb)
            self.columnsMenu.addAction(wa)

        self.columnsMenu.setMinimumWidth(180)

    def _on_attr_toggled(self, attr: str, checked: bool):
        """Persist toggle to controller and update the model columns."""
        if not self._controller:
            return
        if checked:
            self._controller.add_visible_record_attr(attr)
        else:
            self._controller.remove_visible_record_attr(attr)

        # reflect new visible set
        self._apply_visible_attrs_from_controller()

        
    def _apply_record_column_widths(self):
        """Resize columns from controller’s persisted widths; fall back to contents."""
        if not self._controller:
            return
        width_map = self._controller.record_column_widths()  # attr -> px
        logger.debug(f"[GUI][{Language.locale_tag()}] Applying record column widths: {width_map}")
        self._suppress_header_resize = True
        try:
            for col, attr in enumerate(self.model.active_attrs):
                w = width_map.get(attr, 0)
                if w and w > 0:
                    self.view.setColumnWidth(col, int(w))
                else:
                    self.view.resizeColumnToContents(col)
        finally:
            self._suppress_header_resize = False

    def _apply_visible_attrs_from_controller(self):
        if not self._controller:
            return

        # Remember the currently sorted attribute (by name, not index)
        hdr = self.view.horizontalHeader()
        have_sort = self.view.isSortingEnabled()
        prev_attr = None
        prev_order = hdr.sortIndicatorOrder()
        prev_section = hdr.sortIndicatorSection()
        if have_sort and 0 <= prev_section < len(self.model.active_attrs):
            prev_attr = self.model.active_attrs[prev_section]

        # Rebuild the visible columns in the model
        attrs = self._controller.get_visible_record_attrs()
        self.model.set_active_attrs(attrs, Record.ALL_ATTRIBUTES)

        # Reset the view and install delegates
        self.view.reset()

        dt_editable = {"validity_start", "validity_end"}
        dt_readonly = {"created", "modified"}
        for col, a in enumerate(self.model.active_attrs):
            if a in dt_editable:
                self.view.setItemDelegateForColumn(col, DateOnlyDelegate(editable=True, parent=self))
            elif a in dt_readonly:
                self.view.setItemDelegateForColumn(col, DateOnlyDelegate(editable=False, parent=self))
            else:
                self.view.setItemDelegateForColumn(col, self._defaultDelegate)

        # Apply persisted widths (don’t auto-size over them)
        self._apply_record_column_widths()

        # Re-apply the previous sort by attribute, if still visible
        if have_sort and prev_attr in self.model.active_attrs:
            new_section = self.model.active_attrs.index(prev_attr)
            self.view.sortByColumn(new_section, prev_order)

        self.update_auto_height()

    # --------- Context Menu Methods ---------
    
    def _show_context_menu(self, position: QPoint):
        """Handle context menu request"""
        from datetime import datetime
        index = self.view.indexAt(position)
        global_pos = self.view.mapToGlobal(position)
        
        if index.isValid():
            # Get the record at this position
            record = self.model.records[index.row()]
            self.recordRightClicked.emit(record, global_pos)
        else:
            # Clicked on empty space
            self.spaceRightClicked.emit(global_pos)
    
    def _on_selection_changed(self):
        """Handle selection changes"""
        from datetime import datetime
        selected_records = self.get_selected_records()
        self.recordsSelectionChanged.emit(selected_records)
        logger.debug(f"[RecordPane][{datetime.now()}] Selection changed: {len(selected_records)} records selected")
    
    def get_selected_records(self) -> list[Record]:
        """Get currently selected records"""
        selection_model = self.view.selectionModel()
        if not selection_model:
            return []
        
        selected_indexes = selection_model.selectedRows()
        selected_records = []
        
        for index in selected_indexes:
            if index.isValid():
                record = self.model.records[index.row()]
                selected_records.append(record)
        
        return selected_records

class DateOnlyDelegate(QStyledItemDelegate):
    """Date-only editor with calendar popup. Writes a Python datetime at 00:00."""
    def __init__(self, editable: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self.editable = editable
        self._locale: QLocale = Language.load_locale()

    def createEditor(self, parent, option, index):
        if not self.editable:
            return None  # keep read-only columns non-editable
        w = QDateEdit(parent)
        w.setCalendarPopup(True)
        w.setDisplayFormat("dd-MM-yyyy")  # same style as Search pane
        w.setDate(QDate.currentDate())
        w.setLocale(self._locale)
        # also apply to the calendar widget
        cw = w.calendarWidget()
        if cw:
            cw.setLocale(self._locale)
        return w

    def setEditorData(self, editor: QDateEdit, index):
        val = index.model().data(index, Qt.ItemDataRole.EditRole)
        # Accept either datetime or ISO string or empty
        from datetime import datetime
        if isinstance(val, datetime):
            editor.setDate(QDate(val.year, val.month, val.day))
        elif isinstance(val, str) and val:
            try:
                dt = datetime.fromisoformat(val)
                editor.setDate(QDate(dt.year, dt.month, dt.day))
            except Exception:
                editor.setDate(QDate.currentDate())
        else:
            editor.setDate(QDate.currentDate())

    def setModelData(self, editor: QDateEdit, model, index):
        from datetime import datetime
        qd = editor.date()
        dt = datetime(qd.year(), qd.month(), qd.day(), 0, 0, 0, 0)
        # prefer typed datetime; if model rejects, fall back to iso string
        if not model.setData(index, dt, Qt.ItemDataRole.EditRole):
            model.setData(index, dt.isoformat(), Qt.ItemDataRole.EditRole)