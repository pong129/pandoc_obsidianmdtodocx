import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QGroupBox, QSplitter, QMessageBox, QFileDialog, QCheckBox, QLabel, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QSettings
from PySide6.QtGui import QGuiApplication

from .widgets import FileListWidget
from ..core.docx_to_md_converter import DocxToMdConverter
from ..core.settings_store import create_settings

class DocxToMdConversionSignals(QObject):
    progress = Signal(str)
    finished = Signal(list)
    error = Signal(str)

class DocxToMdConversionWorker(QThread):
    def __init__(self, converter, files, output_dir, config):
        super().__init__()
        self.converter = converter
        self.files = list(files)
        self.output_dir = output_dir
        self.config = config
        self.signals = DocxToMdConversionSignals()

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


class DocxToMdSettingsPanel(QWidget):
    """Simplified settings panel for DOCX to MD conversion."""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Output options
        output_group = QGroupBox("저장 설정")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(0, 8, 0, 0)
        output_layout.setSpacing(6)

        self.save_to_original_chk = QCheckBox("원본 문서와 같은 폴더에 저장")
        self.save_to_original_chk.setChecked(True)
        self.save_to_original_chk.stateChanged.connect(self.toggle_custom_dir)

        self.custom_dir_widget = QWidget()
        custom_dir_layout = QHBoxLayout(self.custom_dir_widget)
        custom_dir_layout.setContentsMargins(0, 0, 0, 0)
        custom_dir_layout.setSpacing(6)
        
        self.output_dir_edit = QLineEdit(os.getcwd())
        self.output_dir_btn = QPushButton("찾아보기")
        self.output_dir_btn.clicked.connect(self.browse_output)
        
        custom_dir_layout.addWidget(QLabel("저장 폴더:"))
        custom_dir_layout.addWidget(self.output_dir_edit)
        custom_dir_layout.addWidget(self.output_dir_btn)

        self.custom_dir_widget.setEnabled(False)

        output_layout.addWidget(self.save_to_original_chk)
        output_layout.addWidget(self.custom_dir_widget)
        
        # Extra options
        self.extract_media_chk = QCheckBox("이미지 추출")
        self.extract_media_chk.setChecked(False)
        self.extract_media_chk.setToolTip("문서 안의 이미지를 Markdown 파일 옆 별도 폴더로 추출합니다.")
        output_layout.addWidget(self.extract_media_chk)

        self.open_after_conversion_chk = QCheckBox("변환 완료 후 결과 파일 열기")
        self.open_after_conversion_chk.setChecked(False)
        output_layout.addWidget(self.open_after_conversion_chk)

        layout.addWidget(output_group)
        layout.addStretch()

    def toggle_custom_dir(self, state):
        self.custom_dir_widget.setEnabled(state != Qt.Checked.value)

    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if directory:
            self.output_dir_edit.setText(directory)

    def load_settings(self, settings: QSettings, prefix: str = ""):
        self.save_to_original_chk.setChecked(settings.value(f"{prefix}save_to_original", True, type=bool))
        self.output_dir_edit.setText(settings.value(f"{prefix}output_dir", os.getcwd()))
        self.extract_media_chk.setChecked(settings.value(f"{prefix}extract_media", False, type=bool))
        self.open_after_conversion_chk.setChecked(settings.value(f"{prefix}open_after_conversion", False, type=bool))
        self.toggle_custom_dir(self.save_to_original_chk.checkState().value)

    def save_settings(self, settings: QSettings, prefix: str = ""):
        settings.setValue(f"{prefix}save_to_original", self.save_to_original_chk.isChecked())
        settings.setValue(f"{prefix}output_dir", self.output_dir_edit.text())
        settings.setValue(f"{prefix}extract_media", self.extract_media_chk.isChecked())
        settings.setValue(f"{prefix}open_after_conversion", self.open_after_conversion_chk.isChecked())

    def get_config_dict(self) -> dict:
        return {
            'save_to_original': self.save_to_original_chk.isChecked(),
            'output_dir': self.output_dir_edit.text(),
            'extract_media': self.extract_media_chk.isChecked(),
            'open_after_conversion': self.open_after_conversion_chk.isChecked()
        }


