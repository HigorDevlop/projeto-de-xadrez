"""Give only Coach Chess windows and shortcuts one Windows taskbar identity."""
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

APP_ID='CoachChess.Desktop'

class GUID(C.Structure):
    _fields_=[('bytes',C.c_ubyte*16)]
    def __init__(self,value):super().__init__((C.c_ubyte*16).from_buffer_copy(uuid.UUID(value).bytes_le))

class PROPERTYKEY(C.Structure):
    _fields_=[('fmtid',GUID),('pid',W.DWORD)]

class Value(C.Union):
    _fields_=[('pointer',C.c_void_p),('storage',C.c_ubyte*16)]

class PROPVARIANT(C.Structure):
    _fields_=[('vt',C.c_ushort),('reserved',C.c_ushort*3),('value',Value)]

PROPERTY_GUID='9f4c2855-9f79-4b39-a8d0-e1d42de1d5f3'
STORE_GUID='886d8eeb-8cf2-4446-8d02-cdba1dbdcf99'

def method(pointer,index,result,*types):
    table=C.cast(pointer,C.POINTER(C.POINTER(C.c_void_p))).contents
    return C.WINFUNCTYPE(result,C.c_void_p,*types)(table[index])

def check(result):
    if result<0:raise OSError('Windows identity HRESULT '+hex(result&0xffffffff))

def query(pointer,iid):
    result=C.c_void_p();check(method(pointer,0,C.c_long,C.POINTER(GUID),C.POINTER(C.c_void_p))(pointer,C.byref(GUID(iid)),C.byref(result)));return result

def release(pointer):
    if pointer:method(pointer,2,W.ULONG)(pointer)

def set_string(store,pid,text):
    key=PROPERTYKEY(GUID(PROPERTY_GUID),pid);value=PROPVARIANT()
    buffer=C.create_unicode_buffer(text);value.vt=31;value.value.pointer=C.cast(buffer,C.c_void_p).value
    check(method(store,6,C.c_long,C.POINTER(PROPERTYKEY),C.POINTER(PROPVARIANT))(store,C.byref(key),C.byref(value)))

def get_string(store,pid):
    key=PROPERTYKEY(GUID(PROPERTY_GUID),pid);value=PROPVARIANT()
    check(method(store,5,C.c_long,C.POINTER(PROPERTYKEY),C.POINTER(PROPVARIANT))(store,C.byref(key),C.byref(value)))
    try:return C.wstring_at(value.value.pointer) if value.vt==31 and value.value.pointer else ''
    finally:C.windll.ole32.PropVariantClear(C.byref(value))

def window_store(hwnd):
    store=C.c_void_p();shell=C.windll.shell32
    shell.SHGetPropertyStoreForWindow.argtypes=[W.HWND,C.POINTER(GUID),C.POINTER(C.c_void_p)]
    check(shell.SHGetPropertyStoreForWindow(hwnd,C.byref(GUID(STORE_GUID)),C.byref(store)));return store

def identify_window(hwnd,root,python):
    root=Path(root);icon=root/'assets/acervo-chess.ico'
    store=window_store(hwnd)
    try:
        # Relaunch metadata must precede the explicit AppUserModelID.
        set_string(store,2,subprocess.list2cmdline([str(python),str(root/'installed_entry.py')]))
        set_string(store,3,str(icon)+',0');set_string(store,4,'Coach Chess');set_string(store,5,APP_ID)
    finally:release(store)
    user=C.windll.user32
    user.LoadImageW.argtypes=[W.HINSTANCE,W.LPCWSTR,W.UINT,C.c_int,C.c_int,W.UINT];user.LoadImageW.restype=W.HANDLE
    user.SendMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];user.SendMessageW.restype=W.LPARAM
    # Shared icon handles remain valid for the lifetime of the browser window.
    for kind,size in ((0,32),(1,256)):
        handle=user.LoadImageW(None,str(icon),1,size,size,0x10|0x8000)
        if handle:user.SendMessageW(hwnd,0x80,kind,handle)


