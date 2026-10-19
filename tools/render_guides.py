"""Render this repository's deliberately small Markdown guide subset offline.

No network resources, scripts or runtime dependency are required by the output.
"""
import html
from pathlib import Path
import re


def inline(value):
    value = html.escape(value)
    value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
    value = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', value)


def render(source):
    output = []
    paragraph = []
    table = False
    listing = False
    headings = []

    def flush():
        if paragraph:
            output.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()

    for line in source.read_text(encoding='utf-8').splitlines() + ['']:
        if not line.strip():
            flush()
            if table:
                output.append('</tbody></table></div>'); table = False
            if listing:
                output.append('</ul>'); listing = False
            continue
        if line.startswith('#'):
            flush()
            level = len(line) - len(line.lstrip('#'))
            title = line[level:].strip()
            anchor = 'section-' + str(len(headings) + 1)
            headings.append((level, title, anchor))
            output.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
        elif line.startswith('!['):
            flush()
            match = re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)', line)
            if not match: raise ValueError('Unsupported image syntax')
            caption, path = match.groups()
            output.append(f'<figure><a href="{html.escape(path)}"><img loading="lazy" src="{html.escape(path)}" alt="{html.escape(caption)}"></a><figcaption>{html.escape(caption)}</figcaption></figure>')
        elif line.startswith('|'):
            flush()
            if re.fullmatch(r'[| :\-]+', line): continue
            cells = [inline(x.strip()) for x in line.strip('|').split('|')]
            if not table:
                output.append('<div class="table"><table><thead><tr>' + ''.join('<th>' + x + '</th>' for x in cells) + '</tr></thead><tbody>')
                table = True
            else:
                output.append('<tr>' + ''.join('<td>' + x + '</td>' for x in cells) + '</tr>')
        elif line.startswith('- '):
            flush()
            if not listing: output.append('<ul>'); listing = True
            output.append('<li>' + inline(line[2:]) + '</li>')
        else:
            paragraph.append(line)
    language = 'fr' if '.fr.' in source.name else 'en'
    toc = ''.join(f'<a href="#{anchor}">{html.escape(title)}</a>' for level, title, anchor in headings if level == 2)
    style = '''body{margin:0;background:#101426;color:#e7edf8;font:17px/1.65 system-ui,Segoe UI,sans-serif}header,main{max-width:1100px;margin:auto;padding:28px}header{border-bottom:1px solid #39435d}h1{font-size:2.25rem}h2{font-size:1.65rem;margin-top:3rem;border-top:1px solid #39435d;padding-top:1.5rem}h3{font-size:1.2rem;color:#b9c9e6}a{color:#93dcef}code{background:#202940;padding:2px 5px;border-radius:4px;font-size:.9em}figure{margin:24px 0;padding:12px;background:#192138;border:1px solid #39435d;border-radius:12px}img{display:block;max-width:100%;height:auto;margin:auto}figcaption{font-size:.88rem;color:#b6c7e2;padding:10px 8px 0}nav{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:8px 20px}nav a{font-size:.92rem}.table{overflow-x:auto}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:12px;border-bottom:1px solid #39435d}th{background:#202940}.note{color:#b6c7e2}@media(max-width:650px){main,header{padding:18px}h1{font-size:1.8rem}}@media print{body{background:white;color:#172033;font-size:10pt}a{color:#172033}header nav{display:none}h2{break-before:page}figure{background:white;border:1px solid #bbb;break-inside:avoid}img{max-height:210mm;max-width:100%;object-fit:contain}code,th{background:#eee}figcaption,.note,h3{color:#334155}}'''
    title = headings[0][1]
    note = ('Cliquez sur une capture pour la voir en taille réelle. Ce guide fonctionne hors connexion.' if language == 'fr' else 'Click a screenshot to see it at full size. This guide works offline.')
    document = f'<!doctype html><html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{style}</style></head><body><header><strong>BIOME-next · 3.0.0-alpha.3</strong><p class="note">{note}</p><nav aria-label="Contents">{toc}</nav></header><main>' + '\n'.join(output) + '</main></body></html>'
    # Keep offline links within the rendered guides in HTML form.
    document = document.replace('href="guide-utilisateur.fr.md"', 'href="guide-utilisateur.fr.html"')
    target = source.with_suffix('.html')
    target.write_text(document, encoding='utf-8')
    for path in re.findall(r'<img[^>]+src="([^"]+)"', document):
        if not (target.parent / path).is_file(): raise ValueError('Missing screenshot: ' + path)
    return target


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    for name in ['user-guide.md', 'guide-utilisateur.fr.md']:
        print(render(root / 'docs' / name))
