import os

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
)


class MarkdownPreviewDialog(QDialog):
    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setWindowTitle("Markdown 미리보기")
        self.resize(860, 640)
        self.init_ui()
        self.load_file()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        self.path_label = QLabel(os.path.basename(self.file_path))
        self.path_label.setToolTip(self.file_path)
        header_layout.addWidget(self.path_label)
        header_layout.addStretch()

        refresh_btn = QPushButton("새로고침")
        refresh_btn.setObjectName("secondaryButton")
        refresh_btn.clicked.connect(self.load_file)
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)

        self.tabs = QTabWidget()
        self.rendered_view = QTextBrowser()
        self.rendered_view.setOpenExternalLinks(True)
        self.raw_view = QTextEdit()
        self.raw_view.setReadOnly(True)

        self.tabs.addTab(self.rendered_view, "미리보기")
        self.tabs.addTab(self.raw_view, "원문")
        layout.addWidget(self.tabs)

    def load_file(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                content = file.read()
        except Exception as exc:
            content = f"파일을 읽을 수 없습니다:\n{exc}"

        self.rendered_view.setMarkdown(content)
        self.raw_view.setPlainText(content)
