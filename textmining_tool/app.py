from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

# Force project root into sys.path so the app runs with `python app.py` or `python -m textmining_tool.app`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from textmining_tool.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("텍스트마이닝 AI 툴")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
