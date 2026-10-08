"""Paginate formatted text using the portable app's existing Qt shaping engine.

No PowerPoint installation is needed. A width reserve covers differences between
Qt and Office line breaking; explicit line spacing makes vertical bounds stable.
"""
from copy import deepcopy
import math
import os
from pathlib import Path
import posixpath
import tempfile
import zipfile
from lxml import etree as ET
from PySide6.QtGui import QFont, QFontMetricsF, QTextLayout, QTextOption, QTextCharFormat
from PySide6.QtWidgets import QApplication
from .pptx_layout import P, A, R, related_xml, inherited_transform, placeholder, compact_untitled_slide, own_transform
from .typography import is_east_asian, is_tibetan

DOC_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
PT = 12700
_measurement_app = None


def ensure_fonts():
    global _measurement_app
    if QApplication.instance() is None:
        if os.name != 'nt' and not os.environ.get('DISPLAY'):
            os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
        _measurement_app = QApplication([])


def paragraph_text(paragraph):
    return ''.join(('\n' if node.tag == f'{{{A}}}br' else
                    ''.join(node.itertext()) if node.tag in (f'{{{A}}}r', f'{{{A}}}fld') else '')
                   for node in paragraph if node.tag in (f'{{{A}}}r', f'{{{A}}}fld', f'{{{A}}}br'))


def utf16_length(text):
    return len(text.encode('utf-16-le')) // 2


def line_ranges(paragraph, width):
    """Return Python character ranges, never slice a Tibetan glyph cluster."""
    text = paragraph_text(paragraph)
    layout = QTextLayout(text.replace('\n', '\u2028'))
    options = QTextOption()
    options.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
    layout.setTextOption(options)
    formats = []
    offset = 0
    line_height = 0
    for node in paragraph:
        if node.tag not in (f'{{{A}}}r', f'{{{A}}}fld', f'{{{A}}}br'):
            continue
        value = '\n' if node.tag == f'{{{A}}}br' else ''.join(node.itertext())
        props = node.find(f'{{{A}}}rPr')
        size = float(props.get('sz', '2000')) / 100 if props is not None else 20
        slot = 'ea' if value and is_east_asian(value[0]) else 'latin'
        font_node = props.find(f'{{{A}}}{slot}') if props is not None else None
        font = QFont(font_node.get('typeface') if font_node is not None else 'Arial')
        font.setPixelSize(max(1, round(size * 4)))
        font.setBold(props is not None and props.get('b') == '1')
        font.setItalic(props is not None and props.get('i') == '1')
        line_height = max(line_height, QFontMetricsF(font).height() / 4, size * 1.25)
        fmt = QTextCharFormat(); fmt.setFont(font)
        span = QTextLayout.FormatRange()
        span.start = offset; span.length = utf16_length(value); span.format = fmt
        formats.append(span); offset += span.length
    layout.setFormats(formats)
    layout.beginLayout()
    ranges = []
    # QTextLine uses UTF-16 indices, Python uses Unicode code points.
    boundaries = {0: 0}
    offset = 0
    for index, char in enumerate(text):
        offset += utf16_length(char); boundaries[offset] = index + 1
    while True:
        line = layout.createLine()
        if not line.isValid():
            break
        line.setLineWidth(max(4, width * .90 * 4))
        start, end = line.textStart(), line.textStart() + line.textLength()
        ranges.append((boundaries[start], boundaries[end]))
    layout.endLayout()
    return ranges or [(0, len(text))], math.ceil(max(line_height, 20) * 1.10)


def slice_paragraph(paragraph, start, end, line_height):
    result = deepcopy(paragraph)
    for node in list(result):
        if node.tag in (f'{{{A}}}r', f'{{{A}}}fld', f'{{{A}}}br'):
            result.remove(node)
    position = 0
    insert_at = 1 if result.find(f'{{{A}}}pPr') is not None else 0
    for node in paragraph:
        if node.tag not in (f'{{{A}}}r', f'{{{A}}}fld', f'{{{A}}}br'):
            continue
        value = '\n' if node.tag == f'{{{A}}}br' else ''.join(node.itertext())
        lo, hi = max(0, start - position), min(len(value), end - position)
        if lo < hi:
            clone = deepcopy(node)
            if node.tag != f'{{{A}}}br':
                text_node = clone.find(f'{{{A}}}t')
                if text_node is not None:
                    text_node.text = value[lo:hi]
            result.insert(insert_at, clone); insert_at += 1
        position += len(value)
    props = result.find(f'{{{A}}}pPr')
    if props is None:
        props = ET.Element(f'{{{A}}}pPr'); result.insert(0, props)
    for tag, points in (('lnSpc', line_height), ('spcBef', 0), ('spcAft', 6)):
        existing = props.find(f'{{{A}}}{tag}')
        if existing is not None:
            props.remove(existing)
        spacing = ET.Element(f'{{{A}}}{tag}')
        ET.SubElement(spacing, f'{{{A}}}spcPts', val=str(round(points * 100)))
        # DrawingML requires spacing before bullet/tab/default run properties.
        props.insert({'lnSpc': 0, 'spcBef': 1, 'spcAft': 2}[tag], spacing)
    return result


