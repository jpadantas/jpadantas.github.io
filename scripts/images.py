"""Resized WebP copies of site images in img/opt/, so each page downloads only what it displays.

The originals stay untouched (they are still used for social previews and as the source).
"""
import os
import re

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPT_DIR = 'img/opt'
QUALITY = 82
SKIP_BYTES = 60_000  # small images are left as they are...
CLASS_WIDTHS = {'institution-logo': 240}  # ...unless their class has its own width (logos shown 45 px tall)

_IMG_TAG = re.compile(r'<img\b[^>]*>', re.S)


def optimized(src, width):
    """Return (path, width, height) of a WebP copy of src at most `width` px wide (site-relative paths)."""
    full = os.path.join(ROOT, src)
    name = os.path.splitext(os.path.basename(src))[0]
    out = f'{OPT_DIR}/{name}-{width}.webp'
    out_full = os.path.join(ROOT, out)
    if not os.path.exists(out_full) or os.path.getmtime(out_full) < os.path.getmtime(full):
        os.makedirs(os.path.dirname(out_full), exist_ok=True)
        with Image.open(full) as img:
            img = img.convert('RGBA' if img.mode in ('RGBA', 'LA', 'P') else 'RGB')
            if img.width > width:
                img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
            img.save(out_full, 'WEBP', quality=QUALITY, method=6)
    with Image.open(out_full) as img:
        return out, img.width, img.height


def size_of(src):
    with Image.open(os.path.join(ROOT, src)) as img:
        return img.width, img.height


def rewrite_img_tags(html, width):
    """Point every local <img> to an optimized copy (unless small) and declare its width/height."""
    def fix(match):
        tag = match.group(0)
        src_match = re.search(r'\bsrc="([^"]+)"', tag)
        if not src_match:
            return tag
        src = src_match.group(1)
        prefix = '/' if src.startswith('/') else ''
        path = src.lstrip('/')
        if not path.startswith('img/') or not os.path.exists(os.path.join(ROOT, path)):
            return tag
        class_width = next((cw for cls, cw in CLASS_WIDTHS.items() if re.search(rf'\bclass="[^"]*\b{cls}\b', tag)), None)
        if not path.startswith(OPT_DIR + '/') and (class_width or os.path.getsize(os.path.join(ROOT, path)) > SKIP_BYTES):
            path, w, h = optimized(path, class_width or width)
        else:
            w, h = size_of(path)
        tag = tag.replace(src_match.group(0), f'src="{prefix}{path}"')
        tag = re.sub(r'\s(width|height)="\d+"', '', tag)
        return tag.replace('<img', f'<img width="{w}" height="{h}"', 1)
    return _IMG_TAG.sub(fix, html)
