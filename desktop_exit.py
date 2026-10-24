"""Gracefully close only this installation's dedicated desktop window."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import platform
import re
import subprocess

from desktop_launcher import desktop_state


def desktop_record():
    if platform.system()!='Windows': return None
    try:
        record=json.loads((desktop_state()/'server.json').read_text(encoding='utf-8'))
        if int(record['pid'])!=os.getpid() or not 1024<=int(record['port'])<=65535: return None
        return record
    except (OSError,ValueError,TypeError,KeyError):
        return None


def matching_browser_pids(records,profile,port):
    """Require both our dedicated profile and our own loopback app URL."""
    profile_arg=re.compile(r'(?:^|\s)--user-data-dir='+re.escape(str(profile))+r'(?=\s--|$)',re.IGNORECASE)
    url_arg=re.compile(r'(?:^|\s)--app=http://127\.0\.0\.1:'+str(int(port))+r'/(?=\S*\s|\S*$)',re.IGNORECASE)
    result=set()
    for record in records:
        if record.get('Name','').lower() not in ('msedge.exe','chrome.exe'): continue
        command=(record.get('CommandLine') or '').replace('"','')
        pid=record.get('ProcessId')
        if isinstance(pid,int) and pid>0 and profile_arg.search(command) and url_arg.search(command): result.add(pid)
    return result


def _close_windows(pids):
    user32=ctypes.WinDLL('user32',use_last_error=True)
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user32.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    user32.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes=[wintypes.HWND]
    user32.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    closed=[]
    @callback_type
    def visit(window,_):
        pid=wintypes.DWORD()
        user32.GetWindowThreadProcessId(window,ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(window):
            if user32.PostMessageW(window,0x0010,0,0): closed.append(window) # WM_CLOSE
        return True
    user32.EnumWindows(visit,0)
    return bool(closed)


def close_desktop():
    record=desktop_record()
    if not record: return False
    shell=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    command="[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); Get-CimInstance Win32_Process -Filter \"Name = 'msedge.exe' OR Name = 'chrome.exe'\" | Select-Object Name,ProcessId,CommandLine | ConvertTo-Json -Compress"
    try:
        response=subprocess.run([str(shell),'-NoProfile','-NonInteractive','-Command',command],
            capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=8,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=True)
        records=json.loads(response.stdout or '[]')
        if isinstance(records,dict): records=[records]
        pids=matching_browser_pids(records,(desktop_state()/'browser-profile').resolve(),record['port'])
        return _close_windows(pids) if pids else False
    except (OSError,ValueError,TypeError,AttributeError,subprocess.SubprocessError):
        return False


def render_exit_button(in_sidebar=False):
    import streamlit as st
    if not desktop_record() or st.context.ip_address not in (None,'127.0.0.1','::1'): return
    if in_sidebar:
        if st.button('Fechar aplicativo',icon=':material/power_settings_new:',key='desktop_exit_sidebar',width='stretch'):
            if not close_desktop():st.warning('Não foi possível fechar a janela. Use Alt+F4.')
        return
    st.html('''<style>.st-key-desktop_exit{position:fixed;right:18px;top:12px;width:auto;z-index:100002}
    .st-key-question_launcher{right:154px!important}
    .st-key-desktop_exit button{min-height:34px;border-radius:10px;background:#211a19;color:#edc7c1;border:1px solid #69433d;font-size:12px}
    .st-key-desktop_exit button:hover{background:#412723;border-color:#bc786b}</style>''')
    with st.container(key='desktop_exit'):
        if st.button('Fechar app',icon=':material/close:',key='desktop_exit_button',help='Fechar a janela do Coach Chess'):
            if not close_desktop(): st.warning('Não foi possível fechar a janela. Use Alt+F4.')
