import os
import tempfile
from pathlib import Path
from .base_converter import BaseConverter
from .output_paths import available_output, run_pandoc


class DocxToMdConverter(BaseConverter):
    def __init__(self, pandoc_manager):
        super().__init__(pandoc_manager, target_format='md')

    def convert(self, input_paths, output_dir, config, progress_callback=None):
        self.last_errors = []
        self.last_warnings = []
        if not self.pandoc_manager.is_installed():
            raise RuntimeError('Pandoc이 설치되어 있지 않습니다.')
        results = []
        for i, source in enumerate(input_paths):
            temporary = None
            try:
                output = available_output(source, output_dir, config, 'md')
                fd, temporary = tempfile.mkstemp(suffix='.md', dir=output.parent)
                os.close(fd)
                if progress_callback:
                    progress_callback(f'Markdown 변환 중 [{i+1}/{len(input_paths)}]: {Path(source).name}')
                command = [self.pandoc_manager.pandoc_path, str(source), '-o', temporary, '--to', 'markdown']
                if config.get('extract_media'):
                    command.append(f'--extract-media={output.parent / (output.stem + "_media")}')
                process = run_pandoc(command)
                if process.stderr.strip():
                    self.last_warnings.append(process.stderr.strip())
                output = available_output(source, output_dir, config, 'md')
                os.rename(temporary, output); temporary = None
                results.append(str(output))
            except Exception as error:
                message = f'{Path(source).name}: {error}'
                self.last_errors.append(message)
                if progress_callback:
                    progress_callback(f'실패: {message}')
            finally:
                if temporary and os.path.exists(temporary):
                    os.unlink(temporary)
        return results
