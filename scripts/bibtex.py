"""Minimal BibTeX reader for the one-entry-per-file files in bib/."""
import re
import unicodedata

_ACCENTS = {"'": '́', '`': '̀', '^': '̂', '~': '̃', '"': '̈', 'c': '̧'}


def latex_to_unicode(text):
    r"""Convert the LaTeX accents used in bib/ (e.g. Jo\~{a}o, \c{c}) to Unicode."""
    def repl(m):
        letter = 'i' if m.group(2) == '\\i' else m.group(2)
        return unicodedata.normalize('NFC', letter + _ACCENTS[m.group(1)])
    text = re.sub(r"\{?\\([`'^~\"c])\s*\{?(\\i|[A-Za-z])\}?\}?", repl, text)
    text = text.replace('--', '–').replace('\\&', '&')
    return re.sub(r'\s+', ' ', text.replace('{', '').replace('}', '')).strip()


def _read_value(s, i):
    """Read a braced or bare value starting at s[i]; return (raw_value, next_index)."""
    if s[i] == '{':
        depth = 0
        for j in range(i, len(s)):
            if s[j] == '{':
                depth += 1
            elif s[j] == '}':
                depth -= 1
                if depth == 0:
                    return s[i + 1:j], j + 1
        raise ValueError('unbalanced braces')
    m = re.match(r'[^,\n}]+', s[i:])
    return m.group(0).strip(), i + m.end()


def parse(text):
    """Parse a single BibTeX entry into {'type', 'key', 'fields'} (raw LaTeX values)."""
    m = re.match(r'\s*@(\w+)\s*\{\s*([^,\s]+)\s*,', text)
    entry = {'type': m.group(1).lower(), 'key': m.group(2), 'fields': {}}
    field = re.compile(r'\s*(\w+)\s*=\s*')
    sep = re.compile(r'\s*,?')
    i = m.end()
    while True:
        f = field.match(text, i)
        if not f:
            break
        value, i = _read_value(text, f.end())
        entry['fields'][f.group(1).lower()] = value
        i = sep.match(text, i).end()
    return entry


def authors(raw):
    """Split a BibTeX author field into [(family, given)] in Unicode."""
    out = []
    for name in re.split(r'\s+and\s+', raw):
        name = latex_to_unicode(name)
        if ',' in name:
            family, given = [p.strip() for p in name.split(',', 1)]
        else:
            parts = name.rsplit(' ', 1)
            given, family = (parts[0], parts[1]) if len(parts) == 2 else ('', parts[0])
        out.append((family, given))
    return out