def language_flags(paragraphs):
    text = ''.join(paragraph_text(p) for p in paragraphs)
    return any(is_tibetan(c) for c in text), any('\uac00' <= c <= '\ud7a3' for c in text)


def translation_groups(paragraphs):
    """A Tibetan paragraph plus subsequent Korean paragraphs is one unit.

    Mixed-language paragraphs are already units. A new Tibetan paragraph after
    a completed translation starts the next unit. No translation is invented.
    """
    groups = []
    pending = []
    for paragraph in paragraphs:
        tibetan, korean = language_flags([paragraph])
        old_tibetan, old_korean = language_flags(pending)
        if pending and tibetan:
            groups.append(pending); pending = []
        pending.append(paragraph)
        # Plain Korean/English blocks do not absorb a following original text.
        if not tibetan and not old_tibetan and korean:
            groups.append(pending); pending = []
    if pending:
        groups.append(pending)
    return groups


def fit_group(group, width, height):
    measured = [(p, *line_ranges(p, width)) for p in group]
    required = sum(len(lines) * line_height + 6 for _, lines, line_height in measured)
    if required <= height:
        return measured
    preview = ' '.join(''.join(paragraph_text(p) for p in group).split())[:140]
    raise ValueError('티베트어 원문·한국어 번역 한 묶음이 한 장보다 깁니다. '
                     '글자를 줄이거나 번역을 분리하지 않고 변환을 중단했습니다. '
                     f'아래 묶음을 원문과 번역이 대응하도록 나눠주세요: {preview}…')


def paginate_paragraphs(paragraphs, width, height, continuation_height=None):
    continuation_height = continuation_height or height
    current_height = height
    pages = [[]]
    used = 0
    queue = []
    for group in translation_groups(paragraphs):
        tibetan, korean = language_flags(group)
        if tibetan and korean:
            measured = fit_group(group, width, continuation_height)
            required = sum(len(lines) * line_height + 6 for _, lines, line_height in measured)
            queue.append((measured, required, True))
        else:
            queue.extend(([(p, *line_ranges(p, width))], 0, False) for p in group)
    for measured, required, paired in queue:
        if paired:
            if used + required > current_height:
                if not pages[-1]:
                    fit_group([p for p, _, _ in measured], width, current_height)
                pages.append([]); used = 0; current_height = continuation_height
            for paragraph, lines, line_height in measured:
                pages[-1].append(slice_paragraph(paragraph, 0, len(paragraph_text(paragraph)), line_height))
            used += required
            continue
        paragraph, lines, line_height = measured[0]
        whole_height = len(lines) * line_height + 6
        if whole_height <= continuation_height and used + whole_height > current_height and pages[-1]:
            pages.append([]); used = 0; current_height = continuation_height
        index = 0
        while index < len(lines):
            capacity = math.floor((current_height - used - 6) / line_height)
            if capacity < 1:
                if not pages[-1]:
                    raise ValueError('글자 크기가 슬라이드 본문 영역보다 큽니다. 글자 크기를 줄여주세요.')
                pages.append([]); used = 0; current_height = continuation_height
                continue
            count = min(capacity, len(lines) - index)
            start = lines[index][0]; end = lines[index + count - 1][1]
            pages[-1].append(slice_paragraph(paragraph, start, end, line_height))
            used += count * line_height + 6
            index += count
            if index < len(lines):
                pages.append([]); used = 0; current_height = continuation_height
    return pages


def set_transform(shape, transform):
    existing = own_transform(shape)
    if existing is not None:
        existing.getparent().replace(existing, transform)
    else:
        shape.find(f'{{{P}}}spPr').insert(0, transform)


