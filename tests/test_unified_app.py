"""Regression tests for the real converters and the shared export screen."""
import json
import os
from pathlib import Path
import shutil
import time
import zipfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from lxml import etree as ET
import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QInputDialog, QMessageBox
from src.core.converter import Converter
from src.core.pptx_converter import PptxConverter
from src.core.docx_to_md_converter import DocxToMdConverter
from src.core.pandoc_manager import PandocManager
from src.core.typography import W, A, is_tibetan, is_east_asian
from src.ui.main_window import MainWindow

ROOT = Path(__file__).resolve().parents[1]
CONFIG = {
    'size_body': 12, 'size_east_asia': 15, 'size_cs': 24,
    'size_h1': 30, 'size_h2': 24, 'size_h3': 20, 'size_footnote': 9,
    'font_ascii': 'Arial', 'font_korean': 'Malgun Gothic',
    'font_tibetan': 'Microsoft Himalaya', 'insert_title': False,
    'save_to_original': True, 'preserve_breaks': False, 'slide_level': 2,
}


@pytest.fixture(scope='module')
def app():
    application = QApplication.instance() or QApplication([])
    # Windows' headless Qt plugin does not enumerate system fonts itself.
    for name in ('malgun.ttf', 'arial.ttf', 'himalaya.ttf'):
        QFontDatabase.addApplicationFont(f'C:/Windows/Fonts/{name}')
    return application


@pytest.fixture
def window(app, tmp_path):
    settings = QSettings(str(tmp_path/'settings.ini'), QSettings.IniFormat)
    w = MainWindow(settings=settings)
    yield w
    if w.worker:
        w.worker.wait(10000)
        app.processEvents()
    w.close()


def xml_parts(path):
    with zipfile.ZipFile(path) as archive:
        return {n: ET.fromstring(archive.read(n)) for n in archive.namelist()
                if n.endswith('.xml')}


def text_runs(tree, ns):
    for r in tree.iter(f'{{{ns}}}r'):
        text = ''.join(t.text or '' for t in r.findall(f'{{{ns}}}t'))
        if text:
            yield r, text


def assert_run(r, text, ns, normal, config=CONFIG):
    props = r.find(f'{{{ns}}}rPr')
    tibetan = all(is_tibetan(c) for c in text)
    if any(is_tibetan(c) for c in text):
        assert tibetan, f'Mixed Tibetan/non-Tibetan run: {text}'
    size = normal * (config['size_cs'] / config['size_body'] if tibetan else
                     config['size_east_asia'] / config['size_body'] if is_east_asian(text[0]) else 1)
    if ns == W:
        fonts = props.find(f'{{{W}}}rFonts')
        assert fonts.get(f'{{{W}}}ascii') == (config['font_tibetan'] if tibetan else config['font_ascii'])
        assert fonts.get(f'{{{W}}}eastAsia') == (config['font_tibetan'] if tibetan else config['font_korean'])
        assert int(props.find(f'{{{W}}}sz').get(f'{{{W}}}val')) == round(size * 2)
        assert int(props.find(f'{{{W}}}szCs').get(f'{{{W}}}val')) == round(size * 2)
    else:
        assert props.find(f'{{{A}}}latin').get('typeface') == (config['font_tibetan'] if tibetan else config['font_ascii'])
        assert props.find(f'{{{A}}}ea').get('typeface') == (config['font_tibetan'] if tibetan else config['font_korean'])
        assert props.find(f'{{{A}}}cs').get('typeface') == config['font_tibetan']
        assert int(props.get('sz')) == round(size * 100)


@pytest.mark.parametrize('kind,cls', [('docx', Converter), ('pptx', PptxConverter)])
def test_real_converter_mixed_languages_headers_table_and_notes(tmp_path, kind, cls):
    source = tmp_path/'mixed.md'
    source.write_text('## 한글བོད་Title\n\n한국어ABCབོད་ཡིག་DEF\n\n'
                      '**한글Boldབོད་**와 *기울임སྐྱེས་*\n\n'
                      '[링크ABCཆོས་](https://example.com) 각주[^1]\n\n'
                      '| 한글 | ABCབོད་ |\n|---|---|\n| 한국어 | སྐྱེས་བུ། |\n\n'
                      '[^1]: 각주Englishབོད་\n', encoding='utf-8')
    converter = cls(PandocManager())
    results = converter.convert([str(source)], str(tmp_path), CONFIG)
    assert len(results) == 1 and not converter.last_errors
    parts = xml_parts(results[0]); ns = W if kind == 'docx' else A
    checked = 0
    for name, tree in parts.items():
        if not (name.startswith('word/') if kind == 'docx' else name.startswith('ppt/slides/slide')):
            continue
        for paragraph in tree.iter(f'{{{ns}}}p'):
            text = ''.join(t.text or '' for t in paragraph.iter(f'{{{ns}}}t'))
            assert '{{H' not in text
            heading = 'Title' in text
            normal = 24 if heading else 9 if 'footnotes' in name else 12
            # Pandoc's generated Notes slide has a regular title placeholder.
            if kind == 'pptx' and text == 'Notes':
                normal = 32  # production default title size for PPTX
            for r, text in text_runs(paragraph, ns):
                assert_run(r, text, ns, normal)
                checked += 1
    assert checked > 20


