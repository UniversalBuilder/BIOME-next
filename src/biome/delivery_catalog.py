"""Human-readable delivery inventory and bounded, read-only previews."""
import hashlib
import json
import os
from pathlib import Path
import re

from storage import load, safe_file

TEXT_LIMIT = 64_000
IMAGE_LIMIT = 20_000_000
KINDS = {'note': 'Note de travail', 'experiment': 'Essai / run', 'exchange': 'Échange',
         'meeting': 'Réunion', 'decision': 'Décision'}


def note_body(text):
    text = text.lstrip('\ufeff').replace('\r\n','\n').replace('\r','\n')
    if text.startswith('---\n'):
        text = text.split('---', 2)[-1].strip()
    return text.split('\n## Fichiers associés\n', 1)[0].strip()


def readable_title(text, fallback):
    lines = [line.strip() for line in note_body(text).splitlines() if line.strip()]
    for line in lines[:12]:
        match = re.match(r'^(?:Objet|Subject)\s*:\s*(.+)', line, re.I)
        if match:
            return match[1][:160]
    useful = [re.sub(r'^#+\s*', '', line) for line in lines
              if not re.match(r'^(?:De|À|From|To|Date du message)\s*:', line, re.I)]
    return (useful[0][:160] if useful else fallback)


def text_sample(path):
    with path.open('rb') as stream:
        return stream.read(TEXT_LIMIT + 1).decode('utf-8-sig', errors='replace')


def kind_for(path, record):
    ext = path.suffix.lower()
    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
        return 'image'
    if ext in ['.msg', '.eml']:
        return 'source'
    if record.get('role') == 'version' or ext in ['.ijm', '.py', '.groovy', '.r', '.js', '.sh']:
        return 'script'
    if path.parts[0] == 'journal':
        return 'note'
    return 'document'


def inventory(root):
    root = Path(root).resolve()
    entries = load(root / 'records/entries.json')
    records = {record['file']: record for record in load(root / 'records/versions.json')}
    by_path = {}
    for entry in entries:
        by_path[entry['file']] = (entry, {})
        for record in entry.get('attachments', []):
            by_path.setdefault(record['file'], (entry, record))
    groups = {}
    result = []
    for folder in ['journal', 'files', 'exchanges']:
        start = root / folder
        if not start.is_dir() or start.is_symlink() or start.is_junction():
            continue
        for directory, dirs, files in os.walk(start, followlinks=False):
            parent = Path(directory)
            dirs[:] = sorted(name for name in dirs if not (parent / name).is_symlink()
                             and not (parent / name).is_junction())
            for name in sorted(files):
                path = parent / name
                if path.is_symlink() or not path.is_file():
                    continue
                relative = path.relative_to(root).as_posix()
                entry, attachment = by_path.get(relative, (None, {}))
                record = {**records.get(relative, {}), **attachment}
                kind = kind_for(Path(relative), record)
                technical = kind == 'source' or 'legacy-source' in path.relative_to(root).parts
                original = record.get('original_name') or name
                caption = record.get('caption') or ''
                generic = caption.startswith(('Illustration extraite du message', 'Message source importé'))
                title = caption[:160] if caption and not generic else original
                if entry:
                    group_id = entry['id']
                    if group_id not in groups:
                        note_path = safe_file(root, entry['file'])
                        text = text_sample(note_path) if note_path.is_file() else ''
                        groups[group_id] = {'id': group_id, 'title': readable_title(text, KINDS.get(entry['type'], 'Entrée du cahier')),
                                            'date': entry.get('date_source', ''), 'type': KINDS.get(entry['type'], 'Entrée du cahier')}
                    if kind == 'note':
                        title = groups[group_id]['title']
                else:
                    group_id = 'other'
                    groups.setdefault(group_id, {'id': group_id, 'title': 'Autres documents du projet', 'date': '', 'type': 'Documents'})
                    if kind == 'note':
                        title = readable_title(text_sample(path), original)
                stat = path.stat()
                revision = hashlib.sha256(json.dumps([relative, stat.st_size, stat.st_mtime_ns,
                                                     title, caption, record.get('version_label')], ensure_ascii=False).encode()).hexdigest()
                result.append({'file': relative, 'id': record.get('id') or 'document-' + hashlib.sha256(relative.encode()).hexdigest()[:24],
                               'bytes': stat.st_size, 'modified_ns': stat.st_mtime_ns, 'title': title, 'name': original, 'kind': kind,
                               'group': group_id, 'date': entry.get('date_source', '') if entry else '',
                               'group_title': groups[group_id]['title'], 'group_type': groups[group_id]['type'],
                               'caption': caption, 'version': record.get('version_label') or '',
                               'technical': technical, 'revision': revision})
    return result


