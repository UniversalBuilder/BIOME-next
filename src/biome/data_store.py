"""Project workflows independent of HTTP and the user interface."""
from mail_messages import MAX_MESSAGE_BYTES, MAX_IMAGE_BYTES, MAX_ENTRY_FILES, MAX_ENTRY_BYTES
from pathlib import Path
import csv, io, json, os, uuid, base64, hashlib, zipfile, html, re, unicodedata
from urllib.parse import quote
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo
from datetime import datetime
from storage import load, atomic, write_json, safe_file, publish_directory
from project_format import FORMAT, CURRENT_VERSION
from data_receipts import dataset_path, write_companion, recover_receipt

HERE = Path(__file__).resolve().parent

class EntryConflict(ValueError):
    def __init__(self, payload):
        super().__init__(payload['error'])
        self.payload=payload

def entry_revision(root, entry):
    path=safe_file(root,entry['file'])
    raw=path.read_bytes() if path.is_file() else None
    logs=[log for log in load(root/'records/work-logs.json')['logs'] if entry['id'] in log['entry_ids']]
    state={'entry':{k:v for k,v in entry.items() if k not in ['text','revision']},'logs':logs,'file':hashlib.sha256(raw).hexdigest() if raw is not None else None}
    return hashlib.sha256(json.dumps(state,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def preserve_entry_conflict(root, entry, draft):
    path=safe_file(root,entry['file'])
    raw=path.read_bytes() if path.is_file() else None
    text=raw.decode('utf-8',errors='replace') if raw is not None else ''
    folder=root/'records/conflicts';folder.mkdir(exist_ok=True)
    name='conflict-'+uuid.uuid4().hex+'.json'
    record={'created_at':datetime.now().astimezone().isoformat(),'entry_id':entry['id'],
            'current_entry':entry,'current_note_base64':base64.b64encode(raw).decode() if raw is not None else None,
            'draft':draft,'current_work_logs':[log for log in load(root/'records/work-logs.json')['logs'] if entry['id'] in log['entry_ids']]}
    write_json(folder/name,record)
    return {'error':'Cette note a changé depuis son ouverture. Votre correction est conservée ; le fichier sur disque reste intact.',
            'conflict':True,'saved_copy':'records/conflicts/'+name,'current_revision':entry_revision(root,entry),
            'current_note':text,'current_entry':entry,'current_logs':record['current_work_logs'],
            'missing':raw is None}

def read_project(root):
    entries = load(root/'records/entries.json')
    for entry in entries:
        entry['revision']=entry_revision(root,entry)
        text = safe_file(root, entry['file']).read_text(encoding='utf-8')
        entry['text'] = text.split('---', 2)[-1].strip() if text.startswith('---\n') else text
    entries.sort(key=lambda e: datetime.strptime(e['date_source'], '%d/%m/%Y %H:%M:%S'), reverse=True)
    work = load(root/'records/work-logs.json')
    logs = work['logs']
    if len({x['id'] for x in logs}) != len(logs): raise ValueError('Temps dupliqués')
    linked={file['id'] for entry in entries for file in entry.get('attachments',[])}
    return {'project': load(root/'biome.json'), 'entries': entries, 'logs': logs,
            'unlinked_files':[file for file in load(root/'records/versions.json') if file['id'] not in linked],
            'datasets':[dict(item,resolved_location=str(dataset_path(root,item)) if item.get('storage')=='project' else item['location']) for item in load(root/'records/datasets.json')],
            'next_delivery':delivery_title(root),'delivery_files':delivery_files(root),'deliveries':load(root/'records/deliveries.json') if (root/'records/deliveries.json').exists() else [],
            'total_minutes': sum(x['minutes'] for x in logs), 'historical_time_unknown': True}

def delivery_files(root):
    return [{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size} for folder in ['files','exchanges','journal'] for p in sorted((root/folder).rglob('*')) if p.is_file() and not p.is_symlink()]

def delivery_title(root):
    records=load(root/'records/deliveries.json') if (root/'records/deliveries.json').exists() else []
    version=max([d.get('version',i+1) for i,d in enumerate(records)]+[0])+1
    title=load(root/'biome.json')['title']
    return {'label':f"{title} — livraison v{version:02d} — {datetime.now().strftime('%Y-%m-%d')}",'version':version}

def make_delivery(root,data):
    available={f['file'] for f in delivery_files(root)}
    selected=data.get('files',[])
    if not isinstance(selected,list) or any(not isinstance(f,str) or f not in available for f in selected): raise ValueError('Sélection de fichiers invalide')
    selected=list(dict.fromkeys(selected))
    datasets=load(root/'records/datasets.json')
    requested=data.get('dataset_ids',[]);copies=data.get('copy_dataset_ids',[])
    ids={x['id'] for x in datasets}
    if not isinstance(requested,list) or any(d not in ids for d in requested): raise ValueError('Référence invalide')
    if not isinstance(copies,list) or any(d not in requested for d in copies): raise ValueError('Données à inclure invalides')
    if not selected and not requested: raise ValueError('Choisissez au moins un fichier ou des données externes')
    references=[dict(d,included=d['id'] in copies) for d in datasets if d['id'] in requested]
    sources=[(safe_file(root,f),f) for f in selected]
    for i,d in enumerate(references):
        if not d['included']: continue
        if re.match(r'^https?://',d['location'],re.I): raise ValueError('Pour inclure un lien web, téléchargez ses fichiers puis sélectionnez leur emplacement local')
        path=dataset_path(root,d)
        if not path.is_absolute() or not path.exists(): raise ValueError('Données inaccessibles : '+d['name'])
        if path.is_symlink() or path.is_junction(): raise ValueError('Sélectionnez le dossier réel plutôt qu’un lien : '+d['name'])
        prefix=f'donnees/{i+1:02d}/'
        if path.is_file(): sources.append((path,prefix+path.name))
        else:
            for directory,dirs,files in os.walk(path,followlinks=False,onerror=lambda error: (_ for _ in ()).throw(error)):
                parent=Path(directory)
                if any((parent/name).is_symlink() or (parent/name).is_junction() for name in dirs): raise ValueError('Le dossier contient un lien : '+str(parent))
                for name in files:
                    source=parent/name
                    if source.is_symlink(): raise ValueError('Le dossier contient un lien : '+str(source))
                    sources.append((source,prefix+path.name+'/'+source.relative_to(path).as_posix()))
    project=load(root/'biome.json');did='delivery-'+uuid.uuid4().hex
    title=delivery_title(root);stamp=datetime.now().astimezone().isoformat()
    slug=re.sub(r'[^a-zA-Z0-9]+','-',unicodedata.normalize('NFKD',project['title']).encode('ascii','ignore').decode()).strip('-')[:80] or 'projet'
    filename=f"{datetime.now().strftime('%Y-%m-%d')}_{slug}_livraison-v{title['version']:02d}.zip"
    item={'id':did,**title,'created_at':stamp,'file':'deliveries/'+filename,'files':selected,'references':references,'note':str(data.get('note','')).strip()[:4000]}
    folder=root/'deliveries';folder.mkdir(exist_ok=True)
    destination=safe_file(root,item['file']);temporary=folder/(did+'.tmp')
    history=[]
    for path in sorted((root/'records/framing-history').glob('*.json')):
        event=load(path);previous=event['previous'];updated=event['updated']
        history.append({'date':event['date'],'status':updated['status']['value'],'framing':updated.get('framing',{})})
    snapshot={'status':project['status']['value'],'framing':project.get('framing',{}),'history':sorted(history,key=lambda event:event['date'])}
    item['project_snapshot']=snapshot
    manifest=dict(item);manifest['checksums']={}
    esc=html.escape
    page=['<!doctype html><html lang="fr"><meta charset="utf-8"><title>'+esc(title['label'])+'</title><style>body{font:16px/1.6 system-ui;max-width:1000px;margin:40px auto;padding:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f4f4;padding:16px}li{margin:8px 0}@media print{a{color:inherit}}</style>', '<h1>'+esc(project['title'])+'</h1>','<p>'+esc(title['label'])+'</p>','<pre>'+esc(item['note'])+'</pre>','<h2>Fichiers inclus</h2><ul>']
    for source,name in sources: page.append('<li><a href="'+quote(name,safe='/')+'">'+esc(name)+'</a></li>')
    page+=['</ul><h2>Cadrage au moment de la livraison</h2>']
    statuses={'Intake':'À cadrer','Active':'En cours','Review':'En validation','Completed':'Terminé','OnHold':'En pause'}
    page.append('<p>Statut : '+esc(statuses.get(snapshot['status'],snapshot['status']))+'</p>')
    for key,label in [('objective','Objectif convenu'),('deliverable','Livrable convenu'),('next_step','Prochaine étape à cette date'),('validation','Validation / critères d’acceptation')]:
        page+=['<h3>'+label+'</h3><pre>'+esc(snapshot['framing'].get(key) or 'Non renseigné')+'</pre>']
    for key,label in [('software','Logiciels utilisés'),('modalities','Modalités d’imagerie'),('topics','Thématiques d’analyse')]:
        page+=['<h3>'+label+'</h3><pre>'+esc(', '.join(snapshot['framing'].get(key,[])) or 'Non renseigné')+'</pre>']
    if history:
        page.append('<h3>Évolution du cadrage</h3><ul>')
        for event in snapshot['history']:
            page.append('<li>'+esc(event['date'])+' — '+esc(statuses.get(event['status'],event['status']))+'<pre>'+esc(event['framing'].get('objective',''))+'\n'+esc(event['framing'].get('deliverable',''))+'</pre></li>')
        page.append('</ul>')
    page+=['<h2>Données externes</h2>']
    for d in references: page+=['<h3>'+esc(d['name'])+'</h3><p>'+('Contenu inclus dans donnees/.' if d['included'] else 'Emplacement uniquement ; accès institutionnel nécessaire.')+'</p><pre>'+esc(d['location'])+'</pre><p>'+esc(d.get('description',''))+'</p>']
    page+=['<h2>Notes et documents Markdown</h2><p>Le contenu des fichiers Markdown sélectionnés est reproduit ci-dessous pour être lu sans logiciel supplémentaire.</p>']
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,allowZip64=True) as archive:
            for source,name in sources:
                before=source.stat();digest=hashlib.sha256()
                with source.open('rb') as stream, archive.open(name,'w',force_zip64=True) as target:
                    while chunk:=stream.read(1024*1024): target.write(chunk);digest.update(chunk)
                after=source.stat()
                if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns): raise ValueError('Fichier modifié pendant la livraison : '+source.name)
                manifest['checksums'][name]=digest.hexdigest()
                if source.suffix.lower()=='.md':
                    if before.st_size>10_000_000: raise ValueError('Document Markdown trop volumineux pour la synthèse : '+source.name)
                    page+=['<h3>'+esc(name)+'</h3><pre>'+esc(source.read_text(encoding='utf-8-sig',errors='replace'))+'</pre>']
            archive.writestr('README.html','\n'.join(page)+ '</html>')
            archive.writestr('README.md','# '+title['label']+'\n\nOuvrez README.html dans votre navigateur pour lire la synthèse et les notes.\n')
            archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        os.replace(temporary,destination)
        records=load(root/'records/deliveries.json') if (root/'records/deliveries.json').exists() else []
        records.append(item);write_json(root/'records/deliveries.json',records)
    finally:
        if temporary.exists(): temporary.unlink()
    return item

