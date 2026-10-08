from pathlib import Path
import subprocess
import os


def available_output(input_path, output_dir, config, extension):
    source = Path(input_path).resolve()
    folder = source.parent if config.get('save_to_original', True) else Path(output_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f'{source.stem}.{extension}'
    number = 2
    while output.exists():
        output = folder / f'{source.stem} ({number}).{extension}'
        number += 1
    return output


def run_pandoc(command):
    return subprocess.run(command, capture_output=True, text=True, check=True,
                          encoding='utf-8', errors='replace', timeout=180,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
