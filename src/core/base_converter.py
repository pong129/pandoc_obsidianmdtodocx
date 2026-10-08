import os
import subprocess
import tempfile
from .pandoc_manager import PandocManager
from .output_paths import available_output, run_pandoc

class BaseConverter:
    """
    Abstract Base Class for Pandoc document conversions.
    Handles parallel/bulk processing, temporary file lifecycles, and subprocess execution.
    """
    def __init__(self, pandoc_manager: PandocManager, target_format: str):
        self.pandoc_manager = pandoc_manager
        self.target_format = target_format
        self.last_errors = []
        self.last_warnings = []

    def preprocess_content(self, raw_content: str, config: dict) -> str:
        """Override in subclasses to modify raw markdown string before saving to disk."""
        return raw_content

    def build_custom_cmd_args(self, input_path: str, output_path: str, config: dict) -> list[str]:
        """Override in subclasses to add specific pandoc CLI flags (like --reference-doc)."""
        return []

    def postprocess_file(self, output_path: str, config: dict, progress_callback=None):
        """Override in subclasses to execute Python-based modifications after Pandoc finishes."""
        pass

    def convert(self, input_paths: list[str], output_dir: str, config: dict, progress_callback=None) -> list[str]:
        """
        Main orchestration loop for converting a batch of files.
        """
        self.last_errors = []
        self.last_warnings = []
        if not self.pandoc_manager.is_installed():
            self.last_errors.append('Pandoc이 설치되어 있지 않습니다.')
            if progress_callback:
                progress_callback("오류: Pandoc이 설치되어 있지 않습니다.")
            return []

        pandoc_exe = self.pandoc_manager.pandoc_path
        created_files = []
        total = len(input_paths)

        for i, input_path in enumerate(input_paths):
            file_name = os.path.basename(input_path)
            base_name = os.path.splitext(file_name)[0]
            actual_output_dir = os.path.dirname(os.path.abspath(input_path)) if config.get('save_to_original', True) else output_dir
            output_path = None
            tmp_output_path = None
            
            if progress_callback:
                progress_callback(f"{self.target_format.upper()} 변환 중 [{i+1}/{total}]: {file_name}")

            tmp_input_path = None
            try:
                output_path = available_output(input_path, output_dir, config, self.target_format)
                fd, tmp_output_path = tempfile.mkstemp(suffix=f'.{self.target_format}', dir=output_path.parent)
                os.close(fd)
                # 1. Read & Preprocess Content
                with open(input_path, 'r', encoding='utf-8-sig') as f:
                    raw_content = f.read()
                
                processed_content = self.preprocess_content(raw_content, config)
                
                # Write to temp markdown file
                with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode='w', encoding='utf-8') as tmp_md:
                    tmp_md.write(processed_content)
                    tmp_input_path = tmp_md.name

                # 2. Build Base Command
                input_dir = os.path.dirname(os.path.abspath(input_path))
                input_format = "markdown+smart"
                if config.get('preserve_breaks', False):
                    input_format += "+hard_line_breaks"

                cmd = [
                    pandoc_exe,
                    tmp_input_path,
                    "-o", tmp_output_path,
                    "--from", input_format,
                    "--to", self.target_format,
                    f"--resource-path={os.pathsep.join([input_dir, os.getcwd()])}"
                ]

                # Insert Title from Filename if requested and it applies
                if config.get('insert_title', False):
                    cmd.append(f"--metadata=title:{base_name}")

                # Append custom args from subclasses
                cmd.extend(self.build_custom_cmd_args(tmp_input_path, tmp_output_path, config))

                # 3. Execute Pandoc
                process = run_pandoc(cmd)
                if process.stderr.strip():
                    warning = f'{file_name}: {process.stderr.strip()}'
                    self.last_warnings.append(warning)
                    if progress_callback:
                        progress_callback(f'주의: {warning}')
                self.postprocess_file(tmp_output_path, config, progress_callback)
                # Recheck after conversion in case another batch created this name.
                output_path = available_output(input_path, output_dir, config, self.target_format)
                os.rename(tmp_output_path, output_path)
                tmp_output_path = None
                
                if progress_callback:
                    progress_callback(f"{self.target_format.upper()} 변환 완료: {output_path}")

                created_files.append(str(output_path))

            except subprocess.CalledProcessError as e:
                error_msg = f"{file_name} 파일의 {self.target_format.upper()} 변환 실패: {e.stderr}"
                self.last_errors.append(error_msg)
                if progress_callback:
                    progress_callback(error_msg)
            except Exception as e:
                self.last_errors.append(f'{file_name}: {e}')
                if progress_callback:
                    progress_callback(f"{file_name} 처리 중 예상치 못한 오류: {e}")
            finally:
                if tmp_output_path and os.path.exists(tmp_output_path):
                    os.unlink(tmp_output_path)
                # Always cleanup the temp input file mapping to this iteration
                if tmp_input_path and os.path.exists(tmp_input_path):
                    try:
                        os.remove(tmp_input_path)
                    except:
                        pass

        return created_files