def fit_titles(slide, layout, master, slide_height):
    shapes = slide.findall(f'{{{P}}}cSld/{{{P}}}spTree/{{{P}}}sp')
    for shape in shapes:
        ph = placeholder(shape)
        if ph is None or ph.get('type') not in ('title', 'ctrTitle'):
            continue
        body = shape.find(f'{{{P}}}txBody')
        paragraphs = body.findall(f'{{{A}}}p') if body is not None else []
        if not any(paragraph_text(p).strip() for p in paragraphs):
            continue
        transform = deepcopy(inherited_transform(shape, layout, master))
        if transform is None:
            continue
        ext, off = transform.find(f'{{{A}}}ext'), transform.find(f'{{{A}}}off')
        props = body.find(f'{{{A}}}bodyPr')
        width = int(ext.get('cx')) / PT - 14.4
        measured = [(p, *line_ranges(p, width)) for p in paragraphs]
        required = sum(len(lines) * line_height + 6 for _, lines, line_height in measured) + 16
        old_height = int(ext.get('cy')) / PT
        if int(off.get('y')) / PT + required > slide_height - 18:
            raise ValueError('제목이 슬라이드보다 깁니다. 제목을 짧게 나눠주세요.')
        if required <= old_height:
            continue
        ext.set('cy', str(round(required * PT)))
        set_transform(shape, transform)
        for p, _, line_height in measured:
            body.replace(p, slice_paragraph(p, 0, len(paragraph_text(p)), line_height))
        if props is not None:
            props.set('anchor', 't')
        bottom = int(off.get('y')) + round((required + 12) * PT)
        for other in shapes:
            if other is shape:
                continue
            other_ph = placeholder(other)
            if other_ph is not None and other_ph.get('type') in ('dt','ftr','sldNum'):
                continue
            geom = deepcopy(inherited_transform(other, layout, master))
            if geom is None:
                continue
            other_off, other_ext = geom.find(f'{{{A}}}off'), geom.find(f'{{{A}}}ext')
            y = int(other_off.get('y'))
            if int(off.get('y')) < y < bottom:
                shift = bottom - y
                remaining = int(other_ext.get('cy')) - shift
                if remaining <= PT * 30:
                    raise ValueError('제목이 너무 길어 원문·번역을 배치할 공간이 없습니다. 제목을 짧게 나눠주세요.')
                other_off.set('y', str(bottom)); other_ext.set('cy', str(remaining))
                set_transform(other, geom)


def paginate_slide(archive, part, slide):
    layout_part, layout = related_xml(archive, part, 'slideLayout')
    _, master = related_xml(archive, layout_part, 'slideMaster') if layout_part else (None, None)
    slide_size = ET.fromstring(archive.read('ppt/presentation.xml')).find(f'{{{P}}}sldSz')
    fit_titles(slide, layout, master, int(slide_size.get('cy')) / PT)
    continuation = deepcopy(slide)
    for shape in continuation.findall(f'{{{P}}}cSld/{{{P}}}spTree/{{{P}}}sp'):
        ph = placeholder(shape)
        if ph is not None and ph.get('type') in ('title', 'ctrTitle'):
            body = shape.find(f'{{{P}}}txBody')
            if body is not None:
                for paragraph in list(body.findall(f'{{{A}}}p')):
                    body.remove(paragraph)
                ET.SubElement(body, f'{{{A}}}p')
    compact_untitled_slide(archive, part, continuation)
    continuation_shapes = continuation.find(f'{{{P}}}cSld/{{{P}}}spTree')
    columns = []
    for shape in slide.findall(f'{{{P}}}cSld/{{{P}}}spTree/{{{P}}}sp'):
        body = shape.find(f'{{{P}}}txBody')
        ph = placeholder(shape)
        if body is None or (ph is not None and ph.get('type') in ('title', 'ctrTitle', 'subTitle', 'dt', 'ftr', 'sldNum')):
            continue
        paragraphs = body.findall(f'{{{A}}}p')
        if not any(paragraph_text(p).strip() for p in paragraphs):
            continue
        transform = inherited_transform(shape, layout, master)
        if transform is None:
            raise ValueError('자동 슬라이드 분할: 본문 영역의 크기를 확인할 수 없습니다.')
        ext = transform.find(f'{{{A}}}ext')
        props = body.find(f'{{{A}}}bodyPr')
        width = int(ext.get('cx')) / PT
        height = int(ext.get('cy')) / PT
        # Use explicit margins; unspecified PPT defaults are .1in/.05in.
        for key, fallback in (('lIns', 91440), ('rIns', 91440), ('tIns', 45720), ('bIns', 45720)):
            value = int(props.get(key, fallback)) if props is not None else fallback
            if key in ('lIns', 'rIns'):
                width -= value / PT
            else:
                height -= value / PT
        # Leave room for Office's final baseline and rendering differences.
        index = shape.getparent().index(shape)
        next_transform = inherited_transform(continuation_shapes[index], layout, master)
        next_ext = next_transform.find(f'{{{A}}}ext')
        next_height = int(next_ext.get('cy')) / PT
        next_body = continuation_shapes[index].find(f'{{{P}}}txBody/{{{A}}}bodyPr')
        next_height -= sum(int(next_body.get(key, 45720)) / PT for key in ('tIns', 'bIns')) if next_body is not None else 7.2
        pages = paginate_paragraphs(paragraphs, max(1, width - 8),
                                    max(1, height - min(14, height * .04)),
                                    max(1, next_height - min(14, next_height * .04)))
        columns.append((index, pages))
    count = max((len(pages) for _, pages in columns), default=1)
    output = []
    for page in range(count):
        clone = deepcopy(slide if page == 0 else continuation)
        shapes = clone.find(f'{{{P}}}cSld/{{{P}}}spTree')
        for index, pages in columns:
            body = shapes[index].find(f'{{{P}}}txBody')
            for paragraph in list(body.findall(f'{{{A}}}p')):
                body.remove(paragraph)
            if page < len(pages):
                body.extend(deepcopy(pages[page]))
            else:
                ET.SubElement(body, f'{{{A}}}p')
            props = body.find(f'{{{A}}}bodyPr')
            if props is not None:
                props.set('anchor', 't')
        output.append(clone)
    return output


