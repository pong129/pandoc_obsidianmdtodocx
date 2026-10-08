import json
import os
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QUrl, QSettings
from PySide6.QtGui import QDesktopServices, QFontDatabase
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTabWidget, QTextEdit, QMessageBox, QSplitter, QComboBox,
    QStackedWidget, QListWidgetItem, QTextBrowser, QInputDialog, QScrollArea,
    QCheckBox, QDialog, QToolButton,
)
from .widgets import FileListWidget
from .styles import MAIN_WINDOW_STYLE, WIDGET_STYLE
from .settings_panel import SettingsPanel
from ..core.pandoc_manager import PandocManager
from ..core.converter import Converter
from ..core.pptx_converter import PptxConverter
from ..core.settings_store import create_settings


class ConversionWorker(QThread):
    progress = Signal(str)
    completed = Signal(list, list, list)
    failed = Signal(str)

    def __init__(self, converter, files, output_dir, config):
        super().__init__()
        self.converter = converter
        self.files = list(files)
        self.output_dir = output_dir
        self.config = dict(config)

    def run(self):
        try:
            results = self.converter.convert(self.files, self.output_dir, self.config, self.progress.emit)
            self.completed.emit(results, self.converter.last_errors, self.converter.last_warnings)
        except Exception as error:
            self.failed.emit(str(error))


class PandocSetupWorker(QThread):
    progress = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def run(self):
        try:
            self.completed.emit(self.manager.install_or_update_pandoc(self.progress.emit))
        except Exception as error:
            self.failed.emit(str(error))


