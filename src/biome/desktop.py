"""Windows standalone entry point, with an isolated writable state directory."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
from app_window import open_window
import traceback
from app_version import VERSION


def main():
    # Frozen executables must dispatch helper work before acquiring the UI lock.
    if '--probe-location' in sys.argv:
        if getattr(sys,'frozen',False):
            import ctypes,msvcrt
            ctypes.windll.kernel32.GetStdHandle.restype=ctypes.c_void_p
            if sys.stdin is None:sys.stdin=os.fdopen(msvcrt.open_osfhandle(ctypes.windll.kernel32.GetStdHandle(-10),os.O_RDONLY),'r',encoding='utf-8')
            if sys.stdout is None:sys.stdout=os.fdopen(msvcrt.open_osfhandle(ctypes.windll.kernel32.GetStdHandle(-11),os.O_WRONLY),'w',encoding='utf-8')
        from check_location import probe
        print(json.dumps(probe(json.load(sys.stdin)['location']),ensure_ascii=True))
        return 0
    parser=argparse.ArgumentParser()
    parser.add_argument('--state-dir',type=Path)
    parser.add_argument('--workspace',type=Path)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--port',type=int,default=0)
    args=parser.parse_args()
    state=(args.state_dir or Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'BIOME').resolve()
    state.mkdir(parents=True,exist_ok=True)
    lock=(state/'instance.lock').open('a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
    import msvcrt
    try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        lock.close()
        for _ in range(30):
            try:
                instance=json.loads((state/'instance.json').read_text(encoding='utf-8'))
                url=instance['url']
                from urllib.parse import urlsplit
                parsed=urlsplit(url)
                if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port:raise ValueError('Invalid local instance')
                running=instance.get('version') or 'version antérieure'
                if running!=VERSION:
                    message=f'BIOME {running} est déjà ouvert. Vous avez lancé BIOME {VERSION}.\n\nDans la fenêtre existante, cliquez sur « Quitter BIOME », puis relancez cette nouvelle version. Vos projets restent conservés.'
                    if args.no_browser:
                        if sys.stderr:sys.stderr.write(message+'\n')
                    else:
                        import ctypes
                        ctypes.windll.user32.MessageBoxW(None,message,'BIOME — autre version ouverte',0x30)
                    return 2
                if not args.no_browser:open_window(url,state)
                return 0
            except (OSError,ValueError,KeyError):time.sleep(.1)
        raise RuntimeError('BIOME démarre déjà. Réessayez dans quelques secondes.')
    try:
        (state/'instance.json').unlink(missing_ok=True)
        import server
        import data_store as store
        settings=state/'workspace.json';warning=None;catalogue_required=False
        if args.workspace:
            root=store.workspace_anchor(str(args.workspace.resolve()))
            from catalogues import remember_catalogue
            remember_catalogue(settings,str(root.parent))
        elif settings.exists():
            try:root=store.workspace_anchor(store.load(settings)['location'])
            except (OSError,ValueError,KeyError):
                catalog=state/'Projects';catalog.mkdir(exist_ok=True);root=store.workspace_anchor(str(catalog))
                warning='Votre dossier de travail mémorisé est inaccessible. Reconnectez le stockage ou choisissez un dossier dans Dossier de travail. Le réglage précédent reste conservé jusqu’à votre choix.'
        else:
            catalog=state/'No-catalogue-selected';catalog.mkdir(exist_ok=True)
            root=store.workspace_anchor(str(catalog))
            catalogue_required=True
        # Shared browser logs and errors live outside the program folder.
        log=(state/'application.log').open('a',encoding='utf-8',buffering=1)
        previous_stderr=sys.stderr
        sys.stderr=log
        def ready(port):
            url='http://127.0.0.1:'+str(port)+'/'
            store.write_json(state/'instance.json',{'url':url,'pid':os.getpid(),'version':VERSION})
            if not args.no_browser:open_window(url,state)
        try:server.serve(root,args.port,settings,state_dir=state,on_ready=ready,desktop=True,startup_warning=warning,catalogue_required=catalogue_required)
        finally:sys.stderr=previous_stderr;log.close()
    finally:
        (state/'instance.json').unlink(missing_ok=True)
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1);lock.close()
    return 0


if __name__=='__main__':
    # Windowed PyInstaller executables have no stdout/stdin. Helper subprocesses
    # receive redirected handles and keep their JSON protocol available.
    try:raise SystemExit(main())
    except Exception:
        message=traceback.format_exc()
        if '--no-browser' in sys.argv or '--probe-location' in sys.argv:
            if sys.stderr:sys.stderr.write(message)
        else:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,'BIOME ne peut pas démarrer. Vérifiez que votre dossier de travail est accessible.\n\n'+message[-1800:],'BIOME',0x10)
        raise SystemExit(1)