class MailText(HTMLParser):
    def __init__(self): super().__init__();self.parts=[];self.hidden=0
    def handle_starttag(self,tag,attrs):
        if tag in ['script','style']: self.hidden+=1
        if tag in ['p','br','div','tr','li','h1','h2']: self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ['script','style']: self.hidden=max(0,self.hidden-1)
        if tag in ['td','th']: self.parts.append(' : ')
    def handle_data(self,text):
        if not self.hidden: self.parts.append(text)

def preview_import(data):
    name=str(data.get('name','exchange.txt'))
    if Path(name).name!=name or name.lower().split('.')[-1] not in ['eml','txt','msg']: raise ValueError('Choisissez un fichier .msg, .eml ou .txt ; vous pouvez aussi coller le texte du mail')
    raw=base64.b64decode(data.get('content',''),validate=True)
    if not raw or len(raw)>MAX_MESSAGE_BYTES: raise ValueError('Message vide ou supérieur à 50 Mo')
    stamp=None;headers=[];images=[];warnings=[]
    if name.lower().endswith('.msg'):
        from mail_messages import read_msg
        imported=read_msg(raw)
        headers=[label+' : '+str(value) for label,value in imported['headers'] if value]
        text=imported['body']
        if not text and imported['html']:
            parser=MailText();parser.feed(imported['html']);text=''.join(parser.parts)
        text=re.sub(r'\[cid:[^\]]+\]','[Illustration intégrée au message]',text or '')
        if imported['date']:
            stamp=imported['date'].astimezone(ZoneInfo('Europe/Zurich')) if imported['date'].tzinfo else imported['date']
        images=imported['images']['files']
        if imported['images']['omitted']:
            warnings.append(str(imported['images']['omitted'])+' élément(s) non extrait(s) (format ou taille). Le message original les conserve.')
    elif name.lower().endswith('.eml'):
        message=BytesParser(policy=policy.default).parsebytes(raw)
        for key,label in [('Subject','Objet'),('From','De'),('To','À'),('Date','Date du message')]:
            if message.get(key): headers.append(label+' : '+str(message[key]))
        body=message.get_body(preferencelist=('plain','html'))
        if body is None: raise ValueError('Le message ne contient pas de texte exploitable')
        text=body.get_content()
        if body.get_content_type()=='text/html':
            parser=MailText();parser.feed(text);text=''.join(parser.parts)
        try:
            date=parsedate_to_datetime(str(message.get('Date','')))
            if date.tzinfo is not None: date=date.astimezone(ZoneInfo('Europe/Zurich'))
            stamp=date
        except (ValueError,TypeError,KeyError): pass
    else:
        try: text=raw.decode('utf-8-sig')
        except UnicodeDecodeError: text=raw.decode('cp1252',errors='replace')
    text=('\n'.join(headers)+'\n\n'+text).strip()
    if not text or len(text)>50000: raise ValueError('Texte vide ou trop long pour une entrée du cahier')
    return {'text':text,'date':stamp.strftime('%Y-%m-%d') if stamp else None,'time':stamp.strftime('%H:%M') if stamp else None,'images':images,'warnings':warnings,'source':{'name':name,'content':base64.b64encode(raw).decode(),'role':'attachment','caption':'Message source importé'}}

