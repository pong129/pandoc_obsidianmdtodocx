from pptx import Presentation
from pptx.util import Pt
from pptx.enum.shapes import PP_PLACEHOLDER
import os

class PptxPostProcessor:
    """
    Post-processes the generated PPTX to enforce specific font sizes
    that Pandoc might miss.
    """

    @staticmethod
    def process(pptx_path: str, config: dict):
        """
        Applies post-processing to the given PPTX file.
        Enforces font sizes on all text runs.
        """
        if not config:
            return

        # Sizes in points
        size_body = config.get('size_body')
        title_size = config.get('title_size')
        
        if not size_body and not title_size:
            return

        try:
            prs = Presentation(pptx_path)
            
            # Map of tag to config key and default size
            header_keys = {
                '{{H1}}': 'size_h1',
                '{{H2}}': 'size_h2',
                '{{H3}}': 'size_h3',
                '{{H4}}': 'size_h4',
                '{{H5}}': 'size_h5',
                '{{H6}}': 'size_h6'
            }

            for slide in prs.slides:
                for shape in slide.shapes:
                    if not shape.has_text_frame:
                        continue
                    
                    # Determine if this shape is a title or subtitle
                    is_title = False
                    if shape.is_placeholder:
                        ptype = shape.placeholder_format.type
                        if ptype in [PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.SUBTITLE]:
                            is_title = True

                    for paragraph in shape.text_frame.paragraphs:
                        # Extract the full text of the paragraph to look for tags
                        full_text = paragraph.text.strip()
                        detected_header_level = None
                        
                        # Look for our hidden tag
                        for tag, key in header_keys.items():
                            if tag in full_text:
                                detected_header_level = tag
                                break
                                
                        # Decide target font size
                        target_size = None
                        if detected_header_level:
                            # Use config mapped header size
                            key = header_keys[detected_header_level]
                            target_size = config.get(key)
                        elif is_title and title_size:
                            target_size = title_size
                        elif not is_title and size_body:
                            target_size = size_body

                        # Apply to all runs
                        for run in paragraph.runs:
                            # If we found a tag in the paragraph, we need to remove it from the run text
                            if detected_header_level and detected_header_level in run.text:
                                run.text = run.text.replace(f" {detected_header_level}", "")
                                run.text = run.text.replace(detected_header_level, "") # Fallback just in case space was lost

                            try:
                                if target_size:
                                    run.font.size = Pt(target_size)
                            except AttributeError:
                                # Fallback if font size cannot be set directly
                                pass

            # Save in place
            prs.save(pptx_path)
            
        except Exception as e:
            print(f"PPTX 후처리 실패: {e}")
