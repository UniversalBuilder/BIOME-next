"""Per-chart coverage: missing metadata never becomes a statistical category."""
import unicodedata


def known_label(value):
    if not isinstance(value, str):
        return False
    normalized = ''.join(c for c in unicodedata.normalize('NFKD', value.strip().strip('[]').strip().casefold()) if not unicodedata.combining(c))
    return normalized not in ('', 'non renseigne', 'non renseignee', 'not specified', 'unknown', 'n/a')


def summarize(projects, key):
    timed = key in ('group', 'activity_type')
    categories = {}
    excluded = 0
    for project in projects:
        raw = project.get(key)
        values = {v.strip() for v in (raw if isinstance(raw, list) else [raw]) if known_label(v)}
        if not values or (timed and project.get('minutes') is None):
            excluded += 1
            continue
        for label in values:
            item = categories.setdefault(label, {'label': label, 'count': 0, 'value': 0})
            item['count'] += 1
            item['value'] += project['minutes'] if timed else 1
    return {'items': sorted(categories.values(), key=lambda item: (-item['value'], item['label'])),
            'excluded': excluded, 'included': len(projects) - excluded,
            'reason': 'catégorie ou temps non renseigné' if timed else 'catégorie non renseignée'}
