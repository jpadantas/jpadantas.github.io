"""Generate the publication pages from bib/, abstract/ and publications.json.

Usage (from the repository root):
    python scripts/build.py

Outputs:
    publications/<id>/index.html   one page per publication (Google Scholar meta tags)
    publications/index.html        redirect to /publications.html
    publications.html              only the regions between the "BEGIN generated" markers
    sitemap.xml
    img/opt/*.webp                 resized copies of the images; the <img> tags of
                                   PAGE_IMAGE_WIDTHS pages are pointed to them (needs Pillow)
"""
import datetime
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from string import Template

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibtex  # noqa: E402
import images  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://www.joaopadantas.com'
MONTHS = {m: i for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}

# type -> (list tooltip, icon classes, opens in new tab, label on the publication page)
LINKS = {
    'pdf': ('Download PDF', 'fa-solid fa-file-pdf', False, 'PDF'),
    'publisher': ('Publisher Link', 'ai ai-doi', True, 'Publisher'),
    'github': ('GitHub Repository', 'fa-brands fa-github', True, 'Code'),
    'arxiv': ('arXiv Preprint', 'ai ai-arxiv', True, 'arXiv'),
    'slides': ('View Slides', 'fa-solid fa-person-chalkboard', False, 'Slides'),
    'poster': ('View Poster', 'fa-solid fa-print', False, 'Poster'),
    'video': ('Watch Video', 'fa-brands fa-youtube', True, 'Video'),
    'researchgate': ('ResearchGate', 'ai ai-researchgate', True, 'ResearchGate'),
    'library': ('ITA Library', 'fa-solid fa-book', True, 'ITA Library'),
}
# Hand-written pages whose images are swapped for resized WebP copies (value: widest display size x2).
PAGE_IMAGE_WIDTHS = {'index.html': 440, 'software.html': 320, 'research.html': 960, 'media.html': 640}
LIST_THUMB_WIDTH = 320  # shown at 160 px in publications.html
PAGE_THUMB_WIDTH = 880  # shown at 440 px on each publication page
MAIN_PAGES = [('', '1.00'), ('publications.html', '0.90'), ('software.html', '0.80'),
              ('research.html', '0.80'), ('awards.html', '0.70'), ('media.html', '0.70')]

esc = html.escape


