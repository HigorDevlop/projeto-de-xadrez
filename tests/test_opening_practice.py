from copy import deepcopy
from datetime import timedelta

from streamlit.testing.v1 import AppTest
import pytest
import sys


@pytest.fixture(autouse=True)
def isolated_components():
    modules = ("opening_home_ui", "opening_practice", "opening_catalog_ui", "opening_training_ui", "interactive_board", "preparation_ui", "opening_transition", "opening_course_ui")
    for name in modules:
        sys.modules.pop(name, None)
    yield
    for name in modules:
        sys.modules.pop(name, None)

from opening_training_state import create_repertoire_plan, session_for
from preparation_state import load_plan, save_plan, today


def test_opening_practice_save_does_not_replace_preparation(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    prep = create_repertoire_plan('player', ['london'], today(), today()+timedelta(days=6))
    practice = create_repertoire_plan('player', ['caro'], today(), today())
    save_plan(prep)
    save_plan(practice, namespace='openings')
    assert load_plan('player') == prep
    assert load_plan('player', namespace='openings') == practice


def test_free_practice_card_starts_without_extra_confirmation(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    app = AppTest.from_string('''
from types import SimpleNamespace
import streamlit as st
import opening_practice

def click_catalog(plan, on_select, **kwargs):
    st.session_state.openings_home = SimpleNamespace(select={'id':'caro'})
    on_select()

opening_practice.opening_home = click_catalog
opening_practice.render_opening_practice('practice-test')
''', default_timeout=20).run()
    app.run()
    assert not app.exception
    assert app.session_state.openings_plan['repertoire_ids'] == ['caro']
    assert load_plan('practice-test') is None
    assert load_plan('practice-test', namespace='openings') is not None
    assert 'Todas as aberturas' in [b.label for b in app.button]
    assert 'Treinar' in [b.label for b in app.button]
    assert 'Aprender com setas' not in [b.label for b in app.button]
    next(b for b in app.button if b.label == 'Treinar').click().run()
    assert not app.exception
    assert app.session_state.openings_active
    assert any(b.label == 'Voltar ao curso' for b in app.button)


def test_free_practice_resumes_an_unfinished_previous_day(tmp_path, monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR', str(tmp_path))
    previous = today()-timedelta(days=1)
    plan = create_repertoire_plan('practice-resume', ['italian'], previous, previous)
    session = session_for(plan, previous)
    session.update(ply=2, history=['e2e4', 'e7e5'])
    saved = deepcopy(session)
    save_plan(plan, namespace='openings')
    app = AppTest.from_string('''
from opening_practice import render_opening_practice
render_opening_practice('practice-resume')
''', default_timeout=20).run()
    assert not app.exception
    restored = session_for(app.session_state.openings_plan)
    assert restored['history'] == saved['history']
    assert restored['token'] == saved['token']
    assert restored['day'] == str(today())
