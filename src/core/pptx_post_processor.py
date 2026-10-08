from .typography import format_package


class PptxPostProcessor:
    @staticmethod
    def process(path: str, config: dict):
        if config:
            format_package(path, config, 'pptx')
