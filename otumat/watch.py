import subprocess
from datetime import datetime
from watchdog.observers.polling import PollingObserver
from watchdog.events import FileSystemEventHandler


class OnMyWatch:
    def __init__(self, watch_file, watch_interval, watch_init, watch_script, watch_args):
        self.observer = PollingObserver(timeout=watch_interval)
        self.watch_directory = watch_file
        self.watch_init = watch_init
        self.watch_script = watch_script
        self.watch_args = watch_args


    def run(self):
        if self.watch_init:
            self.watch_args = subprocess.Popen(
                [self.watch_script, *self.watch_args],
                stdout=subprocess.PIPE).communicate()[0].decode('utf-8').split('\n')[:-1]
        event_handler = Handler(self.watch_directory, self.watch_script, self.watch_args)
        self.observer.schedule(event_handler, self.watch_directory, recursive=True)
        self.observer.start()
        try:
            self.observer.join()
        except KeyboardInterrupt:
            self.observer.stop()
            print("\nObserver Stopped")


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
            print(f'=== [{datetime.now().isoformat()}] \
                OTUMAT WATCH: {event.src_path} modified ===')
            self.watch_args = subprocess.Popen(
                [self.watch_script, *self.watch_args],
                stdout=subprocess.PIPE).communicate()[0].decode('utf-8').split('\n')[:-1]


class WatchAgent():
    def __init__(self, watch_file, watch_interval, watch_init, watch_script, watch_args):
        self.watch = OnMyWatch(watch_file, watch_interval, watch_init, watch_script,
                               watch_args)

    def run(self):
        self.watch.run()
