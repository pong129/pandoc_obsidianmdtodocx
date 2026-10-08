"""Reclaim the inherited title band on Pandoc slides without a title."""
from copy import deepcopy
import posixpath
from lxml import etree as ET

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/package/2006/relationships'
EMU = 914400


def related_xml(archive, part, relation):
    directory, filename = posixpath.split(part)
    rels = posixpath.join(directory, '_rels', filename + '.rels')
    if rels not in archive.namelist():
        return None, None
    for item in ET.fromstring(archive.read(rels)):
        if item.get('Type', '').endswith('/' + relation):
            target = item.get('Target', '')
            name = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(directory, target))
            if name in archive.namelist():
                return name, ET.fromstring(archive.read(name))
    return None, None


def placeholder(shape):
    return shape.find(f'.//{{{P}}}ph')


def own_transform(shape):
    if shape.tag == f'{{{P}}}graphicFrame':
        return shape.find(f'{{{P}}}xfrm')
    return shape.find(f'{{{P}}}spPr/{{{A}}}xfrm')


def inherited_transform(shape, layout, master):
    direct = own_transform(shape)
    ph = placeholder(shape)
    if ph is None:
        return direct
    inherited = None
    kind = ph.get('type', 'obj')
    if layout is not None:
        for candidate in layout.findall(f'.//{{{P}}}sp'):
            other = placeholder(candidate)
            if other is not None and ph.get('idx', '0') == other.get('idx', '0'):
                kind = other.get('type', 'obj')
                inherited = own_transform(candidate)
                break
    if inherited is None and master is not None:
        # A layout's generic content placeholder inherits the master's body.
        master_kind = 'body' if kind == 'obj' else kind
        for candidate in master.findall(f'.//{{{P}}}sp'):
            other = placeholder(candidate)
            if other is not None and other.get('type', 'obj') == master_kind:
                inherited = own_transform(candidate)
                break
    if direct is None:
        return inherited
    if inherited is not None:
        direct = deepcopy(direct)
        ext, default_ext = direct.find(f'{{{A}}}ext'), inherited.find(f'{{{A}}}ext')
        if ext is not None and default_ext is not None:
            for dimension in ('cx', 'cy'):
                if int(ext.get(dimension, '0')) == 0:
                    ext.set(dimension, default_ext.get(dimension))
    return direct


def compact_untitled_slide(archive, part, slide):
    """Move content as a group; never move a slide with a real title.

    Placeholder bounds are often absent from slide XML, so resolve the layout
    and master before writing explicit slide-level geometry.
    """
    tree = slide.find(f'{{{P}}}cSld/{{{P}}}spTree')
    if tree is None:
        return
    candidates = []
    for shape in tree:
        ph = placeholder(shape)
        kind = ph.get('type', 'obj') if ph is not None else ''
        text = ''.join(shape.itertext()).strip()
        if kind in ('title', 'ctrTitle'):
            if text:
                return
            continue
        if kind in ('dt', 'ftr', 'sldNum'):
            continue
        if shape.tag in (f'{{{P}}}pic', f'{{{P}}}graphicFrame') or (shape.tag == f'{{{P}}}sp' and text):
            candidates.append(shape)
    if not candidates:
        return
    layout_part, layout = related_xml(archive, part, 'slideLayout')
    _, master = related_xml(archive, layout_part, 'slideMaster') if layout_part else (None, None)
    presentation = ET.fromstring(archive.read('ppt/presentation.xml'))
    size = presentation.find(f'{{{P}}}sldSz')
    if size is None:
        return
    height = int(size.get('cy'))
    bounds = []
    for shape in candidates:
        transform = inherited_transform(shape, layout, master)
        if transform is None:
            return  # Don't partially move an arrangement with unknown geometry.
        off, ext = transform.find(f'{{{A}}}off'), transform.find(f'{{{A}}}ext')
        if off is None or ext is None:
            return
        bounds.append((shape, transform, int(off.get('x')), int(off.get('y')),
                       int(ext.get('cx')), int(ext.get('cy'))))
    margin = round(.25 * EMU)
    shift = max(0, min(b[3] for b in bounds) - margin)
    for shape, original, x, y, width, old_height in bounds:
        transform = deepcopy(original)
        off, ext = transform.find(f'{{{A}}}off'), transform.find(f'{{{A}}}ext')
        new_y = y - shift
        off.set('y', str(new_y))
        # Stretch text columns only when no content below shares their width.
        blockers = [b for b in bounds if b[0] is not shape and b[3] > y
                    and b[2] < x + width and b[2] + b[4] > x]
        ph = placeholder(shape)
        body = ph is not None and ph.get('type', 'obj') in ('obj', 'body')
        if body and shape.tag == f'{{{P}}}sp' and not blockers:
            ext.set('cy', str(max(old_height, height - margin - new_y)))
            props = shape.find(f'{{{P}}}txBody/{{{A}}}bodyPr')
            if props is not None:
                props.set('anchor', 't')
                props.set('anchorCtr', '0')
                props.set('tIns', '0')
        existing = own_transform(shape)
        if existing is not None:
            parent = existing.getparent()
            parent.replace(existing, transform)
        else:
            props = shape.find(f'{{{P}}}spPr')
            if props is None:
                props = ET.SubElement(shape, f'{{{P}}}spPr')
            props.insert(0, transform)