def preview_request(data):
    preview=preview_import(data)
    labels={'contact email':'email','email de contact':'email','contact name':'contact','nom du contact':'contact','your name and research group':'combined','research group':'group','groupe de recherche':'group','project title':'title','titre du projet':'title'}
    lines=[line.strip().rstrip(':').strip() for line in preview['text'].splitlines() if line.strip()]
    suggestions={}
    for index,line in enumerate(lines):
        for label,key in labels.items():
            match=re.match(r'^'+re.escape(label)+r'\s*:\s*(.+)$',line,re.I)
            value=match.group(1).strip() if match else (lines[index+1] if line.casefold()==label and index+1<len(lines) else None)
            if not value or value.casefold() in labels: continue
            if key=='combined':
                parts=re.split(r'\s+in\s+',value,maxsplit=1,flags=re.I)
                if len(parts)==2 and all(part and len(part)<=200 for part in parts): suggestions.update(contact=parts[0],group=parts[1])
                continue
            if key=='email' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value): continue
            if len(value)<=(254 if key=='email' else 200): suggestions[key]=value
    return {**preview,'suggestions':suggestions}

def add_dataset(root,data):
    load(root/'biome.json')
    name=str(data.get('name','')).strip()
    location=str(data.get('location','')).strip()
    role=data.get('role')
    if not name or len(name)>300: raise ValueError('Nom requis, maximum 300 caractères')
    if not location or len(location)>4000 or '\n' in location: raise ValueError('Emplacement requis')
    if role not in ['original','derived','results','installer','reference','manual','article']: raise ValueError('Rôle invalide')
    records=load(root/'records/datasets.json')
    existing=next((d for d in records if d['id']==data.get('edit_id')),None)
    if data.get('edit_id') and existing is None: raise ValueError('Référence introuvable')
    if existing and existing.get('receipt') and location!=existing['location']:
        raise ValueError('Une copie reçue reste liée à son reçu. Son emplacement ne peut pas être modifié ici.')
    if any(d['id']!=data.get('edit_id') and d['location'].casefold().rstrip('/\\')==location.casefold().rstrip('/\\') for d in records):
        raise ValueError('Cet emplacement est déjà référencé')
    item={'id':existing['id'] if existing else 'dataset-'+uuid.uuid4().hex,'name':name,'location':location,'role':role,
          'storage':'external','description':str(data.get('description','')).strip()[:4000],
          'access_state':'not_checked','created_at':datetime.now().astimezone().isoformat()}
    if existing:
        item['created_at']=existing.get('created_at',item['created_at'])
        item['edited_at']=datetime.now().astimezone().isoformat()
        item['storage']=existing.get('storage','external')
        existing.update(item)
    else: records.append(item)
    write_json(root/'records/datasets.json',records)
    # Portable readable companion; JSON remains the source of reference.
    write_companion(root,records)
    return item