class MainWindow(QMainWindow):
    def __init__(self, settings=None, pandoc_manager=None):
        super().__init__()
        self.setWindowTitle('옵시디언 문서 변환기')
        self.resize(1180, 860)
        self.setMinimumSize(940, 700)
        self.setStyleSheet(MAIN_WINDOW_STYLE)
        self.settings = settings if settings is not None else create_settings()
        self.pandoc_manager = pandoc_manager or PandocManager()
        self.converters = {'docx': Converter(self.pandoc_manager), 'pptx': PptxConverter(self.pandoc_manager)}
        self.files_to_convert = []
        self.worker = None
        self.pandoc_worker = None
        self.last_results = []
        self.import_dir = str(self.settings.value('import_dir', str(Path.home())))
        self.init_ui()
        self.load_settings()
        self.check_pandoc()

    @property
    def current_format(self):
        return self.format_combo.currentData()

    @property
    def settings_panel(self):
        return self.panels[self.current_format]

    def button(self, text, callback, secondary=True):
        button = QPushButton(text)
        if secondary:
            button.setObjectName('secondaryButton')
        button.clicked.connect(callback)
        return button

    def init_ui(self):
        central = QWidget(); central.setStyleSheet(WIDGET_STYLE)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 14, 18, 14); layout.setSpacing(12)
        top = QHBoxLayout()
        title = QLabel('옵시디언 문서 변환기'); title.setObjectName('appTitle')
        top.addWidget(title); top.addStretch()
        self.status_label = QLabel('Pandoc 확인 중…'); top.addWidget(self.status_label)
        self.refresh_pandoc_btn = self.button('다시 확인', self.check_pandoc)
        top.addWidget(self.refresh_pandoc_btn)
        self.check_pandoc_btn = self.button('Pandoc 설치/업데이트', self.check_and_install_pandoc)
        top.addWidget(self.check_pandoc_btn)
        layout.addLayout(top)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        layout.addWidget(self.splitter, 1)

        self.import_panel = QWidget(); left = QVBoxLayout(self.import_panel)
        left.setContentsMargins(0, 0, 14, 0); left.setSpacing(10)
        label = QLabel('1  Markdown 가져오기'); label.setObjectName('sectionLabel'); left.addWidget(label)
        row = QHBoxLayout()
        row.addWidget(self.button('파일 열기', self.browse_files))
        row.addWidget(self.button('폴더 열기', self.browse_folder))
        left.addLayout(row)
        self.import_tabs = QTabWidget(); left.addWidget(self.import_tabs, 1)
        files_page = QWidget(); files_layout = QVBoxLayout(files_page)
        files_layout.setContentsMargins(0, 8, 0, 0)
        hint = QLabel('Markdown 파일이나 폴더를 아래로 끌어다 놓으세요.')
        hint.setWordWrap(True); files_layout.addWidget(hint)
        self.file_list = FileListWidget()
        self.file_list.setTextElideMode(Qt.ElideMiddle)
        self.file_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.file_list.files_dropped.connect(self.add_files)
        self.file_list.currentItemChanged.connect(self.update_preview)
        self.file_list.itemSelectionChanged.connect(self.update_count)
        self.file_list.itemDoubleClicked.connect(lambda *_: self.import_tabs.setCurrentIndex(1))
        files_layout.addWidget(self.file_list)
        actions = QHBoxLayout()
        actions.addWidget(self.button('선택 삭제', self.remove_selected))
        actions.addWidget(self.button('목록 비우기', self.clear_files))
        files_layout.addLayout(actions)
        self.import_tabs.addTab(files_page, '파일 목록')
        self.preview = QTextBrowser(); self.preview.setOpenExternalLinks(True)
        self.import_tabs.addTab(self.preview, '선택 파일 미리보기')
        self.only_selected = QCheckBox('선택한 파일만 변환')
        self.only_selected.toggled.connect(self.update_count)
        left.addWidget(self.only_selected)
        self.count_label = QLabel('파일 0개'); left.addWidget(self.count_label)
        self.splitter.addWidget(self.import_panel)

        self.export_panel = QWidget(); right = QVBoxLayout(self.export_panel)
        right.setContentsMargins(14, 0, 0, 0); right.setSpacing(10)
        label = QLabel('2  변환 · 내보내기'); label.setObjectName('sectionLabel'); right.addWidget(label)
        row = QHBoxLayout(); row.addWidget(QLabel('내보내기 유형'))
        self.format_combo = QComboBox()
        self.format_combo.addItem('Word 문서 (.docx)', 'docx')
        self.format_combo.addItem('PowerPoint 발표 (.pptx)', 'pptx')
        row.addWidget(self.format_combo, 1); right.addLayout(row)
        preset_row = QHBoxLayout()
        self.preset_combo = QComboBox(); self.preset_combo.setMinimumWidth(130)
        self.preset_combo.activated.connect(self.load_preset)
        preset_row.addWidget(self.preset_combo, 1)
        preset_row.addWidget(self.button('서식 저장', self.save_preset))
        preset_row.addWidget(self.button('삭제', self.delete_preset))
        right.addLayout(preset_row)
        self.panels = {}; self.settings_stack = QStackedWidget()
        for kind in ('docx', 'pptx'):
            panel = SettingsPanel(is_pptx=kind == 'pptx')
            self.panels[kind] = panel
            scroll = QScrollArea(); scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.NoFrame); scroll.setWidget(panel)
            self.settings_stack.addWidget(scroll)
        right.addWidget(self.settings_stack, 1)
        self.convert_btn = self.button('DOCX로 변환', self.start_conversion, False)
        self.convert_btn.setMinimumHeight(44); right.addWidget(self.convert_btn)
        self.result_label = QLabel('파일을 추가하고 서식을 설정한 뒤 변환하세요.')
        self.result_label.setWordWrap(True); right.addWidget(self.result_label)
        self.open_result_btn = self.button('결과 폴더 열기', self.open_result_folder)
        self.open_result_btn.setEnabled(False); right.addWidget(self.open_result_btn)
        self.splitter.addWidget(self.export_panel); self.splitter.setSizes([470, 650])
        self.format_combo.currentIndexChanged.connect(self.change_format)

        bottom = QHBoxLayout()
        self.log_toggle = QToolButton(); self.log_toggle.setText('작업 로그 보기')
        self.log_toggle.setCheckable(True); bottom.addWidget(self.log_toggle)
        bottom.addStretch()
        bottom.addWidget(self.button('DOCX → Markdown 도구', self.open_reverse_tool))
        layout.addLayout(bottom)
        self.console = QTextEdit(); self.console.setReadOnly(True)
        self.console.document().setMaximumBlockCount(1500)
        self.console.setMaximumHeight(130); self.console.hide()
        self.log_toggle.toggled.connect(self.console.setVisible)
        layout.addWidget(self.console)
        self.statusBar().showMessage('서식과 설정은 다음 실행에서도 유지됩니다.')
        self.statusBar().setToolTip(f'설정 저장 위치: {self.settings.fileName()}')

    def load_settings(self):
        for kind, panel in self.panels.items():
            panel.load_settings(self.settings, prefix=f'{kind}_')
        self.format_combo.setCurrentIndex(1 if self.settings.value('export_format', 'docx') == 'pptx' else 0)
        self.change_format()

    def save_settings(self):
        for kind, panel in self.panels.items():
            panel.save_settings(self.settings, prefix=f'{kind}_')
        self.settings.setValue('export_format', self.current_format)
        self.settings.setValue('import_dir', self.import_dir)
        self.settings.sync()
        if self.settings.status() != QSettings.Status.NoError:
            self.log('설정을 저장하지 못했습니다. 설정 파일의 쓰기 권한을 확인하세요.')

    def change_format(self, *_):
        self.settings_stack.setCurrentIndex(self.format_combo.currentIndex())
        self.convert_btn.setText(f'{self.current_format.upper()}로 변환')
        self.refresh_presets()

    def preset_key(self):
        return f'presets/{self.current_format}'

    def presets(self):
        try:
            value = json.loads(self.settings.value(self.preset_key(), '{}'))
            return value if isinstance(value, dict) else {}
        except (TypeError, ValueError):
            return {}

    def refresh_presets(self):
        self.preset_combo.clear(); self.preset_combo.addItem('저장한 서식 선택', None)
        for name in sorted(self.presets()):
            self.preset_combo.addItem(name, name)

    def save_preset(self):
        name, ok = QInputDialog.getText(self, '서식 저장', '서식 이름 (예: 보성론 강의)')
        if not ok or not name.strip():
            return
        name = name.strip(); presets = self.presets()
        if name in presets and QMessageBox.question(self, '서식 저장', f'“{name}” 서식을 갱신할까요?') != QMessageBox.Yes:
            return
        config = self.settings_panel.get_config_dict()
        presets[name] = {k: v for k, v in config.items() if k not in ('output_dir', 'save_to_original', 'open_after_conversion')}
        self.settings.setValue(self.preset_key(), json.dumps(presets, ensure_ascii=False))
        self.save_settings(); self.refresh_presets()
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(name))
        self.log(f'{self.current_format.upper()} 서식 저장: {name}')

    def load_preset(self, *_):
        name = self.preset_combo.currentData()
        if name in self.presets():
            self.settings_panel.apply_config(self.presets()[name])
            self.log(f'서식 적용: {name}')

    def delete_preset(self):
        name = self.preset_combo.currentData(); presets = self.presets()
        if name not in presets:
            return
        if QMessageBox.question(self, '서식 삭제', f'“{name}” 서식을 삭제할까요?') == QMessageBox.Yes:
            del presets[name]
            self.settings.setValue(self.preset_key(), json.dumps(presets, ensure_ascii=False))
            self.settings.sync(); self.refresh_presets()

    def log(self, message):
        self.console.append(message)

    def check_pandoc(self):
        self.pandoc_manager.refresh()
        installed = self.pandoc_manager.is_installed()
        version = self.pandoc_manager.get_version() if installed else ''
        self.status_label.setText(f'Pandoc {version}' if installed else 'Pandoc 없음')
        self.status_label.setToolTip(self.pandoc_manager.pandoc_path or 'Pandoc 설치/업데이트를 눌러 준비하세요.')
        self.status_label.setObjectName('statusReady' if installed else 'statusMissing')
        self.status_label.style().unpolish(self.status_label); self.status_label.style().polish(self.status_label)

    def check_and_install_pandoc(self):
        if self.worker or self.pandoc_worker:
            return
        message = '앱 폴더에 포터블 Pandoc을 다운로드합니다. 시스템 설치 없이 사용할 수 있습니다. 계속할까요?'
        if QMessageBox.question(self, 'Pandoc 설치/업데이트', message) != QMessageBox.Yes:
            return
        self.set_busy(True)
        self.status_label.setText('Pandoc 준비 중…')
        self.pandoc_worker = PandocSetupWorker(self.pandoc_manager)
        self.pandoc_worker.progress.connect(self.log)
        self.pandoc_worker.completed.connect(self.on_pandoc_setup_finished)
        self.pandoc_worker.failed.connect(self.on_pandoc_setup_error)
        self.pandoc_worker.finished.connect(self.release_pandoc_worker)
        self.pandoc_worker.start()

    def on_pandoc_setup_finished(self, path):
        self.log(f'Pandoc 준비 완료: {path}'); self.check_pandoc()
        self.result_label.setText('Pandoc 준비가 완료되었습니다.')

    def on_pandoc_setup_error(self, message):
        self.log(f'Pandoc 오류: {message}'); self.log_toggle.setChecked(True)
        self.check_pandoc(); QMessageBox.critical(self, 'Pandoc 오류', message)

    def release_pandoc_worker(self):
        self.pandoc_worker.deleteLater(); self.pandoc_worker = None; self.set_busy(False)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Markdown 파일 선택', self.import_dir, 'Markdown (*.md)')
        if files:
            self.import_dir = str(Path(files[0]).parent); self.add_files(files)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Markdown 폴더 선택', self.import_dir)
        if folder:
            self.import_dir = folder; self.add_files([folder])

    def add_files(self, paths):
        known = {os.path.normcase(p) for p in self.files_to_convert}; added = 0
        candidates = []
        for path in paths:
            path = Path(path)
            if path.is_dir():
                for directory, folders, names in os.walk(path, followlinks=False):
                    folders[:] = sorted(f for f in folders if f not in ('.obsidian', '.git', '.trash', '.venv', 'node_modules'))
                    candidates.extend(Path(directory)/name for name in sorted(names) if name.lower().endswith('.md'))
            else:
                candidates.append(path)
        for path in candidates:
            if not path.is_file() or path.suffix.lower() != '.md':
                continue
            absolute = str(path.resolve()); key = os.path.normcase(absolute)
            if key in known:
                continue
            known.add(key); self.files_to_convert.append(absolute)
            item = QListWidgetItem(f'{path.name}\n{path.resolve().parent}')
            item.setData(Qt.UserRole, absolute); item.setToolTip(absolute)
            self.file_list.addItem(item); added += 1
        if self.file_list.currentRow() < 0 and self.file_list.count():
            self.file_list.setCurrentRow(0)
        self.update_count(); self.log(f'Markdown {added}개 추가 · 전체 {len(self.files_to_convert)}개')

    def remove_selected(self):
        for item in list(self.file_list.selectedItems()):
            self.files_to_convert.remove(item.data(Qt.UserRole))
            self.file_list.takeItem(self.file_list.row(item))
        self.update_count(); self.update_preview()

    def clear_files(self):
        self.files_to_convert.clear(); self.file_list.clear()
        self.preview.clear(); self.update_count()

    def update_count(self, *_):
        count = len(self.file_list.selectedItems()) if self.only_selected.isChecked() else len(self.files_to_convert)
        self.count_label.setText(f'전체 {len(self.files_to_convert)}개 · 이번에 변환할 파일 {count}개')

    def update_preview(self, *_):
        item = self.file_list.currentItem()
        if item is None:
            self.preview.clear(); return
        path = Path(item.data(Qt.UserRole))
        try:
            # Preview is deliberately bounded; conversion reads the full file.
            with path.open(encoding='utf-8-sig') as stream:
                content = stream.read(300_000)
            self.preview.document().setBaseUrl(QUrl.fromLocalFile(str(path.parent) + os.sep))
            self.preview.setMarkdown(content)
        except Exception as error:
            self.preview.setPlainText(f'미리보기 실패: {error}')

    def set_busy(self, busy):
        self.import_panel.setEnabled(not busy); self.export_panel.setEnabled(not busy)
        self.check_pandoc_btn.setEnabled(not busy); self.refresh_pandoc_btn.setEnabled(not busy)

    def start_conversion(self):
        if self.worker or self.pandoc_worker:
            return
        files = [item.data(Qt.UserRole) for item in self.file_list.selectedItems()] if self.only_selected.isChecked() else list(self.files_to_convert)
        if not files:
            QMessageBox.warning(self, '파일 없음', '변환할 Markdown 파일을 추가하거나 선택해 주세요.'); return
        self.pandoc_manager.refresh()
        if not self.pandoc_manager.is_installed():
            QMessageBox.warning(self, 'Pandoc 없음', 'Pandoc 설치/업데이트를 눌러 먼저 준비해 주세요.'); return
        config = self.settings_panel.get_config_dict()
        installed = {f.casefold() for f in QFontDatabase.families()}
        missing = [config[key] for key in ('font_ascii', 'font_korean', 'font_tibetan') if config[key].casefold() not in installed]
        if missing:
            self.log('설치되지 않은 글꼴은 결과를 여는 프로그램에서 대체될 수 있습니다: ' + ', '.join(missing))
            self.log_toggle.setChecked(True)
        self.save_settings()
        self.current_conversion_config = config
        self.last_results = []; self.open_result_btn.setEnabled(False)
        self.result_label.setText(f'{self.current_format.upper()} 변환 중 · {len(files)}개')
        self.set_busy(True)
        self.worker = ConversionWorker(self.converters[self.current_format], files, config['output_dir'], config)
        self.worker.progress.connect(self.log); self.worker.completed.connect(self.on_conversion_finished)
        self.worker.failed.connect(self.on_conversion_error)
        self.worker.finished.connect(self.release_worker)
        self.worker.start()

    def on_conversion_finished(self, results, errors, warnings):
        self.last_results = results; self.open_result_btn.setEnabled(bool(results))
        message = f'완료 · 성공 {len(results)}개 · 실패 {len(errors)}개'
        if warnings:
            message += f' · 주의 {len(warnings)}개'
        self.result_label.setText(message); self.log(message)
        if errors or warnings:
            self.log_toggle.setChecked(True)
        if self.current_conversion_config.get('open_after_conversion'):
            for path in results:
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def on_conversion_error(self, message):
        self.result_label.setText('변환 실패 · 작업 로그를 확인해 주세요.')
        self.log(message); self.log_toggle.setChecked(True)

    def release_worker(self):
        self.worker.deleteLater(); self.worker = None; self.set_busy(False)

    def open_result_folder(self):
        for folder in dict.fromkeys(str(Path(p).parent) for p in self.last_results):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def open_reverse_tool(self):
        if self.worker or self.pandoc_worker:
            return
        from .docx_to_md_tab import DocxToMdTab
        class ToolDialog(QDialog):
            def reject(dialog):
                if getattr(tool, 'worker', None) is None:
                    super().reject()
                else:
                    self.log('Markdown 변환 완료 후 도구 창을 닫을 수 있습니다.')

            def closeEvent(dialog, event):
                if getattr(tool, 'worker', None) is not None:
                    event.ignore()
                else:
                    event.accept()

        dialog = ToolDialog(self); dialog.setWindowTitle('DOCX → Markdown'); dialog.resize(900, 600)
        content = QVBoxLayout(dialog)
        tool = DocxToMdTab(self.pandoc_manager, settings=self.settings)
        tool.log_message.connect(self.log); content.addWidget(tool)
        dialog.exec()
        tool.save_settings()

    def closeEvent(self, event):
        if self.worker or self.pandoc_worker:
            self.result_label.setText('진행 중인 작업이 완료된 뒤 앱을 닫아 주세요.')
            event.ignore(); return
        self.save_settings(); event.accept()
