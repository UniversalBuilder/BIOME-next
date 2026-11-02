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


def open_window(url,state,profile=None):
    parsed=urlsplit(url)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port:
        raise ValueError('Adresse locale BIOME invalide')
    browser=find_browser()
    if browser is None:raise RuntimeError('Une fenêtre BIOME nécessite Microsoft Edge ou Google Chrome installé sur ce PC.')
    profile=Path(profile) if profile is not None else Path(state).resolve()/'Browser';profile.mkdir(parents=True,exist_ok=True)
    return subprocess.Popen([str(browser),'--app='+url,'--user-data-dir='+str(profile),'--no-first-run','--no-default-browser-check','--disable-background-mode','--window-size=1280,900'],creationflags=0x08000000 if os.name=='nt' else 0)


def browser_windows(pids):
    """Visible Chromium windows owned by our launched processes, never personal browsers."""
    import ctypes
    from ctypes import wintypes
    user32=ctypes.WinDLL('user32',use_last_error=True)
    user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes=[wintypes.HWND]
    user32.GetClassNameW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    windows=[]
    @callback_type
    def collect(hwnd,_):
        pid=wintypes.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(hwnd):
            name=ctypes.create_unicode_buffer(256);user32.GetClassNameW(hwnd,name,256)
            if name.value.startswith('Chrome_WidgetWin_'):windows.append(hwnd)
        return True
    user32.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    if not user32.EnumWindows(collect,0):raise ctypes.WinError(ctypes.get_last_error())
    return windows


class WindowLifetime:
    """Distinguish startup delay, temporary window replacement and final closure."""
    def __init__(self,started,startup_timeout=45,close_grace=1.5):
        self.started=started;self.startup_timeout=startup_timeout;self.close_grace=close_grace
        self.seen=False;self.empty_since=None

    def should_stop(self,now,count):
        if count:
            self.seen=True;self.empty_since=None;return False
        if not self.seen:return now-self.started>=self.startup_timeout
        if self.empty_since is None:self.empty_since=now
        return now-self.empty_since>=self.close_grace


class ApplicationWindows:
    def __init__(self,state,url):
        import tempfile,threading,time
        self.state=Path(state);self.url=url
        parent=self.state/'Browser';parent.mkdir(parents=True,exist_ok=True)
        # A unique session avoids handing ownership to a stale/personal Chromium process.
        self.profile=Path(tempfile.mkdtemp(prefix='session-',dir=parent))
        self.processes=[];self.lock=threading.Lock();self.closed=threading.Event()
        self.lifetime=WindowLifetime(time.monotonic());self.thread=None

    def open(self):
        import time
        with self.lock:
            self.lifetime=WindowLifetime(time.monotonic())
            process=open_window(self.url,self.state,self.profile)
            self.processes.append(process)
        return process

    def owned_windows(self):
        with self.lock:
            pids={p.pid for p in self.processes if p.poll() is None}
        return browser_windows(pids) if pids else []

    def start(self,shutdown):
        import threading,time
        def watch():
            while not self.closed.wait(.25):
                try:count=len(self.owned_windows())
                except OSError:
                    # Failed observation is not evidence that the user closed a window.
                    continue
                if self.lifetime.should_stop(time.monotonic(),count):
                    shutdown();return
        self.thread=threading.Thread(target=watch,name='biome-window-lifetime',daemon=True)
        self.thread.start()

    def close(self):
        import ctypes,shutil
        from ctypes import wintypes
        self.closed.set()
        try:
            user32=ctypes.WinDLL('user32',use_last_error=True)
            user32.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
            for hwnd in self.owned_windows():user32.PostMessageW(hwnd,0x0010,0,0)  # WM_CLOSE
            for process in self.processes:
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:pass
            if all(p.poll() is not None for p in self.processes):
                shutil.rmtree(self.profile,ignore_errors=True)
        except OSError:pass