def add_entry(root, data):
    load(root/'biome.json')
    text = data.get('text', '').strip()
    kind = data.get('type')
    if not text or len(text)>50000: raise ValueError('Une note de 1 à 50000 caractères est requise')
    if kind not in ['note','experiment','meeting','exchange','decision']: raise ValueError('Type invalide')
    day = datetime.strptime(data['date'], '%Y-%m-%d')
    minutes = data.get('minutes')
    if minutes is not None and (type(minutes) is not int or minutes<0 or minutes>1440):
        raise ValueError('Durée attendue : 0 à 1440 minutes, ou non renseignée')
    tags = [s.strip() for s in data.get('tags','').split(',') if s.strip()]
    entries = load(root/'records/entries.json')
    work = load(root/'records/work-logs.json')
    existing=next((e for e in entries if e['id']==data.get('edit_id')),None)
    if data.get('edit_id') and existing is None: raise ValueError('Entrée introuvable')
    if existing and (not data.get('base_revision') or data['base_revision']!=entry_revision(root,existing) or not safe_file(root,existing['file']).is_file()):
        raise EntryConflict(preserve_entry_conflict(root,existing,data))
    eid = existing['id'] if existing else 'entry-' + uuid.uuid4().hex
    relative = existing['file'] if existing else 'journal/' + eid + '.md'
    previous_logs=[l for l in work['logs'] if eid in l['entry_ids']]
    if existing and any(len(l['entry_ids'])!=1 for l in previous_logs):
        raise ValueError('Temps partagé entre plusieurs notes : modification par séance nécessaire')
    clock = data.get('time') or datetime.now().strftime('%H:%M')
    parsed_clock = datetime.strptime(clock, '%H:%M')
    stamp = day.strftime('%d/%m/%Y') + ' ' + parsed_clock.strftime('%H:%M:00')
    note = f'---\nid: {eid}\ndate_source: "{stamp}"\ntimezone: Europe/Zurich\ntype: {kind}\ntags: {json.dumps(tags,ensure_ascii=False)}\n---\n\n{text}\n'
    item = {'id':eid,'date_source':stamp,'date_precision':'minute','timezone':'Europe/Zurich','type':kind,
            'file':relative,'tags':tags,'linked_file_ids':[], 'created_at':datetime.now().astimezone().isoformat()}
    if existing:
        item={**existing,**item,'created_at':existing.get('created_at'),'edited_at':datetime.now().astimezone().isoformat()}
    attached=[]
    uploads=data.get('attachments',[])
    if not isinstance(uploads,list) or len(uploads)>MAX_ENTRY_FILES: raise ValueError('Maximum 100 fichiers')
    uploaded_bytes=0
    for upload in uploads:
        name=upload['name']
        if not isinstance(name,str) or not name or any(c in name for c in '/\\:\r\n') or name in ('.','..'):
            raise ValueError('Nom de fichier invalide')
        raw=base64.b64decode(upload['content'],validate=True)
        uploaded_bytes+=len(raw)
        if uploaded_bytes>MAX_ENTRY_BYTES: raise ValueError('Maximum 100 Mo de pièces jointes par enregistrement')
        limit = MAX_MESSAGE_BYTES if Path(name).suffix.lower() in ['.msg', '.eml', '.txt'] else MAX_IMAGE_BYTES
        if len(raw)>limit: raise ValueError('Maximum 50 Mo par message ou fichier texte ; 10 Mo par autre fichier')
        role=upload.get('role','attachment')
        if role not in ['attachment','version']: raise ValueError('Rôle invalide')
        fid='file-'+uuid.uuid4().hex
        file_relative='files/attached/'+fid+'/'+name
        record={'id':fid,'file':file_relative,'original_name':name,'role':role,'sha256':hashlib.sha256(raw).hexdigest(),
                'bytes':len(raw),'entry_ids':[eid],'created_at':item['created_at'],
                'version_label':upload.get('label','').strip() or None,
                'caption':str(upload.get('caption','')).strip()[:2000]}
        attached.append({'record':record,'content':upload['content']})
        item['linked_file_ids'].append(fid)
    kept=json.loads(json.dumps(existing.get('attachments',[]))) if existing else []
    captions=data.get('captions',{})
    labels=data.get('version_labels',{})
    if not isinstance(labels,dict) or any(not isinstance(v,str) or len(v)>300 for v in labels.values()): raise ValueError('Libellé de version invalide (300 caractères maximum)')
    for f in kept:
        if f['id'] in labels: f['version_label']=labels[f['id']].strip() or None
        if f['id'] in captions: f['caption']=str(captions[f['id']]).strip()[:2000]
    item['attachments']=kept+[x['record'] for x in attached]
    item['linked_file_ids']=[f['id'] for f in item['attachments']]
    if item['attachments']:
        note+='\n## Fichiers associés\n'
        for f in item['attachments']:
            note+=f'- [{f["original_name"]}](../{f["file"]}) — {f["role"]}\n'
    log = None if minutes is None else {'id':previous_logs[0]['id'] if previous_logs else 'work-'+uuid.uuid4().hex,'date':data['date'],
            'minutes':minutes,'activity_type':kind,'entry_ids':[eid],'description':text[:120]}
    # Journal transaction: recovery finishes an interrupted multi-file update before serving.
    transaction = {'file':relative,'note':note,'entry':item,'work_log':log,'attachments':attached}
    if existing:
        if data['base_revision']!=entry_revision(root,existing):
            raise EntryConflict(preserve_entry_conflict(root,existing,data))
        transaction['edit']=True
        transaction['history_id']=uuid.uuid4().hex
        transaction['previous']={'entry':existing,'note':safe_file(root,relative).read_text(encoding='utf-8'),'work_logs':previous_logs}
    write_json(root/'records/pending-entry.json',transaction)
    recover(root)
    return item

def recover(root):
    if (root/'biome.json').exists() or (root/'records').is_dir(): load(root/'biome.json')
    recover_receipt(root)
    recover_project_info(root)
    recover_framing(root)
    pending = root/'records/pending-entry.json'
    if not pending.exists(): return
    t=load(pending)
    if t.get('edit') and t.get('previous'):
        current=next((entry for entry in load(root/'records/entries.json') if entry['id']==t['entry']['id']),None)
        path=safe_file(root,t['file'])
        note=path.read_text(encoding='utf-8') if path.is_file() else None
        logs=[log for log in load(root/'records/work-logs.json')['logs'] if t['entry']['id'] in log['entry_ids']]
        desired=[t['work_log']] if t.get('work_log') else []
        if current not in [t['previous']['entry'],t['entry']] or note not in [t['previous']['note'],t['note']] or logs not in [t['previous']['work_logs'],desired]:
            payload=preserve_entry_conflict(root,current or t['previous']['entry'],{'pending_transaction':t})
            pending.unlink()
            raise EntryConflict(payload)
    if t.get('edit'):
        history=root/'records/history';history.mkdir(exist_ok=True)
        write_json(history/(t['history_id']+'.json'),t['previous'])
    versions=load(root/'records/versions.json')
    for attachment in t.get('attachments',[]):
        record=attachment['record']; destination=safe_file(root,record['file'])
        destination.parent.mkdir(parents=True,exist_ok=True)
        raw=base64.b64decode(attachment['content'],validate=True)
        temporary=destination.with_name('upload.tmp')
        temporary.write_bytes(raw);os.replace(temporary,destination)
        if not any(v['id']==record['id'] for v in versions): versions.append(record)
    if t.get('edit'):
        changed={f['id']:f for f in t['entry'].get('attachments',[])}
        versions=[changed.get(v['id'],v) for v in versions]
    write_json(root/'records/versions.json',versions)
    atomic(safe_file(root,t['file']),t['note'])
    entries=load(root/'records/entries.json')
    if t.get('edit'): entries=[t['entry'] if e['id']==t['entry']['id'] else e for e in entries]
    elif not any(e['id']==t['entry']['id'] for e in entries): entries.append(t['entry'])
    write_json(root/'records/entries.json',entries)
    work=load(root/'records/work-logs.json')
    log=t['work_log']
    if t.get('edit'): work['logs']=[l for l in work['logs'] if t['entry']['id'] not in l['entry_ids']]
    if log and not any(e['id']==log['id'] for e in work['logs']): work['logs'].append(log)
    write_json(root/'records/work-logs.json',work)
    stream=io.StringIO(newline='')
    writer=csv.writer(stream)
    writer.writerow(['id','date','minutes','activity_type','entry_ids','description'])
    for x in work['logs']:
        writer.writerow([x['id'],x['date'],x['minutes'],x['activity_type'],';'.join(x['entry_ids']),x['description']])
    atomic(root/'records/activity.csv','\ufeff'+stream.getvalue())
    pending.unlink()

