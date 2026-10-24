import desktop_launcher


def test_each_open_requests_fullscreen_in_the_same_dedicated_profile(tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setenv('COACH_DESKTOP_STATE',str(tmp_path/'desktop'))
    monkeypatch.setattr(desktop_launcher,'start_server',lambda:('http://127.0.0.1:8501',None))
    monkeypatch.setattr(desktop_launcher,'browser_executable',lambda:tmp_path/'msedge.exe')
    monkeypatch.setattr(desktop_launcher.subprocess,'Popen',lambda args,**kwargs:calls.append(args))
    desktop_launcher.main()
    desktop_launcher.main()
    assert len(calls)==2
    for args in calls:
        assert '--start-fullscreen' in args and '--new-window' in args
        assert '--no-first-run' in args
        assert '--app=http://127.0.0.1:8501/?view=aberturas' in args
        assert '--user-data-dir='+str((tmp_path/'desktop/browser-profile').resolve()) in args
    assert calls[0]==calls[1]


def test_reopening_desktop_reuses_its_server_and_browser_storage_origin(tmp_path,monkeypatch):
    (tmp_path/'app.py').write_text("import streamlit as st\nst.write('isolated desktop test')\n",encoding='utf8')
    monkeypatch.setattr(desktop_launcher,'ROOT',tmp_path)
    url,process=desktop_launcher.start_server()
    try:
        reused,second=desktop_launcher.start_server()
        assert reused==url and second is None
        (tmp_path/'app.py').write_text("import streamlit as st\nst.write('updated desktop test')\n",encoding='utf8')
        updated,replacement=desktop_launcher.start_server()
        assert updated==url and replacement is not None
        process.wait(timeout=15)
        process=replacement
    finally:
        process.terminate()
        process.wait(timeout=15)
