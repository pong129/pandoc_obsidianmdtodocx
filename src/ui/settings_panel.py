import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QFontComboBox,
    QGroupBox, QLineEdit, QPushButton, QFileDialog, QTabWidget, QGridLayout,
    QSizePolicy, QFrame
)
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator, QFont


class NumberStepper(QWidget):
    def __init__(self, value=0, minimum=0, maximum=100, step=1, decimals=0, parent=None):
        super().__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.step = step
        self.decimals = decimals
        self._value = value

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        self.minus_btn = QPushButton("-")
        self.minus_btn.setObjectName("stepperButton")
        self.minus_btn.setToolTip("값 줄이기")
        self.minus_btn.clicked.connect(lambda: self.setValue(self._value - self.step))

        self.value_edit = QLineEdit()
        self.value_edit.setObjectName("stepperValue")
        self.value_edit.setAlignment(Qt.AlignCenter)
        self.value_edit.setFixedWidth(48 if decimals else 42)
        if decimals:
            validator = QDoubleValidator(float(minimum), float(maximum), decimals, self)
        else:
            validator = QIntValidator(int(minimum), int(maximum), self)
        self.value_edit.setValidator(validator)
        self.value_edit.editingFinished.connect(self._commit_text)

        self.plus_btn = QPushButton("+")
        self.plus_btn.setObjectName("stepperButton")
        self.plus_btn.setToolTip("값 늘리기")
        self.plus_btn.clicked.connect(lambda: self.setValue(self._value + self.step))

        layout.addWidget(self.minus_btn)
        layout.addWidget(self.value_edit)
        layout.addWidget(self.plus_btn)
        self.setFixedWidth(104 if decimals else 98)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setValue(value)

    def value(self):
        return round(self._value, self.decimals) if self.decimals else int(self._value)

    def setValue(self, value):
        value = max(self.minimum, min(self.maximum, value))
        if not self.decimals:
            value = int(round(value))
        self._value = value
        self.value_edit.setText(self._format_value(value))

    def setRange(self, minimum, maximum):
        self.minimum = minimum
        self.maximum = maximum
        self.setValue(self._value)

    def setSingleStep(self, step):
        self.step = step

    def _format_value(self, value):
        if self.decimals:
            return f"{value:.{self.decimals}f}"
        return str(int(value))

    def _commit_text(self):
        text = self.value_edit.text().strip()
        if not text:
            self.setValue(self._value)
            return
        try:
            self.setValue(float(text) if self.decimals else int(text))
        except ValueError:
            self.setValue(self._value)