def update_project_info(root,data):
    fields={}
    for key in ['title','contact','group','contact_email']:
        value=data.get(key,'')
        if not isinstance(value,str) or len(value)>(254 if key=='contact_email' else 200): raise ValueError('Informations invalides ou trop longues')
        fields[key]=value.strip()
    if not fields['title'] or not fields['contact']: raise ValueError('Titre et contact requis')
    if fields['contact_email'] and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',fields['contact_email']): raise ValueError('Adresse email invalide')
    project=load(root/'biome.json')
    for key in ['contact_id','group_id']:
        if key in data: fields[key]=data[key]
    if all(project.get(key,'')==value for key,value in fields.items()): return project
    updated={**project,**fields,'updated_at':datetime.now().astimezone().isoformat()}
    write_json(root/'records/pending-info.json',{'id':'info-'+uuid.uuid4().hex,'previous':project,'updated':updated})
    recover_project_info(root)
    return updated

def recover_project_info(root):
    pending=root/'records/pending-info.json'
    if not pending.exists(): return
    record=load(pending);folder=root/'records/project-history';folder.mkdir(exist_ok=True)
    write_json(folder/(record['id']+'.json'),record)
    project=record['updated'];write_json(root/'biome.json',project)
    lines=['# Project information','','Title: '+project['title'],'','Contact: '+project['contact'],'','Email: '+project.get('contact_email',''),'','Group: '+project.get('group',''),'','Updated: '+project['updated_at'],'']
    atomic(root/'records/project-info.md','\n'.join(lines))
    pending.unlink()

def update_framing(root,data):
    status=data.get('status')
    if status not in ['Intake','Active','Review','Completed','OnHold','Unknown']: raise ValueError('Statut invalide')
    fields={}
    for key in ['objective','deliverable','next_step','validation']:
        value=data.get(key,'')
        if not isinstance(value,str) or len(value)>2000: raise ValueError('Texte attendu, maximum 2000 caractères par champ')
        fields[key]=value.strip()
    activity=data.get('activity_type','')
    if activity not in ['','consulting','training','development','analysis']: raise ValueError('Type d’intervention invalide')
    fields['activity_type']=activity
    for key in ['software','modalities','topics']:
        values=data.get(key,load(root/'biome.json').get('framing',{}).get(key,[]))
        if not isinstance(values,list) or len(values)>20 or any(not isinstance(v,str) or not v.strip() or len(v)>100 for v in values): raise ValueError('Catégories invalides, maximum 20 valeurs par liste')
        fields[key]=list(dict.fromkeys(v.strip() for v in values))
    project=load(root/'biome.json')
    if project.get('framing',{})==fields and project['status']['value']==status: return project
    updated=dict(project);stamp=datetime.now().astimezone().isoformat()
    updated.update(framing=fields,updated_at=stamp)
    updated['status']={**project.get('status',{}),'value':status,'updated_at':stamp}
    if project['status']['value']!=status: updated['status'].pop('source',None)
    record={'id':'framing-'+uuid.uuid4().hex,'date':stamp,'previous':project,'updated':updated}
    write_json(root/'records/pending-framing.json',record)
    recover_framing(root)
    return updated

def recover_framing(root):
    pending=root/'records/pending-framing.json'
    if not pending.exists(): return
    record=load(pending);history=root/'records/framing-history';history.mkdir(exist_ok=True)
    write_json(history/(record['id']+'.json'),record)
    project=record['updated'];write_json(root/'biome.json',project)
    framing=project['framing']
    lines=['# Project framing','','Status: '+project['status']['value'],'','Updated: '+record['date'],'']
    for key,label in [('objective','Agreed objective'),('deliverable','Agreed deliverable'),('next_step','Next step'),('validation','Validation / acceptance'),('activity_type','Activity type')]:
        lines+=['## '+label,'',framing[key] or 'Not specified','']
    for key,label in [('software','Software'),('modalities','Imaging modalities'),('topics','Analysis topics')]:
        lines+=['## '+label,'',', '.join(framing.get(key,[])) or 'Not specified','']
    atomic(root/'records/framing.md','\n'.join(lines))
    pending.unlink()

def directory(initial):
    recover_directory(initial)
    path=initial.parent/'.biome-directory.json'
    records=load(path) if path.exists() else {'groups':[],'contacts':[]}
    # Existing spellings remain separate until an explicit project correction.
    for root in project_catalog(initial).values():
        project=load(root/'biome.json')
        for kind,key in [('groups','group'),('contacts','contact')]:
            name=project.get(key,'').strip()
            if name and not any(item['name']==name for item in records[kind]):
                records[kind].append({'id':uuid.uuid4().hex,'name':name,'email':project.get('contact_email','') if kind=='contacts' else ''})
    write_json(path,records)
    return records

