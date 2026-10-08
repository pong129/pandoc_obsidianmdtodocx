from PySide6.QtWidgets import QListWidget, QAbstractItemView
from PySide6.QtCore import Qt, Signal
import os

class FileListWidget(QListWidget):
    """
    A QListWidget that supports drag & drop of files and folders.
    Emits a signal when files are added.
    """
    files_dropped = Signal(list)

    def __init__(self, parent=None, allowed_extensions=None):
        super().__init__(parent)
        self.allowed_extensions = self._normalize_extensions(allowed_extensions or [".md"])
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DropOnly)

    def _normalize_extensions(self, extensions):
        normalized = []
        for extension in extensions:
            extension = extension.lower()
            normalized.append(extension if extension.startswith(".") else f".{extension}")
        return tuple(normalized)

    def accepts_file(self, path):
        return os.path.isfile(path) and path.lower().endswith(self.allowed_extensions)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if self.accepts_file(path):
                files.append(path)
            elif os.path.isdir(path):
                for root, folders, filenames in os.walk(path, followlinks=False):
                    folders[:] = sorted(f for f in folders if f not in
                                        ('.obsidian', '.git', '.trash', '.venv', 'node_modules'))
                    for filename in sorted(filenames):
                        candidate = os.path.join(root, filename)
                        if self.accepts_file(candidate):
                            files.append(candidate)
        
        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()
        else:
            event.ignore()
