import os
import re
import tempfile
from .base_converter import BaseConverter
from .pandoc_manager import PandocManager
from .doc_generator import ReferenceDocGenerator
from .post_processor import PostProcessor

class Converter(BaseConverter):
    """
    Orchestrates the conversion from Markdown to Docx.
    """
    def __init__(self, pandoc_manager: PandocManager):
        super().__init__(pandoc_manager, target_format="docx")
        self.ref_doc_path = None

    def convert(self, input_paths: list[str], output_dir: str, config: dict, progress_callback=None) -> list[str]:
        # Generate Reference Doc once per batch
        if progress_callback:
            progress_callback("스타일 기준 문서를 준비하는 중입니다.")
            
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_ref:
            self.ref_doc_path = tmp_ref.name
            
        try:
            generator = ReferenceDocGenerator(config)
            generator.generate(self.ref_doc_path)
            
            # Call the shared conversion loop
            return super().convert(input_paths, output_dir, config, progress_callback)
            
        finally:
            if self.ref_doc_path and os.path.exists(self.ref_doc_path):
                try:
                    os.remove(self.ref_doc_path)
                except:
                    pass

    def preprocess_content(self, raw_content: str, config: dict) -> str:
        """
        Pre-processes markdown content to ensure headers and footnotes work 
        even when hard_line_breaks is enabled.
        """
        lines = raw_content.split('\n')
        new_lines = []
        in_code_block = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('```'):
                in_code_block = not in_code_block
            
            if not in_code_block:
                if re.match(r'^#{1,6}\s', line):
                    if i > 0 and lines[i-1].strip() != "":
                        new_lines.append("") 
                
                if re.match(r'^\[\^.+\]:', line):
                     if i > 0 and lines[i-1].strip() != "":
                        new_lines.append("")

            new_lines.append(line)
            
        return '\n'.join(new_lines)

    def build_custom_cmd_args(self, input_path: str, output_path: str, config: dict) -> list[str]:
        """Inject the reference doc path into the Pandoc command."""
        if self.ref_doc_path:
            return [f"--reference-doc={self.ref_doc_path}"]
        return []

    def postprocess_file(self, output_path: str, config: dict, progress_callback=None):
        """
        Applies font sizes to complex scripts like Tibetan.
        """
        if progress_callback:
            progress_callback(f"DOCX 후처리 중: {os.path.basename(output_path)}")
        PostProcessor.process(output_path, config)