def add_directory_item(initial,data):
    kind=data.get('kind');name=data.get('name','');email=data.get('email','')
    if kind not in ['groups','contacts'] or not isinstance(name,str) or not name.strip() or len(name)>200: raise ValueError('Nom requis, maximum 200 caractères')
    if not isinstance(email,str) or len(email)>254 or (email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email)): raise ValueError('Adresse email invalide')
    records=directory(initial);name=name.strip()
    edit_id=data.get('edit_id')
    if any(item['name']==name and item['id']!=edit_id for item in records[kind]): raise ValueError('Ce nom existe déjà dans l’annuaire')
    if edit_id:
        item=next((item for item in records[kind] if item['id']==edit_id),None)
        if item is None: raise ValueError('Élément introuvable dans l’annuaire')
        previous=dict(item);item.update(name=name,email=email.strip() if kind=='contacts' else '')
        key='contact' if kind=='contacts' else 'group'
        updates=[]
        for project_key,root in project_catalog(initial).items():
            project=load(root/'biome.json')
            if project.get(key+'_id')==edit_id or (not project.get(key+'_id') and project.get(key)==previous['name']):
                fields={field:project.get(field,'') for field in ['title','contact','group','contact_email','contact_id','group_id']}
                fields[key]=name;fields[key+'_id']=edit_id
                if kind=='contacts': fields['contact_email']=item['email']
                updates.append({'project':project_key,'fields':fields})
        write_json(initial.parent/'.biome-directory-pending.json',{'directory':records,'updates':updates})
        recover_directory(initial)
        return records
    records[kind].append({'id':uuid.uuid4().hex,'name':name,'email':email.strip() if kind=='contacts' else ''})
    write_json(initial.parent/'.biome-directory.json',records)
    return records

def recover_directory(initial):
    pending=initial.parent/'.biome-directory-pending.json'
    if not pending.exists(): return
    operation=load(pending);catalog=project_catalog(initial)
    for update in operation['updates']:
        root=catalog.get(update['project'])
        if root is None: raise ValueError('Un projet associé est indisponible ; correction en attente')
        recover(root)
        update_project_info(root,update['fields'])
    write_json(initial.parent/'.biome-directory.json',operation['directory'])
    pending.unlink()

VOCABULARIES={
    'software':['QuPath','Fiji','Imaris','CellProfiler','Zeiss ZEN','napari','Python','R','Arivis'],
    'modalities':['Confocal microscopy','Widefield fluorescence microscopy','Brightfield microscopy','Slide scanning','Light sheet microscopy','Super-resolution microscopy','Electron microscopy'],
    'topics':['Segmentation','Object detection','Classification','Intensity measurement','Morphometry','Tracking','Spatial analysis','3D reconstruction','Image preprocessing','Workflow automation']}

def recover_vocabularies(initial):
    pending=initial.parent/'.biome-vocabularies-pending.json'
    if not pending.exists(): return
    operation=load(pending);catalog=project_catalog(initial)
    for update in operation['updates']:
        root=catalog.get(update['project'])
        if root is None: raise ValueError('Un projet associé est indisponible ; correction en attente')
        recover(root)
        update_framing(root,update['fields'])
    write_json(initial.parent/'.biome-vocabularies.json',operation['vocabularies'])
    pending.unlink()

def vocabularies(initial):
    recover_vocabularies(initial)
    path=initial.parent/'.biome-vocabularies.json'
    records=load(path) if path.exists() else {key:[{'id':uuid.uuid4().hex,'name':name,'active':True} for name in values] for key,values in VOCABULARIES.items()}
    for root in project_catalog(initial).values():
        framing=load(root/'biome.json').get('framing',{})
        for key in VOCABULARIES:
            for name in framing.get(key,[]):
                if not any(item['name']==name for item in records[key]): records[key].append({'id':uuid.uuid4().hex,'name':name,'active':True})
    write_json(path,records)
    return records

def edit_vocabulary(initial,data):
    kind=data.get('kind');name=data.get('name','');edit_id=data.get('edit_id');active=data.get('active',True)
    if kind not in VOCABULARIES or not isinstance(name,str) or not name.strip() or len(name)>100 or type(active) is not bool: raise ValueError('Catégorie invalide, maximum 100 caractères')
    records=vocabularies(initial);name=name.strip()
    if any(item['name'].casefold()==name.casefold() and item['id']!=edit_id for item in records[kind]): raise ValueError('Cette valeur existe déjà dans la liste')
    if not edit_id:
        records[kind].append({'id':uuid.uuid4().hex,'name':name,'active':active})
        write_json(initial.parent/'.biome-vocabularies.json',records)
        return records
    item=next((item for item in records[kind] if item['id']==edit_id),None)
    if item is None: raise ValueError('Valeur introuvable')
    previous=item['name'];item.update(name=name,active=active)
    updates=[]
    if name!=previous:
        for project_key,root in project_catalog(initial).items():
            project=load(root/'biome.json');framing=project.get('framing',{})
            if previous not in framing.get(kind,[]): continue
            fields={**framing,'status':project['status']['value'],kind:[name if value==previous else value for value in framing[kind]]}
            updates.append({'project':project_key,'fields':fields})
    write_json(initial.parent/'.biome-vocabularies-pending.json',{'vocabularies':records,'updates':updates})
    recover_vocabularies(initial)
    return records

def bind_directory(initial,data):
    for key in ['contact','group']:
        if not isinstance(data.get(key,''),str) or len(data.get(key,''))>200: raise ValueError('Nom invalide')
    email=data.get('contact_email',data.get('email',''))
    if not isinstance(email,str) or len(email)>254 or (email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email)): raise ValueError('Adresse email invalide')
    if not data.get('contact','').strip() or not isinstance(data.get('title'),str) or not data['title'].strip() or len(data['title'])>200: raise ValueError('Titre et contact requis')
    records=directory(initial)
    result=dict(data)
    for kind,key in [('groups','group'),('contacts','contact')]:
        name=data.get(key,'').strip()
        match=next((item for item in records[kind] if item['name']==name),None)
        if name and match is None:
            match={'id':uuid.uuid4().hex,'name':name,'email':email.strip() if kind=='contacts' else ''}
            records[kind].append(match)
        result[key+'_id']=match['id'] if match else None
    write_json(initial.parent/'.biome-directory.json',records)
    return result

