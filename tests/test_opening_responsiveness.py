from pathlib import Path

from test_browser_components import browser_page, mount
from test_opening_training_ui import repertoire_server


def test_transition_is_one_shot_and_inactive_while_thinking(browser_page):
    page = browser_page
    mount(page, 'opening_transition.py', {'active': False, 'revision': 'idle', 'delay': 30})
    page.wait_for_timeout(100)
    assert page.evaluate('window.events') == []
    page.evaluate("()=>{window.render({active:true,revision:'reply:1',delay:30});}")
    page.wait_for_function('window.events.length === 1')
    page.wait_for_timeout(100)
    assert page.evaluate('window.events') == [{'key': 'tick', 'value': 'reply:1'}]
    page.evaluate("window.cancelTimer=window.render({active:true,revision:'reply:2',delay:50});window.cancelTimer()")
    page.wait_for_timeout(100)
    assert page.evaluate('window.events.length') == 1


