import re
from .base_converter import BaseConverter
from .pandoc_manager import PandocManager
from .pptx_post_processor import PptxPostProcessor

class PptxConverter(BaseConverter):
    """
    Orchestrates the conversion from Markdown to PPTX using Pandoc.
    Inherits the conversion orchestration loop from BaseConverter.
    """
    def __init__(self, pandoc_manager: PandocManager):
        super().__init__(pandoc_manager, target_format="pptx")

    def preprocess_content(self, raw_content: str, config: dict) -> str:
        """Keep section headings with their content and preserve original font levels."""
        lines = raw_content.split('\n')
        new_lines = []
        fence = None
        slide_level = int(config.get('slide_level', 2))
        title_pending = False

        for line in lines:
            stripped = line.strip()
            fence_match = re.match(r'^(`{3,}|~{3,})', stripped)
            if fence_match:
                marker = fence_match.group(1)
                if fence is None:
                    fence = marker
                    title_pending = False
                elif marker[0] == fence[0] and len(marker) >= len(fence):
                    fence = None
                new_lines.append(line)
                continue

            if fence is None:
                match = re.match(r'^(#{1,6})\s+(.*)', line)
                if match:
                    level = len(match.group(1))
                    # Pandoc otherwise gives H1 a section-only slide at slide-level 2.
                    # A consecutive subheading belongs below the first heading.
                    output_level = max(level, slide_level)
                    if level <= slide_level and title_pending:
                        output_level = min(6, slide_level + 1)
                    elif level <= slide_level:
                        title_pending = True
                    text = re.sub(r'\s+#+\s*$', '', match.group(2))
                    line = '#' * output_level + f" {text} {{{{H{level}}}}}"
                elif stripped:
                    title_pending = False

            new_lines.append(line)

        return '\n'.join(new_lines)

    def postprocess_file(self, output_path: str, config: dict, progress_callback=None):
        """
        Applies font sizes to slides and shapes.
        """
        if progress_callback:
            progress_callback(f"PPTX 후처리 중: {output_path}")
        PptxPostProcessor.process(output_path, config)
        if config.get('auto_paginate', True):
            from .pptx_pagination import paginate_package
            added = paginate_package(output_path)
            if progress_callback and added:
                progress_callback(f'본문 넘침 방지: 슬라이드 {added}장 자동 추가')

    def build_custom_cmd_args(self, input_path, output_path, config):
        return [f"--slide-level={int(config.get('slide_level', 2))}"]

