from wave import Wave_write
from otumat.watch import WatchAgent


def test_watch_agent():
    test_watch_agent = WatchAgent('/test_general.py', '../main/test.sh', [])

    assert test_watch_agent.__class__ == WatchAgent
