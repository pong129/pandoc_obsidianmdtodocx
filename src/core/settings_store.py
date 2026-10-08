"""Portable settings beside the executable, with a writable user fallback."""
import os
import sys
import tempfile
from pathlib import Path
from PySide6.QtCore import QSettings


def application_dir():
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]


def create_settings(path=None):
    if path is None:
        folder = application_dir()
        try:
            with tempfile.TemporaryFile(dir=folder):
                pass
        except OSError:
            folder = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ObsiDeck'
            folder.mkdir(parents=True, exist_ok=True)
        path = folder / 'ObsidianConverter.ini'
    settings = QSettings(str(path), QSettings.IniFormat)
    if not settings.contains('migration_complete'):
        for app in ('Converter', 'PptxConverter', 'DocxToMdConverter'):
            legacy = QSettings('ObsiDeck', app)
            for key in legacy.allKeys():
                if not settings.contains(key):
                    settings.setValue(key, legacy.value(key))
        settings.setValue('migration_complete', True)
        settings.sync()
    if not settings.contains('pptx_compact_defaults_v1'):
        for key, old, new in (('pptx_size_cs', 32, 20), ('pptx_size_east_asia', 20, 18)):
            if settings.contains(key) and settings.value(key, type=int) == old:
                settings.setValue(key, new)
        settings.setValue('pptx_compact_defaults_v1', True)
        settings.sync()
    return settings
