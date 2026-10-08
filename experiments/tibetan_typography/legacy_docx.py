from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt

class PostProcessor:
    """
    Post-processes the generated DOCX to enforce specific formatting 
    that Pandoc might miss or that requires direct XML manipulation.
    """

    @staticmethod
    def process(docx_path: str, config: dict):
        """
        Applies post-processing to the given DOCX file.
        Enforces font families and sizes on all runs.
        """
        if not config:
            return

        # Extract config
        font_ascii = config.get('font_ascii')
        font_korean = config.get('font_korean')
        font_tibetan = config.get('font_tibetan')
        
        # Sizes in points
        size_body = config.get('size_body')
        size_cs = config.get('size_cs')
        title_size = config.get('title_size')
        
        # Load header sizes
        header_sizes = {
            'Heading 1': config.get('size_h1'),
            'Heading 2': config.get('size_h2'),
            'Heading 3': config.get('size_h3'),
            'Heading 4': config.get('size_h4'),
            'Heading 5': config.get('size_h5'),
            'Heading 6': config.get('size_h6'),
        }
        
        # Convert to half-points for XML (helper function)
        def to_half_pt(size):
            return str(int(size * 2)) if size else None

        sz_cs_val = to_half_pt(size_cs)

        try:
            doc = Document(docx_path)

            def enforce_run_formatting(run, paragraph_style_name):
                rPr = run.element.get_or_add_rPr()
                
                # Determine intended size for this run based on paragraph style
                sz_val = to_half_pt(size_body) # Default to body
                if paragraph_style_name == 'Title':
                    sz_val = to_half_pt(title_size)
                elif paragraph_style_name in header_sizes:
                    sz_val = to_half_pt(header_sizes[paragraph_style_name])
                
                # Check for Tibetan characters (Force Mode Condition)
                is_tibetan = any('\u0f00' <= char <= '\u0fff' for char in run.text)
                
                # 1. Enforce Fonts
                rFonts = rPr.get_or_add_rFonts()
                
                if is_tibetan and font_tibetan:
                    # FORCE MODE: Set ALL font slots to Tibetan font
                    rFonts.set(qn('w:ascii'), font_tibetan)
                    rFonts.set(qn('w:hAnsi'), font_tibetan)
                    rFonts.set(qn('w:eastAsia'), font_tibetan)
                    rFonts.set(qn('w:cs'), font_tibetan)
                else:
                    # Standard Mode
                    if font_ascii:
                        rFonts.set(qn('w:ascii'), font_ascii)
                        rFonts.set(qn('w:hAnsi'), font_ascii)
                    if font_korean:
                        rFonts.set(qn('w:eastAsia'), font_korean)
                    if font_tibetan:
                        rFonts.set(qn('w:cs'), font_tibetan)
                
                # 2. Enforce Sizes
                # w:sz controls Latin and East Asian size
                if sz_val:
                    sz = rPr.find(qn('w:sz'))
                    if sz is None:
                        sz = OxmlElement('w:sz')
                        rPr.append(sz)
                    
                    if is_tibetan and sz_cs_val:
                         # FORCE MODE: properties often use w:sz for rendering if hint is missing or ignored
                         sz.set(qn('w:val'), sz_cs_val)
                    else:
                         sz.set(qn('w:val'), sz_val)

                # w:szCs controls Complex Script size
                if sz_cs_val:
                    szCs = rPr.find(qn('w:szCs'))
                    if szCs is None:
                        szCs = OxmlElement('w:szCs')
                        rPr.append(szCs)
                    szCs.set(qn('w:val'), sz_cs_val)

                # 3. Enforce Language
                lang = rPr.find(qn('w:lang'))
                if lang is None:
                    lang = OxmlElement('w:lang')
                    rPr.append(lang)
                lang.set(qn('w:val'), 'en-US')
                lang.set(qn('w:eastAsia'), 'ko-KR')
                lang.set(qn('w:bidi'), 'bo-CN')

                # 4. Enforce Hint for Complex Scripts
                if is_tibetan:
                    rPr.set(qn('w:hint'), 'cs')



            # Iterate over all paragraphs and runs in body
            for paragraph in doc.paragraphs:
                for run in paragraph.runs:
                    enforce_run_formatting(run, paragraph.style.name)

            # Iterate over tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                enforce_run_formatting(run, paragraph.style.name)
            
            # --- New Feature: Add Empty Line Between Paragraphs ---
            if config.get('add_empty_line', False):
                # We iterate backwards through the body paragraphs so that inserting 
                # new paragraphs doesn't shift the indices of the ones we haven't visited yet.
                # We stop at index 1 because we insert *before* the current paragraph.
                paragraphs = doc.paragraphs
                for i in range(len(paragraphs) - 1, 0, -1):
                    curr_p = paragraphs[i]
                    prev_p = paragraphs[i-1]
                    
                    # Only insert an empty line if both the current and previous paragraphs
                    # actually contain some text. This prevents stacking empty lines where
                    # they already exist (e.g., from hard breaks or structural gaps).
                    if curr_p.text.strip() and prev_p.text.strip():
                        curr_p.insert_paragraph_before('')

            doc.save(docx_path)
            
        except Exception as e:
            print(f"DOCX 후처리 실패: {e}")
            raise e