def create_project(initial,data):
    title=str(data.get('title','')).strip();contact=str(data.get('contact','')).strip()
    request=str(data.get('request','')).strip();group=str(data.get('group','')).strip();email=str(data.get('email','')).strip()
    if not title or len(title)>200: raise ValueError('Titre requis, maximum 200 caractères')
    if not contact or len(contact)>200: raise ValueError('Contact requis, maximum 200 caractères')
    if not request or len(request)>50000: raise ValueError('Demande requise, maximum 50000 caractères')
    if len(group)>200 or len(email)>254: raise ValueError('Coordonnées trop longues')
    if email and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise ValueError('Adresse email invalide')
    originals=str(data.get('originals_location') or '').strip()
    if originals:
        original_path=Path(originals)
        if not original_path.is_absolute() or not original_path.is_dir() or original_path.is_symlink() or original_path.is_junction():
            raise ValueError('Choisissez un dossier existant pour les images originales.')
        if original_path.resolve().is_relative_to(initial.parent.resolve()) or initial.parent.resolve().is_relative_to(original_path.resolve()):
            raise ValueError('Le dossier des images originales doit être séparé du catalogue.')
    imported=None
    if data.get('source') is not None:
        if not isinstance(data['source'],dict): raise ValueError('Message source invalide')
        imported=preview_import(data['source'])
    pid=uuid.uuid4().hex;now=datetime.now().astimezone()
    slug=re.sub(r'[^a-zA-Z0-9]+','-',unicodedata.normalize('NFKD',title).encode('ascii','ignore').decode()).strip('-')[:60] or 'project'
    folder=initial.parent/(now.strftime('%Y-%m-%d')+'_'+slug+'_'+pid[:8])
    staging=initial.parent/('.creating-'+pid);staging.mkdir()
    for name in ['records','journal','request']: (staging/name).mkdir()
    metadata={'format':FORMAT,'format_version':CURRENT_VERSION,'id':'project-'+pid,'example':initial.parent.resolve()==(HERE.parent/'examples').resolve(),'title':title,'description':request,'contact':contact,'contact_email':email,'group':group,'created_at':now.isoformat(),'status':{'value':'Intake'},'metadata':{}}
    metadata.update({key:value for key,value in bind_directory(initial,metadata).items() if key in ['contact_id','group_id']})
    write_json(staging/'biome.json',metadata)
    for name in ['entries','versions','datasets','deliveries']: write_json(staging/('records/'+name+'.json'),[])
    write_json(staging/'records/work-logs.json',{'logs':[]})
    atomic(staging/'request/request.txt',request+'\n')
    atomic(staging/'README.md','# '+title+'\n\n## Contact\n'+contact+(' — '+email if email else '')+'\n\n## Group\n'+(group or 'Not specified')+'\n\n## Initial request\n'+request+'\n\nThe journal is in journal/. Linked data locations are stored in records/datasets.json.\n')
    source_date=(imported.get('date') if imported else None) or now.strftime('%Y-%m-%d')
    source_time=(imported.get('time') if imported else None) or now.strftime('%H:%M')
    add_entry(staging,{'type':'exchange','text':request,'date':source_date,'time':source_time,'minutes':None,'tags':'initial-request','attachments':[imported['source'],*imported['images']] if imported else []})
    if originals:add_dataset(staging,{'name':'Original images','role':'original','location':str(original_path.resolve()),'description':'Original data folder selected when creating the project.'})
    publish_directory(staging,folder)
    key=hashlib.sha256(str(folder.resolve()).encode()).hexdigest()[:16]
    return project_overview(folder,key)

def project_catalog(initial):
    paths=[initial]+[p for p in sorted(initial.parent.iterdir()) if p.is_dir() and p!=initial and not p.is_symlink() and (p/'biome.json').exists()]
    result={}
    for path in paths:
        try:
            project=load(path/'biome.json')
            if path.name.startswith('.'): continue
            if project.get('format')!='biome-project' or not (path/'records/entries.json').exists(): continue
            key=hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]
            result[key]=path
        except (OSError,ValueError): continue
    return result

def project_overview(path,key):
    project=load(path/'biome.json');entries=load(path/'records/entries.json')
    dates=[datetime.strptime(e['date_source'],'%d/%m/%Y %H:%M:%S') for e in entries]
    legacy=project.get('legacy_import')
    created=project.get('created_at') if not legacy else legacy.get('source_created_at')
    if legacy and legacy.get('source_last_updated'):
        value=datetime.fromisoformat(legacy['source_last_updated'].replace('Z','+00:00'))
        dates.append(value.astimezone().replace(tzinfo=None) if value.tzinfo else value)
    if project.get('updated_at'): dates.append(datetime.fromisoformat(project['updated_at']).astimezone().replace(tzinfo=None))
    for item in load(path/'records/datasets.json'):
        if item.get('receipt') and item.get('created_at'):
            dates.append(datetime.fromisoformat(item['created_at']).astimezone().replace(tzinfo=None))
    last=max(dates).isoformat() if dates else None
    return {'key':key,'title':project['title'],'contact':project.get('contact',''),'group':project.get('group',''),'status':project.get('status',{}).get('value',''),'last_activity':last,'created_at':created,'historical':bool(legacy),'entry_count':len(entries)}

