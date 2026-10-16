"""Set the embedded metadata of files/<id>.pdf from bib/<id>.bib and shrink oversized PDFs.

Usage (from the repository root, needs PyMuPDF: pip install pymupdf):
    python scripts/optimize_pdfs.py            # every publication
    python scripts/optimize_pdfs.py <id> ...   # only these

- Title, Author and Subject come from the BibTeX entry, so search engines and PDF readers
  show the real title instead of e.g. "Microsoft Word - ...".
- PDFs larger than 5 MB get their images downsampled to 200 dpi at the size they are drawn
  on the page (Google Scholar may skip very large PDFs). Text and vector graphics are untouched.
- A PDF is only replaced if the result keeps the same page count and the same text.
"""
import os
import re
import sys
import tempfile

import fitz  # PyMuPDF

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibtex  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE_LIMIT = 5_000_000
# (dpi, jpeg quality) tried in order until the PDF fits under SIZE_LIMIT
LEVELS = [(200, 85), (150, 75)]
MIN_IMAGE_BYTES = 150_000

fitz.TOOLS.mupdf_display_errors(False)


def bib_metadata(pid):
    entry = bibtex.parse(open(os.path.join(ROOT, 'bib', f'{pid}.bib'), encoding='utf-8').read())
    f = {k: bibtex.latex_to_unicode(v) for k, v in entry['fields'].items()}
    authors = '; '.join(f'{given} {family}'.strip() for family, given in bibtex.authors(entry['fields']['author']))
    venue = f.get('journal') or f.get('booktitle') or f.get('school') or f.get('howpublished') or ''
    return {'title': f['title'], 'author': authors, 'subject': ', '.join(x for x in (venue, f['year']) if x)}


def drawn_sizes(doc):
    """{xref: (width, height)} — largest size in points at which each image is drawn."""
    sizes = {}
    for page in doc:
        for xref in {img[0] for img in page.get_images(full=True)}:
            for rect in page.get_image_rects(xref):
                w, h = sizes.get(xref, (0, 0))
                sizes[xref] = (max(w, rect.width), max(h, rect.height))
    return sizes


def load_image(doc, xref, smask):
    """Image as an RGB/gray Pixmap, with alpha only if its soft mask is not fully opaque."""
    pix = fitz.Pixmap(doc, xref)
    if pix.n - pix.alpha == 4:  # CMYK -> RGB
        pix = fitz.Pixmap(fitz.csRGB, pix)
    if smask:
        mask = fitz.Pixmap(doc, smask)
        if min(mask.samples) < 255 and (mask.width, mask.height) == (pix.width, pix.height):
            pix = fitz.Pixmap(pix, mask)
    return pix


def shrink_images(doc, dpi, quality):
    seen, changed = set(), 0
    sizes = drawn_sizes(doc)
    for page in doc:
        for img in page.get_images(full=True):
            xref, smask, w, h, filt = img[0], img[1], img[2], img[3], img[8]
            if xref in seen:
                continue
            seen.add(xref)
            size = len(doc.xref_stream_raw(xref)) + (len(doc.xref_stream_raw(smask)) if smask else 0)
            if size < MIN_IMAGE_BYTES:
                continue
            draw_w, draw_h = sizes.get(xref, (0, 0))
            if not draw_w:
                continue
            scale = min(1.0, max(draw_w / 72 * dpi / w, draw_h / 72 * dpi / h))
            pix = load_image(doc, xref, smask)
            if pix.n - pix.alpha not in (1, 3):
                continue
            photo = not pix.alpha and (filt == 'DCTDecode' or fitz.Pixmap(pix, 64, 64, None).color_count() > 256)
            if scale > 0.9 and not photo:
                continue
            if scale < 0.9:
                pix = fitz.Pixmap(pix, max(1, round(w * scale)), max(1, round(h * scale)), None)
            if photo:
                page.replace_image(xref, stream=pix.tobytes('jpg', jpg_quality=quality))
            else:
                page.replace_image(xref, pixmap=pix)
            changed += 1
    return changed


def apply_metadata(doc, current, meta, wrong_xmp):
    doc.set_metadata({**current, **meta})
    if wrong_xmp:
        doc.del_xml_metadata()  # a stale XMP title would override the corrected one in some readers


def page_texts(doc):
    return [re.sub(r'\s+', ' ', page.get_text()).strip() for page in doc]


def temp_path(path):
    fd, tmp = tempfile.mkstemp(suffix='.pdf', dir=os.path.dirname(path))
    os.close(fd)
    return tmp


def compressed_copy(path, dpi, quality, metadata):
    """Write a copy of path with resampled images; return (tmp_path, images_changed)."""
    doc = fitz.open(path)
    images = shrink_images(doc, dpi, quality)
    metadata(doc)
    tmp = temp_path(path)
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    return tmp, images


def metadata_copy(path, metadata):
    """Copy of path with only an incremental metadata update appended (original bytes untouched)."""
    tmp = temp_path(path)
    with open(path, 'rb') as src, open(tmp, 'wb') as dst:
        dst.write(src.read())
    doc = fitz.open(tmp)
    metadata(doc)
    try:
        doc.saveIncr()
        doc.close()
    except (RuntimeError, ValueError):  # damaged xref table: a full rewrite repairs it
        doc.save(tmp + '.full', garbage=1)
        doc.close()
        os.replace(tmp + '.full', tmp)
    return tmp


def optimize(pid):
    path = os.path.join(ROOT, 'files', f'{pid}.pdf')
    before = os.path.getsize(path)
    doc = fitz.open(path)
    original_text = page_texts(doc)
    meta = bib_metadata(pid)
    current = doc.metadata or {}
    needs_meta = any((current.get(k) or '') != v for k, v in meta.items())
    xmp_title = re.search(r'<dc:title>.*?<rdf:li[^>]*>(.*?)</rdf:li>', doc.get_xml_metadata() or '', re.S)
    wrong_xmp = bool(xmp_title) and xmp_title.group(1).strip() != meta['title']
    doc.close()
    if before <= SIZE_LIMIT and not (needs_meta or wrong_xmp):
        return f'{pid:24} unchanged'

    def metadata(d):
        apply_metadata(d, current, meta, wrong_xmp)

    tmp, note = None, ''
    if before > SIZE_LIMIT:
        for dpi, quality in LEVELS:
            if tmp:
                os.remove(tmp)
            tmp, images = compressed_copy(path, dpi, quality, metadata)
            note = f', {images} images resampled at {dpi} dpi'
            if os.path.getsize(tmp) <= SIZE_LIMIT:
                break
        if os.path.getsize(tmp) >= before:
            os.remove(tmp)
            tmp = None
    if tmp is None:
        if not (needs_meta or wrong_xmp):
            return f'{pid:24} unchanged (could not shrink)'
        tmp, note = metadata_copy(path, metadata), ''

    check = fitz.open(tmp)
    same = check.page_count == len(original_text) and page_texts(check) == original_text
    check.close()
    if not same:
        os.remove(tmp)
        return f'{pid:24} SKIPPED (content changed)'
    after = os.path.getsize(tmp)
    os.replace(tmp, path)
    return f'{pid:24} {before / 1e6:6.1f} MB -> {after / 1e6:6.1f} MB  metadata set{note}'


def main():
    ids = sys.argv[1:] or sorted(name[:-4] for name in os.listdir(os.path.join(ROOT, 'bib')) if name.endswith('.bib'))
    for pid in ids:
        print(optimize(pid))


if __name__ == '__main__':
    main()
