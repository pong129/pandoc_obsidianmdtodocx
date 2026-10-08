import io
from pathlib import Path
import zipfile
import pytest
import requests
from src.core import pandoc_manager as module


def test_portable_copy_wins_over_system_install(tmp_path, monkeypatch):
    portable = tmp_path/'pandoc.exe'; portable.write_bytes(b'MZportable')
    monkeypatch.setattr(module, 'application_dir', lambda: tmp_path)
    monkeypatch.setattr(module.shutil, 'which', lambda _: 'C:/system/pandoc.exe')
    assert module.PandocManager().pandoc_path == str(portable)


class DownloadResponse:
    def __init__(self, data):
        self.data = data
        self.headers = {'content-length': str(len(data))}
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def raise_for_status(self): pass
    def iter_content(self, chunk_size): yield self.data


def archive_bytes(content, filename='pandoc/pandoc.exe'):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr(filename, content)
    return buffer.getvalue()


@pytest.mark.parametrize('content', [b'not an executable', b'broken zip'])
def test_failed_download_keeps_previous_pandoc(tmp_path, monkeypatch, content):
    target = tmp_path/'pandoc.exe'; target.write_bytes(b'MZprevious')
    monkeypatch.setattr(module, 'application_dir', lambda: tmp_path)
    payload = content if content == b'broken zip' else archive_bytes(content)
    monkeypatch.setattr(module.requests, 'get', lambda *a, **k: DownloadResponse(payload))
    manager = module.PandocManager()
    with pytest.raises((RuntimeError, zipfile.BadZipFile)):
        manager.download_pandoc()
    assert target.read_bytes() == b'MZprevious'
    assert not list(tmp_path.glob('pandoc-setup-*'))


def test_successful_portable_download_is_verified_before_replace(tmp_path, monkeypatch):
    target = tmp_path/'pandoc.exe'; target.write_bytes(b'MZprevious')
    monkeypatch.setattr(module, 'application_dir', lambda: tmp_path)
    monkeypatch.setattr(module.requests, 'get', lambda *a, **k: DownloadResponse(archive_bytes(b'MZnew')))
    calls = []
    class Process:
        stdout = 'pandoc 3.9.0.2\n'
    def run(command, **kwargs):
        calls.append(command)
        if Path(command[0]) != target:
            assert target.read_bytes() == b'MZprevious'
        return Process()
    monkeypatch.setattr(module.subprocess, 'run', run)
    manager = module.PandocManager()
    assert manager.download_pandoc() == str(target)
    assert target.read_bytes() == b'MZnew'
    assert calls[0][1] == '--version'


def test_update_uses_pinned_fallback_when_release_lookup_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'application_dir', lambda: tmp_path)
    def fail(*a, **k): raise requests.ConnectionError('offline')
    monkeypatch.setattr(module.requests, 'get', fail)
    manager = module.PandocManager()
    chosen = []
    monkeypatch.setattr(manager, 'download_pandoc', lambda **kwargs: chosen.append(kwargs['url']) or 'portable')
    assert manager.install_or_update_pandoc() == 'portable'
    assert chosen == [manager.PANDOC_URL]
