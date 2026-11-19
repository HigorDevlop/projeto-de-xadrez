import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import os
import pytest
import desktop_identity as identity

pytestmark=pytest.mark.skipif(os.name!='nt',reason='Windows taskbar integration')


def test_window_identity_icon_and_relaunch_use_the_installed_entry():
    root=Path(identity.__file__).parent
    user=C.windll.user32;user.CreateWindowExW.restype=W.HWND
    user.CreateWindowExW.argtypes=[W.DWORD,W.LPCWSTR,W.LPCWSTR,W.DWORD,C.c_int,C.c_int,C.c_int,C.c_int,W.HWND,W.HMENU,W.HINSTANCE,C.c_void_p]
    user.DestroyWindow.argtypes=[W.HWND]
    hwnd=user.CreateWindowExW(0,'STATIC','Coach identity test',0,0,0,10,10,None,None,None,None)
    assert hwnd
    C.windll.ole32.CoInitializeEx(None,2)
    try:
        identity.identify_window(hwnd,root,Path(os.sys.executable))
        store=identity.window_store(hwnd)
        try:
            assert identity.get_string(store,5)==identity.APP_ID
            assert identity.get_string(store,4)=='Coach Chess'
            assert 'installed_entry.py' in identity.get_string(store,2)
            assert 'acervo-chess.ico' in identity.get_string(store,3)
        finally:identity.release(store)
        user.SendMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];user.SendMessageW.restype=W.LPARAM
        assert user.SendMessageW(hwnd,0x7f,1,0)
    finally:user.DestroyWindow(hwnd);C.windll.ole32.CoUninitialize()


def test_shortcut_repair_sets_identity_without_changing_launch_target(tmp_path):
    C.windll.ole32.CoInitializeEx(None,2)
    root=Path(identity.__file__).parent;python=Path(os.sys.executable).with_name('pythonw.exe');path=tmp_path/'Coach Chess.lnk'
    link=C.c_void_p();persist=None
    try:
        identity.check(C.windll.ole32.CoCreateInstance(C.byref(identity.GUID('00021401-0000-0000-c000-000000000046')),None,1,C.byref(identity.GUID('000214f9-0000-0000-c000-000000000046')),C.byref(link)))
        identity.check(identity.method(link,20,C.c_long,W.LPCWSTR)(link,str(python)))
        identity.check(identity.method(link,11,C.c_long,W.LPCWSTR)(link,'"'+str(root/'installed_entry.py')+'"'))
        persist=identity.query(link,'0000010b-0000-0000-c000-000000000046')
        identity.check(identity.method(persist,6,C.c_long,W.LPCWSTR,W.BOOL)(persist,str(path),True))
        assert identity.repair_shortcut(path,root,python)
        identity.release(persist);identity.release(link);persist=None;link=C.c_void_p()
        identity.check(C.windll.ole32.CoCreateInstance(C.byref(identity.GUID('00021401-0000-0000-c000-000000000046')),None,1,C.byref(identity.GUID('000214f9-0000-0000-c000-000000000046')),C.byref(link)))
        persist=identity.query(link,'0000010b-0000-0000-c000-000000000046')
        identity.check(identity.method(persist,5,C.c_long,W.LPCWSTR,W.DWORD)(persist,str(path),0))
        store=identity.query(link,identity.STORE_GUID)
        try:assert identity.get_string(store,5)==identity.APP_ID
        finally:identity.release(store)
        assert not identity.repair_shortcut(path,tmp_path,python)
    finally:identity.release(persist);identity.release(link);C.windll.ole32.CoUninitialize()
