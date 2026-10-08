import sys
import os

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.pandoc_manager import PandocManager
from src.core.docx_to_md_converter import DocxToMdConverter

def test_conversion():
    manager = PandocManager()
    if not manager.is_installed():
        print("Pandoc is not installed!")
        return

    converter = DocxToMdConverter(manager)
    
    # Let's use the test_footnote.docx we generated earlier
    input_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_footnote.docx"))
    output_dir = os.path.dirname(input_file)
    
    if not os.path.exists(input_file):
        print(f"Test file not found: {input_file}")
        return
        
    print(f"Testing conversion of {input_file}")
    
    config = {
        'save_to_original': True,
        'extract_media': False
    }

    def on_progress(msg):
        print(msg)

    results = converter.convert([input_file], output_dir, config, progress_callback=on_progress)
    print("Conversion results:", results)
    
    if results and os.path.exists(results[0]):
        with open(results[0], 'r', encoding='utf-8') as f:
            content = f.read()
            print("\nConverted Content:\n---")
            print(content)
            print("---")
            if "[^1]" in content and "[^1]: footnote" in content:
                print("SUCCESS: Footnote syntax preserved!")
            else:
                print("FAILED: Footnote syntax not found.")

if __name__ == "__main__":
    test_conversion()
