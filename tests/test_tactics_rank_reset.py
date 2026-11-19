from tactics_progress import record,summary,reset_rank,database


def test_reset_rank_preserves_history_and_other_accounts_and_is_idempotent(tmp_path,monkeypatch):
    monkeypatch.setenv('ACERVO_PREPARATION_DIR',str(tmp_path))
    record('owner','first','one','fork',True,True,15)
    record('other','second','two','pin',True,True,10)
    record('owner','miss','three','fork',False,False)
    before=summary('owner')
    assert reset_rank('owner','explicit-reset')
    after=summary('owner')
    assert after['xp']==0 and after['rank']=='Bronze 1'
    for field in ('attempts','hits','errors','solved','average','recent','known'):
        assert after[field]==before[field]
    assert summary('other')['xp']==5
    assert record('owner','repeat','one','fork',True,True,15)==0
    assert record('owner','new','four','fork',True,True,15)==5
    assert not reset_rank('owner','explicit-reset')
    assert summary('owner')['xp']==5
    with database() as db:
        assert db.execute('SELECT previous_points FROM rank_resets WHERE owner=?',('owner',)).fetchone()[0]==5
