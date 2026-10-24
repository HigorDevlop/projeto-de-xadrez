from threading import Event
from concurrent.futures import ThreadPoolExecutor

from opening_reference_engine import Evaluations


def test_slow_engine_never_blocks_moves_and_obsolete_boards_are_cancelled(monkeypatch):
    started, release = Event(), Event()

    def slow(fen):
        started.set()
        release.wait(timeout=5)
        return '+0.18'

    monkeypatch.setattr('opening_reference_engine._calculate', slow)
    service = Evaluations()
    caller = ThreadPoolExecutor(max_workers=1)
    try:
        assert caller.submit(service.get, 'first-board').result(timeout=1) is None
        assert started.wait(timeout=1)
        assert service.get('obsolete-board') is None
        assert service.get('latest-board') is None
        assert 'obsolete-board' not in service.jobs
        assert len(service.jobs) == 2
        release.set()
        assert service.jobs['first-board'].result(timeout=1) == '+0.18'
        assert service.get('first-board') == '+0.18'
    finally:
        release.set()
        caller.shutdown(wait=True)
        service.executor.shutdown(wait=True)
