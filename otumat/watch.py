from . import watch_file


class WatchAgent():
    def __init__(self, watchfile, watch_script, watch_args):
        watch = watch_file.OnMyWatch(watchfile, watch_script, watch_args)
        watch.run()
