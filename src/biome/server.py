"""Local HTTP adapter for folder-backed BIOME workflows."""
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse, json, subprocess, uuid, threading
from urllib.parse import urlparse, parse_qs
import data_store as store

HERE = Path(__file__).resolve().parent

def serve(root,port,settings=None,*,state_dir=None,on_ready=None,desktop=False,startup_warning=None,catalogue_required=False):
    try: store.recover(root)
    except store.EntryConflict: pass  # Both versions have been preserved; do not prevent reading the project.
    token_path=(Path(state_dir) if state_dir else HERE)/'.local-session-token'
    if not token_path.exists(): store.atomic(token_path,uuid.uuid4().hex)
    token=token_path.read_text(encoding='utf-8').strip()
    initial=root
    diagnostic_jobs={}
    class Handler(BaseHTTPRequestHandler):
        def selected_project(self):
            key=parse_qs(urlparse(self.path).query).get('project',[''])[0]
            if not key: return initial
            path=store.project_catalog(initial).get(key)
            if path is None: raise ValueError('Projet introuvable dans le catalogue du prototype')
            return path

        def send(self,code,body,mime='application/json; charset=utf-8'):
            raw=body.encode('utf-8'); self.send_response(code)
            self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            try:
                route=urlparse(self.path).path
                root=self.selected_project()
                if route=='/':
                    page=(HERE/'index.html').read_text(encoding='utf-8').replace('__TOKEN__',token)
                    if startup_warning:
                        import html
                        page=page.replace('<main>','<main><p role="status" style="padding:16px;border:1px solid #f4cf91;border-radius:8px">'+html.escape(startup_warning)+'</p>',1)
                    if desktop:
                        page=page.replace('BIOME · Prototype local','BIOME').replace('Prototype local','Application locale')
                        page=page.replace('</nav>', '<button type="button" id="stop-biome">Quitter BIOME</button></nav>',1)
                        page+='''<script>document.querySelector('#stop-biome').onclick=async function(){this.disabled=true;try{const r=await fetch('/api/shutdown',{method:'POST',headers:{'X-Biome-Token':token,'Content-Type':'application/json'},body:'{}'});if(!r.ok)throw new Error('Arrêt impossible');document.body.replaceChildren();const p=document.createElement('p');p.style.padding='40px';p.textContent='BIOME est arrêté. Vous pouvez fermer cet onglet.';document.body.append(p)}catch(e){this.disabled=false;alert(e.message)}};</script>'''
                    self.send(200,page,'text/html; charset=utf-8')
                elif route=='/project-sort.js': self.send(200,(HERE/'project_sort.js').read_text(encoding='utf-8'),'application/javascript; charset=utf-8')
                elif route=='/api/about':
                    from app_version import VERSION,CHANNEL
                    self.send(200,json.dumps({'name':'BIOME','version':VERSION,'channel':CHANNEL,'project_format':'1.1','catalogue_format':1,'ui_language':'fr','publication_ready':False}))
                elif route=='/api/workspace':
                    from catalogues import catalogue_info
                    info=catalogue_info(initial.parent)
                    recent=store.load(settings).get('recent_catalogues',[]) if settings and Path(settings).exists() else []
                    self.send(200,json.dumps({**info,'needs_selection':catalogue_required,'recent_catalogues':recent,'example':bool(info.get('demo')) or initial.parent.resolve()==(HERE.parent/'examples').resolve()},ensure_ascii=False))
                elif route=='/api/diagnostics':
                    from diagnostics import diagnose_catalog
                    self.send(200,json.dumps(diagnose_catalog(initial.parent,check_locations=True),ensure_ascii=False))
                elif route=='/api/diagnostics-progress':
                    identifier=parse_qs(urlparse(self.path).query).get('id',[''])[0]
                    job=diagnostic_jobs.get(identifier)
                    self.send(200 if job else 404,json.dumps(job or {'error':'Contrôle introuvable.'},ensure_ascii=False))
                elif route=='/api/trash':
                    from catalogue_management import trash_contents
                    self.send(200,json.dumps(trash_contents(initial.parent),ensure_ascii=False))
                elif route=='/api/activity-report': self.send(200,json.dumps(store.activity_report(initial,**{key:parse_qs(urlparse(self.path).query).get(key,[None])[0] for key in ['year','start','end']}),ensure_ascii=False))
                elif route=='/api/activity-export':
                    report=store.activity_report(initial,**{key:parse_qs(urlparse(self.path).query).get(key,[None])[0] for key in ['year','start','end']})
                    packed=store.export_activity(report)
                    self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Disposition','attachment; filename="BIOME_activity_'+report['start']+'_'+report['end']+'.zip"');self.send_header('Content-Length',str(len(packed)));self.end_headers();self.wfile.write(packed)
                elif route=='/api/projects': self.send(200,json.dumps([store.project_overview(p,k) for k,p in store.project_catalog(initial).items()],ensure_ascii=False))
                elif route=='/api/directory': self.send(200,json.dumps(store.directory(initial),ensure_ascii=False))
                elif route=='/api/vocabularies': self.send(200,json.dumps(store.vocabularies(initial),ensure_ascii=False))
                elif route=='/api/project': self.send(200,json.dumps(store.read_project(root),ensure_ascii=False))
                elif urlparse(self.path).path=='/api/delivery':
                    did=parse_qs(urlparse(self.path).query).get('id',[''])[0]
                    records=store.load(root/'records/deliveries.json') if (root/'records/deliveries.json').exists() else []
                    item=next((d for d in records if d['id']==did),None)
                    if item is None: return self.send(404,'{}')
                    self.send_response(200);self.send_header('Content-Type','application/zip');self.send_header('Content-Disposition','attachment; filename="'+Path(item['file']).name+'"');self.end_headers()
                    with store.safe_file(root,item['file']).open('rb') as stream:
                        while chunk:=stream.read(65536): self.wfile.write(chunk)
                elif urlparse(self.path).path=='/api/file':
                    fid=parse_qs(urlparse(self.path).query).get('id',[''])[0]
                    match=next((x for x in store.load(root/'records/versions.json') if x['id']==fid),None)
                    if match is None: return self.send(404,'{}')
                    raw=store.safe_file(root,match['file']).read_bytes()
                    preview=parse_qs(urlparse(self.path).query).get('preview',[''])[0]=='1'
                    mime=None
                    if raw.startswith(b'\x89PNG\r\n\x1a\n'): mime='image/png'
                    elif raw.startswith(b'\xff\xd8\xff'): mime='image/jpeg'
                    elif raw[:6] in (b'GIF87a',b'GIF89a'): mime='image/gif'
                    elif raw[:4]==b'RIFF' and raw[8:12]==b'WEBP': mime='image/webp'
                    if preview and mime is None: return self.send(415,json.dumps({'error':'Aperçu indisponible pour ce format'}))
                    self.send_response(200);self.send_header('Content-Type',mime if preview else 'application/octet-stream')
                    self.send_header('Content-Disposition','inline' if preview else 'attachment');self.send_header('X-Content-Type-Options','nosniff')
                    self.end_headers();self.wfile.write(raw)
                else: self.send(404,'{}')
            except Exception as e: self.send(500,json.dumps({'error':str(e)}))
        def do_POST(self):
            nonlocal initial,catalogue_required
            route=urlparse(self.path).path
            if route=='/api/shutdown' and desktop:
                if self.headers.get('X-Biome-Token')!=token: return self.send(403,'{}')
                self.send(200,'{}');threading.Thread(target=httpd.shutdown,daemon=True).start();return
            if route not in ['/api/catalogue-create','/api/catalogue-open','/api/demo-install','/api/project-trash','/api/project-restore','/api/relocate-catalogue','/api/diagnostics-start','/api/entries','/api/datasets','/api/select-data','/api/deliveries','/api/import-preview','/api/projects','/api/framing','/api/project-info','/api/directory','/api/vocabularies','/api/request-preview','/api/workspace','/api/backup','/api/restore','/api/receive-preview','/api/receive-data','/api/open-dataset']: return self.send(404,'{}')
            if self.headers.get('X-Biome-Token')!=token:
                return self.send(403,json.dumps({'error':'Cette page utilise une ancienne session. Copiez votre note, puis rechargez la page.'}))
            try:
                root=self.selected_project()
                size=int(self.headers.get('Content-Length','0'))
                limit = 140_000_000 if route in ['/api/entries','/api/projects'] else 70_000_000 if route in ['/api/import-preview','/api/request-preview'] else 35_000_000
                if size<1 or size>limit: raise ValueError('Requête trop grande ou vide')
                data=json.loads(self.rfile.read(size))
                if route in ['/api/catalogue-create','/api/catalogue-open','/api/demo-install']:
                    from catalogues import create_catalogue,open_catalogue,remember_catalogue
                    if route!='/api/catalogue-open' and Path(str(data.get('destination',''))).resolve().is_relative_to(initial.parent.resolve()):
                        raise ValueError('Choisissez une destination en dehors du catalogue courant.')
                    if route=='/api/demo-install':
                        from demo_catalogue import install_demo
                        result=install_demo(data.get('destination'))
                    elif route=='/api/catalogue-create':result=create_catalogue(data.get('destination'),data.get('name'))
                    else:result=open_catalogue(data.get('location'))
                    anchor=store.workspace_anchor(result['location'])
                    remember_catalogue(settings,result['location']);initial=anchor;catalogue_required=False
                    return self.send(200,json.dumps(result,ensure_ascii=False))
                if catalogue_required and route=='/api/projects':raise ValueError('Créez ou ouvrez un catalogue avant de commencer un projet.')
                if route=='/api/diagnostics-start':
                    from diagnostics import diagnose_catalog
                    location=str(initial.parent)
                    active=next((job for job in diagnostic_jobs.values() if job['state']=='running' and job['location']==location),None)
                    if active:return self.send(200,json.dumps(active))
                    if len(diagnostic_jobs)>=8:
                        for identifier in list(diagnostic_jobs):
                            if diagnostic_jobs[identifier]['state']!='running':del diagnostic_jobs[identifier]
                    identifier=uuid.uuid4().hex
                    diagnostic_jobs[identifier]={'id':identifier,'state':'running','location':location,'checked':0,'total':None}
                    def run_diagnostic():
                        def progress(checked,total):diagnostic_jobs[identifier]={**diagnostic_jobs[identifier],'checked':checked,'total':total}
                        try:
                            result=diagnose_catalog(Path(location),check_locations=True,progress=progress)
                            diagnostic_jobs[identifier]={**diagnostic_jobs[identifier],'state':'done','result':result}
                        except Exception as error:diagnostic_jobs[identifier]={**diagnostic_jobs[identifier],'state':'error','error':str(error)}
                    threading.Thread(target=run_diagnostic,daemon=True).start()
                    return self.send(202,json.dumps(diagnostic_jobs[identifier]))
                if route=='/api/project-trash':
                    from catalogue_management import trash_project
                    return self.send(200,json.dumps(trash_project(initial.parent,root),ensure_ascii=False))
                if route=='/api/project-restore':
                    from catalogue_management import restore_project
                    return self.send(200,json.dumps(restore_project(initial.parent,data.get('id')),ensure_ascii=False))
                if route=='/api/relocate-catalogue':
                    from catalogue_management import relocate_catalogue
                    result=relocate_catalogue(initial.parent,data.get('destination'))
                    anchor=store.workspace_anchor(result['location'])
                    from catalogues import remember_catalogue
                    remember_catalogue(settings,result['location'])
                    initial=anchor
                    return self.send(201,json.dumps(result,ensure_ascii=False))
                if route=='/api/receive-preview':
                    from data_receipts import preview_receipt
                    return self.send(200,json.dumps(preview_receipt(data.get('source')),ensure_ascii=False))
                if route not in ['/api/backup','/api/restore']:
                    try: store.recover(root)
                    except store.EntryConflict:
                        if route=='/api/entries' and data.get('edit_id'):
                            entry=next((item for item in store.load(root/'records/entries.json') if item['id']==data['edit_id']),None)
                            if entry: raise store.EntryConflict(store.preserve_entry_conflict(root,entry,data))
                        raise
                if route=='/api/backup':
                    from backups import create_backup
                    return self.send(201,json.dumps(create_backup(initial.parent,data.get('destination')),ensure_ascii=False))
                if route=='/api/restore':
                    from backups import restore_backup, existing_folder
                    if existing_folder(data.get('destination')).is_relative_to(initial.parent.resolve()):
                        raise ValueError('Choisissez une destination en dehors du catalogue actuel pour restaurer la copie.')
                    return self.send(201,json.dumps(restore_backup(data.get('archive'),data.get('destination')),ensure_ascii=False))
                if route=='/api/workspace':
                    anchor=store.workspace_anchor(data.get('location'))
                    from catalogues import remember_catalogue
                    remember_catalogue(settings,str(anchor.parent));initial=anchor;catalogue_required=False
                    return self.send(200,json.dumps({'location':str(initial.parent)},ensure_ascii=False))
                if route=='/api/directory': return self.send(201,json.dumps(store.add_directory_item(initial,data),ensure_ascii=False))
                if route=='/api/vocabularies': return self.send(200,json.dumps(store.edit_vocabulary(initial,data),ensure_ascii=False))
                if route=='/api/project-info': return self.send(200,json.dumps(store.update_project_info(root,store.bind_directory(initial,data)),ensure_ascii=False))
                if route=='/api/framing': return self.send(200,json.dumps(store.update_framing(root,data),ensure_ascii=False))
                if route=='/api/projects': return self.send(201,json.dumps(store.create_project(initial,data),ensure_ascii=False))
                if route=='/api/request-preview': return self.send(200,json.dumps(store.preview_request(data),ensure_ascii=False))
                if route=='/api/import-preview': return self.send(200,json.dumps(store.preview_import(data),ensure_ascii=False))
                if route=='/api/receive-data':
                    from data_receipts import receive_data
                    return self.send(201,json.dumps(receive_data(root,data),ensure_ascii=False))
                if route=='/api/open-dataset':
                    from data_receipts import dataset_path
                    item=next((item for item in store.load(root/'records/datasets.json') if item['id']==data.get('id')),None)
                    if item is None: raise ValueError('Données inconnues.')
                    if item['location'].lower().startswith(('http:','https:')): raise ValueError('Ce lien web ne correspond pas à un dossier local.')
                    path=dataset_path(root,item)
                    if not path.is_absolute(): raise ValueError('Cet emplacement ne contient pas un chemin complet.')
                    if not path.exists(): raise ValueError('Emplacement inaccessible depuis cet ordinateur.')
                    subprocess.Popen(['explorer.exe',str(path if path.is_dir() else path.parent)])
                    return self.send(200,json.dumps({'opened':True}))
                if route=='/api/select-data':
                    kind=data.get('kind')
                    if kind not in ['file','folder']: raise ValueError('Sélection invalide')
                    purpose=data.get('purpose') if data.get('purpose') in ['workspace','backup','restore','receive'] else 'data'
                    result=subprocess.run(['powershell.exe','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',str(HERE/'Select-Data.ps1'),'-Kind',kind,'-Purpose',purpose],capture_output=True,encoding='utf-8-sig',creationflags=0x08000000)
                    if result.returncode!=0: raise ValueError('Le sélecteur Windows n’a pas pu être ouvert')
                    return self.send(200,result.stdout.strip())
                item=store.make_delivery(root,data) if route=='/api/deliveries' else store.add_dataset(root,data) if route=='/api/datasets' else store.add_entry(root,data)
                self.send(201,json.dumps(item))
            except store.EntryConflict as e: self.send(409,json.dumps(e.payload,ensure_ascii=False))
            except (ValueError,KeyError,TypeError) as e: self.send(400,json.dumps({'error':str(e)}))
            except Exception as e: self.send(500,json.dumps({'error':str(e)}))
    httpd=HTTPServer(('127.0.0.1',port),Handler)
    print(f'BIOME prototype: http://127.0.0.1:{httpd.server_port}',flush=True)
    if on_ready: on_ready(httpd.server_port)
    try: httpd.serve_forever()
    finally: httpd.server_close()

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',type=Path)
    parser.add_argument('--settings',type=Path,default=HERE/'.workspace-settings.json')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    root=args.project.resolve() if args.project else store.workspace_anchor(store.load(args.settings)['location']) if args.settings.exists() else (HERE.parent/'examples/ct-fire-project-v1').resolve()
    serve(root,args.port,args.settings)