class DocxToMdTab(QWidget):
    log_message = Signal(str)

    def __init__(self, pandoc_manager, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else create_settings()
        self.pandoc_manager = pandoc_manager
        self.converter = DocxToMdConverter(self.pandoc_manager)
        self.files_to_convert = []
        self.init_ui()

    def load_settings(self):
        settings = self.settings
        self.settings_panel.load_settings(settings, prefix="md_")

    def save_settings(self):
        settings = self.settings
        self.settings_panel.save_settings(settings, prefix="md_")

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
        
        file_box = QGroupBox("변환할 DOCX 파일")
        file_box_layout = QVBoxLayout()
        file_box_layout.setContentsMargins(0, 8, 0, 0)
        file_box_layout.setSpacing(6)
        
        self.file_list = FileListWidget(allowed_extensions=[".docx"])
        self.file_list.files_dropped.connect(self.add_files)
        self.file_list.setToolTip("DOCX 파일 또는 폴더를 끌어다 놓을 수 있습니다.")
        file_box_layout.addWidget(self.file_list)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        add_btn = QPushButton("파일 추가")
        add_btn.clicked.connect(self.browse_files)
        clear_btn = QPushButton("목록 비우기")
        clear_btn.setObjectName("secondaryButton")
        clear_btn.clicked.connect(self.clear_files)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(clear_btn)
        file_box_layout.addLayout(btn_layout)
        
        file_box.setLayout(file_box_layout)
        left_layout.addWidget(file_box)
        
        # Right Panel: Settings and Action
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(6)
        
        # Settings
        self.settings_panel = DocxToMdSettingsPanel()
        right_layout.addWidget(self.settings_panel)
        
        # Action Area
        action_box = QGroupBox("실행")
        action_layout = QVBoxLayout()
        action_layout.setContentsMargins(0, 8, 0, 0)
        action_layout.setSpacing(6)
        
        self.convert_btn = QPushButton("Markdown으로 변환")
        self.convert_btn.clicked.connect(self.start_conversion)
        self.convert_btn.setFixedHeight(34)
        action_layout.addWidget(self.convert_btn)

        self.copy_btn = QPushButton("Markdown 복사")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setObjectName("secondaryButton")
        self.copy_btn.setToolTip("마지막으로 변환한 Markdown 내용을 클립보드에 복사합니다.")
        self.copy_btn.setEnabled(False)
        action_layout.addWidget(self.copy_btn)

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
        files, _ = QFileDialog.getOpenFileNames(self, "DOCX 파일 선택", "", "Word 문서 (*.docx)")
        if files:
            self.add_files(files)

    def add_files(self, files):
        for f in files:
            if f.lower().endswith('.docx') and f not in self.files_to_convert:
                self.files_to_convert.append(f)
                self.file_list.addItem(os.path.basename(f))
        self.log(f"Markdown 변환 목록에 {len(self.files_to_convert)}개 파일이 있습니다.")

    def clear_files(self):
        self.files_to_convert.clear()
        self.file_list.clear()
        self.log("DOCX 변환 목록을 비웠습니다.")

    def start_conversion(self):
        if not self.files_to_convert:
            QMessageBox.warning(self, "파일 없음", "변환할 DOCX 파일을 추가해 주세요.")
            return

        if not self.pandoc_manager.is_installed():
            QMessageBox.critical(self, "오류", "Pandoc이 설치되어 있지 않습니다. 먼저 설치해 주세요.")
            return
            
        config = self.settings_panel.get_config_dict()
        output_dir = config.get('output_dir', os.getcwd())
        
        if not config.get('save_to_original') and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except OSError:
                QMessageBox.critical(self, "오류", "사용자 지정 저장 폴더가 올바르지 않습니다.")
                return

        self.worker = DocxToMdConversionWorker(self.converter, self.files_to_convert, output_dir, config)
        self.current_conversion_config = config
        self.worker.signals.progress.connect(self.log)
        self.worker.signals.finished.connect(self.on_conversion_finished)
        self.worker.signals.error.connect(self.on_conversion_error)
        
        self.convert_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.last_converted_file = None
        self.log("Markdown 변환을 시작합니다.")
        self.worker.start()

    def on_conversion_finished(self, results):
        self.convert_btn.setEnabled(True)
        self.log(f"Markdown 작업 완료: {len(results)}개 파일을 만들었습니다.")
        if self.converter.last_errors:
            self.log(f'실패: {len(self.converter.last_errors)}개 · 작업 로그를 확인해 주세요.')
        
        if results:
            self.last_converted_file = results[-1]  # Keep track of the last done file
            self.copy_btn.setEnabled(True)
            if getattr(self, "current_conversion_config", {}).get("open_after_conversion", False):
                self.open_result_files(results)
            QMessageBox.information(self, "완료", f"{len(results)}개 Markdown 파일을 변환했습니다.")
        else:
            QMessageBox.warning(self, "완료", "변환은 끝났지만 생성된 파일이 없습니다.")

        self.worker.wait()
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
        self.worker.wait()
        self.worker.deleteLater()
        self.worker = None

    def copy_to_clipboard(self):
        if not hasattr(self, 'last_converted_file') or not self.last_converted_file:
            return
        
        if os.path.exists(self.last_converted_file):
            try:
                with open(self.last_converted_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                clipboard = QGuiApplication.clipboard()
                clipboard.setText(content)
                self.log(f"{os.path.basename(self.last_converted_file)} 내용을 클립보드에 복사했습니다.")
            except Exception as e:
                self.log(f"클립보드 복사 실패: {e}")
                QMessageBox.critical(self, "오류", f"변환된 파일을 읽지 못했습니다:\n{e}")
        else:
            self.log(f"복사할 파일을 찾을 수 없습니다: {self.last_converted_file}")
            QMessageBox.warning(self, "오류", "변환된 파일이 더 이상 존재하지 않습니다.")
