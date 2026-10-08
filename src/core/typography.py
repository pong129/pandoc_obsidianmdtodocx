"""Unicode-aware typography for DOCX and PPTX text runs.

Split text runs at Tibetan Unicode boundaries before applying typography.
Keep every existing run property, relationship and non-text node. This avoids
replacing a whole mixed-language run with Tibetan formatting.
"""
from copy import deepcopy
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
import zipfile
import os
import re
import tempfile
from .pptx_layout import compact_untitled_slide

from lxml import etree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


@dataclass(frozen=True)
class Typography:
    latin_font: str = "Arial"
    korean_font: str = "Malgun Gothic"
    tibetan_font: str = "Microsoft Himalaya"
    body_pt: float = 12
    tibetan_pt: float = 20
    heading_pt: float = 24
    korean_pt: float = 12

    def tibetan_size(self, normal_pt):
        # Preserve heading hierarchy, using the body Tibetan/normal ratio.
        return normal_pt * self.tibetan_pt / self.body_pt


def is_tibetan(char):
    # Includes Tibetan letters, vowel signs, subjoined letters, digits and shad.
    # Wylie/Latin transliteration is intentionally not classified as Tibetan.
    return "\u0f00" <= char <= "\u0fff"


def is_east_asian(char):
    return any(start <= ord(char) <= end for start, end in (
        (0x1100, 0x11FF), (0x3130, 0x318F), (0xA960, 0xA97F),
        (0xAC00, 0xD7AF), (0xD7B0, 0xD7FF), (0x3400, 0x9FFF),
        (0x3040, 0x30FF), (0xF900, 0xFAFF)))


def segments(text):
    flags = [is_tibetan(char) for char in text]
    # Join controls/variation selectors next to Tibetan belong to that script.
    # Do not move ordinary spaces or punctuation into the Tibetan segment.
    for i, char in enumerate(text):
        if char in "\u200c\u200d\ufe00\ufe01\ufe02\ufe03\ufe04\ufe05\ufe06\ufe07\ufe08\ufe09\ufe0a\ufe0b\ufe0c\ufe0d\ufe0e\ufe0f":
            left = i - 1
            while left >= 0 and text[left] in "\u200c\u200d":
                left -= 1
            right = i + 1
            while right < len(text) and text[right] in "\u200c\u200d":
                right += 1
            flags[i] = ((left >= 0 and is_tibetan(text[left])) or
                        (right < len(text) and is_tibetan(text[right])))
    return [(flag, "".join(char for _, char in group))
            for flag, group in groupby(zip(flags, text), key=lambda item: item[0])]


def child(parent, ns, name):
    element = parent.find(f"{{{ns}}}{name}")
    if element is None:
        element = ET.SubElement(parent, f"{{{ns}}}{name}")
    return element


def order_properties(props, ns):
    # OOXML has ordered property children. In particular font nodes must precede
    # hyperlinks in DrawingML, and rFonts must precede bold/italic in WordML.
    names = ("rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow "
             "emboss imprint noProof snapToGrid vanish webHidden color spacing w kern "
             "position sz szCs highlight u effect bdr shd fitText vertAlign rtl cs em "
             "lang eastAsianLayout specVanish oMath" if ns == W else
             "ln noFill solidFill gradFill blipFill pattFill grpFill effectLst effectDag "
             "highlight uLnTx uLn uFillTx uFill latin ea cs sym hlinkClick hlinkMouseOver "
             "rtl extLst")
    order = {f"{{{ns}}}{name}": i for i, name in enumerate(names.split())}
    props[:] = sorted(props, key=lambda node: order.get(node.tag, len(order)))


def apply_word(run, tibetan, normal_pt, config):
    props = run.find(f"{{{W}}}rPr")
    if props is None:
        props = ET.Element(f"{{{W}}}rPr")
        run.insert(0, props)
    fonts = child(props, W, "rFonts")
    # Clear theme references which could compete with explicit font choices.
    for name in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme", "csTheme"):
        fonts.attrib.pop(f"{{{W}}}{name}", None)
    for slot, font in (("ascii", config.latin_font), ("hAnsi", config.latin_font),
                       ("eastAsia", config.korean_font), ("cs", config.tibetan_font)):
        fonts.set(f"{{{W}}}{slot}", config.tibetan_font if tibetan else font)
    fonts.set(f"{{{W}}}hint", "cs" if tibetan else "default")
    # Old app code placed hint on rPr, rather than rFonts.
    props.attrib.pop(f"{{{W}}}hint", None)
    size = config.tibetan_size(normal_pt) if tibetan else normal_pt
    for name in ("sz", "szCs"):
        child(props, W, name).set(f"{{{W}}}val", str(round(size * 2)))
    order_properties(props, W)


def apply_drawing(run, tibetan, normal_pt, config):
    props = run.find(f"{{{A}}}rPr")
    if props is None:
        props = ET.Element(f"{{{A}}}rPr")
        run.insert(0, props)
    size = config.tibetan_size(normal_pt) if tibetan else normal_pt
    props.set("sz", str(round(size * 100)))
    props.set("lang", "bo-CN" if tibetan else "en-US")
    for slot, font in (("latin", config.latin_font), ("ea", config.korean_font),
                       ("cs", config.tibetan_font)):
        child(props, A, slot).set("typeface", config.tibetan_font if tibetan else font)
    order_properties(props, A)


