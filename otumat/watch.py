import subprocess
import time
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler
from pathlib import Path


class OnMyWatch:
    def __init__(self, watch_file, watch_script, watch_args):
        self.observer = PollingObserver(timeout=0)
        self.watch_directory = watch_file
        self.watch_script = watch_script
        self.watch_args = watch_args

    def run(self):
        event_handler = Handler(self.watch_directory, self.watch_script, self.watch_args)
        self.observer.schedule(event_handler, self.watch_directory, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            self.observer.stop()
            print("\nObserver Stopped")

        self.observer.join()


class Handler(FileSystemEventHandler):

    def __init__(self, watch_file, watch_script, watch_args):
        self.watch_file = watch_file
        self.watch_script = watch_script
        self.watch_args = watch_args

    def on_any_event(self, event):
        if event.is_directory:
            return None

        elif event.event_type == 'modified':
            # Event is modified, you can process it now
            print("Watchdog received modified event - % s." % event.src_path)
            file_extension = Path(self.watch_script).suffix
            if file_extension == '.sh':
                self.watch_args = subprocess.Popen(
                    ['sh', self.watch_script, *self.watch_args],
                    stdout=subprocess.PIPE).communicate()[0].decode('utf-8').split('\n')[:-1]
            # elif file_extension == '.bat':


class WatchAgent():
    def __init__(self, watch_file, watch_script, watch_args):
        self.watch = OnMyWatch(watch_file, watch_script, watch_args)

    def run(self):
        self.watch.run()
