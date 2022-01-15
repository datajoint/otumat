from otumat.watch import WatchAgent


def test_watch_agent():
    test_watch_agent = WatchAgent('/test_general.py', '../main/test.sh', [])

    assert isinstance(test_watch_agent, WatchAgent)