def activity_report(initial,year=None,start=None,end=None):
    collected=[];years=set();warnings=[]
    for key,path in project_catalog(initial).items():
        try:
            project=load(path/'biome.json');entries=load(path/'records/entries.json');logs=load(path/'records/work-logs.json')['logs']
            if len({log['id'] for log in logs})!=len(logs): raise ValueError('Temps dupliqués')
            dated=[(entry,datetime.strptime(entry['date_source'],'%d/%m/%Y %H:%M:%S').date()) for entry in entries]
            timed=[]
            for log in logs:
                if type(log['minutes']) is not int or log['minutes']<0: raise ValueError('Durée invalide')
                timed.append((log,datetime.strptime(log['date'],'%Y-%m-%d').date()))
            years.update(d.year for _,d in dated);years.update(d.year for _,d in timed)
            collected.append((key,project,dated,timed))
        except (OSError,ValueError,KeyError,TypeError) as error: warnings.append(path.name+' : '+str(error))
    chosen=int(year) if year else max(years or {datetime.now().year})
    if bool(start)!=bool(end): raise ValueError('Date de début et de fin requises')
    first=datetime.strptime(start,'%Y-%m-%d').date() if start else datetime(chosen,1,1).date()
    last=datetime.strptime(end,'%Y-%m-%d').date() if end else datetime(chosen,12,31).date()
    if first>last: raise ValueError('La date de début doit précéder la date de fin')
    rows=[];monthly={}
    for key,project,dated,timed in collected:
        notes=[entry for entry,y in dated if first<=y<=last];work=[log for log,y in timed if first<=y<=last]
        if not notes and not work: continue
        for log in work:
            month=log['date'][:7];monthly[month]=monthly.get(month,0)+log['minutes']
        accounted={eid for log,_ in timed for eid in log.get('entry_ids',[])}
        rows.append({'key':key,'title':project['title'],'group':project.get('group',''),'contact':project.get('contact',''),'activity_type':project.get('framing',{}).get('activity_type',''),'status':project['status']['value'],'minutes':sum(log['minutes'] for log in work) if work else None,'session_count':len(work),'entry_count':len(notes),'entries_without_time':sum(entry['id'] not in accounted for entry in notes)})
    for row in rows:
        project=next(project for key,project,_,_ in collected if key==row['key'])
        row.update({key:project.get('framing',{}).get(key,[]) for key in ['software','modalities','topics']})
        row.update(group_id=project.get('group_id'),contact_id=project.get('contact_id'))
    return {'monthly_minutes':[{'month':month,'minutes':minutes} for month,minutes in sorted(monthly.items())],'start':first.isoformat(),'end':last.isoformat(),'group_count':len({row.get('group_id') or row['group'] for row in rows if row['group']}),'contact_count':len({row.get('contact_id') or row['contact'] for row in rows if row['contact']}),'year':chosen,'years':sorted(years|{chosen},reverse=True),'projects':rows,'total_minutes':sum(row['minutes'] or 0 for row in rows),'projects_with_time':sum(row['minutes'] is not None for row in rows),'entries_without_time':sum(row['entries_without_time'] for row in rows),'warnings':warnings}

def export_activity(report):
    tables={}
    tables['projects.csv']=[['Project','Group','Contact','Current status','Recorded minutes','Sessions','Activity type','Software','Imaging modalities','Analysis topics']]
    for row in report['projects']:
        tables['projects.csv'].append([row['title'],row['group'],row['contact'],row['status'],row['minutes'] if row['minutes'] is not None else '',row['session_count'],row['activity_type'],'; '.join(row['software']),'; '.join(row['modalities']),'; '.join(row['topics'])])
    for key in ['group','activity_type','software','modalities','topics']:
        categories={}
        for row in report['projects']:
            values=(row[key] or ['Not specified']) if isinstance(row[key],list) else [row[key] or 'Not specified']
            for value in set(values):
                item=categories.setdefault(value,{'projects':0,'minutes':None});item['projects']+=1
                if key in ['group','activity_type'] and row['minutes'] is not None: item['minutes']=(item['minutes'] or 0)+row['minutes']
        headers=['Category','Projects']+(['Recorded minutes'] if key in ['group','activity_type'] else [])
        tables[key+'.csv']=[headers]+[[name,item['projects']]+([item['minutes'] if item['minutes'] is not None else ''] if len(headers)==3 else []) for name,item in sorted(categories.items(),key=lambda pair:(-pair[1]['projects'],pair[0]))]
    esc=lambda value:html.escape(str(value))
    page=['<!doctype html><html lang="fr"><meta charset="utf-8"><title>BIOME — Bilan d’activité</title><style>body{font:15px system-ui;max-width:1100px;margin:40px auto;padding:20px;color:#20242a}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{text-align:left;border-bottom:1px solid #ccc;padding:9px;overflow-wrap:anywhere}th{background:#eee}h2{margin-top:35px}@media print{button{display:none}thead{display:table-header-group}tr{break-inside:avoid}body{margin:0;font-size:10pt}}</style><button onclick="window.print()">Imprimer / enregistrer en PDF</button><h1>Bilan d’activité BIOME</h1>', '<p>Période : '+esc(report['start'])+' au '+esc(report['end'])+' (dates incluses).</p>', '<p>'+esc(report['total_minutes']//60)+' h '+esc(report['total_minutes']%60)+' min renseignées · '+esc(len(report['projects']))+' projets · '+esc(report['group_count'])+' groupes · '+esc(report['contact_count'])+' contacts.</p>', '<p>Temps humain saisi à la date des séances. Une valeur vide signifie un temps non renseigné, pas zéro travail. '+esc(report['entries_without_time'])+' entrées sans saisie de temps associée. Les catégories et statuts sont les valeurs actuelles des projets. Un projet peut compter dans plusieurs catégories scientifiques ; ne pas additionner ces nombres. Aucune répartition des heures par logiciel n’est supposée.</p>']
    labels={'projects':'Détail des projets','group':'Par groupe','activity_type':'Par intervention principale','software':'Logiciels','modalities':'Modalités d’imagerie','topics':'Thématiques d’analyse'}
    for filename,rows in tables.items():
        page+=['<h2>'+labels[filename[:-4]]+'</h2><table><thead><tr>'+''.join('<th>'+esc(v)+'</th>' for v in rows[0])+'</tr></thead><tbody>']
        page.extend('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows[1:])
        page.append('</tbody></table>')
    if report['warnings']: page.append('<h2>Dossiers non comptabilisés</h2><p>'+esc('; '.join(report['warnings']))+'</p>')
    page.append('<p>Exporté le '+esc(datetime.now().astimezone().isoformat())+'. Les CSV sont encodés en UTF-8 et les temps y sont exprimés en minutes.</p></html>')
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        from activity_pdf import create_pdf
        archive.writestr('activity-report.pdf',create_pdf(report))
        archive.writestr('README.html','\n'.join(page))
        archive.writestr('activity-report.json',json.dumps(report,ensure_ascii=False,indent=2))
        for filename,rows in tables.items():
            stream=io.StringIO(newline='');writer=csv.writer(stream)
            # Prevent spreadsheet applications from interpreting user text as formulas.
            writer.writerows([["'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v for v in row] for row in rows])
            archive.writestr(filename,('\ufeff'+stream.getvalue()).encode('utf-8'))
    return buffer.getvalue()

def workspace_anchor(location):
    if not isinstance(location,str) or not location.strip() or len(location)>4000: raise ValueError('Choisissez un dossier existant')
    path=Path(location)
    if not path.is_absolute() or not path.is_dir() or path.is_symlink(): raise ValueError('Le dossier doit être accessible et son chemin absolu')
    path=path.resolve()
    if (path/'biome.json').exists(): raise ValueError('Choisissez le dossier parent des projets, pas un dossier projet individuel')
    return path/'.catalog-anchor'

