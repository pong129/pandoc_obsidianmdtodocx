from .typography import format_package


class PostProcessor:
    @staticmethod
    def process(path: str, config: dict):
        if config:
            format_package(path, config, 'docx')
