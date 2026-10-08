from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

class ReferenceDocGenerator:
    """
    Generates a reference.docx for Pandoc to use as a style template.
    Handles specific font requirements for mixed language support and layout options.
    """

    def __init__(self, config=None):
        self.config = config or {}
        # Default fonts
        self.fonts = {
            'ascii': self.config.get('font_ascii', 'Arial'),
            'hAnsi': self.config.get('font_ascii', 'Arial'),
            'eastAsia': self.config.get('font_korean', 'Malgun Gothic'),
            'cs': self.config.get('font_tibetan', 'Microsoft Himalaya'), 
        }
        # Sizes
        self.sizes = {
            'body': self.config.get('size_body', 11),
            'h1': self.config.get('size_h1', 24),
            'h2': self.config.get('size_h2', 18),
            'h3': self.config.get('size_h3', 14),
            'h4': self.config.get('size_h4', 12),
            'h5': self.config.get('size_h5', 11),
            'h6': self.config.get('size_h6', 11),
            'footnote': self.config.get('size_footnote', 9),
            'east_asia': self.config.get('size_east_asia', 11), # Note: Word styles usually share w:sz for Latin/EastAsia
            'cs': self.config.get('size_cs', 12),
        }
        # Spacing
        self.spacing = {
            'body': self.config.get('spacing_body', 1.2),
            'header': self.config.get('spacing_header', 1.2),
        }
        # Title
        self.title_config = {
             'align': self.config.get('title_align', 'center'),
             'size': self.config.get('title_size', 24),
        }

    def generate(self, output_path: str):
        doc = Document()

        # 1. Update Normal Style (Body Text)
        style = doc.styles['Normal']
        self._set_font(style, self.sizes['body'], self.sizes['cs'])
        self._set_spacing(style, self.spacing['body'])
        
        # 2. Update Heading Styles 1-6
        for i in range(1, 7):
            style_name = f'Heading {i}'
            size_key = f'h{i}'
            if style_name in doc.styles:
                style = doc.styles[style_name]
                self._set_font(style, self.sizes[size_key], self.sizes['cs']) # Headings usually larger
                self._set_spacing(style, self.spacing['header'])

        # 3. Update Footnote Text
        try:
            style = doc.styles['Footnote Text']
            self._set_font(style, self.sizes['footnote'], self.sizes['footnote'])
        except KeyError:
            pass 

        # 4. Create/Update Title Style
        # Pandoc uses 'Title' style for the document title if metadata is set
        if 'Title' in doc.styles:
            style = doc.styles['Title']
        else:
            # Create if missing (though usually standard styles exist, python-docx might need explicit access)
            # Actually, python-docx doesn't easily create *builtin* styles if they aren't in the template.
            # But we can try to access it. If not found, we might add it as a custom style, 
            # but Pandoc expects the standard 'Title'.
            # A blank reference doc from python-docx default template usually has 'Title'.
            try:
                style = doc.styles['Title']
            except KeyError:
                # Fallback: Create a user style named Title? Pandoc maps to "Title".
                style = doc.styles.add_style('Title', 1) # 1 = Paragraph Style

        self._set_font(style, self.title_config['size'], self.title_config['size']) 
        self._set_paragraph_format(style, self.title_config['align'])
        self._set_lang(style) # Set language
        
        doc.save(output_path)
        return output_path

    def _set_lang(self, style):
        """
        Sets the language for the style to help Word identify scripts.
        """
        rPr = style.element.get_or_add_rPr()
        lang = rPr.find(qn('w:lang'))
        if lang is None:
            lang = OxmlElement('w:lang')
            rPr.append(lang)
        
        # Set explicitly for Asian and Complex Scripts
        lang.set(qn('w:val'), 'en-US')       # Western
        lang.set(qn('w:eastAsia'), 'ko-KR')  # Korean
        lang.set(qn('w:bidi'), 'bo-CN')      # Tibetan

    def _set_font(self, style, size_pt_latin, size_pt_cs):
        """
        Sets fonts and size for a style.
        """
        # Set primary font name (Latin)
        style.font.name = self.fonts['ascii']
        style.font.size = Pt(size_pt_latin)

        # Access OXML to set specific language fonts and CS size
        rPr = style.element.get_or_add_rPr()
        rFonts = rPr.get_or_add_rFonts()
        
        # Set attributes for w:rFonts
        rFonts.set(qn('w:ascii'), self.fonts['ascii'])
        rFonts.set(qn('w:hAnsi'), self.fonts['hAnsi'])
        rFonts.set(qn('w:eastAsia'), self.fonts['eastAsia'])
        rFonts.set(qn('w:cs'), self.fonts['cs'])

        # Set specific size for Complex Scripts (w:szCs)
        szCs = rPr.find(qn('w:szCs'))
        if szCs is None:
            szCs = OxmlElement('w:szCs')
            rPr.append(szCs)
        szCs.set(qn('w:val'), str(int(size_pt_cs * 2))) # Measured in half-points

        # Ensure language is set for every style modified
        self._set_lang(style)


    def _set_spacing(self, style, line_spacing_multiplier):
        """
        Sets paragraph line spacing (multiple).
        """
        pPr = style.element.get_or_add_pPr()
        spacing = pPr.find(qn('w:spacing'))
        if spacing is None:
            spacing = OxmlElement('w:spacing')
            pPr.append(spacing)
        
        # w:line is measured in 240ths of a line if w:lineRule is auto.
        # But 'lines' (multiplier) is easier to set via python-docx high level API if possible.
        # Let's use high level API which modifies pPr/spacing
        style.paragraph_format.line_spacing = line_spacing_multiplier

    def _set_paragraph_format(self, style, align_str):
        if align_str == 'center':
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align_str == 'right':
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        else:
            style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