def read(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()


def write(path, text):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


def git_date(*paths):
    """Last commit date (YYYY-MM-DD) touching any of paths; today if uncommitted."""
    try:
        out = subprocess.run(['git', 'log', '-1', '--format=%cs', '--', *paths], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        out = ''
    dirty = subprocess.run(['git', 'status', '--porcelain', '--', *paths], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    return datetime.date.today().isoformat() if dirty or not out else out


def absolute(url):
    """Site-relative URL (files/x.pdf) -> root-relative (/files/x.pdf); external URLs unchanged."""
    return url if re.match(r'^(https?:|mailto:|#|/)', url) else '/' + url


# ---------------------------------------------------------------------------- data

def load():
    data = json.loads(read('publications.json'))
    pubs, problems = [], []
    for section in data['sections']:
        for i, item in enumerate(section['items']):
            pid = item['id']
            for path in (f'bib/{pid}.bib', f'abstract/{pid}.txt', f'files/{pid}.pdf', item['thumbnail']):
                if not os.path.exists(os.path.join(ROOT, path)):
                    problems.append(f'{pid}: missing {path}')
            if problems:
                continue
            raw_bib = read(f'bib/{pid}.bib').strip()
            entry = bibtex.parse(raw_bib)
            f = {k: bibtex.latex_to_unicode(v) for k, v in entry['fields'].items()}
            pubs.append({**item, 'section': section, 'first_in_section': i < 3, 'bib': raw_bib,
                         'type': entry['type'], 'f': f,
                         'authors': bibtex.authors(entry['fields']['author']),
                         'abstract': re.sub(r'\s+', ' ', read(f'abstract/{pid}.txt')).strip()})
    listed = {p['id'] for p in pubs}
    for name in sorted(os.listdir(os.path.join(ROOT, 'bib'))):
        if name.endswith('.bib') and name[:-4] not in listed and not problems:
            problems.append(f'{name[:-4]}: bib/{name} is not listed in publications.json')
    if problems:
        sys.exit('Build stopped:\n  ' + '\n  '.join(problems))
    for p in pubs:  # all thumbnails are shown at the same square size
        w, h = images.size_of(p['thumbnail'])
        if abs(w - h) > max(w, h) * 0.02:
            print(f"Warning: {p['thumbnail']} is {w}x{h}, not square; pad it with white to {max(w, h)}x{max(w, h)}")
    return data, pubs


def is_me(family, given):
    return family == 'Dantas' and given.startswith('Jo')


def authors_html(p):
    names = []
    for n, (family, given) in enumerate(p['authors'], 1):
        name = esc(f'{given} {family}'.strip())
        if is_me(family, given):
            name = f'<span class="author-highlight">{name}</span>'
        if n in p.get('equal_contribution', []):
            name += '*'
        names.append(name)
    return ', '.join(names)


def date_parts(p):
    year = p['f']['year']
    month = MONTHS.get(p['f'].get('month', '').lower()[:3])
    return year, month


def kind_label(p):
    kind = p['section']['kind']
    if kind == 'thesis':
        if p['type'] == 'phdthesis':
            return 'Ph.D. Thesis'
        return p['f'].get('type', "Master's Thesis")
    return {'journal': 'Journal Article', 'conference': 'Conference Paper', 'preprint': 'Preprint'}[kind]


def full_reference(p):
    """Venue line for the publication page, e.g. 'Journal, 23(4):579–599, 2026'."""
    f, parts = p['f'], []
    if p['type'] == 'article':
        vol = f.get('volume', '') + (f"({f['number']})" if f.get('number') else '')
        if vol and not f.get('pages'):
            vol = f'vol. {vol}'  # e.g. early-access articles: "IEEE Access, vol. 14, 2026"
        parts = [f['journal'], vol + (f":{f['pages']}" if f.get('pages') and vol else '')]
        if f.get('pages') and not vol:
            parts.append(f"pp. {f['pages']}")
    elif p['type'] == 'inproceedings':
        parts = [f['booktitle'], f.get('series', ''), f"pp. {f['pages']}" if f.get('pages') else '']
    elif p['type'] in ('phdthesis', 'mastersthesis'):
        parts = [f['school']]
    else:
        parts = [f.get('howpublished', '')]
    year, month = date_parts(p)
    parts.append(year)
    return ', '.join(x for x in parts if x)


def page_title(title, limit=70):
    """<title> text within `limit` chars (search engines flag longer titles); the full title stays in <h1>."""
    if len(title) <= limit:
        return title
    return title[:limit - 1].rsplit(' ', 1)[0].rstrip(' :,;–-') + '…'


def summary(text, limit=160):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(' ', 1)[0].rstrip(',;:') + '…'


def page_url(p):
    return f"{SITE}/publications/{p['id']}/"


# ---------------------------------------------------------------------------- publication page

def scholar_meta(p):
    f, meta = p['f'], []
    add = lambda name, value: value and meta.append(f'  <meta name="{name}" content="{esc(value)}" />')
    add('citation_title', f['title'])
    for family, given in p['authors']:
        add('citation_author', f'{family}, {given}' if given else family)
    year, month = date_parts(p)
    add('citation_publication_date', f'{year}/{month:02d}' if month else year)
    if p['type'] == 'article':
        add('citation_journal_title', f.get('journal'))
    elif p['type'] == 'inproceedings':
        add('citation_conference_title', f.get('booktitle'))
    elif p['type'] in ('phdthesis', 'mastersthesis'):
        add('citation_dissertation_institution', f.get('school'))
    add('citation_publisher', f.get('publisher') or (f.get('howpublished') if p['type'] == 'misc' else ''))
    add('citation_volume', f.get('volume'))
    add('citation_issue', f.get('number'))
    if f.get('pages'):
        first, _, last = f['pages'].partition('–')
        add('citation_firstpage', first.strip())
        add('citation_lastpage', last.strip())
    add('citation_doi', f.get('doi'))
    add('citation_isbn', f.get('isbn'))
    add('citation_issn', f.get('issn'))
    add('citation_language', p.get('language', 'en'))
    add('citation_abstract_html_url', page_url(p))
    add('citation_pdf_url', f"{SITE}/files/{p['id']}.pdf")
    return '\n'.join(meta)


def json_ld(p):
    f = p['f']
    year, month = date_parts(p)
    data = {
        '@context': 'https://schema.org',
        '@type': 'Thesis' if p['section']['kind'] == 'thesis' else 'ScholarlyArticle',
        'headline': f['title'],
        'name': f['title'],
        'author': [{'@type': 'Person', 'name': f'{g} {fam}'.strip(),
                    **({'url': SITE} if is_me(fam, g) else {})} for fam, g in p['authors']],
        'datePublished': f'{year}-{month:02d}' if month else year,
        'abstract': p['abstract'],
        'inLanguage': p.get('language', 'en'),
        'image': f"{SITE}/{p['thumbnail']}",
        'url': page_url(p),
    }
    if f.get('journal'):
        data['isPartOf'] = {'@type': 'Periodical', 'name': f['journal']}
    if f.get('doi'):
        data['sameAs'] = f"https://doi.org/{f['doi']}"
    return json.dumps(data, ensure_ascii=False, indent=2).replace('</', '<\\/')


def highlight_bibtex(raw):
    text = esc(raw, quote=False)
    text = re.sub(r'^@(\w+)\{([^,]+),', r'<span class="bib-type">@\1</span>{<span class="bib-key">\2</span>,', text)
    return re.sub(r'^(\s+)(\w+)(\s*=)', r'\1<span class="bib-field">\2</span>\3', text, flags=re.M)


def page_buttons(p):
    links = [{'type': 'pdf', 'url': f"files/{p['id']}.pdf"}] + p['links']
    out = []
    for link in links:
        _, icon, external, label = LINKS[link['type']]
        if link['type'] == 'publisher' and 'doi.org' in link['url']:
            label = 'DOI'
        target = ' target="_blank" rel="noopener"' if external else ''
        out.append(f'<a href="{esc(absolute(link["url"]))}"{target}><i class="{icon}"></i> {label}</a>')
    out.append('<a href="#cite"><i class="fa-solid fa-quote-right"></i> Cite</a>')
    return '\n          '.join(out)


def site_chrome(publications_html):
    """Header and footer of publications.html, with links made root-relative."""
    def fix(block):
        return re.sub(r'(href|src)="([^"]*)"', lambda m: f'{m.group(1)}="{absolute(m.group(2)) if m.group(2) != "./" else "/"}"', block)
    header = re.search(r'<header class="site-header">.*?</header>', publications_html, re.S).group(0)
    footer = re.search(r'<footer class="site-footer">.*?</footer>', publications_html, re.S).group(0)
    return fix(header), fix(footer)


def css_version():
    """Short hash of css/style.css, so browsers fetch the stylesheet again when it changes."""
    with open(os.path.join(ROOT, 'css', 'style.css'), 'rb') as f:
        return hashlib.sha1(f.read().replace(b'\r\n', b'\n')).hexdigest()[:8]


def render_page(p, template, header, footer):
    thumb, thumb_w, thumb_h = images.optimized(p['thumbnail'], PAGE_THUMB_WIDTH)
    lang = p.get('language', 'en')
    lang_attr = f' lang="{lang}"' if lang != 'en' else ''
    year, _ = date_parts(p)
    description = summary(p['abstract'])
    return template.substitute(
        id=p['id'],
        css_version=css_version(),
        page_title=esc(page_title(p['f']['title'])),
        title=esc(p['f']['title']),
        description=esc(description),
        url=page_url(p),
        scholar_meta=scholar_meta(p),
        json_ld=json_ld(p),
        og_title=esc(p['f']['title']),
        og_description=esc(f"{p['venue']}. {description}"),
        image=f"{SITE}/{p['thumbnail']}",
        header=header,
        footer=footer,
        kind=esc(f'{kind_label(p)} · {year}'),
        lang_attr=lang_attr,
        authors=authors_html(p),
        equal_note='\n        <div class="pub-note">* Equal contribution</div>' if p.get('equal_contribution') else '',
        reference=esc(full_reference(p)),
        buttons=page_buttons(p),
        thumbnail=esc(absolute(thumb)),
        thumb_width=thumb_w,
        thumb_height=thumb_h,
        thumbnail_alt=esc(p['thumbnail_alt']),
        abstract=esc(p['abstract']),
        bibtex=highlight_bibtex(p['bib']),
    )


# ---------------------------------------------------------------------------- publications.html

def render_list_item(p):
    pid = p['id']
    thumb, thumb_w, thumb_h = images.optimized(p['thumbnail'], LIST_THUMB_WIDTH)
    reveal = ' reveal' if p['first_in_section'] else ''
    links = [{'type': 'pdf', 'url': f'files/{pid}.pdf'}] + p['links']
    link_html = []
    for link in links:
        tooltip, icon, external, _ = LINKS[link['type']]
        target = ' target="_blank"' if external else ''
        link_html.append(f'            <a href="{esc(link["url"])}"{target} title="{tooltip}"><i class="{icon}"></i></a>')
    # Real hrefs keep the links crawlable; the onclick handlers keep the in-page behaviour.
    link_html.append(f'            <a href="#abstract-{pid}" onclick="toggleAbstract(\'{pid}\'); return false;" title="Abstract"><i class="fa-solid fa-align-left"></i></a>')
    link_html.append(f'            <a href="publications/{pid}/#cite" onclick="openBibtex(\'{pid}\'); return false;" title="Cite"><i class="fa-solid fa-quote-right"></i></a>')
    note = '\n          <div class="pub-note">* Equal contribution</div>' if p.get('equal_contribution') else ''
    lang = f' lang="{p["language"]}"' if p.get('language') else ''
    return f'''      <div class="publication-item-with-thumb{reveal}" id="{pid}">
        <div class="pub-thumb">
          <img width="{thumb_w}" height="{thumb_h}" alt="{esc(p['thumbnail_alt'])}" loading="lazy" src="{esc(thumb)}" />
        </div>
        <div class="pub-content">
          <div class="pub-title"{lang}>
            <a href="publications/{pid}/">{esc(p['f']['title'])}</a>
          </div>
          <div class="pub-authors">
            {authors_html(p)}
          </div>{note}
          <div class="pub-venue">
            {esc(p['venue'])}
          </div>
          <div class="pub-links">
{chr(10).join(link_html)}
          </div>
          <div class="pub-abstract" id="abstract-{pid}"{lang} style="display: none;">
            <p><strong>Abstract:</strong> {esc(p['abstract'])}</p>
          </div>
        </div>
      </div>'''


def render_list(data, pubs):
    by_id = {p['id']: p for p in pubs}
    out = []
    for section in data['sections']:
        out.append(f'    <section class="publications-section">\n      <h2 class="section-title">{esc(section["title"])}</h2>')
        year = None
        for item in section['items']:
            p = by_id[item['id']]
            if p['f']['year'] != year:
                year = p['f']['year']
                out.append(f'      <!-- {year} -->')
            out.append(render_list_item(p))
        out.append('    </section>')
    return '\n'.join(out)


def render_item_list(pubs):
    items = [{'@type': 'ListItem', 'position': i, 'url': page_url(p), 'name': p['f']['title']}
             for i, p in enumerate(pubs, 1)]
    data = {'@context': 'https://schema.org', '@type': 'ItemList', 'itemListElement': items}
    body = json.dumps(data, ensure_ascii=False, indent=2).replace('</', '<\\/')
    return '  <script type="application/ld+json">\n' + body + '\n  </script>'


def replace_region(text, name, content):
    pattern = re.compile(rf'(<!-- BEGIN generated:{name} [^>]*-->\r?\n).*?(\r?\n[ \t]*<!-- END generated:{name} -->)', re.S)
    if not pattern.search(text):
        sys.exit(f'publications.html: markers for "{name}" not found')
    return pattern.sub(lambda m: m.group(1) + content + m.group(2), text)


# ---------------------------------------------------------------------------- sitemap

def render_sitemap(pubs):
    rows = []
    for path, priority in MAIN_PAGES:
        lastmod = git_date(path or 'index.html')
        rows.append((f'{SITE}/{path}', lastmod, priority))
    for p in pubs:
        pid = p['id']
        lastmod = git_date(f'bib/{pid}.bib', f'abstract/{pid}.txt', f'files/{pid}.pdf', 'publications.json')
        rows.append((page_url(p), lastmod, '0.80'))
    urls = '\n'.join(f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n'
                     f'    <priority>{priority}</priority>\n  </url>' for loc, lastmod, priority in rows)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + '\n</urlset>\n')


REDIRECT = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Publications | Joao P. A. Dantas</title>
  <link rel="canonical" href="https://www.joaopadantas.com/publications.html" />
  <meta http-equiv="refresh" content="0; url=/publications.html" />
</head>
<body>
  <p><a href="/publications.html">Publications</a></p>
</body>
</html>
'''


def main():
    data, pubs = load()
    pub_html = read('publications.html')

    template = Template(read('scripts/templates/publication.html'))
    header, footer = site_chrome(pub_html)
    for p in pubs:
        write(f"publications/{p['id']}/index.html", render_page(p, template, header, footer))
    write('publications/index.html', REDIRECT)

    pub_html = replace_region(pub_html, 'publications', render_list(data, pubs))
    pub_html = replace_region(pub_html, 'itemlist', render_item_list(pubs))
    write('publications.html', pub_html)

    for page, width in PAGE_IMAGE_WIDTHS.items():
        path = os.path.join(ROOT, page)
        with open(path, encoding='utf-8', newline='') as f:  # keep the page's own line endings
            original = f.read()
        updated = images.rewrite_img_tags(original, width)
        if updated != original:
            with open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(updated)

    write('sitemap.xml', render_sitemap(pubs))
    print(f'Built {len(pubs)} publication pages, publications.html, sitemap.xml and optimized page images')


if __name__ == '__main__':
    main()
