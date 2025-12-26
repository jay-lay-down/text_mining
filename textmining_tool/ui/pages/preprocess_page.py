from __future__ import annotations

from typing import Dict, List

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QPushButton,
    QSlider,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ...core import preprocess
from ...core.state import AppState
from ...core.workers import WorkerRunner
from ..widgets import PandasModel, StatusStrip


class PreprocessPage(QWidget):
    def __init__(self, app_state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.worker_runner = WorkerRunner()

        self.file_info = QLabel("파일을 업로드하세요")
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.column_date = QComboBox()
        self.column_title = QComboBox()
        self.column_text = QListWidget()
        self.column_text.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.column_page_type = QComboBox()
        self.dimensions_list = QListWidget()
        self.dimensions_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        self.page_type_list = QListWidget()
        self.exclude_news_chk = QCheckBox("뉴스 제외")

        self.similar_chk = QCheckBox("유사중복 제거")
        self.similar_slider = QSlider(Qt.Orientation.Horizontal)
        self.similar_slider.setRange(70, 100)
        self.similar_slider.setValue(95)

        self.preview_model = PandasModel(pd.DataFrame())
        self.preview_table = QTableView()
        self.preview_table.setModel(self.preview_model)

        self.duplicate_model = PandasModel(pd.DataFrame())
        self.duplicate_table = QTableView()
        self.duplicate_table.setModel(self.duplicate_model)

        self.status_strip = StatusStrip()

        self._build_ui()

    def _build_ui(self) -> None:
        form = QFormLayout()
        form.addRow("Date/시간", self.column_date)
        form.addRow("Title", self.column_title)
        form.addRow("Text 컬럼(복수 선택)", self.column_text)
        form.addRow("Source/Page Type", self.column_page_type)
        form.addRow("분석 축(Dim) 선택", self.dimensions_list)

        mapping_box = QGroupBox("스키마 매핑")
        mapping_box.setLayout(form)

        page_type_box = QGroupBox("Page Type 필터")
        pt_layout = QVBoxLayout()
        pt_layout.addWidget(self.page_type_list)
        pt_layout.addWidget(self.exclude_news_chk)
        page_type_box.setLayout(pt_layout)

        duplicate_box = QGroupBox("중복")
        dup_layout = QHBoxLayout()
        dup_layout.addWidget(self.similar_chk)
        dup_layout.addWidget(QLabel("Threshold"))
        dup_layout.addWidget(self.similar_slider)
        duplicate_box.setLayout(dup_layout)

        btn_browse = QPushButton("찾아보기")
        btn_browse.clicked.connect(self.load_file)
        btn_apply = QPushButton("적용/스키마 확정")
        btn_apply.clicked.connect(self.apply_preprocess)

        load_bar = QHBoxLayout()
        load_bar.addWidget(QLabel("데이터 로드"))
        load_bar.addWidget(self.path_edit)
        load_bar.addWidget(btn_browse)
        load_bar.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(load_bar)
        layout.addWidget(mapping_box)
        layout.addWidget(page_type_box)
        layout.addWidget(duplicate_box)
        layout.addWidget(btn_apply)
        layout.addWidget(QLabel("미리보기"))
        layout.addWidget(self.preview_table)
        layout.addWidget(QLabel("제거된 중복"))
        layout.addWidget(self.duplicate_table)
        layout.addWidget(self.status_strip)
        layout.addStretch()
        self.setLayout(layout)

    def load_file(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(self, "파일 선택", filter="CSV or Excel (*.csv *.xlsx)")
        if not path:
            return
        df = pd.read_excel(path) if path.lower().endswith("xlsx") else pd.read_csv(path)
        self.app_state.raw_df = df
        self.path_edit.setText(path)
        self.file_info.setText(path)
        self._populate_columns(df.columns)
        self.preview_model.update(df.head(100))
        self.status_strip.update(len(df), self.app_state.period_unit, self.app_state.runtime_options.get("news_excluded", False))

    def _populate_columns(self, columns: List[str]) -> None:
        self.column_date.clear()
        self.column_title.clear()
        self.column_page_type.clear()
        self.column_date.addItems(columns)
        self.column_title.addItems(columns)
        self.column_page_type.addItems(columns)
        self.column_text.clear()
        self.dimensions_list.clear()
        for col in columns:
            self.column_text.addItem(col)
            self.dimensions_list.addItem(col)
        self.page_type_list.clear()

    def apply_preprocess(self) -> None:
        if self.app_state.raw_df is None:
            return
        text_cols = [self.column_text.item(i).text() for i in range(self.column_text.count()) if self.column_text.item(i).isSelected()]
        if not text_cols:
            text_cols = [self.column_text.item(0).text()] if self.column_text.count() else []
        df = self.app_state.raw_df
        # schema mapping and canonical conversion
        canonical_df, mapping_df = preprocess.build_canonical(
            df,
            dt_col=self.column_date.currentText(),
            text_cols=text_cols,
            title_col=self.column_title.currentText(),
            source_type_col=self.column_page_type.currentText(),
            extra_dims=[self.dimensions_list.item(i).text() for i in range(self.dimensions_list.count()) if self.dimensions_list.item(i).isSelected()],
        )
        self.app_state.canonical_df = canonical_df
        self.app_state.canonical_export_df = canonical_df
        self.app_state.schema_mapping_df = mapping_df
        mapping = {
            "Date": self.column_date.currentText(),
            "Title": self.column_title.currentText(),
            "Full Text": text_cols[0] if text_cols else self.column_title.currentText(),
            "Page Type": self.column_page_type.currentText(),
        }
        df = preprocess.map_columns(df, mapping)
        if "Page Type" in df.columns:
            self.page_type_list.clear()
            for val in sorted(df["Page Type"].dropna().unique()):
                item = QListWidgetItem(str(val))
                item.setCheckState(Qt.CheckState.Unchecked)
                self.page_type_list.addItem(item)
        selected_types = [
            self.page_type_list.item(i).text()
            for i in range(self.page_type_list.count())
            if self.page_type_list.item(i).checkState() == Qt.CheckState.Checked
        ]
        filtered = preprocess.filter_page_types(df, selected_types, self.exclude_news_chk.isChecked())
        with_keys = preprocess.generate_keys(filtered)
        deduped, removed = preprocess.remove_exact_duplicates(with_keys)
        if self.similar_chk.isChecked():
            deduped, similar_removed = preprocess.remove_similar(deduped, threshold=self.similar_slider.value())
            removed = pd.concat([removed, similar_removed])
        # sync canonical with dedup info
        if self.app_state.canonical_df is not None:
            self.app_state.canonical_df = self.app_state.canonical_df[self.app_state.canonical_df["doc_id"].isin(deduped["key"])]
        self.app_state.filtered_df = filtered
        self.app_state.dedup_df = deduped
        self.app_state.runtime_options["page_type_filter"] = selected_types
        self.app_state.runtime_options["news_excluded"] = self.exclude_news_chk.isChecked()
        self.preview_model.update(deduped.head(100))
        self.duplicate_model.update(removed.head(200))
        self.status_strip.update(len(deduped), self.app_state.period_unit, self.app_state.runtime_options.get("news_excluded", False))
        self.app_state.update_log("preprocess", "completed", {"rows": len(deduped)})