@pytest.mark.parametrize('cls', [Converter, PptxConverter])
def test_no_overwrite_and_relative_image_resource_path(tmp_path, cls):
    nested = tmp_path/'한글 폴더'; nested.mkdir()
    shutil.copy2(ROOT/'tests'/'fixtures'/'test_image.png', nested/'그림.png')
    source = nested/'input.md'; source.write_text('## 제목\n\n![image](그림.png)\n', encoding='utf-8')
    converter = cls(PandocManager()); suffix = converter.target_format
    original = nested/f'input.{suffix}'; original.write_bytes(b'KEEP ORIGINAL')
    results = converter.convert([str(source)], str(tmp_path), CONFIG)
    assert not converter.last_errors and not converter.last_warnings
    assert Path(results[0]).name == f'input (2).{suffix}'
    assert original.read_bytes() == b'KEEP ORIGINAL'
    with zipfile.ZipFile(results[0]) as package:
        assert any('/media/' in n for n in package.namelist())


def test_postprocessing_failure_is_not_counted_as_success(tmp_path, monkeypatch):
    source = tmp_path/'input.md'; source.write_text('ABCབོད་', encoding='utf-8')
    converter = PptxConverter(PandocManager())
    def fail(*_):
        raise RuntimeError('forced formatting failure')
    monkeypatch.setattr(converter, 'postprocess_file', fail)
    assert converter.convert([str(source)], str(tmp_path), CONFIG) == []
    assert len(converter.last_errors) == 1
    assert not list(tmp_path.glob('*.pptx'))


def test_batch_continues_after_missing_input(tmp_path):
    source = tmp_path/'valid.md'; source.write_text('한국어བོད་', encoding='utf-8')
    converter = Converter(PandocManager())
    results = converter.convert([str(tmp_path/'missing.md'), str(source)], str(tmp_path), CONFIG)
    assert len(results) == 1 and len(converter.last_errors) == 1


def test_reverse_conversion_does_not_replace_markdown_source(tmp_path):
    from docx import Document
    doc = Document(); doc.add_paragraph('한국어ABCབོད་')
    source = tmp_path/'original.docx'; doc.save(source)
    md = tmp_path/'original.md'; md.write_text('ORIGINAL MARKDOWN', encoding='utf-8')
    converter = DocxToMdConverter(PandocManager())
    results = converter.convert([str(source)], str(tmp_path), CONFIG)
    assert Path(results[0]).name == 'original (2).md'
    assert md.read_text(encoding='utf-8') == 'ORIGINAL MARKDOWN'


def test_file_queue_survives_format_switch_and_filters_metadata(window, tmp_path):
    (tmp_path/'first.md').write_text('ABC')
    folder = tmp_path/'folder'; folder.mkdir(); (folder/'second.MD').write_text('DEF')
    hidden = folder/'.obsidian'; hidden.mkdir(); (hidden/'ignore.md').write_text('hidden')
    window.add_files([tmp_path/'first.md', folder, tmp_path/'first.md'])
    assert window.file_list.count() == 2
    files = list(window.files_to_convert)
    window.panels['docx'].size_cs.setValue(23)
    window.format_combo.setCurrentIndex(1)
    window.settings_panel.size_cs.setValue(35)
    window.format_combo.setCurrentIndex(0)
    assert window.files_to_convert == files
    assert window.settings_panel.size_cs.value() == 23
    window.format_combo.setCurrentIndex(1)
    assert window.settings_panel.size_cs.value() == 35


def test_settings_restart_and_preset_does_not_move_output(window, tmp_path, monkeypatch):
    window.panels['docx'].size_cs.setValue(23)
    window.panels['pptx'].size_cs.setValue(35)
    window.save_settings()
    reopened = MainWindow(settings=QSettings(window.settings.fileName(), QSettings.IniFormat))
    assert reopened.panels['docx'].size_cs.value() == 23
    assert reopened.panels['pptx'].size_cs.value() == 35
    reopened.close()
    monkeypatch.setattr(QInputDialog, 'getText', lambda *_: ('강의', True))
    window.save_preset()
    window.settings_panel.size_cs.setValue(40)
    window.settings_panel.output_dir_edit.setText(str(tmp_path/'new-output'))
    window.load_preset()
    assert window.settings_panel.size_cs.value() == 23
    assert window.settings_panel.output_dir_edit.text() == str(tmp_path/'new-output')


def test_worker_converts_in_both_formats_with_same_queue(window, app, tmp_path):
    source = tmp_path/'input.md'; source.write_text('## 제목\n\n한국어ABCབོད་', encoding='utf-8')
    window.add_files([source])
    for index, suffix in [(0, 'docx'), (1, 'pptx')]:
        window.format_combo.setCurrentIndex(index)
        window.start_conversion()
        deadline = time.monotonic() + 15
        while window.worker is not None and time.monotonic() < deadline:
            app.processEvents(); time.sleep(.01)
        assert window.worker is None
        assert len(window.last_results) == 1
        assert Path(window.last_results[0]).suffix == '.' + suffix
        assert window.file_list.count() == 1
        assert window.convert_btn.isEnabled()


def test_close_guard_and_worker_file_snapshot(window, tmp_path):
    from src.ui.main_window import ConversionWorker
    converter = Converter(PandocManager())
    files = ['original.md']; worker = ConversionWorker(converter, files, str(tmp_path), CONFIG)
    files.append('added.md'); assert worker.files == ['original.md']
    class Event:
        ignored = False
        def ignore(self): self.ignored = True
        def accept(self): pass
    window.worker = worker
    event = Event(); window.closeEvent(event)
    assert event.ignored
    window.worker = None
