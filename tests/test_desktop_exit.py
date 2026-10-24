import json
from types import SimpleNamespace
from pathlib import Path
import desktop_exit


def test_only_the_dedicated_profile_and_own_app_port_can_close():
    profile=Path('C:/Users/Test User/Coach Chess/browser-profile')
    command=f'edge.exe "--user-data-dir={profile}" --app=http://127.0.0.1:8501/?view=aberturas --start-fullscreen'
    rows=[dict(Name='msedge.exe',ProcessId=21,CommandLine=command),
          dict(Name='chrome.exe',ProcessId=22,CommandLine=command.replace('8501','8502')),
          dict(Name='msedge.exe',ProcessId=23,CommandLine=command.replace('browser-profile','personal-profile')),
          dict(Name='other.exe',ProcessId=24,CommandLine=command),
          dict(Name='msedge.exe',ProcessId=25,CommandLine=command.replace('--app=','--unused=')),
          dict(Name='msedge.exe',ProcessId=26,CommandLine=command.replace('browser-profile','browser-profile-copy'))]
    assert desktop_exit.matching_browser_pids(rows,profile,8501)=={21}


def test_record_requires_this_running_server(tmp_path,monkeypatch):
    monkeypatch.setattr(desktop_exit.platform,'system',lambda:'Windows')
    monkeypatch.setattr(desktop_exit,'desktop_state',lambda:tmp_path)
    monkeypatch.setattr(desktop_exit.os,'getpid',lambda:123)
    path=tmp_path/'server.json'
    path.write_text(json.dumps(dict(pid=124,port=8501)))
    assert desktop_exit.desktop_record() is None
    path.write_text(json.dumps(dict(pid=123,port=8501)))
    assert desktop_exit.desktop_record()['port']==8501


def test_close_posts_only_to_matching_app_windows(tmp_path,monkeypatch):
    monkeypatch.setattr(desktop_exit,'desktop_record',lambda:dict(port=8501))
    monkeypatch.setattr(desktop_exit,'desktop_state',lambda:tmp_path)
    profile=(tmp_path/'browser-profile').resolve()
    records=[dict(Name='msedge.exe',ProcessId=77,CommandLine=f'edge.exe "--user-data-dir={profile}" --app=http://127.0.0.1:8501/?view=aberturas')]
    monkeypatch.setattr(desktop_exit.subprocess,'run',lambda *a,**kw:SimpleNamespace(stdout=json.dumps(records)))
    called=[]
    monkeypatch.setattr(desktop_exit,'_close_windows',lambda pids:called.append(pids) or True)
    assert desktop_exit.close_desktop() is True
    assert called==[{77}]
    monkeypatch.setattr(desktop_exit,'desktop_record',lambda:None)
    assert desktop_exit.close_desktop() is False
    assert called==[{77}]


def test_close_button_is_available_without_logging_out(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(desktop_exit,'desktop_record',lambda:dict(port=8501))
    monkeypatch.setattr(st,'context',SimpleNamespace(ip_address='127.0.0.1'))
    called=[]
    monkeypatch.setattr(desktop_exit,'close_desktop',lambda:called.append(True) or True)
    app=AppTest.from_string('from desktop_exit import render_exit_button\nrender_exit_button()').run()
    assert not app.exception
    app.button(key='desktop_exit_button').click().run()
    assert called==[True] and not app.exception


def test_sidebar_exit_is_visible_for_desktop_context_without_reported_ip(monkeypatch):
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(desktop_exit,'desktop_record',lambda:dict(port=8501))
    monkeypatch.setattr(st,'context',SimpleNamespace(ip_address=None))
    called=[]
    monkeypatch.setattr(desktop_exit,'close_desktop',lambda:called.append(True) or True)
    app=AppTest.from_string('import streamlit as st\nfrom desktop_exit import render_exit_button\nwith st.sidebar:render_exit_button(in_sidebar=True)').run()
    assert app.sidebar.button[0].label=='Fechar aplicativo'
    app.sidebar.button[0].click().run()
    assert called==[True] and not app.exception