def paginate_package(path):
    ensure_fonts()
    path = Path(path)
    with zipfile.ZipFile(path) as source:
        data = {name: source.read(name) for name in source.namelist()}
        presentation = ET.fromstring(data['ppt/presentation.xml'])
        relationships = ET.fromstring(data['ppt/_rels/presentation.xml.rels'])
        types = ET.fromstring(data['[Content_Types].xml'])
        slide_list = presentation.find(f'{{{P}}}sldIdLst')
        if slide_list is None:
            return 0
        next_slide = max(int(posixpath.basename(n)[5:-4]) for n in data
                         if n.startswith('ppt/slides/slide') and n.endswith('.xml')) + 1
        next_id = max(int(n.get('id')) for n in slide_list) + 1
        used_rids = {n.get('Id') for n in relationships}
        added = 0
        for slide_id in list(slide_list):
            rid = slide_id.get(f'{{{DOC_R}}}id')
            relation = next(n for n in relationships if n.get('Id') == rid)
            target = relation.get('Target')
            part = target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/' + target)
            pages = paginate_slide(source, part, ET.fromstring(data[part]))
            data[part] = ET.tostring(pages[0], xml_declaration=True, encoding='UTF-8', standalone=True)
            insertion = slide_list.index(slide_id) + 1
            for page in pages[1:]:
                new_part = f'ppt/slides/slide{next_slide}.xml'; next_slide += 1
                data[new_part] = ET.tostring(page, xml_declaration=True, encoding='UTF-8', standalone=True)
                old_rels = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
                if old_rels in data:
                    rels = ET.fromstring(data[old_rels])
                    for item in list(rels):
                        if item.get('Type', '').endswith('/notesSlide'):
                            rels.remove(item)
                    data[f'ppt/slides/_rels/{posixpath.basename(new_part)}.rels'] = ET.tostring(rels)
                new_rid = f'rIdAutoSlide{next_id}'
                while new_rid in used_rids:
                    new_rid += '_'
                used_rids.add(new_rid)
                ET.SubElement(relationships, f'{{{R}}}Relationship', Id=new_rid,
                              Type=DOC_R + '/slide', Target=new_part[4:])
                item = ET.Element(f'{{{P}}}sldId', id=str(next_id), attrib={f'{{{DOC_R}}}id': new_rid})
                slide_list.insert(insertion, item); insertion += 1; next_id += 1
                ET.SubElement(types, f'{{{CT}}}Override', PartName='/' + new_part,
                              ContentType='application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
                added += 1
        data['ppt/presentation.xml'] = ET.tostring(presentation)
        data['ppt/_rels/presentation.xml.rels'] = ET.tostring(relationships)
        data['[Content_Types].xml'] = ET.tostring(types)
        if 'docProps/app.xml' in data:
            app = ET.fromstring(data['docProps/app.xml'])
            slides = app.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Slides')
            if slides is not None:
                slides.text = str(len(slide_list))
            data['docProps/app.xml'] = ET.tostring(app)
    fd, temporary = tempfile.mkstemp(suffix='.pptx', dir=path.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as target:
            for name, content in data.items():
                target.writestr(name, content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return added
