"""Open BIOME in an isolated Chromium application window, without browser chrome."""
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit


def find_browser():
    candidates=[]
    # Prefer Chrome when available, then the Windows-provided Edge browser.
    for product,exe in [('Google/Chrome/Application','chrome.exe'),('Microsoft/Edge/Application','msedge.exe')]:
        try:
            import winreg
            for hive in [winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE]:
                try:
                    with winreg.OpenKey(hive,'Software\\Microsoft\\Windows\\CurrentVersion\\App Paths\\'+exe) as key:
                        candidates.append(Path(winreg.QueryValue(key,None)))
                except OSError:pass
        except ImportError:pass
        for variable in ['PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA']:
            if os.environ.get(variable):candidates.append(Path(os.environ[variable])/product/exe)
    return next((path for path in candidates if path.is_file()),None)


def open_window(url,state):
    parsed=urlsplit(url)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port:
        raise ValueError('Adresse locale BIOME invalide')
    browser=find_browser()
    if browser is None:raise RuntimeError('Une fenêtre BIOME nécessite Microsoft Edge ou Google Chrome installé sur ce PC.')
    profile=Path(state).resolve()/'Browser';profile.mkdir(parents=True,exist_ok=True)
    return subprocess.Popen([str(browser),'--app='+url,'--user-data-dir='+str(profile),'--no-first-run','--no-default-browser-check','--window-size=1280,900'],creationflags=0x08000000 if os.name=='nt' else 0)