def browser_windows(profile,port):
    from desktop_exit import matching_browser_pids
    command="[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Process -Filter \"Name='msedge.exe' OR Name='chrome.exe'\" | Select-Object Name,ProcessId,CommandLine | ConvertTo-Json -Compress"
    shell=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    response=subprocess.run([str(shell),'-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=8,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=True)
    records=json.loads(response.stdout or '[]');records=[records] if isinstance(records,dict) else records
    pids=matching_browser_pids(records,profile,port);windows=[]
    user=C.windll.user32;callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    user.EnumWindows.argtypes=[callback,W.LPARAM];user.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];user.IsWindowVisible.argtypes=[W.HWND]
    @callback
    def visit(hwnd,_):
        pid=W.DWORD();user.GetWindowThreadProcessId(hwnd,C.byref(pid))
        if pid.value in pids and user.IsWindowVisible(hwnd):windows.append(hwnd)
        return True
    user.EnumWindows(visit,0);return windows


def apply_to_browser(profile,url,root,python):
    if os.name!='nt':return
    from urllib.parse import urlparse
    initialized=C.windll.ole32.CoInitializeEx(None,2)>=0
    try:
        for _attempt in range(5):
            windows=browser_windows(Path(profile).resolve(),urlparse(url).port)
            if windows:
                for hwnd in windows:identify_window(hwnd,root,python)
                # Edge may finish its own taskbar initialization after first paint.
                time.sleep(1)
                for hwnd in windows:identify_window(hwnd,root,python)
                return
            time.sleep(.5)
    except (OSError,ValueError,subprocess.SubprocessError):return
    finally:
        if initialized:C.windll.ole32.CoUninitialize()


def repair_shortcut(path,root,python):
    """Preserve shortcut settings; touch only verified Coach Chess launchers."""
    link=C.c_void_p();ole=C.windll.ole32
    check(ole.CoCreateInstance(C.byref(GUID('00021401-0000-0000-c000-000000000046')),None,1,C.byref(GUID('000214f9-0000-0000-c000-000000000046')),C.byref(link)))
    persist=store=None
    try:
        persist=query(link,'0000010b-0000-0000-c000-000000000046')
        check(method(persist,5,C.c_long,W.LPCWSTR,W.DWORD)(persist,str(path),2))
        target=C.create_unicode_buffer(32768);arguments=C.create_unicode_buffer(32768)
        check(method(link,3,C.c_long,W.LPWSTR,C.c_int,C.c_void_p,W.DWORD)(link,target,len(target),None,0))
        check(method(link,10,C.c_long,W.LPWSTR,C.c_int)(link,arguments,len(arguments)))
        if Path(target.value).resolve()!=Path(python).resolve() or arguments.value.strip('"')!=str(Path(root)/'installed_entry.py'):return False
        store=query(link,STORE_GUID);set_string(store,5,APP_ID)
        check(method(link,17,C.c_long,W.LPCWSTR,C.c_int)(link,str(Path(root)/'assets/acervo-chess.ico'),0))
        check(method(store,7,C.c_long)(store));check(method(persist,6,C.c_long,W.LPCWSTR,W.BOOL)(persist,str(path),True));return True
    finally:release(store);release(persist);release(link)


def repair_shortcuts(root=None,python=None):
    if os.name!='nt':return 0
    root=Path(root or Path(__file__).parent);python=Path(python or sys.executable).with_name('pythonw.exe')
    folders=[Path(os.environ.get('PUBLIC',r'C:\Users\Public'))/'Desktop',Path(os.environ.get('PROGRAMDATA',r'C:\ProgramData'))/'Microsoft/Windows/Start Menu/Programs',Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs',Path(os.environ['APPDATA'])/'Microsoft/Internet Explorer/Quick Launch/User Pinned/TaskBar',Path.home()/'Desktop',Path.home()/'OneDrive/Desktop',Path.home()/'OneDrive/Área de Trabalho']
    initialized=C.windll.ole32.CoInitializeEx(None,2)>=0
    try:
        count=0
        for folder in folders:
            for path in folder.rglob('Coach Chess.lnk') if folder.is_dir() else []:
                count+=int(repair_shortcut(path,root,python))
        return count
    finally:
        if initialized:C.windll.ole32.CoUninitialize()

if __name__=='__main__':print('Atalhos identificados:',repair_shortcuts())
