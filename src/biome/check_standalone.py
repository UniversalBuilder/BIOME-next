"""Exercise the compiled application from a relocated copy, without developer Python."""
import argparse,base64,hashlib,io,json,os,re,shutil,subprocess,tempfile,time,urllib.request,urllib.error,urllib.parse,zipfile
from pathlib import Path


def run(executable,msg=None):
    scratch=Path(__file__).resolve().parent/'test-tmp';scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='standalone-',dir=scratch) as tmp:
        base=Path(tmp).resolve();program=base/'Program with spaces';shutil.copytree(executable.parent,program)
        exe=program/executable.name;state=base/'User state';catalog=base/'Project catalogue'
        files_before={p.relative_to(program).as_posix():(p.stat().st_size,p.stat().st_mtime_ns) for p in program.rglob('*') if p.is_file()}
        process=None
        def launch(*extra):
            p=subprocess.Popen([str(exe),'--no-browser','--state-dir',str(state),*extra],cwd=base,creationflags=0x08000000)
            for _ in range(150):
                if p.poll() is not None:raise AssertionError('Application exited before readiness: '+str(p.returncode))
                try:
                    instance=json.loads((state/'instance.json').read_text(encoding='utf-8'))
                    if instance['pid']==p.pid:
                        page=urllib.request.urlopen(instance['url'],timeout=2).read().decode();return p,instance['url'],page
                except (OSError,ValueError):pass
                time.sleep(.1)
            raise AssertionError('Application readiness timeout')
        def stop(p,url,token):
            req=urllib.request.Request(url+'api/shutdown',data=b'{}',headers={'X-Biome-Token':token,'Content-Type':'application/json'})
            urllib.request.urlopen(req,timeout=10).read();assert p.wait(timeout=15)==0
        try:
            process,url,page=launch();assert 'Quitter BIOME' in page
            token=re.search("const token='([^']+)'",page).group(1)
            def get(path):return json.load(urllib.request.urlopen(url+path,timeout=20))
            def post(path,data):return json.load(urllib.request.urlopen(urllib.request.Request(url+path,data=json.dumps(data).encode(),headers={'X-Biome-Token':token,'Content-Type':'application/json'}),timeout=30))
            from app_version import VERSION
            assert VERSION in page and '__APP_VERSION__' not in page
            assert get('api/about')['version']==VERSION
            with urllib.request.urlopen(url+'favicon.ico',timeout=10) as response:
                assert response.headers['Content-Type']=='image/x-icon' and response.read()[:4]==b'\x00\x00\x01\x00'
            # Check packaged UI/font assets as well as backend functionality.
            source=Path(__file__).resolve().parent
            for asset,mime in [('interface.css','text/css'),('interface.js','application/javascript'),('accounting.js','application/javascript')]+[(f'fonts/roboto-latin-{weight}-normal.woff2','font/woff2') for weight in [400,500,600,700]]:
                with urllib.request.urlopen(url+asset,timeout=10) as response:
                    assert response.headers['Content-Type'].startswith(mime)
                    assert hashlib.sha256(response.read()).digest()==hashlib.sha256((source/asset).read_bytes()).digest(),asset
            assert 'page-help-dialog' in page and 'Comprendre cet écran' not in page
            assert get('api/workspace')['needs_selection'] is True
            post('api/catalogue-create',{'destination':str(base),'name':catalog.name})
            assert get('api/projects')==[]
            instance=(state/'instance.json').read_bytes()
            again=subprocess.run([str(exe),'--no-browser','--state-dir',str(state)],timeout=15,creationflags=0x08000000)
            assert again.returncode==0 and (state/'instance.json').read_bytes()==instance and process.poll() is None
            item=post('api/projects',{'title':'Standalone synthetic','contact':'Example person','request':'Synthetic request'})
            key=item['key'];query='?project='+key
            post('api/entries'+query,{'type':'note','text':'Local session','date':'2026-10-15','time':'10:00','minutes':15})
            for asset in ['delivery-selector.js','delivery-selector.css']:
                assert urllib.request.urlopen(url+asset,timeout=10).status==200
            directory=get('api/directory');old=next(x for x in directory['contacts'] if x['name']=='Example person')
            directory=post('api/directory',{'kind':'contacts','name':'Replacement person','email':'replacement@example.org'})
            replacement=next(x for x in directory['contacts'] if x['name']=='Replacement person')
            removal={'kind':'contacts','id':old['id'],'replacement_id':replacement['id']}
            preview=post('api/directory-removal-preview',removal);assert len(preview['projects'])==1
            request=urllib.request.Request(url+'api/directory-remove',data=b'{}',headers={'Content-Type':'application/json'})
            try:urllib.request.urlopen(request,timeout=10);raise AssertionError('Unauthenticated deletion accepted')
            except urllib.error.HTTPError as error:assert error.code==403
            post('api/directory-remove',{**removal,'revision':preview['revision']})
            assert get('api/project'+query)['project']['contact']=='Replacement person'
            project=get('api/project'+query);selected=project['delivery_files'][0]
            preview=get('api/delivery-preview'+query+'&file='+urllib.parse.quote(selected['file']))
            assert preview['text'] and selected['revision'] and selected['group_title']
            post('api/deliveries'+query,{'files':[selected['file']],'display_labels':{selected['file']:'Synthetic delivery note'},'revisions':{selected['file']:selected['revision']},'note':'Packaged selector smoke test'})
            project=get('api/project'+query)
            assert project['deliveries'][-1]['selection'][0]['title']=='Synthetic delivery note'
            post('api/project-info'+query,{'title':'Standalone synthetic','contact':'Example person','group':'','contact_email':'','project_date':'2020-03-24','known_activity_date':''})
            assert get('api/project'+query)['dates']['project_date']=='2020-03-24'
            assert get('api/projects')[0]['created_at']=='2020-03-24'
            data_parent=base/'Original data';data_parent.mkdir()
            suggestion=get('api/project'+query)['data_folder']['suggested_name']
            folder=post('api/create-data-folder'+query,{'parent':str(data_parent),'name':suggestion})
            raw_folder=Path(folder['location'])
            assert raw_folder.is_dir() and (raw_folder.parent/'02_processed').is_dir() and (raw_folder.parent/'README.txt').is_file()
            assert get('api/project'+query)['data_folder']['default_raw']==str(raw_folder)
            received_source=base/'synthetic-raw.tif';received_source.write_bytes(b'Synthetic original')
            prepared=post('api/receive-preview'+query,{'source':str(received_source)})
            received=post('api/receive-data'+query,{**prepared,'storage':'external','destination':str(raw_folder)})
            assert (Path(received['location'])/received_source.name).read_bytes()==received_source.read_bytes()
            source=base/'external.txt';source.write_text('Synthetic external data',encoding='utf-8')
            post('api/datasets'+query,{'name':'Synthetic external','location':str(source),'role':'reference'})
            result=get('api/diagnostics');assert result['errors']==0 and all(x['state']=='accessible' for x in result['locations']),result
            report=get('api/activity-report?year=2026')
            assert report['projects_with_time']==1
            assert report['breakdowns']['group']['excluded']==1
            assert report['breakdowns']['group']['items']==[]
            assert "['group','Groupe / laboratoire'],['contact','Contact']" in page
            assert 'report-missing-projects' in page
            with urllib.request.urlopen(url+'api/activity-export?year=2026',timeout=30) as response:packed=response.read()
            with zipfile.ZipFile(io.BytesIO(packed)) as archive:
                assert archive.read('activity-report.pdf').startswith(b'%PDF')
                assert 'coverage.csv' in archive.namelist()
            # Independent time and explicit report scope survive in the packaged application.
            accounting=get('api/project'+query)
            saved=post('api/accounting'+query,{'action':'save','base_revision':accounting['work_revision'],'date':'2026-03-02','minutes':150,'estimate':True,'description':'Standalone historical estimate'})
            independent=next(log for log in saved['logs'] if log.get('source')=='manual')
            assert get('api/activity-report?year=2026')['estimated_minutes']==150
            hidden=post('api/accounting'+query,{'action':'scope','base_revision':saved['work_revision'],'excluded':True,'reason':'Standalone scope check'})
            excluded=get('api/activity-report?year=2026');assert excluded['projects']==[] and len(excluded['excluded_projects'])==1
            included=post('api/accounting'+query,{'action':'scope','base_revision':hidden['work_revision'],'excluded':False,'reason':''})
            post('api/accounting'+query,{'action':'delete','base_revision':included['work_revision'],'id':independent['id']})
            assert get('api/activity-report?year=2026')['estimated_minutes']==0
            if msg:
                imported=post('api/import-preview',{'name':msg.name,'content':base64.b64encode(msg.read_bytes()).decode()})
                assert imported['text'] and imported['date'] and len(imported['images'])==5
            demo_parent=base/'Demo destination';demo_parent.mkdir()
            demo=post('api/demo-install',{'destination':str(demo_parent)})
            assert demo['projects']==3 and get('api/workspace')['demo'] is True
            assert len(get('api/projects'))==3
            post('api/catalogue-open',{'location':str(catalog)})
            assert len(get('api/projects'))==1 and get('api/workspace').get('demo') is not True
            try:urllib.request.urlopen(urllib.request.Request(url+'api/shutdown',data=b'{}',headers={'X-Biome-Token':'wrong'}),timeout=10)
            except urllib.error.HTTPError as error:assert error.code==403
            else:raise AssertionError('Unauthenticated shutdown accepted')
            stop(process,url,token);assert not (state/'instance.json').exists()
            process,url,page=launch();token=re.search("const token='([^']+)'",page).group(1)
            assert str(catalog)==get('api/workspace')['location'] and len(get('api/projects'))==1
            stop(process,url,token)
            original_settings=(state/'workspace.json').read_bytes();catalog.rename(base/'offline catalogue')
            process,url,page=launch();token=re.search("const token='([^']+)'",page).group(1)
            assert 'inaccessible' in page and (state/'workspace.json').read_bytes()==original_settings
            stop(process,url,token)
            assert files_before=={p.relative_to(program).as_posix():(p.stat().st_size,p.stat().st_mtime_ns) for p in program.rglob('*') if p.is_file()}
            print('Compiled standalone OK: relocated path with spaces, empty catalogue, singleton, persisted workspace, PDF, external-access helper, optional MSG, authenticated stop, clean restart and inaccessible-workspace recovery. Program folder untouched.')
        finally:
            if process and process.poll() is None:
                process.terminate();process.wait(timeout=10)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('executable',type=Path);parser.add_argument('--msg',type=Path);args=parser.parse_args();run(args.executable.resolve(),args.msg)
