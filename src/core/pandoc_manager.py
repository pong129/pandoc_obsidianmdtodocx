import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
import requests
from .settings_store import application_dir


class PandocManager:
    PANDOC_VERSION = '3.9.0.2'
    PANDOC_URL = f'https://github.com/jgm/pandoc/releases/download/{PANDOC_VERSION}/pandoc-{PANDOC_VERSION}-windows-x86_64.zip'
    WINGET_PACKAGE_ID = 'JohnMacFarlane.Pandoc'

    def __init__(self):
        self.pandoc_path = self._find_pandoc()

    def _find_pandoc(self):
        user = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
        # Portable copies deliberately take precedence over system installations.
        candidates = [application_dir()/'pandoc.exe', application_dir()/'bin/pandoc.exe',
                      user/'ObsiDeck/bin/pandoc.exe']
        system = shutil.which('pandoc')
        if system:
            candidates.append(Path(system))
        candidates.extend([Path(os.environ.get('ProgramFiles', 'C:/Program Files'))/'Pandoc/pandoc.exe',
                           user/'Pandoc/pandoc.exe'])
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return None

    def refresh(self):
        self.pandoc_path = self._find_pandoc()
        return self.pandoc_path

    def is_installed(self):
        return bool(self.pandoc_path and Path(self.pandoc_path).is_file())

    def get_version(self):
        if not self.is_installed():
            return '설치되지 않음'
        try:
            result = subprocess.run([self.pandoc_path, '--version'], capture_output=True,
                                    text=True, check=True, timeout=10,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return result.stdout.splitlines()[0].split()[1]
        except Exception as error:
            return f'실행 오류: {error}'

    def is_winget_available(self):
        return shutil.which('winget') is not None

    def install_or_update_pandoc(self, progress_callback=None):
        # System package managers are not needed by a portable application.
        url = self.PANDOC_URL
        if progress_callback:
            progress_callback('포터블 Pandoc 최신 버전을 확인합니다.')
        try:
            with requests.get('https://api.github.com/repos/jgm/pandoc/releases/latest', timeout=15) as response:
                response.raise_for_status()
                assets = response.json().get('assets', [])
                asset = next(a for a in assets if a['name'].endswith('windows-x86_64.zip'))
                url = asset['browser_download_url']
        except (requests.RequestException, ValueError, KeyError, StopIteration):
            if progress_callback:
                progress_callback(f'최신 버전 조회가 어려워 호환 버전 {self.PANDOC_VERSION}을 사용합니다.')
        return self.download_pandoc(progress_callback=progress_callback, url=url)

    def download_pandoc(self, download_callback=None, progress_callback=None, url=None):
        folder = application_dir()
        try:
            with tempfile.TemporaryFile(dir=folder):
                pass
        except OSError:
            folder = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))/'ObsiDeck/bin'
            folder.mkdir(parents=True, exist_ok=True)
        if progress_callback:
            progress_callback(f'Pandoc 다운로드 위치: {folder}')
        # Extract only the executable, verify ZIP CRC and executable signature,
        # then replace the previous copy. A failed download keeps it intact.
        with tempfile.TemporaryDirectory(prefix='pandoc-setup-', dir=folder) as temporary:
            archive_path = Path(temporary)/'pandoc.zip'
            with requests.get(url or self.PANDOC_URL, stream=True, timeout=(15, 60)) as response:
                response.raise_for_status()
                total = int(response.headers.get('content-length', 0))
                current = 0
                with archive_path.open('wb') as stream:
                    for chunk in response.iter_content(chunk_size=1024*256):
                        stream.write(chunk); current += len(chunk)
                        if download_callback:
                            download_callback(current, total)
            with zipfile.ZipFile(archive_path) as archive:
                entry = next((n for n in archive.namelist() if Path(n).name == 'pandoc.exe'), None)
                if entry is None:
                    raise RuntimeError('다운로드에 pandoc.exe가 없습니다.')
                data = archive.read(entry)
                if not data.startswith(b'MZ'):
                    raise RuntimeError('올바른 Windows 실행 파일이 아닙니다.')
                executable = Path(temporary)/'pandoc.exe'; executable.write_bytes(data)
                subprocess.run([str(executable), '--version'], check=True, capture_output=True,
                               timeout=10, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                target = folder/'pandoc.exe'
                os.replace(executable, target)
        self.pandoc_path = str(target)
        if progress_callback:
            progress_callback(f'Pandoc 준비 완료: {self.get_version()}')
        return self.pandoc_path
