"""Generate reproducible before/after samples using the app's actual Pandoc."""
from dataclasses import asdict
from pathlib import Path
import json
import subprocess

from experiments.tibetan_typography.prototype import Typography, process_package
from experiments.tibetan_typography.legacy_docx import PostProcessor
from experiments.tibetan_typography.legacy_pptx import PptxPostProcessor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    output = HERE / "output"
    output.mkdir(exist_ok=True)
    profiles = {
        "docx": Typography(body_pt=12, tibetan_pt=20, heading_pt=24),
        "pptx": Typography(body_pt=20, tibetan_pt=32, heading_pt=32),
    }
    for kind, config in profiles.items():
        raw = output / f"pandoc_original.{kind}"
        legacy = output / f"current_app.{kind}"
        corrected = output / f"tibetan_corrected.{kind}"
        sample = HERE / ('sample.md' if kind == 'docx' else 'sample_pptx.md')
        cmd = [str(ROOT/'pandoc.exe'), str(sample), '-o', str(raw)]
        if kind == 'pptx':
            cmd.append('--slide-level=2')
        subprocess.run(cmd,
                       check=True, capture_output=True, timeout=30)
        legacy.write_bytes(raw.read_bytes())
        settings = {
            'font_ascii': config.latin_font, 'font_korean': config.korean_font,
            'font_tibetan': config.tibetan_font, 'size_body': config.body_pt,
            'size_cs': config.tibetan_pt, 'title_size': config.heading_pt,
            **{f'size_h{i}': config.heading_pt for i in range(1, 7)},
        }
        (PostProcessor if kind == 'docx' else PptxPostProcessor).process(str(legacy), settings)
        process_package(raw, corrected, config, kind)
        print(f'{kind.upper()}: {corrected}')
    (output/'profiles.json').write_text(json.dumps(
        {kind: asdict(config) for kind, config in profiles.items()},
        ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
