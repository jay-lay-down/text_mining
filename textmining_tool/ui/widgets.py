from __future__ import annotations

import pandas as pd
from pandas.api.types import is_scalar
from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class PandasModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame = pd.DataFrame()) -> None:
        super().__init__()
        self._df = df

    def update(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        return 0 if parent and parent.isValid() else len(self._df.index)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        return 0 if parent and parent.isValid() else self._df.columns.size

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):  # noqa: ANN001, N802
        if not index.isValid() or role not in {Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole}:
            return None
        value = self._df.iat[index.row(), index.column()]
        if is_scalar(value):
            return "" if pd.isna(value) else str(value)
        if hasattr(value, "__len__") and len(value) == 0:  # type: ignore[arg-type]
            return ""
        return str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):  # noqa: ANN001, N802
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return str(self._df.columns[section])
        return str(self._df.index[section])


class FilePicker(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.path: str | None = None
        self.label = QLabel(label)
        self.button = QPushButton("파일 선택")
        self.button.clicked.connect(self.pick_file)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "파일 선택", filter="CSV or Excel (*.csv *.xlsx)")
        if path:
            self.path = path
            self.label.setText(path)


class StatusStrip(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.rows_label = QLabel("Rows: 0")
        self.period_label = QLabel("기간: -")
        self.news_label = QLabel("뉴스 제외: -")
        layout = QHBoxLayout()
        layout.addWidget(self.rows_label)
        layout.addWidget(self.period_label)
        layout.addWidget(self.news_label)
        layout.addStretch()
        self.setLayout(layout)

    def update(self, rows: int, period: str, news_excluded: bool) -> None:
        self.rows_label.setText(f"Rows: {rows}")
        self.period_label.setText(f"기간: {period}")
        self.news_label.setText(f"뉴스 제외: {'예' if news_excluded else '아니오'}")