def split_run(run, ns, normal_pt, config):
    if not any(node.tag == f"{{{ns}}}t" and node.text for node in run):
        return
    parent = run.getparent()
    position = parent.index(run)
    props = run.find(f"{{{ns}}}rPr")
    replacements = []
    for node in run:
        if node.tag == f"{{{ns}}}rPr":
            continue
        if node.tag == f"{{{ns}}}t" and node.text:
            pieces = []
            for tibetan, value in segments(node.text):
                if tibetan:
                    pieces.append((True, value))
                else:
                    pieces.extend((False, ''.join(chars)) for _, chars in
                                  groupby(value, key=is_east_asian))
        else:
            # Tabs, line breaks, pictures and footnote references occur once.
            pieces = [(None, None)]
        for tibetan, text in pieces:
            new_run = ET.Element(run.tag, dict(run.attrib))
            if props is not None:
                new_run.append(deepcopy(props))
            new_node = deepcopy(node)
            if text is not None:
                new_node.text = text
                if ns == W:
                    new_node.set(XML_SPACE, "preserve")
            new_run.append(new_node)
            if tibetan is not None:
                size = normal_pt
                if not tibetan and text and is_east_asian(text[0]):
                    size *= config.korean_pt / config.body_pt
                (apply_word if ns == W else apply_drawing)(new_run, tibetan, size, config)
            replacements.append(new_run)
    if replacements:
        replacements[-1].tail = run.tail
    parent.remove(run)
    for offset, replacement in enumerate(replacements):
        parent.insert(position + offset, replacement)


def from_config(config, kind):
    body = float(config.get('size_body', 20 if kind == 'pptx' else 11))
    return Typography(
        latin_font=config.get('font_ascii', 'Arial'),
        korean_font=config.get('font_korean', 'Malgun Gothic'),
        tibetan_font=config.get('font_tibetan', 'Microsoft Himalaya'),
        body_pt=body, korean_pt=float(config.get('size_east_asia', 18 if kind == 'pptx' else body)),
        tibetan_pt=float(config.get('size_cs', 20 if kind == 'pptx' else 18)),
        heading_pt=float(config.get('title_size', 32 if kind == 'pptx' else 24)),
    )


def remove_heading_tag(paragraph):
    nodes = list(paragraph.iter(f'{{{A}}}t'))
    text = ''.join(node.text or '' for node in nodes)
    match = re.search(r' ?\{\{H([1-6])\}\}$', text)
    if match is None:
        return None
    offset = 0
    for node in nodes:
        value = node.text or ''
        keep = max(0, min(len(value), match.start() - offset))
        node.text = value[:keep]
        offset += len(value)
    return int(match.group(1))


def format_package(path, config, kind):
    """Apply typography atomically, preserving ZIP entries and relationships."""
    path = Path(path)
    typography = from_config(config, kind)
    if min(typography.body_pt, typography.tibetan_pt, typography.korean_pt) <= 0:
        raise ValueError('글자 크기는 0보다 커야 합니다.')
    ns = W if kind == 'docx' else A
    fd, temporary = tempfile.mkstemp(suffix=path.suffix, dir=path.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(path) as source, zipfile.ZipFile(temporary, 'w') as target:
            for info in source.infolist():
                data = source.read(info.filename)
                relevant = (info.filename.startswith('word/') if kind == 'docx'
                            else info.filename.startswith('ppt/slides/slide'))
                if relevant and info.filename.endswith('.xml'):
                    tree = ET.fromstring(data)
                    for paragraph in list(tree.iter(f'{{{ns}}}p')):
                        normal = typography.body_pt
                        if kind == 'docx':
                            style = paragraph.find(f'{{{W}}}pPr/{{{W}}}pStyle')
                            name = style.get(f'{{{W}}}val', '') if style is not None else ''
                            heading = re.fullmatch(r'Heading([1-6])', name.replace(' ', ''))
                            if heading:
                                normal = float(config.get(f'size_h{heading[1]}', typography.heading_pt))
                            elif name == 'Title':
                                normal = typography.heading_pt
                            elif 'footnote' in info.filename or 'endnote' in info.filename or name == 'FootnoteText':
                                normal = float(config.get('size_footnote', 9))
                        else:
                            level = remove_heading_tag(paragraph)
                            if level:
                                normal = float(config.get(f'size_h{level}', typography.heading_pt))
                            else:
                                shape = next((p for p in paragraph.iterancestors()
                                              if p.tag == '{http://schemas.openxmlformats.org/presentationml/2006/main}sp'), None)
                                placeholders = shape.findall('.//{http://schemas.openxmlformats.org/presentationml/2006/main}ph') if shape is not None else []
                                if any(p.get('type') in ('title', 'ctrTitle', 'subTitle') for p in placeholders):
                                    normal = typography.heading_pt
                        for run in list(paragraph.iter(f'{{{ns}}}r')):
                            split_run(run, ns, normal, typography)
                    if kind == 'docx' and config.get('add_empty_line') and info.filename == 'word/document.xml':
                        body = tree.find(f'{{{W}}}body')
                        if body is not None:
                            previous = None
                            for node in list(body):
                                if node.tag == f'{{{W}}}p' and ''.join(node.itertext()).strip():
                                    if previous is not None:
                                        body.insert(body.index(node), ET.Element(f'{{{W}}}p'))
                                    previous = node
                                else:
                                    previous = None
                    if kind == 'pptx':
                        compact_untitled_slide(source, info.filename, tree)
                        # Keep exact sizes instead of template autofit shrinking text.
                        for props in tree.iter(f'{{{A}}}bodyPr'):
                            for autofit in list(props):
                                if autofit.tag in (f'{{{A}}}normAutofit', f'{{{A}}}spAutoFit'):
                                    props.remove(autofit)
                            if props.find(f'{{{A}}}noAutofit') is None:
                                props.insert(0, ET.Element(f'{{{A}}}noAutofit'))
                    data = ET.tostring(tree, xml_declaration=True, encoding='UTF-8', standalone=True)
                target.writestr(info, data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