class SettingsPanel(QTabWidget):
    """
    A unified, reusable UI component that houses settings for 
    Fonts, Layout/Spacing, and Output directories.
    Can be loaded directly into Main Window (DOCX) and PPTX Tab.
    """
    def __init__(self, parent=None, is_pptx=False):
        super().__init__(parent)
        self.is_pptx = is_pptx
        self.init_ui()

    def init_ui(self):
        # Tab 1: Fonts & Sizes
        font_tab = QWidget()
        font_layout = QVBoxLayout(font_tab)
        font_layout.setContentsMargins(8, 8, 8, 8)
        font_layout.setSpacing(6)
        
        # Font Selection
        self.font_ascii = QFontComboBox()
        self.font_ascii.setEditable(True)
        self.font_ascii.setMinimumWidth(180)
        self.font_ascii.setCurrentFont("Arial")
        
        self.font_korean = QFontComboBox()
        self.font_korean.setEditable(True)
        self.font_korean.setMinimumWidth(180)
        self.font_korean.setCurrentFont("Malgun Gothic")
        
        self.font_tibetan = QFontComboBox() 
        self.font_tibetan.setEditable(True)
        self.font_tibetan.setMinimumWidth(180)
        self.font_tibetan.setCurrentFont("Microsoft Himalaya") 
        
        # Font Sizes
        self.size_body = self._create_spinbox(11)
        
        self.size_h1 = self._create_spinbox(24)
        self.size_h2 = self._create_spinbox(18)
        self.size_h3 = self._create_spinbox(14)
        self.size_h4 = self._create_spinbox(12)
        self.size_h5 = self._create_spinbox(11)
        self.size_h6 = self._create_spinbox(11)
        
        self.size_footnote = self._create_spinbox(9)
        self.size_east_asia = self._create_spinbox(11)
        self.size_cs = self._create_spinbox(12)

        font_group = QGroupBox("글꼴")
        font_form = QFormLayout(font_group)
        font_form.setContentsMargins(0, 8, 0, 0)
        font_form.setHorizontalSpacing(8)
        font_form.setVerticalSpacing(4)
        font_form.addRow("영문/ASCII:", self.font_ascii)
        font_form.addRow("한국어:", self.font_korean)
        font_form.addRow("티베트어:", self.font_tibetan)
        font_layout.addWidget(font_group)

        size_group = QGroupBox("기본 크기")
        size_grid = QGridLayout(size_group)
        size_grid.setContentsMargins(0, 8, 0, 0)
        size_grid.setHorizontalSpacing(6)
        size_grid.setVerticalSpacing(4)
        size_grid.addWidget(self._compact_field("본문", self.size_body), 0, 0)
        size_grid.addWidget(self._compact_field("티베트어", self.size_cs), 0, 1)
        size_grid.addWidget(self._compact_field("한국어", self.size_east_asia), 1, 0)
        if not self.is_pptx:
            size_grid.addWidget(self._compact_field("각주", self.size_footnote), 1, 1)
        size_grid.setColumnStretch(0, 1)
        size_grid.setColumnStretch(1, 1)
        font_layout.addWidget(size_group)
        hint = QLabel("제목·각주의 한국어와 티베트어 크기도 본문 크기의 비율에 맞춰 적용합니다.")
        hint.setWordWrap(True)
        font_layout.addWidget(hint)

        heading_group = QGroupBox("제목 크기")
        heading_layout = QGridLayout(heading_group)
        heading_layout.setContentsMargins(0, 8, 0, 0)
        heading_layout.setHorizontalSpacing(6)
        heading_layout.setVerticalSpacing(4)
        heading_controls = [
            ("제목 1", self.size_h1), ("제목 2", self.size_h2), ("제목 3", self.size_h3),
            ("제목 4", self.size_h4), ("제목 5", self.size_h5), ("제목 6", self.size_h6),
        ]
        for index, (label, control) in enumerate(heading_controls):
            row = index // 3
            col = index % 3
            heading_layout.addWidget(self._compact_field(label, control), row, col)
        heading_layout.setColumnStretch(0, 1)
        heading_layout.setColumnStretch(1, 1)
        heading_layout.setColumnStretch(2, 1)
        font_layout.addWidget(heading_group)
        font_layout.addStretch()
        self.addTab(font_tab, "글꼴")
        
        # Tab 2: Paragraph & Layout
        layout_tab = QWidget()
        layout_vbox = QVBoxLayout(layout_tab)
        layout_vbox.setContentsMargins(8, 8, 8, 8)
        layout_vbox.setSpacing(6)
        layout_group = QGroupBox("문단")
        layout_layout = QGridLayout(layout_group)
        layout_layout.setContentsMargins(0, 8, 0, 0)
        layout_layout.setHorizontalSpacing(6)
        layout_layout.setVerticalSpacing(4)
        
        self.preserve_breaks = QCheckBox("줄바꿈 유지"); self.preserve_breaks.setChecked(True)
        if self.is_pptx:
            self.slide_level = QComboBox()
            for level in (1, 2, 3):
                self.slide_level.addItem(f'제목 {level} ({"#" * level})에서 새 슬라이드', level)
            self.slide_level.setCurrentIndex(1)
            layout_layout.addWidget(self.slide_level, 1, 0, 1, 2)
            self.auto_paginate = QCheckBox('내용이 넘치면 다음 슬라이드로 자동 분할')
            self.auto_paginate.setChecked(True)
            layout_layout.addWidget(self.auto_paginate, 2, 0, 1, 2)
            tip = QLabel('티베트어 원문과 한국어 번역을 함께 넘깁니다. 한 묶음이 한 장보다 길면 알립니다. *** 수동 구분도 유지합니다.')
            tip.setWordWrap(True)
            layout_layout.addWidget(tip, 3, 0, 1, 2)
        
        if not self.is_pptx:
            self.spacing_body = self._create_double_spinbox(1.2)
            self.spacing_header = self._create_double_spinbox(1.2)
            self.add_empty_line = QCheckBox("문단 사이에 빈 줄 추가"); self.add_empty_line.setChecked(False)
            
            layout_layout.addWidget(self._compact_field("본문 줄 간격", self.spacing_body), 0, 0)
            layout_layout.addWidget(self._compact_field("제목 줄 간격", self.spacing_header), 0, 1)
            layout_layout.addWidget(self.add_empty_line, 1, 0, 1, 2)
            
        layout_layout.addWidget(self.preserve_breaks, 2 if not self.is_pptx else 0, 0, 1, 2)
        layout_layout.setColumnStretch(0, 1)
        layout_layout.setColumnStretch(1, 1)
        layout_vbox.addWidget(layout_group)
        
        # Title Options
        title_group = QGroupBox("문서 제목")
        title_layout = QGridLayout(title_group)
        title_layout.setContentsMargins(0, 8, 0, 0)
        title_layout.setHorizontalSpacing(6)
        title_layout.setVerticalSpacing(4)
        self.insert_title = QCheckBox("파일 이름을 제목으로 넣기"); self.insert_title.setChecked(True)
        if not self.is_pptx:
            self.title_align = QComboBox(); self.title_align.addItems(["왼쪽", "가운데", "오른쪽"]); self.title_align.setCurrentText("가운데")
            self.title_align.setFixedWidth(110)
        self.title_size = self._create_spinbox(24)
        
        title_layout.addWidget(self.insert_title, 0, 0, 1, 2)
        if not self.is_pptx:
            title_layout.addWidget(self._compact_field("정렬", self.title_align), 1, 0)
            title_layout.addWidget(self._compact_field("크기", self.title_size), 1, 1)
        else:
            title_layout.addWidget(self._compact_field("크기", self.title_size), 1, 0)
        title_layout.setColumnStretch(0, 1)
        title_layout.setColumnStretch(1, 1)
        layout_vbox.addWidget(title_group)
        layout_vbox.addStretch()
        self.addTab(layout_tab, "레이아웃")
        
        # Tab 3: Output Settings
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        output_layout.setContentsMargins(8, 8, 8, 8)
        output_layout.setSpacing(6)
        output_group = QGroupBox("저장 위치")
        output_form = QFormLayout(output_group)
        output_form.setContentsMargins(0, 8, 0, 0)
        output_form.setHorizontalSpacing(8)
        output_form.setVerticalSpacing(4)
        self.save_to_original_chk = QCheckBox("원본 파일과 같은 폴더에 저장")
        self.save_to_original_chk.setChecked(True)
        self.save_to_original_chk.stateChanged.connect(self.toggle_output_dir)
        self.open_after_conversion_chk = QCheckBox("변환 완료 후 결과 파일 열기")
        self.open_after_conversion_chk.setChecked(False)
        self.output_dir_edit = QLineEdit(os.getcwd())
        output_btn = QPushButton("찾아보기")
        output_btn.setFixedWidth(92)
        output_btn.clicked.connect(self.browse_output)
        self.output_dir_btn = output_btn
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_dir_edit)
        output_row.addWidget(output_btn)
        output_form.addRow("", self.save_to_original_chk)
        output_form.addRow("", self.open_after_conversion_chk)
        output_form.addRow("저장 폴더:", output_row)
        self.toggle_output_dir(self.save_to_original_chk.checkState().value)
        output_layout.addWidget(output_group)
        output_layout.addStretch()
        self.addTab(output_tab, "저장")

    def _create_spinbox(self, value: int) -> QSpinBox:
        return NumberStepper(value=value, minimum=1, maximum=100, step=1)

    def _create_double_spinbox(self, value: float) -> QDoubleSpinBox:
        return NumberStepper(value=value, minimum=0.5, maximum=5.0, step=0.1, decimals=1)

    def _compact_field(self, label: str, control: QWidget) -> QWidget:
        field = QFrame()
        field.setFrameShape(QFrame.NoFrame)
        row = QHBoxLayout(field)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(5)
        label_widget = QLabel(f"{label}:")
        row.addWidget(label_widget)
        row.addStretch()
        row.addWidget(control)
        return field

    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if directory:
            self.output_dir_edit.setText(directory)

    def toggle_output_dir(self, state):
        enabled = state != Qt.Checked.value
        self.output_dir_edit.setEnabled(enabled)
        self.output_dir_btn.setEnabled(enabled)

    def load_settings(self, settings: QSettings, prefix: str = ""):
        # Load fonts
        self.font_ascii.setCurrentFont(QFont(settings.value(f"{prefix}font_ascii", "Arial")))
        self.font_korean.setCurrentFont(QFont(settings.value(f"{prefix}font_korean", "Malgun Gothic")))
        self.font_tibetan.setCurrentFont(QFont(settings.value(f"{prefix}font_tibetan", "Microsoft Himalaya")))
        
        # Load sizes
        self.size_body.setValue(int(settings.value(f"{prefix}size_body", 11 if not self.is_pptx else 20)))
        self.size_h1.setValue(int(settings.value(f"{prefix}size_h1", 24 if not self.is_pptx else 44)))
        self.size_h2.setValue(int(settings.value(f"{prefix}size_h2", 18 if not self.is_pptx else 32)))
        self.size_h3.setValue(int(settings.value(f"{prefix}size_h3", 14 if not self.is_pptx else 28)))
        self.size_h4.setValue(int(settings.value(f"{prefix}size_h4", 12 if not self.is_pptx else 24)))
        self.size_h5.setValue(int(settings.value(f"{prefix}size_h5", 11 if not self.is_pptx else 20)))
        self.size_h6.setValue(int(settings.value(f"{prefix}size_h6", 11 if not self.is_pptx else 20)))
        
        self.size_east_asia.setValue(int(settings.value(f"{prefix}size_east_asia", 18 if self.is_pptx else 11)))
        self.size_cs.setValue(int(settings.value(f"{prefix}size_cs", 20 if self.is_pptx else 18)))
        if self.is_pptx:
            self.slide_level.setCurrentIndex(max(0, min(2, int(settings.value(f'{prefix}slide_level', 2)) - 1)))
            self.auto_paginate.setChecked(settings.value(f'{prefix}auto_paginate', True, type=bool))
        if not self.is_pptx:
            self.size_footnote.setValue(int(settings.value(f"{prefix}size_footnote", 9)))
            
            # Load spacing
            self.spacing_body.setValue(float(settings.value(f"{prefix}spacing_body", 1.2)))
            self.spacing_header.setValue(float(settings.value(f"{prefix}spacing_header", 1.2)))
            self.add_empty_line.setChecked(settings.value(f"{prefix}add_empty_line", False, type=bool))
            saved_align = settings.value(f"{prefix}title_align", "center")
            align_map = {"left": "왼쪽", "center": "가운데", "right": "오른쪽", "Left": "왼쪽", "Center": "가운데", "Right": "오른쪽"}
            self.title_align.setCurrentText(align_map.get(saved_align, saved_align))

        self.preserve_breaks.setChecked(settings.value(f"{prefix}preserve_breaks", not self.is_pptx, type=bool))

        # Load title
        self.insert_title.setChecked(settings.value(f"{prefix}insert_title", True, type=bool))
        self.title_size.setValue(int(settings.value(f"{prefix}title_size", 24 if not self.is_pptx else 44)))
        
        # Load output dir
        self.save_to_original_chk.setChecked(settings.value(f"{prefix}save_to_original", True, type=bool))
        self.open_after_conversion_chk.setChecked(settings.value(f"{prefix}open_after_conversion", False, type=bool))
        out_dir = settings.value(f"{prefix}output_dir", os.getcwd())
        if out_dir:
            self.output_dir_edit.setText(out_dir)
        self.toggle_output_dir(self.save_to_original_chk.checkState().value)

    def save_settings(self, settings: QSettings, prefix: str = ""):
        settings.setValue(f'{prefix}size_east_asia', self.size_east_asia.value())
        settings.setValue(f'{prefix}size_cs', self.size_cs.value())
        if self.is_pptx:
            settings.setValue(f'{prefix}slide_level', self.slide_level.currentData())
            settings.setValue(f'{prefix}auto_paginate', self.auto_paginate.isChecked())
        settings.setValue(f"{prefix}font_ascii", self.font_ascii.currentFont().family())
        settings.setValue(f"{prefix}font_korean", self.font_korean.currentFont().family())
        settings.setValue(f"{prefix}font_tibetan", self.font_tibetan.currentFont().family())
        
        settings.setValue(f"{prefix}size_body", self.size_body.value())
        settings.setValue(f"{prefix}size_h1", self.size_h1.value())
        settings.setValue(f"{prefix}size_h2", self.size_h2.value())
        settings.setValue(f"{prefix}size_h3", self.size_h3.value())
        settings.setValue(f"{prefix}size_h4", self.size_h4.value())
        settings.setValue(f"{prefix}size_h5", self.size_h5.value())
        settings.setValue(f"{prefix}size_h6", self.size_h6.value())
        
        if not self.is_pptx:
            settings.setValue(f"{prefix}size_footnote", self.size_footnote.value())
            settings.setValue(f"{prefix}size_east_asia", self.size_east_asia.value())
            settings.setValue(f"{prefix}size_cs", self.size_cs.value())
            settings.setValue(f"{prefix}spacing_body", self.spacing_body.value())
            settings.setValue(f"{prefix}spacing_header", self.spacing_header.value())
            settings.setValue(f"{prefix}add_empty_line", self.add_empty_line.isChecked())
            settings.setValue(f"{prefix}title_align", self._title_align_value())

        settings.setValue(f"{prefix}preserve_breaks", self.preserve_breaks.isChecked())
            
        settings.setValue(f"{prefix}insert_title", self.insert_title.isChecked())
        settings.setValue(f"{prefix}title_size", self.title_size.value())
        settings.setValue(f"{prefix}save_to_original", self.save_to_original_chk.isChecked())
        settings.setValue(f"{prefix}open_after_conversion", self.open_after_conversion_chk.isChecked())
        settings.setValue(f"{prefix}output_dir", self.output_dir_edit.text())

    def get_config_dict(self) -> dict:
        config = {
            'size_east_asia': self.size_east_asia.value(),
            'size_cs': self.size_cs.value(),
            'font_ascii': self.font_ascii.currentFont().family(),
            'font_korean': self.font_korean.currentFont().family(),
            'font_tibetan': self.font_tibetan.currentFont().family(),
            'size_body': self.size_body.value(),
            'size_h1': self.size_h1.value(),
            'size_h2': self.size_h2.value(),
            'size_h3': self.size_h3.value(),
            'size_h4': self.size_h4.value(),
            'size_h5': self.size_h5.value(),
            'size_h6': self.size_h6.value(),
            'insert_title': self.insert_title.isChecked(),
            'title_size': self.title_size.value(),
            'preserve_breaks': self.preserve_breaks.isChecked(),
            'save_to_original': self.save_to_original_chk.isChecked(),
            'open_after_conversion': self.open_after_conversion_chk.isChecked(),
            'output_dir': self.output_dir_edit.text()
        }
        if self.is_pptx:
            config['slide_level'] = self.slide_level.currentData()
            config['auto_paginate'] = self.auto_paginate.isChecked()
        
        if not self.is_pptx:
            config.update({
                'size_footnote': self.size_footnote.value(),
                'size_east_asia': self.size_east_asia.value(),
                'size_cs': self.size_cs.value(),
                'spacing_body': self.spacing_body.value(),
                'spacing_header': self.spacing_header.value(),
                'add_empty_line': self.add_empty_line.isChecked(),
                'title_align': self._title_align_value(),
            })
            
        return config

    def apply_config(self, config):
        values = self.get_config_dict()
        values.update(config)

        class Values:
            def value(self, key, default=None, type=None):
                value = values.get(key, default)
                return type(value) if type else value

        self.load_settings(Values())

    def _title_align_value(self) -> str:
        return {
            "왼쪽": "left",
            "가운데": "center",
            "오른쪽": "right",
        }.get(self.title_align.currentText(), self.title_align.currentText().lower())
