import base64
from pathlib import Path
from playwright.sync_api import expect
from test_browser_components import browser_page,mount

ROOT=Path(__file__).resolve().parents[1]


def data(text='Este lance controla o centro.',label='Após 1. e4'):
    return dict(notes=[dict(label=label,text=text)],image='data:image/webp;base64,'+base64.b64encode((ROOT/'assets/bobby-fischer-instructor.webp').read_bytes()).decode())


def speech_mock(page,voices):
    page.evaluate('''voices=>{window.spoken=[];window.cancellations=0;window.voiceListeners=[];
    window.SpeechSynthesisUtterance=class{constructor(text){this.text=text;}};
    Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{getVoices:()=>voices,
    speak:u=>window.spoken.push(u),cancel:()=>window.cancellations++,
    addEventListener:(name,fn)=>window.voiceListeners.push(fn),removeEventListener:(name,fn)=>{window.voiceListeners=window.voiceListeners.filter(v=>v!==fn);}}});}''',voices)


def test_local_voice_reads_exact_teacher_text_and_stops_when_the_move_changes(browser_page):
    page=browser_page;page.set_viewport_size(dict(width=560,height=750))
    speech_mock(page,[dict(name='Voz online',lang='pt-BR',localService=False),dict(name='Voz local',lang='pt-BR',localService=True)])
    mount(page,'classroom_fischer_instructor.py',data())
    expect(page.get_by_text('Este lance controla o centro.',exact=True)).to_be_visible()
    expect(page.locator('img')).to_have_js_property('complete',True)
    assert page.locator('img').evaluate('(image)=>image.naturalWidth>0')
    page.get_by_role('button',name='Ouvir explicação',exact=False).click()
    assert page.evaluate('spoken[0].text')=='Este lance controla o centro.'
    assert page.evaluate('spoken[0].voice.name')=='Voz local'
    expect(page.locator('.fischer-coach')).to_have_class('fischer-coach speaking')
    page.screenshot(path='tests/artifacts/fischer-commentary-coach.png',full_page=True)
    page.evaluate('(data)=>window.render(data)',data('Desenvolva o cavalo.','Após 1... e5'))
    assert page.evaluate('cancellations')>=1
    expect(page.locator('.fischer-coach')).to_have_class('fischer-coach')
    assert page.evaluate('spoken.length')==1
    page.get_by_label('Ler automaticamente',exact=True).check()
    assert page.evaluate('spoken.at(-1).text')=='Desenvolva o cavalo.'
    page.evaluate('(data)=>window.render(data)',data('Proteja o rei.','Após 2. Nf3'))
    assert page.evaluate('spoken.at(-1).text')=='Proteja o rei.'
    page.get_by_role('button',name='Parar',exact=False).click()
    expect(page.locator('.fischer-coach')).to_have_class('fischer-coach')
    page.set_viewport_size(dict(width=360,height=750))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.get_by_role('button',name='Ouvir explicação',exact=False).click()
    before=page.evaluate('cancellations')
    page.evaluate('(data)=>{const cleanup=window.render(data);document.querySelector("main").remove();cleanup();}',data('Proteja o rei.','Após 2. Nf3'))
    page.wait_for_function('(before)=>cancellations>before',arg=before)


def test_online_only_voices_are_not_used_and_commentary_is_not_rendered_as_html(browser_page):
    page=browser_page;speech_mock(page,[dict(name='Online',lang='pt-BR',localService=False)])
    text='<img src=x onerror="throw Error(1)">'
    mount(page,'classroom_fischer_instructor.py',data(text))
    expect(page.get_by_role('button',name='Ouvir explicação',exact=False)).to_be_disabled()
    expect(page.locator('.commentary p')).to_have_text(text)
    expect(page.locator('.commentary img')).to_have_count(0)
    assert page.evaluate('spoken.length')==0
