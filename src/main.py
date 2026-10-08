import sys
import os

# Add the project root directory to sys.path so 'src' can be found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from src.ui.main_window import MainWindow
import ctypes


APP_USER_MODEL_ID = "ObsiDeck.ObsidianDocumentConverter"

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    return os.path.join(base_path, relative_path)

def main():
    # Set AppUserModelID for Windows taskbar icon to work correctly
    if os.name == 'nt':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)

    app = QApplication(sys.argv)
    app.setApplicationName("옵시디언 문서 변환기")
    app.setOrganizationName("ObsiDeck")

    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        from src.diagnostics import run_self_test
        raise SystemExit(run_self_test(app, sys.argv[2]))
    
    # Set Application Icon
    icon_path = get_resource_path(os.path.join('resources', 'icon.ico'))
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)

    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
