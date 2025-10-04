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


import logging
from logging.handlers import RotatingFileHandler
logger = logging.getLogger(__name__)
logger.addHandler(RotatingFileHandler(
    "terminy.log", maxBytes=1024*1024*5, backupCount=5, encoding="utf-8"
))
logger.setLevel(logging.DEBUG)

class SearchPane(QWidget):
    """
    Toggle-driven search/filter pane with heading.

    Buttons (toggles) and their fields:
      - Name            -> Name
      - Description     -> Description
      - Filename        -> Filename
      - Record ID       -> Record id
      - Time created    -> Created min + max
      - Time modified   -> Modified min + max
      - Validity start  -> Val start min + max
      - Validity end    -> Val end min + max
      - Tags            -> required tags + any tags + exclude tags

    Signals:
      - filtersChanged(dict)
      - searchRequested(dict)
    """
    filtersChanged = Signal(dict)
    searchRequested = Signal(dict)
    

    def __init__(self, parent=None):
        super().__init__(parent)


        self._calendar_locale: QLocale = Language.load_locale()
        logger.debug(f"[SearchPane]: initial locale {self._calendar_locale.name()}")
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # ---------- Heading ----------
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        heading = QLabel(Language.get("SEARCH"))
        heading.setStyleSheet("font-weight: 600; color: palette(mid);")
        root.addWidget(heading)

        # ---------- Toggles row ----------
        self.btn_name       = self._mk_toggle(Language.get("NAME"))
        self.btn_desc       = self._mk_toggle(Language.get("DESCRIPTION"))
        self.btn_filename   = self._mk_toggle(Language.get("FILENAME"))
        self.btn_record_id  = self._mk_toggle(Language.get("RECORD_ID"))
        self.btn_created    = self._mk_toggle(Language.get("TIME_CREATED"))
        self.btn_modified   = self._mk_toggle(Language.get("TIME_MODIFIED"))
        self.btn_vstart     = self._mk_toggle(Language.get("VALIDITY_START"))
        self.btn_vend       = self._mk_toggle(Language.get("VALIDITY_END"))
        self.btn_tags       = self._mk_toggle(Language.get("TAGS"))

        toggles = QHBoxLayout()
        toggles.setContentsMargins(0, 0, 0, 0)
        toggles.setSpacing(6)
        for b in (
            self.btn_name, self.btn_desc, self.btn_filename, self.btn_record_id,
            self.btn_created, self.btn_modified, self.btn_vstart, self.btn_vend, self.btn_tags
        ):
            toggles.addWidget(b)
        toggles.addStretch(1)

        self.btn_search = QPushButton(Language.get("SEARCH"), self)
        self.btn_clear  = QPushButton(Language.get("CLEAR"), self)
        toggles.addWidget(self.btn_clear)
        toggles.addWidget(self.btn_search)
        root.addLayout(toggles)

        # ---------- Fields grid (labels + widgets per row) ----------
        fields = QGridLayout()
        fields.setContentsMargins(0, 0, 0, 0)
        fields.setHorizontalSpacing(10)
        fields.setVerticalSpacing(4)

        # Keep references so we can hide BOTH the label and row widget
        # Map: toggle_button -> (label_widget, row_widget)
        self._row_widgets: Dict[QToolButton, Tuple[QWidget, QWidget]] = {}

        def add_row(row: int, label_text: str, row_widget: QWidget, toggle_btn: QToolButton):
            lbl = QLabel(label_text, self)
            fields.addWidget(lbl, row, 0)
            fields.addWidget(row_widget, row, 1)
            self._row_widgets[toggle_btn] = (lbl, row_widget)
            # default hidden
            lbl.setVisible(False)
            row_widget.setVisible(False)

        # --- Row widgets (always created; hidden until toggled) ---
        # Name
        self.edit_name = QLineEdit(self)
        self.edit_name.setPlaceholderText(Language.get("NAME"))

        # Description
        self.edit_desc = QLineEdit(self)
        self.edit_desc.setPlaceholderText(Language.get("DESCRIPTION"))

        # Filename
        self.edit_filename = QLineEdit(self)
        self.edit_filename.setPlaceholderText(Language.get("FILENAME"))

        # Record ID
        self.edit_record_id = QLineEdit(self)
        self.edit_record_id.setPlaceholderText(Language.get("RECORD_ID"))

        # Time created: min + max
        self.date_created_min = self._mk_date()
        self.date_created_max = self._mk_date()
        created_row = self._mk_range_row("Min", self.date_created_min, "Max", self.date_created_max)

        # Time modified: min + max
        self.date_modified_min = self._mk_date()
        self.date_modified_max = self._mk_date()
        modified_row = self._mk_range_row("Min", self.date_modified_min, "Max", self.date_modified_max)

        # Validity start: min + max
        self.date_vstart_min = self._mk_date()
        self.date_vstart_max = self._mk_date()
        vstart_row = self._mk_range_row("Min", self.date_vstart_min, "Max", self.date_vstart_max)

        # Validity end: min + max
        self.date_vend_min = self._mk_date()
        self.date_vend_max = self._mk_date()
        vend_row = self._mk_range_row("Min", self.date_vend_min, "Max", self.date_vend_max)

        # Tags: required + any + exclude
        self.edit_tags_required = QLineEdit(self); self.edit_tags_required.setPlaceholderText(Language.get("REQUIRED_TAGS_COMMA"))
        self.edit_tags_any      = QLineEdit(self); self.edit_tags_any.setPlaceholderText(Language.get("ANY_TAGS_COMMA"))
        self.edit_tags_exclude  = QLineEdit(self); self.edit_tags_exclude.setPlaceholderText(Language.get("EXCLUDE_TAGS_COMMA"))
        tags_row = self._mk_tags_row()

        # Build rows (keep order tidy)
        r = 0
        add_row(r, Language.get("NAME") or "Name", self.edit_name, self.btn_name); r += 1
        add_row(r, Language.get("DESCRIPTION") or "Description", self.edit_desc, self.btn_desc); r += 1
        add_row(r, Language.get("FILENAME"), self.edit_filename, self.btn_filename); r += 1
        add_row(r, Language.get("RECORD_ID"), self.edit_record_id, self.btn_record_id); r += 1
        add_row(r, Language.get("CREATED"), created_row, self.btn_created); r += 1
        add_row(r, Language.get("MODIFIED"), modified_row, self.btn_modified); r += 1
        add_row(r, Language.get("VALIDITY_START"), vstart_row, self.btn_vstart); r += 1
        add_row(r, Language.get("VALIDITY_END"), vend_row, self.btn_vend); r += 1
        add_row(r, Language.get("TAGS"), tags_row, self.btn_tags); r += 1

        root.addLayout(fields)

        # ---------- Wiring ----------
        for b in self._row_widgets.keys():
            b.toggled.connect(self._on_toggle)

        # edits trigger live filters
        self.edit_name.textChanged.connect(self._emit_filters)
        self.edit_desc.textChanged.connect(self._emit_filters)
        self.edit_filename.textChanged.connect(self._emit_filters)
        self.edit_record_id.textChanged.connect(self._emit_filters)

        self.date_created_min.dateChanged.connect(self._emit_filters)
        self.date_created_max.dateChanged.connect(self._emit_filters)
        self.date_modified_min.dateChanged.connect(self._emit_filters)
        self.date_modified_max.dateChanged.connect(self._emit_filters)
        self.date_vstart_min.dateChanged.connect(self._emit_filters)
        self.date_vstart_max.dateChanged.connect(self._emit_filters)
        self.date_vend_min.dateChanged.connect(self._emit_filters)
        self.date_vend_max.dateChanged.connect(self._emit_filters)

        self.edit_tags_required.textChanged.connect(self._emit_filters)
        self.edit_tags_any.textChanged.connect(self._emit_filters)
        self.edit_tags_exclude.textChanged.connect(self._emit_filters)

        self.btn_search.clicked.connect(self._on_search_clicked)
        self.btn_clear.clicked.connect(self._on_clear_clicked)

    # ---------- helpers ----------
    def _mk_toggle(self, text: str) -> QToolButton:
        b = QToolButton(self)
        b.setText(text)
        b.setCheckable(True)
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        return b

    def _mk_date(self) -> QDateEdit:
        d = QDateEdit(self)
        d.setCalendarPopup(True)
        d.setDisplayFormat("dd-MM-yyyy")
        d.setDate(QDate.currentDate())                       

        # apply locale to the editor and its popup calendar
        d.setLocale(self._calendar_locale)
        cal = QCalendarWidget(d)
        cal.setLocale(self._calendar_locale)
        d.setCalendarWidget(cal)

        return d

    def _mk_range_row(self, label_left: str, left_widget: QWidget,
                       label_right: str, right_widget: QWidget) -> QWidget:
        w = QWidget(self)
        h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(6)
        h.addWidget(QLabel(label_left + ":", w))
        h.addWidget(left_widget, 1)
        h.addSpacing(12)
        h.addWidget(QLabel(label_right + ":", w))
        h.addWidget(right_widget, 1)
        return w

    def _mk_tags_row(self) -> QWidget:
        w = QWidget(self)
        h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(6)
        h.addWidget(QLabel(Language.get("REQUIRED") + ":", w))
        h.addWidget(self.edit_tags_required, 1)
        h.addSpacing(8)
        h.addWidget(QLabel(Language.get("ANY") + ":", w))
        h.addWidget(self.edit_tags_any, 1)
        h.addSpacing(8)
        h.addWidget(QLabel(Language.get("EXCLUDE") + ":", w))
        h.addWidget(self.edit_tags_exclude, 1)
        return w

    # ---------- events ----------
    def _on_toggle(self, checked: bool):
        sender = self.sender()
        if not isinstance(sender, QToolButton):
            return
        pair = self._row_widgets.get(sender)
        if not pair:
            return
        lbl, row = pair
        lbl.setVisible(bool(checked))
        row.setVisible(bool(checked))
        self._emit_filters()

    def _on_search_clicked(self):
        self.searchRequested.emit(self.get_filters())

    def _on_clear_clicked(self):
        # Untoggle all → hides full rows
        for b, pair in self._row_widgets.items():
            if b.isChecked():
                b.setChecked(False)
            lbl, row = pair
            lbl.setVisible(False)
            row.setVisible(False)

        # Clear inputs
        self.edit_name.clear()
        self.edit_desc.clear()
        self.edit_filename.clear()
        self.edit_record_id.clear()

        self.edit_tags_required.clear()
        self.edit_tags_any.clear()
        self.edit_tags_exclude.clear()

        # Dates keep their control value; rows are hidden so they won’t apply
        self._emit_filters()
        
        today = QDate.currentDate()
        for w in (
            self.date_created_min, self.date_created_max,
            self.date_modified_min, self.date_modified_max,
            self.date_vstart_min,  self.date_vstart_max,
            self.date_vend_min,    self.date_vend_max,
        ):
            w.setDate(today)

    def _emit_filters(self):
        self.filtersChanged.emit(self.get_filters())

    # ---------- public API ----------
    def get_filters(self) -> Dict:
        """
        Returns only active fields, with keys:
          name, description, filename, record_id
          created_min/max, modified_min/max,
          validity_start_min/max, validity_end_min/max,
          required_tags, any_tags, exclude_tags
        """
        out: Dict = {}

        # text fields
        if self.btn_name.isChecked():
            v = self.edit_name.text().strip()
            if v:
                out["name"] = v

        if self.btn_desc.isChecked():
            v = self.edit_desc.text().strip()
            if v:
                out["description"] = v

        if self.btn_filename.isChecked():
            v = self.edit_filename.text().strip()
            if v:
                out["filename"] = v

        if self.btn_record_id.isChecked():
            v = self.edit_record_id.text().strip()
            if v:
                try:
                    out["record_id"] = int(v)
                except ValueError:
                    # if it's not an int, pass as text to let the controller decide
                    out["record_id_text"] = v

        # helper for day bounds
        def day_start_end(qdate):
            y, m, d = qdate.year(), qdate.month(), qdate.day()
            return (
                datetime(y, m, d, 0, 0, 0, 0),
                datetime(y, m, d, 23, 59, 59, 999999),
            )

        # created range
        if self.btn_created.isChecked():
            s0, _ = day_start_end(self.date_created_min.date())
            _, e1 = day_start_end(self.date_created_max.date())
            out["created_min"] = s0
            out["created_max"] = e1

        # modified range
        if self.btn_modified.isChecked():
            s0, _ = day_start_end(self.date_modified_min.date())
            _, e1 = day_start_end(self.date_modified_max.date())
            out["modified_min"] = s0
            out["modified_max"] = e1

        # validity start range
        if self.btn_vstart.isChecked():
            s0, _ = day_start_end(self.date_vstart_min.date())
            _, e1 = day_start_end(self.date_vstart_max.date())
            out["validity_start_min"] = s0
            out["validity_start_max"] = e1

        # validity end range
        if self.btn_vend.isChecked():
            s0, _ = day_start_end(self.date_vend_min.date())
            _, e1 = day_start_end(self.date_vend_max.date())
            out["validity_end_min"] = s0
            out["validity_end_max"] = e1

        # tags (comma-separated lists)
        if self.btn_tags.isChecked():
            req = [t.strip() for t in self.edit_tags_required.text().split(",") if t.strip()]
            any_ = [t.strip() for t in self.edit_tags_any.text().split(",") if t.strip()]
            exc = [t.strip() for t in self.edit_tags_exclude.text().split(",") if t.strip()]
            if req:
                out["required_tags"] = req
            if any_:
                out["any_tags"] = any_
            if exc:
                out["exclude_tags"] = exc

        return out

    def set_calendar_locale(self, locale: QLocale | str):
        if isinstance(locale, str):
            locale = QLocale(locale)
        self._calendar_locale = locale

        # apply to all existing date edits + their calendars
        for w in (
            self.date_created_min, self.date_created_max,
            self.date_modified_min, self.date_modified_max,
            self.date_vstart_min,  self.date_vstart_max,
            self.date_vend_min,    self.date_vend_max,
        ):
            w.setLocale(locale)
            cw = w.calendarWidget()
            if cw is not None:
                cw.setLocale(locale)