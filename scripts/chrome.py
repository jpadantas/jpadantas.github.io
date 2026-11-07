"""Site header (menu) and footer (profile links), defined once and written into every page by build.py.

To add a menu item or a profile link, edit NAV or PROFILES below and run: python scripts/build.py
"""
import re

# (label, path) — path is relative to the site root
NAV = [
    ('About', ''),
    ('Publications', 'publications.html'),
    ('Software', 'software.html'),
    ('Research', 'research.html'),
    ('Awards', 'awards.html'),
    ('Media', 'media.html'),
    ('CV', 'files/Joao_Dantas_CV.pdf'),
]

# (label, url, icon classes)
PROFILES = [
    ('Email', 'mailto:jpdantas@ita.br', 'fa-solid fa-envelope'),
    ('LinkedIn', 'https://www.linkedin.com/in/jpdantas/', 'fa-brands fa-linkedin'),
    ('GitHub', 'https://github.com/jpadantas', 'fa-brands fa-github'),
    ('Google Scholar', 'https://scholar.google.com/citations?user=RjeTT9cAAAAJ&amp;hl=en', 'ai ai-google-scholar'),
    ('ResearchGate', 'https://www.researchgate.net/profile/Joao-Dantas-17', 'ai ai-researchgate'),
    ('ORCID', 'https://orcid.org/0000-0003-0300-8027', 'ai ai-orcid'),
    ('ResearcherID', 'https://www.webofscience.com/wos/author/record/KBD-3442-2024', 'ai ai-researcherid'),
    ('Scopus', 'https://www.scopus.com/authid/detail.uri?authorId=57345793200', 'ai ai-scopus'),
    ('Lattes CV', 'https://lattes.cnpq.br/3402961044482021', 'ai ai-lattes'),
]
COPYRIGHT = '© Joao P. A. Dantas 2026–present'

# Hand-written pages: page -> (active menu label, link prefix). The 404 page is served at any path,
# so it uses root-relative links.
PAGES = {
    'index.html': ('About', ''),
    'publications.html': ('Publications', ''),
    'software.html': ('Software', ''),
    'research.html': ('Research', ''),
    'awards.html': ('Awards', ''),
    'media.html': ('Media', ''),
    '404.html': (None, '/'),
}


def _href(path, prefix):
    if prefix == '/':
        return '/' + path
    return path or './'


def header(active, prefix, indent=''):
    i = indent
    items = []
    for label, path in NAV:
        cls = ' class="active"' if label == active else ''
        items.append(f'{i}            <li><a href="{_href(path, prefix)}"{cls}>{label}</a></li>')
    return '\n'.join([
        f'{i}<header class="site-header">',
        f'{i}    <nav class="nav-container" aria-label="Main navigation">',
        f'{i}        <ul class="site-nav">',
        *items,
        f'{i}        </ul>',
        f'{i}    </nav>',
        f'{i}</header>',
    ])


def footer(indent=''):
    i = indent
    links = [f'{i}        <a href="{url}" aria-label="{label}" title="{label}"><i class="{icon}"></i></a>'
             for label, url, icon in PROFILES]
    return '\n'.join([
        f'{i}<footer class="site-footer">',
        f'{i}    <div class="footer-icons">',
        *links,
        f'{i}    </div>',
        f'{i}    <p class="copyright">{COPYRIGHT}</p>',
        f'{i}</footer>',
    ])


def apply(html, active, prefix):
    """Replace the <header class="site-header"> and <footer class="site-footer"> blocks of a page."""
    nl = '\r\n' if '\r\n' in html else '\n'  # keep the page's own line endings

    def swap(pattern, render):
        m = re.search(pattern, html, re.S | re.M)
        if not m:
            raise ValueError(f'block not found: {pattern}')
        return html[:m.start()] + render(m.group(1)).replace('\n', nl) + html[m.end():]
    html = swap(r'^([ \t]*)<header class="site-header">.*?</header>', lambda ind: header(active, prefix, ind))
    html = swap(r'^([ \t]*)<footer class="site-footer">.*?</footer>', lambda ind: footer(ind))
    return html
