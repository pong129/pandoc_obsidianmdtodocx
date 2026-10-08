"""Package the approved dist EXE without personal settings or local Pandoc."""
from pathlib import Path
import hashlib
import importlib.metadata as metadata
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEPENDENCIES = (
    'PySide6', 'PySide6-Essentials', 'PySide6-Addons', 'shiboken6',
    'python-docx', 'python-pptx', 'lxml', 'requests', 'certifi',
    'charset-normalizer', 'idna', 'urllib3', 'typing-extensions', 'pyinstaller',
)


def main():
    exe = ROOT / 'dist' / 'ObsidianToDocx.exe'
    if not exe.is_file():
        raise FileNotFoundError(exe)
    output = ROOT / 'release'
    output.mkdir(exist_ok=True)
    archive_path = output / 'ObsidianToDocx-windows-x64.zip'
    manifest = {}
    notices = ['Third-party package metadata from the build environment.',
               'PyInstaller is the build tool; its bootloader is included.',
               'Pandoc and user fonts are not included in this ZIP.', '']
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for source, name in ((exe, 'ObsidianToDocx.exe'),
                             (ROOT / 'PORTABLE_README.txt', '사용방법.txt')):
            data = source.read_bytes()
            archive.writestr(name, data)
            manifest[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        for package in DEPENDENCIES:
            distribution = metadata.distribution(package)
            notices.append(f'{package} {distribution.version}')
            for key in ('License', 'License-Expression', 'Home-page', 'Project-URL'):
                for value in distribution.metadata.get_all(key, []):
                    notices.append(f'{key}: {value}')
            for item in distribution.files or ():
                if any(token in item.name.lower() for token in ('license', 'copying', 'notice')):
                    path = Path(distribution.locate_file(item))
                    if path.is_file():
                        archive.write(path, f'licenses/{package}/{item}')
            notices.append('')
        archive.writestr('THIRD_PARTY_NOTICES.txt', '\n'.join(notices))
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f'ZIP CRC failed: {bad}')
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (output / 'SHA256SUMS.txt').write_text(f'{digest}  {archive_path.name}\n', encoding='utf-8')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'{archive_path}\nSHA256: {digest}')


if __name__ == '__main__':
    main()
