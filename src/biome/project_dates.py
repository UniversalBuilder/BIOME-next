"""Editable calendar dates, separate from catalogue/import timestamps and sessions."""
from datetime import date
from pathlib import Path
import re


def calendar_day(value):
    if not isinstance(value,str):return None
    day=value[:10]
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):return None
        return date.fromisoformat(day).isoformat()
    except ValueError:return None


def checked_date_fields(data):
    result={}
    for key,label in [('project_date','Date du projet'),('known_activity_date','Dernière activité connue')]:
        if key not in data:continue
        value=data[key]
        if value in [None,'']:result[key]=None;continue
        if not isinstance(value,str) or len(value)!=10 or calendar_day(value)!=value:
            raise ValueError(label+' : choisissez une date valide (AAAA-MM-JJ), ou laissez vide.')
        result[key]=value
    return result


def project_date_value(project):
    if 'project_date' in project:return project['project_date']
    legacy=project.get('legacy_import')
    return legacy.get('source_created_at') if legacy else project.get('created_at')


def activity_date_value(project):
    if 'known_activity_date' in project:return project['known_activity_date']
    return (project.get('legacy_import') or {}).get('source_last_updated')


def date_metadata(root,project):
    candidates=[(Path(str((project.get('legacy_import') or {}).get('source') or '')).name,'dossier d’origine'),(project['title'],'titre du projet'),(Path(root).name,'dossier du projet')]
    suggestion=None;origin=None
    for text,source in candidates:
        match=re.match(r'^(\d{4})[.\-_](\d{2})[.\-_](\d{2})(?:[^0-9]|$)',text)
        if match:
            suggestion=calendar_day('-'.join(match.groups()))
            if suggestion:origin=source;break
    return {'project_date':calendar_day(project_date_value(project)),
            'known_activity_date':calendar_day(activity_date_value(project)),
            'suggested_project_date':suggestion,'suggestion_source':origin}
