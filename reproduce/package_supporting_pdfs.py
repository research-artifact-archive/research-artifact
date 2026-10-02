#!/usr/bin/env python3
"""Package existing PDFs without changing their page content.

Requires pypdf. Run after all three source PDFs have stable cross-references.
Writes a linked main.pdf and supplementary_material.pdf in a NEW directory,
plus a compatible technical_appendix.pdf with repaired bibliography links.
An optional front-matter PDF is prepended. Its wording is supplied separately.
Original printed page numbers are retained; PDF page labels are continuous.
"""
import argparse
import io
import math
from collections import Counter
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.constants import PageLabelStyle
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, TextStringObject


def drawing_fonts():
    """Register bundled, embedded fonts without machine-specific font paths."""
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    fonts = Path(reportlab.__file__).parent / 'fonts'
    for name, filename in [('PackSans', 'Vera.ttf'), ('PackSansBold', 'VeraBd.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(fonts / filename)))


def navigation_pdf(readers, paper_title=None):
    """One or two navigation pages derived from current PDF outlines."""
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    drawing_fonts()
    width, height = map(float, (readers['ta'].pages[0].mediabox.width,
                                readers['ta'].pages[0].mediabox.height))
    rows = []
    titles = {'ta': 'Part I: Proofs and definitions (Technical Appendix)',
              's': 'Part II: Validation and experimental detail (Supplement S1-S5)'}
    for key in ('ta', 's'):
        rows.append((True, titles[key], key, 0))
        section_number = 0
        for item in readers[key].outline:
            if not isinstance(item, list):
                section_number += 1
                label = chr(64 + section_number) if key == 'ta' else f'S{section_number}'
                rows.append((False, f'{label}  {item.title}', key,
                             readers[key].get_destination_page_number(item)))
    title_lines = []
    if paper_title:
        for word in paper_title.split():
            if not title_lines or pdfmetrics.stringWidth(title_lines[-1] + ' ' + word, 'PackSansBold', 10) > width - 100:
                title_lines.append(word)
            else:
                title_lines[-1] += ' ' + word
        if len(title_lines) > 3:
            raise ValueError('Paper title exceeds three lines; supply --front-matter')
    capacity = int((height - 245 - 14 * len(title_lines)) // 15)
    count = max(1, math.ceil(len(rows) / capacity))
    if count > 2:
        raise ValueError('Automatic contents exceeds two pages; supply --front-matter')
    offsets = {'ta': count, 's': count + len(readers['ta'].pages)}
    stream = io.BytesIO()
    c = canvas.Canvas(stream, pagesize=(width, height), initialFontName='PackSans', initialFontSize=9)
    c.setAuthor('Anonymous Authors'); c.setTitle('Reading guide and contents'); c.setCreator('Documentation build')
    for number in range(count):
        y = height - 55
        c.setFont('PackSansBold', 16); c.drawString(50, y, 'Supplementary Material'); y -= 28
        if title_lines:
            c.setFont('PackSansBold', 10)
            for title_line in title_lines:
                c.drawString(50, y, title_line); y -= 14
            y -= 8
        c.setFont('PackSans', 9)
        for line in ['Part I follows the argument: proofs and cases (A-C), requirement meaning and',
                     'execution (D-G), interface comparisons (H-I), PC2 (J), and records (K-P).',
                     'Part II adds witnesses (S1), implementation (S2), history proofs (S3),',
                     'current evaluation and separate auxiliary records (S4), and comparisons (S5).',
                     'Use continuous page numbers and bookmarks. Main paper: main.pdf.']:
            c.drawString(50, y, line); y -= 13
        y -= 15; c.setFont('PackSansBold', 10)
        c.drawString(50, y, 'Contents' if count == 1 else f'Contents ({number + 1}/{count})')
        c.drawRightString(width - 50, y, 'PDF page'); y -= 22
        for bold, title, key, page in rows[number * capacity:(number + 1) * capacity]:
            font, size = ('PackSansBold', 9) if bold else ('PackSans', 8)
            c.setFont(font, size)
            if pdfmetrics.stringWidth(title, font, size) > width - 155:
                raise ValueError('Contents title is too wide; supply --front-matter')
            c.drawString(50 if bold else 62, y, title)
            c.drawRightString(width - 50, y, str(offsets[key] + page + 1)); y -= 15
        c.showPage()
    c.save()
    return stream.getvalue()


def page_stamp(page, text):
    """Add a labelled global/component footer below the original page number."""
    from reportlab.pdfgen import canvas
    drawing_fonts()
    stream = io.BytesIO(); width, height = float(page.mediabox.width), float(page.mediabox.height)
    c = canvas.Canvas(stream, pagesize=(width, height), initialFontName='PackSans', initialFontSize=8)
    c.setAuthor('Anonymous Authors'); c.setTitle('Navigation footer'); c.setCreator('Documentation build')
    c.setFont('PackSans', 8); c.drawCentredString(width / 2, 18, text); c.save()
    page.merge_page(PdfReader(io.BytesIO(stream.getvalue())).pages[0])


def compatibility_appendix(source, main, output):
    """Repair only orphaned local citation links in a separate appendix copy."""
    source = Path(source).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Choose a new output file for the compatibility appendix')
    original = source.read_bytes()
    reader = PdfReader(io.BytesIO(original))
    main_reader = PdfReader(main)
    writer = PdfWriter(clone_from=reader)
    repaired = 0
    for page in writer.pages:
        for ref in page.get('/Annots', ArrayObject()).get_object():
            annotation = ref.get_object()
            action = annotation.get('/A')
            dest = annotation.get('/Dest')
            if dest is None and action and action.get('/S') == '/GoTo':
                dest = action.get('/D')
            if not isinstance(dest, str) or dest in reader.named_destinations:
                continue
            if not dest.startswith('cite.') or dest not in main_reader.named_destinations:
                raise ValueError(f'Unresolved component destination: {dest}')
            if action and '/Next' in action:
                raise ValueError('Chained component navigation requires explicit handling')
            annotation[NameObject('/A')] = DictionaryObject({
                NameObject('/S'): NameObject('/GoToR'),
                NameObject('/F'): TextStringObject('main.pdf'),
                NameObject('/D'): TextStringObject(dest),
            })
            annotation.pop('/Dest', None)
            repaired += 1
    with output.open('wb') as stream:
        writer.write(stream)
    result = PdfReader(output)
    if len(result.pages) != len(reader.pages):
        raise ValueError('Component page count changed')
    if set(result.named_destinations) != set(reader.named_destinations):
        raise ValueError('Component named destinations changed')
    for source_page, copied in zip(reader.pages, result.pages):
        if copied.extract_text() != source_page.extract_text():
            raise ValueError('Component page text changed')
        if copied.get_contents().get_data() != source_page.get_contents().get_data():
            raise ValueError('Component page drawing content changed')
        source_annots = source_page.get('/Annots', ArrayObject()).get_object()
        output_annots = copied.get('/Annots', ArrayObject()).get_object()
        if len(source_annots) != len(output_annots):
            raise ValueError('Component annotation was lost')
        for ref in output_annots:
            annotation = ref.get_object()
            action = annotation.get('/A')
            dest = annotation.get('/Dest')
            target = result
            if action and action.get('/S') in ('/GoTo', '/GoToR'):
                dest = action.get('/D')
                if action['/S'] == '/GoToR':
                    file = action.get('/F')
                    file = file.get('/F') if isinstance(file, dict) else str(file)
                    if Path(file).name != 'main.pdf':
                        continue
                    target = main_reader
            if isinstance(dest, str) and dest not in target.named_destinations:
                raise ValueError(f'Output component link has no destination: {dest}')
    if source.read_bytes() != original:
        raise ValueError('Input appendix changed')
    return repaired


def package(main, technical_appendix, supplement, output, front_matter=None,
            auto_guide=False, visible_page_numbers=False, title=None):
    paths = {'main': Path(main), 'ta': Path(technical_appendix), 's': Path(supplement)}
    if front_matter:
        paths['front'] = Path(front_matter)
    paths = {k: v.resolve() for k, v in paths.items()}
    original = {k: p.read_bytes() for k, p in paths.items()}
    readers = {k: PdfReader(p) for k, p in paths.items()}
    if auto_guide:
        if front_matter:
            raise ValueError('Choose either --auto-guide or --front-matter')
        readers['front'] = PdfReader(io.BytesIO(navigation_pdf(readers, title)))
    writers = {'main': PdfWriter(), 'support': PdfWriter()}
    owner = {k: ('main' if k == 'main' else 'support') for k in readers}
    output_names = {'main': 'main.pdf', 'support': 'supplementary_material.pdf'}
    order = ['main'] + (['front'] if 'front' in readers else []) + ['ta', 's']
    offsets = {}
    stats = Counter()
    for key in order:
        writer = writers[owner[key]]
        offsets[key] = len(writer.pages)
        # add_page retains annotations; import/remap them ourselves below.
        for page in readers[key].pages:
            writer.add_page(page)

    def named(key, name):
        return str(name) if key == 'main' else key + '::' + str(name)

    for key in order:
        writer = writers[owner[key]]
        for name, dest in readers[key].named_destinations.items():
            number = readers[key].get_destination_page_number(dest)
            if number is None or number < 0:
                raise ValueError(f'Invalid source named destination: {key}:{name}')
            array = ArrayObject([writer.pages[offsets[key] + number].indirect_reference,
                                 *list(dest.dest_array)[1:]])
            writer.add_named_destination_array(TextStringObject(named(key, name)), array)

    file_keys = {}
    for key, path in paths.items():
        if path.name in file_keys:
            raise ValueError('Input PDF basenames must be distinct')
        file_keys[path.name] = key

    def destination(source_key, target_key, dest, remote_source):
        if isinstance(dest, str):
            if dest not in readers[target_key].named_destinations:
                # xr-hyper citations can be emitted as local links to the main
                # bibliography. Repair only when that exact name is unambiguous.
                candidates = [k for k, r in readers.items() if dest in r.named_destinations]
                if not remote_source and str(dest).startswith('cite.') and len(candidates) == 1:
                    target_key = candidates[0]
                    stats['repaired_citation_links'] += 1
                else:
                    raise ValueError(f'Unresolved destination: {source_key}->{target_key}:{dest}')
            value = TextStringObject(named(target_key, dest))
        elif isinstance(dest, (list, ArrayObject)):
            page = dest[0]
            number = int(page) if remote_source and isinstance(page, (int, NumberObject)) else readers[target_key].get_page_number(page.get_object())
            if not 0 <= number < len(readers[target_key].pages):
                raise ValueError('Invalid explicit destination page')
            out_number = offsets[target_key] + number
            if owner[source_key] == owner[target_key]:
                page = writers[owner[target_key]].pages[out_number].indirect_reference
            else:
                page = NumberObject(out_number)
            value = ArrayObject([page, *list(dest)[1:]])
        else:
            raise ValueError(f'Unsupported destination type: {type(dest)}')
        if owner[source_key] == owner[target_key]:
            result = DictionaryObject({NameObject('/S'): NameObject('/GoTo'), NameObject('/D'): value})
            stats['internal_links'] += 1
        else:
            result = DictionaryObject({NameObject('/S'): NameObject('/GoToR'),
                                       NameObject('/F'): TextStringObject(output_names[owner[target_key]]),
                                       NameObject('/D'): value})
            stats['remote_links'] += 1
        return result

    for key in order:
        writer = writers[owner[key]]
        for index, source_page in enumerate(readers[key].pages):
            output_page = writer.pages[offsets[key] + index]
            src_annots = source_page.get('/Annots', ArrayObject()).get_object()
            out_annots = output_page.get('/Annots', ArrayObject()).get_object()
            if len(src_annots) != len(out_annots):
                raise ValueError('Annotation count changed while copying a page')
            for source_ref, output_ref in zip(src_annots, out_annots):
                source_annotation = source_ref.get_object()
                output_annotation = output_ref.get_object()
                action = source_annotation.get('/A')
                if '/Dest' in source_annotation:
                    output_annotation[NameObject('/A')] = destination(key, key, source_annotation['/Dest'], False)
                    output_annotation.pop('/Dest', None)
                elif action and action.get('/S') in ('/GoTo', '/GoToR'):
                    if '/Next' in action:
                        raise ValueError('Chained navigation actions require explicit handling')
                    remote = action.get('/S') == '/GoToR'
                    target = key
                    if remote:
                        file = action.get('/F')
                        file = file.get('/F') if isinstance(file, dict) else str(file)
                        target = file_keys.get(Path(file).name)
                        if target is None:
                            stats['unchanged_external_file_links'] += 1
                            continue
                    output_annotation[NameObject('/A')] = destination(key, target, action['/D'], remote)

    def outlines(key, nodes, parent=None):
        writer = writers[owner[key]]
        previous = parent
        for node in nodes:
            if isinstance(node, list):
                outlines(key, node, previous)
            else:
                page = readers[key].get_destination_page_number(node)
                if page is None or page < 0:
                    raise ValueError(f'Invalid outline destination: {key}:{node.title}')
                previous = writer.add_outline_item(node.title, offsets[key] + page, parent=parent)

    for key in order:
        parent = None
        if key != 'main':
            part_title = {'front': 'Reading guide and contents', 'ta': 'Part I: Proofs and definitions',
                          's': 'Part II: Experimental detail (S1-S5)'}[key]
            parent = writers['support'].add_outline_item(part_title, offsets[key], bold=True)
        outlines(key, readers[key].outline, parent)
    for key, writer in writers.items():
        document_title = (title or 'Main paper') if key == 'main' else ((title + ' - ') if title else '') + 'Supplementary Material'
        writer.add_metadata({'/Title': document_title,
                             '/Author': 'Anonymous Authors'})
        writer.set_page_label(0, len(writer.pages) - 1, style=PageLabelStyle.DECIMAL, start=1)
    if visible_page_numbers:
        total = len(writers['support'].pages)
        for key in order:
            if key == 'main':
                continue
            part = {'front': 'Guide', 'ta': 'Part I', 's': 'Part II'}[key]
            for number in range(len(readers[key].pages)):
                absolute = offsets[key] + number
                label = (f'Supplementary p. {absolute + 1} / {total}  |  '
                         f'{part} p. {number + 1} / {len(readers[key].pages)}')
                page_stamp(writers['support'].pages[absolute], label)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Choose a new output directory')
    output.mkdir(parents=True)
    for key, writer in writers.items():
        with (output / output_names[key]).open('wb') as stream:
            writer.write(stream)
    # Self-check navigation and page content after serialization.
    result = {key: PdfReader(output / name) for key, name in output_names.items()}
    for key in order:
        target = result[owner[key]]
        for index, source_page in enumerate(readers[key].pages):
            copied = target.pages[offsets[key] + index]
            text, source_text = copied.extract_text(), source_page.extract_text()
            if (source_text not in text if visible_page_numbers and key != 'main' else text != source_text):
                raise ValueError('Page text changed')
            if len(copied.get('/Annots', ArrayObject()).get_object()) != len(source_page.get('/Annots', ArrayObject()).get_object()):
                raise ValueError('Annotation was lost')
            if not (visible_page_numbers and key != 'main') and copied.get_contents().get_data() != source_page.get_contents().get_data():
                raise ValueError('Page drawing content changed')
        if key in paths and paths[key].read_bytes() != original[key]:
            raise ValueError('Input PDF changed')
    for owner_key, reader in result.items():
        for page in reader.pages:
            for ref in page.get('/Annots', []):
                action = ref.get_object().get('/A')
                if not action or action.get('/S') not in ('/GoTo', '/GoToR'):
                    continue
                target = reader
                if action['/S'] == '/GoToR':
                    file = str(action['/F'])
                    targets = [k for k, v in output_names.items() if v == file]
                    if not targets:
                        continue
                    target = result[targets[0]]
                dest = action['/D']
                if isinstance(dest, str) and dest not in target.named_destinations:
                    raise ValueError('Output link has no destination')
    stats['repaired_component_citation_links'] = compatibility_appendix(
        paths['ta'], output / output_names['main'], output / 'technical_appendix.pdf')
    stats.update(main_pages=len(result['main'].pages), supplementary_pages=len(result['support'].pages))
    print('PASS', dict(stats))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main', required=True, type=Path)
    parser.add_argument('--technical-appendix', required=True, type=Path)
    parser.add_argument('--supplement', required=True, type=Path)
    parser.add_argument('--front-matter', type=Path)
    parser.add_argument('--auto-guide', action='store_true', help='Generate a neutral contents page from the input outlines (requires reportlab)')
    parser.add_argument('--visible-page-numbers', action='store_true', help='Add explicitly labelled continuous/component footer numbers (requires reportlab)')
    parser.add_argument('--title', help='Full main-paper title to show on the reading guide and in PDF metadata')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    package(args.main, args.technical_appendix, args.supplement, args.output, args.front_matter,
            args.auto_guide, args.visible_page_numbers, args.title)


if __name__ == '__main__':
    main()