def checked_path(root, relative):
    if not isinstance(relative, str):
        raise ValueError('Document de livraison invalide.')
    item = next((item for item in inventory(root) if item['file'] == relative), None)
    if item is None:
        raise ValueError('Document absent ou inaccessible. Actualisez la sélection.')
    return safe_file(root, relative), item


def image_bytes(root, relative):
    path, item = checked_path(root, relative)
    if item['kind'] != 'image' or item['bytes'] > IMAGE_LIMIT:
        raise ValueError('Aperçu image indisponible pour ce document.')
    raw = path.read_bytes()
    mime = ('image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else
            'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else
            'image/gif' if raw[:6] in [b'GIF87a', b'GIF89a'] else
            'image/webp' if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP' else None)
    if not mime:
        raise ValueError('Ce fichier ne contient pas une image prise en charge.')
    return raw, mime


def preview(root, relative):
    path, item = checked_path(root, relative)
    result = {'item': item, 'text': '', 'truncated': False, 'mode': 'unavailable'}
    if item['kind'] == 'image':
        if item['bytes'] <= IMAGE_LIMIT:
            result['mode'] = 'image'
        else:
            result['text'] = 'Image trop volumineuse pour cet aperçu. Le fichier complet reste sélectionnable.'
        return result
    if path.suffix.lower() == '.msg':
        if item['bytes'] > 50_000_000:
            result['text'] = 'Message trop volumineux pour cet aperçu.'
            return result
        from mail_messages import read_msg
        message = read_msg(path.read_bytes(), include_images=False)
        text = '\n'.join(label + ' : ' + str(value) for label, value in message['headers'] if value)
        body = message['body']
        if not body and message['html']:
            from data_store import MailText
            parser = MailText(); parser.feed(message['html']); body = ''.join(parser.parts)
        text += '\n\n' + (body or '')
        result['notice'] = 'Texte extrait pour l’aperçu. La sélection transmet le message Outlook original complet.'
    elif path.suffix.lower() == '.eml':
        if item['bytes'] > 50_000_000:
            result['text'] = 'Message trop volumineux pour cet aperçu.'
            return result
        from email.parser import BytesParser
        from email import policy
        message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
        body = message.get_body(preferencelist=('plain', 'html'))
        text = body.get_content() if body else ''
        if body and body.get_content_type() == 'text/html':
            from data_store import MailText
            parser = MailText(); parser.feed(text); text = ''.join(parser.parts)
        result['notice'] = 'Texte extrait pour l’aperçu. Le fichier EML original complet sera transmis.'
    elif path.suffix.lower() in ['.md', '.txt', '.csv', '.json', '.ijm', '.py', '.groovy', '.r', '.js', '.sh', '.log', '.yaml', '.yml']:
        text = text_sample(path)
        if item['kind'] == 'note':
            text = note_body(text)
    else:
        result['text'] = 'Aperçu non disponible pour ce format. Consultez le nom, le type et la provenance avant de l’inclure.'
        return result
    result.update(mode='text', text=text[:TEXT_LIMIT], truncated=len(text) > TEXT_LIMIT)
    return result
