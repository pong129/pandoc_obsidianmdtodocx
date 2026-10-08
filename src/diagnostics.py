"""Optional local diagnostic, also usable against the frozen portable EXE."""
import json
import time
from pathlib import Path
from PySide6.QtCore import QSettings
from .ui.main_window import MainWindow


def run_self_test(app, directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    settings = QSettings(str(directory/'self_test.ini'), QSettings.IniFormat)
    window = MainWindow(settings=settings)
    report = {'pandoc_path': window.pandoc_manager.pandoc_path,
              'pandoc_version': window.pandoc_manager.get_version(), 'results': {}}
    exit_code = 0
    try:
        if not window.pandoc_manager.is_installed():
            raise RuntimeError('Pandoc not found')
        source = directory/'mixed.md'
        source.write_text('# 제목 བོད་ Title\n\n한국어Englishབོད་ཡིག་혼합\n\n'
                          '**Bold སྐྱེས་ 굵게**\n', encoding='utf-8')
        window.add_files([source])
        for index, kind in enumerate(('docx', 'pptx')):
            window.format_combo.setCurrentIndex(index)
            window.settings_panel.size_cs.setValue(20)
            window.settings_panel.insert_title.setChecked(False)
            window.start_conversion()
            deadline = time.monotonic() + 60
            while window.worker is not None and time.monotonic() < deadline:
                app.processEvents(); time.sleep(.01)
            if window.worker is not None or len(window.last_results) != 1:
                raise RuntimeError(window.console.toPlainText())
            report['results'][kind] = window.last_results[0]
        report['queue_retained'] = len(window.files_to_convert) == 1
        window.grab().save(str(directory/'screen.png'))
        report['passed'] = True
    except Exception as error:
        report['passed'] = False; report['error'] = str(error); exit_code = 1
    finally:
        if window.worker:
            window.worker.wait(190000); app.processEvents()
        window.close()
        (directory/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return exit_code
