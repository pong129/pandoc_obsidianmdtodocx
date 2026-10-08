import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QGroupBox, QSplitter, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QSettings

from .widgets import FileListWidget
from .settings_panel import SettingsPanel
from .preview_dialog import MarkdownPreviewDialog
from ..core.pptx_converter import PptxConverter

class PptxConversionSignals(QObject):
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

class PptxConversionWorker(QThread):
    def __init__(self, converter, files, output_dir, config):
        super().__init__()
        self.converter = converter
        self.files = files
        self.output_dir = output_dir
        self.config = config
        self.signals = PptxConversionSignals()

    def run(self):
        try:
            results = self.converter.convert(
                self.files, 
                self.output_dir, 
                self.config, 
                progress_callback=self.signals.progress.emit
            )
            self.signals.finished.emit(results)
        except Exception as e:
            self.signals.error.emit(str(e))

class PptxTab(QWidget):
    log_message = Signal(str)

    def __init__(self, pandoc_manager):
        super().__init__()
        self.pandoc_manager = pandoc_manager
        self.converter = PptxConverter(self.pandoc_manager)
        self.files_to_convert = []
        self.init_ui()

    def load_settings(self):
        settings = QSettings("ObsiDeck", "PptxConverter")
        self.settings_panel.load_settings(settings, prefix="pptx_")

    def save_settings(self):
        settings = QSettings("ObsiDeck", "PptxConverter")
        self.settings_panel.save_settings(settings, prefix="pptx_")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 6, 0, 0)
        main_layout.setSpacing(6)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left Panel: File Selection
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 6, 0)
        left_layout.setSpacing(6)
        
        file_box = QGroupBox("변환할 Markdown 파일")
        file_box_layout = QVBoxLayout()
        file_box_layout.setContentsMargins(0, 8, 0, 0)
        file_box_layout.setSpacing(6)
        
        self.file_list = FileListWidget()
        self.file_list.files_dropped.connect(self.add_files)
        self.file_list.setToolTip("Markdown 파일 또는 폴더를 끌어다 놓을 수 있습니다.")
        file_box_layout.addWidget(self.file_list)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        add_btn = QPushButton("파일 추가")
        add_btn.clicked.connect(self.browse_files)
        preview_btn = QPushButton("미리보기")
        preview_btn.setObjectName("secondaryButton")
        preview_btn.clicked.connect(self.preview_selected_file)
        clear_btn = QPushButton("목록 비우기")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self.clear_files)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(clear_btn)
        file_box_layout.addLayout(btn_layout)
        
        file_box.setLayout(file_box_layout)
        left_layout.addWidget(file_box)
        
        # Right Panel: Settings and Action
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(6)
        
        # New Centralized Settings Panel
        self.settings_panel = SettingsPanel(is_pptx=True)
        right_layout.addWidget(self.settings_panel)
        
        # Action Area
        action_box = QGroupBox("실행")
        action_layout = QVBoxLayout()
        action_layout.setContentsMargins(0, 8, 0, 0)
        self.convert_btn = QPushButton("PPTX로 변환")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setFixedHeight(34)
        action_layout.addWidget(self.convert_btn)
        action_box.setLayout(action_layout)
        right_layout.addWidget(action_box)
        
        right_layout.addStretch()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        self.load_settings()

    def log(self, message):
        self.log_message.emit(message)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Markdown 파일 선택", "", "Markdown 파일 (*.md)")
        if files:
            self.add_files(files)

    def add_files(self, files):
        for f in files:
            if f not in self.files_to_convert:
                self.files_to_convert.append(f)
                self.file_list.addItem(os.path.basename(f))
        self.log(f"PPTX 변환 목록에 {len(files)}개 파일을 추가했습니다.")

    def clear_files(self):
        self.files_to_convert.clear()
        self.file_list.clear()
        self.log("PPTX 변환 목록을 비웠습니다.")

    def preview_selected_file(self):
        file_path = self._selected_or_first_file()
        if not file_path:
            QMessageBox.warning(self, "파일 없음", "미리볼 Markdown 파일을 추가해 주세요.")
            return
        dialog = MarkdownPreviewDialog(file_path, self)
        dialog.exec()

    def _selected_or_first_file(self):
        if not self.files_to_convert:
            return None
        selected_rows = [index.row() for index in self.file_list.selectedIndexes()]
        if selected_rows:
            row = selected_rows[0]
            if 0 <= row < len(self.files_to_convert):
                return self.files_to_convert[row]
        return self.files_to_convert[0]

    def start_conversion(self):
        if not self.files_to_convert:
            QMessageBox.warning(self, "파일 없음", "변환할 파일을 추가해 주세요.")
            return

        if not self.pandoc_manager.is_installed():
            QMessageBox.critical(self, "오류", "Pandoc이 설치되어 있지 않습니다. 먼저 설치해 주세요.")
            return
            
        config = self.settings_panel.get_config_dict()
        output_dir = config.get('output_dir', os.getcwd())
        
        if not config.get('save_to_original', True) and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except OSError:
                QMessageBox.critical(self, "오류", "출력 폴더가 올바르지 않습니다.")
                return

        self.worker = PptxConversionWorker(self.converter, self.files_to_convert, output_dir, config)
        self.current_conversion_config = config
        self.worker.signals.progress.connect(self.log)
        self.worker.signals.finished.connect(self.on_conversion_finished)
        self.worker.signals.error.connect(self.on_conversion_error)
        
        self.convert_btn.setEnabled(False)
        self.log("PPTX 변환을 시작합니다.")
        self.worker.start()

    def on_conversion_finished(self, results):
        self.convert_btn.setEnabled(True)
        self.log(f"PPTX 작업 완료: {len(results)}개 파일을 만들었습니다.")
        if getattr(self, "current_conversion_config", {}).get("open_after_conversion", False):
            self.open_result_files(results)
        QMessageBox.information(self, "완료", f"{len(results)}개 PPTX 파일을 변환했습니다.")
        # VERY IMPORTANT: To avoid memory leak, queue thread for deletion
        self.worker.deleteLater()
        self.worker = None

    def open_result_files(self, results):
        for path in results:
            try:
                os.startfile(path)
                self.log(f"결과 파일을 열었습니다: {path}")
            except Exception as e:
                self.log(f"결과 파일 열기 실패: {path} ({e})")

    def on_conversion_error(self, message):
        self.convert_btn.setEnabled(True)
        self.log(f"오류: {message}")
        QMessageBox.critical(self, "변환 오류", message)
        # VERY IMPORTANT: To avoid memory leak, queue thread for deletion
        self.worker.deleteLater()
        self.worker = None
