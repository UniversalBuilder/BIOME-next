"""Project report scope and dated, independent time; canonical logs remain portable."""
import csv
import hashlib
import io
import json
import re
import uuid
from datetime import date, datetime
from storage import load, write_json, atomic


class AccountingConflict(ValueError):
    def __init__(self):
        super().__init__('Les temps ou le périmètre ont changé. Rechargez ce volet avant d’enregistrer ; votre saisie reste affichée.')
        self.payload = {'error': str(self), 'conflict': True}


def revision(work):
    return hashlib.sha256(json.dumps(work, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def scope(work):
    value = work.get('reporting', {})
    if not isinstance(value, dict) or type(value.get('excluded', False)) is not bool or not isinstance(value.get('reason', ''), str):
        raise ValueError('Périmètre du bilan invalide.')
    return {'excluded': value.get('excluded', False), 'reason': value.get('reason', '')}


def valid_minutes(log):
    maximum = 525600 if log.get('source') == 'manual' and log.get('estimate') is True else 1440
    return type(log.get('minutes')) is int and 0 <= log['minutes'] <= maximum


def write_csv(root, work):
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['id', 'date', 'minutes', 'activity_type', 'entry_ids', 'description', 'source', 'estimate'])
    for log in work['logs']:
        values = [log['id'], log['date'], log['minutes'], log['activity_type'], ';'.join(log['entry_ids']), log['description'], log.get('source',''), log.get('estimate',False)]
        writer.writerow(["'"+v if isinstance(v, str) and v.lstrip().startswith(('=', '+', '-', '@')) else v for v in values])
    atomic(root/'records/activity.csv', '\ufeff'+stream.getvalue())


def recover_accounting(root):
    pending = root/'records/pending-accounting.json'
    if not pending.exists():
        return
    transaction = load(pending)
    work = load(root/'records/work-logs.json')
    if revision(work) not in [transaction['base_revision'], revision(transaction['updated'])]:
        raise AccountingConflict()
    write_json(root/'records/work-logs.json', transaction['updated'])
    write_csv(root, transaction['updated'])
    pending.unlink()


def save_accounting(root, data):
    """One guarded transaction for scope, standalone additions, corrections or removal."""
    if not isinstance(data, dict):
        raise ValueError('Objet de temps ou de périmètre attendu.')
    recover_accounting(root)
    work = load(root/'records/work-logs.json')
    if data.get('base_revision') != revision(work):
        raise AccountingConflict()
    before = json.loads(json.dumps(work))
    action = data.get('action')
    stamp = datetime.now().astimezone().isoformat()
    event = {'id': 'accounting-'+uuid.uuid4().hex, 'date': stamp, 'action': action}
    if action == 'scope':
        if type(data.get('excluded')) is not bool:
            raise ValueError('Indiquez si le projet doit être exclu du bilan.')
        reason = data.get('reason', '')
        if not isinstance(reason, str) or len(reason) > 1000:
            raise ValueError('Motif : 1000 caractères maximum.')
        previous = scope(work)
        updated = {'excluded': data['excluded'], 'reason': reason.strip()}
        if previous == updated:
            return accounting_state(work)
        event.update(previous=previous, updated=updated)
        work['reporting'] = {**updated, 'updated_at': stamp}
    elif action in ['save', 'delete']:
        identifier = data.get('id')
        previous = next((log for log in work['logs'] if log['id'] == identifier), None) if identifier else None
        if identifier and previous is None:
            raise ValueError('Cette saisie de temps n’existe plus. Rechargez le projet.')
        if previous and previous.get('entry_ids'):
            raise ValueError('Ce temps est lié au cahier : corrigez-le depuis son entrée.')
        if action == 'delete':
            if not previous:
                raise ValueError('Sélectionnez une saisie existante à retirer.')
            work['logs'] = [log for log in work['logs'] if log['id'] != identifier]
            event.update(previous=previous, updated=None)
        else:
            day = data.get('date')
            if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
                raise ValueError('Date de rattachement requise (AAAA-MM-JJ).')
            try:
                date.fromisoformat(day)
            except ValueError:
                raise ValueError('Date de rattachement invalide.')
            if type(data.get('estimate', False)) is not bool:
                raise ValueError('Nature de la durée invalide.')
            description = data.get('description', '')
            if not isinstance(description, str) or len(description) > 2000:
                raise ValueError('Commentaire : 2000 caractères maximum.')
            log = {**(previous or {}), 'id': identifier or 'work-'+uuid.uuid4().hex,
                   'date': day, 'minutes': data.get('minutes'), 'activity_type': 'manual',
                   'entry_ids': [], 'description': description.strip(), 'source': 'manual',
                   'estimate': data.get('estimate', False), 'updated_at': stamp}
            log.setdefault('created_at', stamp)
            if not valid_minutes(log):
                raise ValueError('Durée : 0 à 1440 minutes par séance, ou 525600 minutes maximum pour une estimation historique.')
            work['logs'] = [log if item['id'] == identifier else item for item in work['logs']]
            if previous is None:
                work['logs'].append(log)
            event.update(previous=previous, updated=log)
    else:
        raise ValueError('Action de temps ou de périmètre inconnue.')
    work.setdefault('accounting_history', []).append(event)
    write_json(root/'records/pending-accounting.json', {'base_revision': revision(before), 'updated': work})
    recover_accounting(root)
    return accounting_state(work)


def accounting_state(work):
    logs = work['logs']
    return {'work_revision': revision(work), 'reporting': scope(work),
            'time_recorded': bool(logs), 'total_minutes': sum(log['minutes'] for log in logs),
            'manual_minutes': sum(log['minutes'] for log in logs if not log.get('entry_ids')),
            'estimated_minutes': sum(log['minutes'] for log in logs if log.get('estimate') is True),
            'logs': logs}
