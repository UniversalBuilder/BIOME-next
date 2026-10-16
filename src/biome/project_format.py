"""Versioned, portable project identity contract; no implicit conversion."""
from datetime import datetime

FORMAT = 'biome-project'
CURRENT_VERSION = '1.1'
READABLE_VERSIONS = frozenset({'0.1-draft', '1.0', CURRENT_VERSION})
STATUSES = frozenset({'Intake', 'Active', 'Review', 'Completed', 'OnHold'})


def validate_project(project):
    if not isinstance(project, dict) or project.get('format') != FORMAT:
        raise ValueError('Ce fichier ne décrit pas un projet BIOME pris en charge.')
    if not isinstance(project.get('format_version'), str) or project['format_version'] not in READABLE_VERSIONS:
        raise ValueError('Version du format de projet non prise en charge ; aucune conversion automatique.')
    for key in ['id', 'title'] + (['contact'] if project['format_version'] != '1.1' else []):
        if not isinstance(project.get(key), str) or not project[key].strip():
            raise ValueError('Information nécessaire absente ou invalide : ' + key)
    if not isinstance(project.get('contact'), str):
        raise ValueError('Contact invalide.')
    if not isinstance(project.get('description'), str):
        raise ValueError('Demande initiale absente ou invalide.')
    for key in ['group', 'contact_email']:
        if key in project and not isinstance(project[key], str):
            raise ValueError('Coordonnée invalide : ' + key)
    status = project.get('status')
    allowed = STATUSES | ({'Unknown'} if project['format_version'] == '1.1' else set())
    if not isinstance(status, dict) or not isinstance(status.get('value'), str) or status['value'] not in allowed:
        raise ValueError('Statut du projet invalide.')
    try:
        created = datetime.fromisoformat(project['created_at'].replace('Z', '+00:00'))
        if created.tzinfo is None:
            raise ValueError('Timezone required')
    except (KeyError, AttributeError, TypeError, ValueError):
        raise ValueError('Date de création invalide ou sans fuseau horaire.')
    if 'framing' in project:
        framing = project['framing']
        if not isinstance(framing, dict):
            raise ValueError('Cadrage invalide.')
        for key in ['objective', 'deliverable', 'next_step', 'validation', 'activity_type']:
            if key in framing and not isinstance(framing[key], str):
                raise ValueError('Champ de cadrage invalide : ' + key)
        if framing.get('activity_type', '') not in ['', 'consulting', 'training', 'development', 'analysis']:
            raise ValueError('Type d’intervention invalide.')
        for key in ['software', 'modalities', 'topics']:
            if key in framing and (not isinstance(framing[key], list) or any(not isinstance(value, str) or not value.strip() for value in framing[key])):
                raise ValueError('Liste de cadrage invalide : ' + key)
    return project
